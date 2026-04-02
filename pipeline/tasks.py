"""
Celery pipeline tasks — scrape → filter → (enrich → draft in tasks_enrichment.py)

Filter pipeline (3 stages):
  Stage 1  Keyword pre-filter          cheap, fast, high recall
  Stage 2  Per-review LLM              is this the CLINIC'S fault? (CONFIRMED/UNCERTAIN/NO)
  Stage 3  Clinic-level LLM analysis   is this a SYSTEMIC pattern?

A clinic is QUALIFIED only if Stage 3 returns is_systemic=True with confidence >= 0.65.

Rate-based guard (applied before Stage 3):
  If a clinic has > 50 known reviews but fewer than 2 CONFIRMED complaints,
  the complaint rate is too low to be meaningful — filter out without LLM cost.
"""

import asyncio
import logging
from contextlib import contextmanager

from db.models import (
    CityRun, Clinic, Review, ClinicStatus, CityRunStatus,
    FlagReason,
)
from filter.keyword_filter import score_review, qualifies_for_llm
from filter.llm_filter import (
    ReviewVerdict,
    classify_reviews,
    analyze_clinic,
)
from pipeline.celery_app import celery_app
import config

log = logging.getLogger(__name__)

# Minimum confirmed complaints to proceed to clinic-level LLM
_MIN_CONFIRMED = 2
# If clinic has this many reviews, require at least _RATE_THRESHOLD complaint rate
_RATE_REVIEW_THRESHOLD = 50
_RATE_COMPLAINT_THRESHOLD = 0.01  # 1 % of total reviews
# Minimum confidence from clinic-level LLM to qualify
_MIN_CLINIC_CONFIDENCE = 0.65


@contextmanager
def SessionLocal():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def scrape_city_task(self, city_run_id: str) -> None:
    from scraper.playwright_scraper import scrape_city

    with SessionLocal() as db:
        run = db.query(CityRun).filter_by(id=city_run_id).first()
        if not run:
            return
        run.status = CityRunStatus.RUNNING
        city, state, max_reviews = run.city, run.state, run.max_reviews

    try:
        clinic_data_list = asyncio.run(scrape_city(city, state, max_reviews))
    except Exception as exc:
        with SessionLocal() as db:
            run = db.query(CityRun).filter_by(id=city_run_id).first()
            if run:
                run.status = CityRunStatus.FAILED
        raise self.retry(exc=exc)

    with SessionLocal() as db:
        run = db.query(CityRun).filter_by(id=city_run_id).first()
        if not run:
            return

        for cd in clinic_data_list:
            existing = db.query(Clinic).filter_by(place_id=cd.place_id).first()
            if existing:
                existing.city_run_id = city_run_id
                clinic = existing
            else:
                clinic = Clinic(
                    city_run_id=city_run_id,
                    name=cd.name,
                    address=cd.address,
                    city=cd.city,
                    state=cd.state,
                    zip=cd.zip,
                    phone=cd.phone,
                    website=cd.website,
                    google_maps_url=cd.google_maps_url,
                    place_id=cd.place_id,
                    overall_rating=cd.overall_rating,
                    total_reviews=cd.total_reviews,
                )
                db.add(clinic)
                db.flush()

            for rd in cd.reviews:
                db.add(Review(
                    clinic_id=clinic.id,
                    author=rd.author,
                    rating=rd.rating,
                    text=rd.text,
                    date=rd.date,
                ))

        run.total_clinics_found = len(clinic_data_list)

    filter_clinics_task.delay(city_run_id)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def filter_clinics_task(self, city_run_id: str) -> None:
    with SessionLocal() as db:
        clinics = (
            db.query(Clinic)
            .filter_by(city_run_id=city_run_id, status=ClinicStatus.SCRAPED)
            .all()
        )

        qualified_count = 0

        for clinic in clinics:
            review_texts = [r.text for r in clinic.reviews]

            # ── Stage 1: keyword pre-filter ───────────────────────────────────
            if not qualifies_for_llm(review_texts):
                clinic.status = ClinicStatus.FILTERED_OUT
                log.debug(f"{clinic.name}: filtered out at keyword stage")
                continue

            # Score individual reviews to find candidates for LLM
            keyword_candidates = []
            for review in clinic.reviews:
                s = score_review(review.text)
                if s.tier1_hits > 0 or s.tier2_hits > 0 or s.tier3_hits > 0:
                    review.keyword_matches = s.matched_keywords
                    keyword_candidates.append(review)

            # ── Stage 2: per-review LLM — is this the clinic's fault? ─────────
            try:
                classifications = classify_reviews([r.text for r in keyword_candidates])
            except Exception as exc:
                raise self.retry(exc=exc)

            confirmed_reviews: list[Review] = []
            uncertain_reviews: list[Review] = []

            for review, clf in zip(keyword_candidates, classifications):
                review.llm_reasoning = clf.reasoning

                if clf.verdict == ReviewVerdict.CONFIRMED:
                    review.insurance_flag = True
                    review.flag_reason = FlagReason.BOTH if review.keyword_matches else FlagReason.LLM
                    confirmed_reviews.append(review)

                elif clf.verdict == ReviewVerdict.UNCERTAIN:
                    review.flag_reason = FlagReason.KEYWORD
                    uncertain_reviews.append(review)

                else:
                    review.flag_reason = FlagReason.KEYWORD if review.keyword_matches else None

            # ── Rate-based guard ──────────────────────────────────────────────
            # Don't burn clinic-level LLM on clinics where complaint rate is
            # too low to be meaningful.
            confirmed_count = len(confirmed_reviews)
            total_known = clinic.total_reviews or len(clinic.reviews)

            if confirmed_count < _MIN_CONFIRMED:
                clinic.status = ClinicStatus.FILTERED_OUT
                log.info(f"{clinic.name}: only {confirmed_count} confirmed complaints — filtered out")
                continue

            if total_known >= _RATE_REVIEW_THRESHOLD:
                rate = confirmed_count / total_known
                if rate < _RATE_COMPLAINT_THRESHOLD:
                    clinic.status = ClinicStatus.FILTERED_OUT
                    log.info(
                        f"{clinic.name}: complaint rate {rate:.2%} below threshold "
                        f"({confirmed_count}/{total_known}) — filtered out"
                    )
                    continue

            # ── Stage 3: clinic-level systemic analysis ───────────────────────
            try:
                verdict = analyze_clinic(
                    clinic_name=clinic.name,
                    overall_rating=clinic.overall_rating,
                    total_reviews=clinic.total_reviews,
                    confirmed_reviews=[r.text for r in confirmed_reviews],
                    uncertain_reviews=[r.text for r in uncertain_reviews],
                )
            except Exception as exc:
                raise self.retry(exc=exc)

            log.info(
                f"{clinic.name}: systemic={verdict.is_systemic} "
                f"confidence={verdict.confidence:.2f} severity={verdict.severity} "
                f"— {verdict.pattern}"
            )

            if verdict.is_systemic and verdict.confidence >= _MIN_CLINIC_CONFIDENCE:
                clinic.status = ClinicStatus.QUALIFIED
                qualified_count += 1
            else:
                clinic.status = ClinicStatus.FILTERED_OUT

        run = db.query(CityRun).filter_by(id=city_run_id).first()
        if run:
            run.total_qualified = qualified_count

    log.info(f"Filter complete for run {city_run_id}: {qualified_count} clinics qualified")

    from pipeline.tasks_enrichment import enrich_clinics_task
    enrich_clinics_task.delay(city_run_id)
