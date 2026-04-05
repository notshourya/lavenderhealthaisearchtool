"""
Celery pipeline tasks — scrape → filter → (enrich → draft in tasks_enrichment.py)

Filter pipeline (3 stages):
    Stage 1  Keyword pre-filter          cheap, fast, high recall
    Stage 2  Per-review LLM              insurer fault vs clinic fault vs shared
    Stage 3  Clinic-level LLM analysis   should we target this clinic for outreach?

A clinic is QUALIFIED once it has repeated insurer-fault complaints and is not
primarily explained by clinic-fault misconduct.

Rate-based guard (applied before Stage 3):
    If a clinic has sufficient review volume but a tiny confirmed-complaint rate,
    do not flag it for outreach even if a small number of complaints exist.
"""

import asyncio
import logging
import math
import re
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from db.models import (
    CityRun, Clinic, Review, ClinicStatus, CityRunStatus,
    FlagReason, FaultParty,
)
from filter.keyword_filter import score_review, qualifies_for_llm, infer_issue_category
from filter.llm_filter import (
    ReviewVerdict,
    classify_reviews,
    analyze_clinic,
)
from pipeline.celery_app import celery_app
import config

log = logging.getLogger(__name__)

# Qualification thresholds (configurable via environment).
_MIN_CONFIRMED = config.MIN_CONFIRMED_COMPLAINTS
_RATE_REVIEW_THRESHOLD = config.RATE_GUARD_MIN_REVIEWS
_RATE_COMPLAINT_THRESHOLD = config.COMPLAINT_RATE_THRESHOLD
_DEEP_STAGE_ONE = config.DEEP_SCRAPE_STAGE_ONE_REVIEWS
_DEEP_STAGE_TWO = config.DEEP_SCRAPE_STAGE_TWO_REVIEWS
_DEEP_STAGE_ONE_MIN_KEYWORD_REVIEWS = config.DEEP_SCRAPE_STAGE_ONE_MIN_KEYWORD_REVIEWS
_DEEP_STAGE_TWO_MIN_KEYWORD_REVIEWS = config.DEEP_SCRAPE_STAGE_TWO_MIN_KEYWORD_REVIEWS
_RECENT_REVIEW_WINDOW_DAYS = config.RECENT_REVIEW_WINDOW_DAYS
_RECENT_REVIEW_MIN_INSURER_COMPLAINTS = config.RECENT_REVIEW_MIN_INSURER_COMPLAINTS
_MIN_UNIQUE_INSURER_REVIEWERS = config.MIN_UNIQUE_INSURER_REVIEWERS
_MIN_DOMINANT_ISSUE_CATEGORY_REVIEWS = config.MIN_DOMINANT_ISSUE_CATEGORY_REVIEWS
_RECENT_CLUSTER_MIN_MONTH_BUCKET_REVIEWS = config.RECENT_CLUSTER_MIN_MONTH_BUCKET_REVIEWS
_QUALIFICATION_PROFILE = config.QUALIFICATION_PROFILE

_SCORE_THRESHOLD_BY_PROFILE = {
    "strict": config.SCORE_THRESHOLD_STRICT,
    "balanced": config.SCORE_THRESHOLD_BALANCED,
    "recall": config.SCORE_THRESHOLD_RECALL,
}

_SCORE_WEIGHT_INSURER = config.SCORE_WEIGHT_INSURER
_SCORE_WEIGHT_RATE = config.SCORE_WEIGHT_RATE
_SCORE_WEIGHT_RECENCY = config.SCORE_WEIGHT_RECENCY
_SCORE_WEIGHT_UNIQUENESS = config.SCORE_WEIGHT_UNIQUENESS

_SHARED_REVIEW_WEIGHT = config.SHARED_REVIEW_WEIGHT
_EFFECTIVE_SIGNAL_CAP = config.EFFECTIVE_SIGNAL_CAP
_RATE_SCORE_CAP_MULTIPLIER = config.RATE_SCORE_CAP_MULTIPLIER
_CONFIDENCE_EVIDENCE_LOG_CAP = config.CONFIDENCE_EVIDENCE_LOG_CAP
_CONFIDENCE_EVIDENCE_WEIGHT = config.CONFIDENCE_EVIDENCE_WEIGHT
_CONFIDENCE_VOLUME_WEIGHT = config.CONFIDENCE_VOLUME_WEIGHT
_FINAL_SCORE_DAMP_BASE = config.FINAL_SCORE_DAMP_BASE
_FINAL_SCORE_DAMP_SCALE = config.FINAL_SCORE_DAMP_SCALE
_ENABLE_GRAY_ZONE_VALIDATION = config.ENABLE_GRAY_ZONE_VALIDATION
_GRAY_ZONE_VALIDATION_BAND = config.GRAY_ZONE_VALIDATION_BAND


def _replace_clinic_reviews(db, clinic: Clinic, reviews_data) -> None:
    existing_reviews = list(clinic.reviews)
    for review in existing_reviews:
        db.delete(review)
    db.flush()

    for review_data in reviews_data:
        db.add(Review(
            clinic_id=clinic.id,
            author=review_data.author,
            rating=review_data.rating,
            text=review_data.text,
            date=review_data.date,
        ))
    db.flush()


def _keyword_signal_review_count(review_texts: list[str]) -> int:
    count = 0
    for review_text in review_texts:
        score = score_review(review_text)
        if score.tier1_hits > 0 or score.tier2_hits > 0 or score.tier3_hits > 0:
            count += 1
    return count


def _screening_review_sort_key(review: Review) -> tuple[int, float]:
    rating = review.rating if review.rating is not None else 6
    review_date = review.date or datetime(1970, 1, 1, tzinfo=timezone.utc)
    return (rating, -review_date.timestamp())


def _select_intelligence_screening_reviews(reviews: list[Review], limit: int = 6) -> list[Review]:
    if not reviews:
        return []
    ordered_reviews = sorted(reviews, key=_screening_review_sort_key)
    return ordered_reviews[:limit]


def _has_intelligence_screening_signal(classifications) -> bool:
    insurer_reviews = 0
    shared_reviews = 0

    for classification in classifications:
        if classification.verdict == ReviewVerdict.INSURER and classification.confidence >= 0.5:
            insurer_reviews += 1
        elif classification.verdict == ReviewVerdict.SHARED and classification.confidence >= 0.65:
            shared_reviews += 1

    return insurer_reviews >= 1 or shared_reviews >= 2


def _adaptive_review_limits(max_reviews: int) -> list[int]:
    if max_reviews <= 0:
        limits: list[int] = []
        for candidate in (_DEEP_STAGE_ONE, _DEEP_STAGE_TWO):
            if candidate > 0 and candidate not in limits:
                limits.append(candidate)
        limits.append(0)
        return limits

    limits: list[int] = []
    for candidate in (_DEEP_STAGE_ONE, _DEEP_STAGE_TWO, max_reviews):
        bounded = min(max_reviews, candidate)
        if bounded > 0 and bounded not in limits:
            limits.append(bounded)
    return limits


def _scrape_clinic_reviews_sync(google_maps_url: str, max_reviews: int):
    from scraper.playwright_scraper import scrape_clinic_reviews

    return asyncio.run(
        scrape_clinic_reviews(
            google_maps_url,
            max_reviews=max_reviews,
        )
    )


def _run_adaptive_deep_scrape(clinic: Clinic, max_reviews: int):
    last_result = None
    limits = _adaptive_review_limits(max_reviews)
    clinic_label = getattr(clinic, "name", None) or getattr(clinic, "id", "unknown-clinic")
    for idx, limit in enumerate(limits):
        result = _scrape_clinic_reviews_sync(clinic.google_maps_url, limit)
        last_result = result

        keyword_review_count = _keyword_signal_review_count([review.text for review in result.reviews])
        log.info(
            f"[DEEP_SCRAPE] {clinic_label}: stage {idx + 1}/{len(limits)} "
            f"limit={limit}, reviews={len(result.reviews)}, keyword_signal_reviews={keyword_review_count}"
        )

        is_last_stage = idx == len(limits) - 1
        min_keyword_reviews_to_expand = (
            _DEEP_STAGE_ONE_MIN_KEYWORD_REVIEWS if idx == 0 else _DEEP_STAGE_TWO_MIN_KEYWORD_REVIEWS
        )
        if keyword_review_count < min_keyword_reviews_to_expand or is_last_stage:
            return result, limit, keyword_review_count

    return last_result, 0, 0


def _count_recent_reviews(reviews: list[Review], window_days: int, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)
    count = 0
    for review in reviews:
        if review.date is None:
            continue
        review_date = review.date
        if review_date.tzinfo is None:
            review_date = review_date.replace(tzinfo=timezone.utc)
        if review_date >= cutoff:
            count += 1
    return count


def _normalize_author(author: str | None) -> str | None:
    if not author:
        return None
    normalized = re.sub(r"\s+", " ", author.strip().lower())
    return normalized or None


def _unique_named_reviewer_count(reviews: list[Review]) -> int:
    return len({
        normalized
        for normalized in (_normalize_author(getattr(review, "author", None)) for review in reviews)
        if normalized is not None
    })


def _issue_category_counts(reviews: list[Review]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for review in reviews:
        category = getattr(review, "issue_category", None)
        if not category:
            continue
        key = category.value if hasattr(category, "value") else str(category)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _dominant_issue_category(reviews: list[Review]) -> tuple[str | None, int]:
    counts = _issue_category_counts(reviews)
    if not counts:
        return None, 0
    category, count = max(counts.items(), key=lambda item: item[1])
    return category, count


def _recent_month_cluster_peak(reviews: list[Review], window_days: int, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)
    buckets: dict[str, int] = {}

    for review in reviews:
        review_date = getattr(review, "date", None)
        if review_date is None:
            continue
        if review_date.tzinfo is None:
            review_date = review_date.replace(tzinfo=timezone.utc)
        if review_date < cutoff:
            continue
        bucket = review_date.strftime("%Y-%m")
        buckets[bucket] = buckets.get(bucket, 0) + 1

    return max(buckets.values(), default=0)


def _passes_recent_cluster_override(
    insurer_reviews: list[Review],
    clinic_fault_reviews: list[Review],
) -> bool:
    recent_insurer_count = _count_recent_reviews(insurer_reviews, _RECENT_REVIEW_WINDOW_DAYS)
    if recent_insurer_count < _RECENT_REVIEW_MIN_INSURER_COMPLAINTS:
        return False

    recent_clinic_fault_count = _count_recent_reviews(clinic_fault_reviews, _RECENT_REVIEW_WINDOW_DAYS)
    unique_insurer_reviewers = _unique_named_reviewer_count(insurer_reviews)
    _, dominant_issue_count = _dominant_issue_category(insurer_reviews)
    recent_cluster_peak = _recent_month_cluster_peak(insurer_reviews, _RECENT_REVIEW_WINDOW_DAYS)

    return (
        recent_insurer_count > recent_clinic_fault_count
        and unique_insurer_reviewers >= _MIN_UNIQUE_INSURER_REVIEWERS
        and dominant_issue_count >= _MIN_DOMINANT_ISSUE_CATEGORY_REVIEWS
        and recent_cluster_peak >= _RECENT_CLUSTER_MIN_MONTH_BUCKET_REVIEWS
    )


def _is_quota_exhausted_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(token in text for token in ("429", "resource_exhausted", "quota", "toomanyrequests"))


def _skip_clinic_on_gemini_quota(clinic: Clinic, stage_label: str) -> None:
    clinic.status = ClinicStatus.FILTERED_OUT
    log.error(
        f"{clinic.name}: Gemini quota exhausted during {stage_label}; "
        "clinic skipped for this run"
    )


def _is_obvious_target(
    insurer_count: int,
    clinic_fault_count: int,
    total_known: int,
    unique_insurer_reviewers: int,
    dominant_issue_count: int,
    recency_override: bool,
) -> bool:
    if insurer_count < _MIN_CONFIRMED:
        return False

    if clinic_fault_count > insurer_count:
        return False

    if total_known >= _RATE_REVIEW_THRESHOLD:
        rate = insurer_count / total_known
        if rate < _RATE_COMPLAINT_THRESHOLD and not recency_override:
            return False

    if unique_insurer_reviewers and unique_insurer_reviewers < _MIN_UNIQUE_INSURER_REVIEWERS:
        return False

    if dominant_issue_count > 0 and dominant_issue_count < _MIN_DOMINANT_ISSUE_CATEGORY_REVIEWS:
        return False

    return (
        insurer_count >= max(_MIN_CONFIRMED, 3)
        or recency_override
        or (insurer_count >= _MIN_CONFIRMED and total_known < _RATE_REVIEW_THRESHOLD)
    )


def _clip_01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _effective_insurer_signal(insurer_count: int, shared_count: int) -> float:
    return max(0.0, insurer_count + (_SHARED_REVIEW_WEIGHT * shared_count))


def _qualification_threshold_for_profile(profile: str) -> float:
    normalized = (profile or "").strip().lower()
    return _SCORE_THRESHOLD_BY_PROFILE.get(normalized, _SCORE_THRESHOLD_BY_PROFILE["balanced"])


def _qualification_scores(
    *,
    insurer_count: int,
    shared_count: int,
    total_known: int,
    complaint_rate: float,
    recent_insurer_count: int,
    recent_cluster_peak: int,
    unique_insurer_reviewers: int,
) -> dict[str, float]:
    effective_signal = _effective_insurer_signal(insurer_count, shared_count)
    insurer_signal_score = _clip_01(effective_signal / max(_EFFECTIVE_SIGNAL_CAP, 1.0))

    rate_cap = max(_RATE_COMPLAINT_THRESHOLD * max(_RATE_SCORE_CAP_MULTIPLIER, 1.0), 1e-6)
    complaint_rate_score = _clip_01(complaint_rate / rate_cap)

    recency_density = _clip_01(recent_insurer_count / max(_RECENT_REVIEW_MIN_INSURER_COMPLAINTS, 1))
    recency_cluster = _clip_01(recent_cluster_peak / max(_RECENT_CLUSTER_MIN_MONTH_BUCKET_REVIEWS, 1))
    recency_score = 0.6 * recency_density + 0.4 * recency_cluster

    uniqueness_target = max(_MIN_UNIQUE_INSURER_REVIEWERS + 3, 1)
    reviewer_uniqueness_score = _clip_01(unique_insurer_reviewers / uniqueness_target)

    weight_total = max(
        _SCORE_WEIGHT_INSURER + _SCORE_WEIGHT_RATE + _SCORE_WEIGHT_RECENCY + _SCORE_WEIGHT_UNIQUENESS,
        1e-6,
    )
    base_score = (
        (_SCORE_WEIGHT_INSURER * insurer_signal_score)
        + (_SCORE_WEIGHT_RATE * complaint_rate_score)
        + (_SCORE_WEIGHT_RECENCY * recency_score)
        + (_SCORE_WEIGHT_UNIQUENESS * reviewer_uniqueness_score)
    ) / weight_total

    evidence_mass = insurer_count + shared_count
    evidence_log_cap = max(_CONFIDENCE_EVIDENCE_LOG_CAP, 1.0)
    confidence_evidence = _clip_01(math.log1p(evidence_mass) / math.log1p(evidence_log_cap))
    confidence_volume = _clip_01(total_known / max(_RATE_REVIEW_THRESHOLD, 1))

    confidence = _clip_01(
        (_CONFIDENCE_EVIDENCE_WEIGHT * confidence_evidence)
        + (_CONFIDENCE_VOLUME_WEIGHT * confidence_volume)
    )
    damp_multiplier = _FINAL_SCORE_DAMP_BASE + (_FINAL_SCORE_DAMP_SCALE * confidence)
    final_score = base_score * damp_multiplier

    return {
        "effective_signal": effective_signal,
        "base_score": base_score,
        "confidence": confidence,
        "final_score": final_score,
        "insurer_signal_score": insurer_signal_score,
        "complaint_rate_score": complaint_rate_score,
        "recency_score": recency_score,
        "reviewer_uniqueness_score": reviewer_uniqueness_score,
        "confidence_evidence": confidence_evidence,
        "confidence_volume": confidence_volume,
    }


def _needs_gray_zone_validation(final_score: float, threshold: float) -> bool:
    if not _ENABLE_GRAY_ZONE_VALIDATION:
        return False
    return abs(final_score - threshold) <= max(_GRAY_ZONE_VALIDATION_BAND, 0.0)


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
        run = db.query(CityRun).filter_by(id=city_run_id).first()
        clinics = (
            db.query(Clinic)
            .filter_by(city_run_id=city_run_id, status=ClinicStatus.SCRAPED)
            .all()
        )

        qualified_count = 0

        for clinic in clinics:
            review_pool = list(clinic.reviews)
            sampled_review_texts = [r.text for r in review_pool]
            screening_promoted = False

            # ── Stage 1: keyword pre-filter ───────────────────────────────────
            if not qualifies_for_llm(sampled_review_texts):
                screening_reviews = _select_intelligence_screening_reviews(review_pool)
                if not screening_reviews:
                    clinic.status = ClinicStatus.FILTERED_OUT
                    log.debug(f"{clinic.name}: filtered out at keyword stage")
                    continue

                try:
                    screening_classifications = classify_reviews([r.text for r in screening_reviews])
                except Exception as exc:
                    if _is_quota_exhausted_error(exc):
                        _skip_clinic_on_gemini_quota(clinic, "review screening")
                        continue
                    raise self.retry(exc=exc)

                if not _has_intelligence_screening_signal(screening_classifications):
                    clinic.status = ClinicStatus.FILTERED_OUT
                    log.info(f"[INTEL_SCREEN] {clinic.name}: Gemini screening found no insurance target signal")
                    continue

                review_pool = screening_reviews
                screening_promoted = True
                log.info(
                    f"[INTEL_SCREEN] {clinic.name}: Gemini screening found a promising insurer-driven pattern "
                    f"in {len(screening_reviews)} low-rated reviews"
                )

            # ── Deep investigation promotion ──────────────────────────────────
            # Discovery pass stores only a small sample. Once a clinic shows
            # enough insurance-friction signal, fetch a deeper evidence set.
            # This uses adaptive escalation:
            #   sampled discovery -> 25 -> 100 -> run max
            # and stops early if the stage no longer shows any keyword evidence.
            try:
                deep_result, used_limit, keyword_review_count = _run_adaptive_deep_scrape(
                    clinic=clinic,
                    max_reviews=run.max_reviews if run else config.MAX_REVIEWS_DEFAULT,
                )
                if deep_result.reviews:
                    _replace_clinic_reviews(db, clinic, deep_result.reviews)
                    clinic.overall_rating = deep_result.overall_rating or clinic.overall_rating
                    clinic.total_reviews = deep_result.total_reviews or clinic.total_reviews
                    db.expire(clinic, ["reviews"])
                    review_pool = list(clinic.reviews)
                    log.info(
                        f"[DEEP_SCRAPE] {clinic.name}: promoted from sampled discovery to deep investigation "
                        f"with {len(clinic.reviews)} reviews (stage limit {used_limit}, "
                        f"{keyword_review_count} keyword-signal reviews)"
                    )
            except Exception as exc:
                log.warning(f"[DEEP_SCRAPE] {clinic.name}: deep scrape failed, falling back to sampled reviews: {exc}")

            # Score individual reviews to find candidates for LLM
            keyword_candidates = []
            for review in review_pool:
                s = score_review(review.text)
                if s.tier1_hits > 0 or s.tier2_hits > 0 or s.tier3_hits > 0:
                    review.keyword_matches = s.matched_keywords
                    keyword_candidates.append(review)

            # If Gemini screening promoted the clinic but keyword matching missed
            # paraphrased insurance complaints, keep the screened low-star reviews.
            if screening_promoted and not keyword_candidates:
                keyword_candidates = list(review_pool)

            # ── Stage 2: per-review LLM — who is primarily at fault? ───────────
            try:
                classifications = classify_reviews([r.text for r in keyword_candidates])
            except Exception as exc:
                if _is_quota_exhausted_error(exc):
                    _skip_clinic_on_gemini_quota(clinic, "review classification")
                    continue
                raise self.retry(exc=Exception(str(exc)))

            insurer_reviews: list[Review] = []
            clinic_fault_reviews: list[Review] = []
            shared_reviews: list[Review] = []

            for review, clf in zip(keyword_candidates, classifications):
                severity = getattr(clf, "severity", 1)
                if isinstance(severity, bool) or not isinstance(severity, (int, float)):
                    severity_value = 1
                else:
                    severity_value = int(max(1, min(5, severity)))

                explicit_mention = getattr(clf, "explicit_insurance_mention", False)
                explicit_mention_value = explicit_mention if isinstance(explicit_mention, bool) else False

                review.llm_reasoning = clf.reasoning
                review.classification_confidence = clf.confidence
                review.llm_severity_score = severity_value
                review.explicit_insurance_mention = explicit_mention_value
                review.issue_category = infer_issue_category(review.text)

                if clf.verdict == ReviewVerdict.INSURER:
                    review.insurance_flag = True
                    review.fault_party = FaultParty.INSURER
                    review.flag_reason = FlagReason.BOTH if review.keyword_matches else FlagReason.LLM
                    insurer_reviews.append(review)

                elif clf.verdict == ReviewVerdict.CLINIC:
                    review.insurance_flag = False
                    review.fault_party = FaultParty.CLINIC
                    review.flag_reason = FlagReason.BOTH if review.keyword_matches else FlagReason.LLM
                    clinic_fault_reviews.append(review)

                elif clf.verdict == ReviewVerdict.SHARED:
                    review.insurance_flag = False
                    review.fault_party = FaultParty.SHARED
                    review.flag_reason = FlagReason.KEYWORD
                    shared_reviews.append(review)

                else:
                    review.insurance_flag = False
                    review.fault_party = FaultParty.NONE
                    review.flag_reason = FlagReason.KEYWORD if review.keyword_matches else None

            # ── Rate-based guard ──────────────────────────────────────────────
            # Don't target clinics on weak or low-volume insurer-fault evidence.
            insurer_count = len(insurer_reviews)
            clinic_fault_count = len(clinic_fault_reviews)
            shared_count = len(shared_reviews)
            total_known = clinic.total_reviews or len(clinic.reviews)
            complaint_rate = (insurer_count / total_known) if total_known else 0.0
            unique_insurer_reviewers = _unique_named_reviewer_count(insurer_reviews)
            dominant_issue_category, dominant_issue_count = _dominant_issue_category(insurer_reviews)
            recent_insurer_count = _count_recent_reviews(insurer_reviews, _RECENT_REVIEW_WINDOW_DAYS)
            recent_cluster_peak = _recent_month_cluster_peak(insurer_reviews, _RECENT_REVIEW_WINDOW_DAYS)
            recency_override = _passes_recent_cluster_override(insurer_reviews, clinic_fault_reviews)

            if insurer_count < _MIN_CONFIRMED:
                clinic.status = ClinicStatus.FILTERED_OUT
                log.info(f"{clinic.name}: only {insurer_count} insurer-fault complaints — filtered out")
                continue

            if unique_insurer_reviewers and unique_insurer_reviewers < _MIN_UNIQUE_INSURER_REVIEWERS:
                clinic.status = ClinicStatus.FILTERED_OUT
                log.info(
                    f"{clinic.name}: only {unique_insurer_reviewers} unique insurer-fault reviewers "
                    f"— filtered out"
                )
                continue

            if (
                dominant_issue_count > 0
                and dominant_issue_count < _MIN_DOMINANT_ISSUE_CATEGORY_REVIEWS
                and insurer_count <= _MIN_DOMINANT_ISSUE_CATEGORY_REVIEWS
            ):
                clinic.status = ClinicStatus.FILTERED_OUT
                log.info(
                    f"{clinic.name}: insurer-fault reviews lack repeated issue-category consistency "
                    f"(top category {dominant_issue_category} count {dominant_issue_count}) — filtered out"
                )
                continue

            if total_known >= _RATE_REVIEW_THRESHOLD:
                if complaint_rate < _RATE_COMPLAINT_THRESHOLD:
                    if not recency_override:
                        clinic.status = ClinicStatus.FILTERED_OUT
                        log.info(
                            f"{clinic.name}: complaint rate {complaint_rate:.2%} below threshold "
                            f"({insurer_count}/{total_known}) — filtered out"
                        )
                        continue
                    log.info(
                        f"{clinic.name}: low overall complaint rate {complaint_rate:.2%} but recent insurer-fault "
                        f"cluster triggered recency override"
                    )

            if clinic_fault_count > insurer_count:
                clinic.status = ClinicStatus.FILTERED_OUT
                log.info(
                    f"{clinic.name}: more clinic-fault reviews than insurer-fault reviews "
                    f"({clinic_fault_count}>{insurer_count}) — filtered out"
                )
                continue

            score_details = _qualification_scores(
                insurer_count=insurer_count,
                shared_count=shared_count,
                total_known=total_known,
                complaint_rate=complaint_rate,
                recent_insurer_count=recent_insurer_count,
                recent_cluster_peak=recent_cluster_peak,
                unique_insurer_reviewers=unique_insurer_reviewers,
            )
            threshold = _qualification_threshold_for_profile(_QUALIFICATION_PROFILE)

            if _is_obvious_target(
                insurer_count=insurer_count,
                clinic_fault_count=clinic_fault_count,
                total_known=total_known,
                unique_insurer_reviewers=unique_insurer_reviewers,
                dominant_issue_count=dominant_issue_count,
                recency_override=recency_override,
            ):
                clinic.status = ClinicStatus.QUALIFIED
                qualified_count += 1
                log.info(
                    f"[SCORE_TARGET] {clinic.name}: qualified with final_score={score_details['final_score']:.3f} "
                    f"(base={score_details['base_score']:.3f}, confidence={score_details['confidence']:.3f}, "
                    f"threshold={threshold:.3f}, profile={_QUALIFICATION_PROFILE})"
                )
                continue

            if not _needs_gray_zone_validation(score_details["final_score"], threshold):
                clinic.status = (
                    ClinicStatus.QUALIFIED
                    if score_details["final_score"] >= threshold
                    else ClinicStatus.FILTERED_OUT
                )
                if clinic.status == ClinicStatus.QUALIFIED:
                    qualified_count += 1
                status_label = clinic.status.value if hasattr(clinic.status, "value") else str(clinic.status)
                log.info(
                    f"[SCORE_POLICY] {clinic.name}: final_score={score_details['final_score']:.3f}, "
                    f"threshold={threshold:.3f}, gray_zone=False -> {status_label}"
                )
                continue

            # ── Stage 3: clinic-level systemic analysis (gray-zone only) ─────
            # In near-threshold ambiguity, Gemini acts as tie-breaker and explainer.
            try:
                verdict = analyze_clinic(
                    clinic_name=clinic.name,
                    overall_rating=clinic.overall_rating,
                    total_reviews=clinic.total_reviews,
                    insurer_reviews=[r.text for r in insurer_reviews],
                    clinic_reviews=[r.text for r in clinic_fault_reviews],
                    shared_reviews=[r.text for r in shared_reviews],
                )
                log.info(
                    f"[GRAY_ZONE] {clinic.name}: target={verdict.is_target} "
                    f"confidence={verdict.confidence:.2f} severity={verdict.severity} "
                    f"— {verdict.pattern}"
                )
            except Exception as exc:
                if _is_quota_exhausted_error(exc):
                    _skip_clinic_on_gemini_quota(clinic, "clinic-level analysis")
                    continue
                raise self.retry(exc=Exception(str(exc)))

            if verdict.is_target:
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
