import asyncio
from contextlib import contextmanager

from db.models import (
    CityRun, Clinic, Review, ClinicStatus, CityRunStatus,
    FlagReason,
)
from filter.keyword_filter import score_review, qualifies_for_llm
from filter.llm_filter import classify_reviews
from pipeline.celery_app import celery_app
import config


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
        clinic_data_list = asyncio.run(
            scrape_city(city, state, max_reviews)
        )
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
                # Reassign to current run so filter_clinics_task finds it
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

    # Chain to filter stage
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

            if not qualifies_for_llm(review_texts):
                clinic.status = ClinicStatus.FILTERED_OUT
                continue

            # Run keyword scoring on individual reviews
            candidate_reviews = []
            for review in clinic.reviews:
                score = score_review(review.text)
                if score.tier1_hits > 0 or score.tier2_hits > 0:
                    review.keyword_matches = score.matched_keywords
                    candidate_reviews.append(review)

            # LLM verification
            texts_to_classify = [r.text for r in candidate_reviews]
            try:
                verdicts = classify_reviews(texts_to_classify)
            except Exception as exc:
                raise self.retry(exc=exc)

            confirmed = 0
            for review, verdict in zip(candidate_reviews, verdicts):
                if verdict.is_insurance_complaint:
                    confirmed += 1
                    review.insurance_flag = True
                    review.llm_reasoning = verdict.reasoning
                    review.flag_reason = (
                        FlagReason.BOTH if review.keyword_matches else FlagReason.LLM
                    )
                else:
                    review.flag_reason = FlagReason.KEYWORD if review.keyword_matches else None

            if confirmed >= 2:
                clinic.status = ClinicStatus.QUALIFIED
                qualified_count += 1
            else:
                clinic.status = ClinicStatus.FILTERED_OUT

        run = db.query(CityRun).filter_by(id=city_run_id).first()
        if run:
            run.total_qualified = qualified_count

    # Chain to enrichment stage (implemented in Plan 03)
    from pipeline.tasks_enrichment import enrich_clinics_task
    enrich_clinics_task.delay(city_run_id)
