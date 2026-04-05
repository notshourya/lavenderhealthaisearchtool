import uuid
from datetime import datetime
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import config
from api.deps import get_db
from api.schemas import (
    CityRunCreate,
    CityRunResponse,
    RunDiagnosticsResponse,
    PolicyReevaluationRequest,
    PolicyReevaluationResponse,
    ClinicPolicyResultResponse,
    PolicyReasonCodeResponse,
)
from db.models import (
    CityRun,
    TriggeredBy,
    Clinic,
    ClinicStatus,
    Review,
    FaultParty,
    ClinicPolicyResult,
)
from pipeline.tasks import scrape_city_task
from pipeline.tasks import (
    _count_recent_reviews,
    _dominant_issue_category,
    _is_obvious_target,
    _passes_recent_cluster_override,
    _qualification_scores,
    _qualification_threshold_for_profile,
    _recent_month_cluster_peak,
    _unique_named_reviewer_count,
)

router = APIRouter(prefix="/api/runs", tags=["runs"])


REASON_CODE_LABELS: dict[str, str] = {
    "HIGH_INSURER_COUNT": "Frequent insurer-related complaints",
    "RECENT_SPIKE": "Recent increase in complaints",
    "MULTIPLE_INDEPENDENT_REVIEWERS": "Multiple independent reviewers",
    "HIGH_COMPLAINT_RATE": "Meaningful complaint rate",
    "LIMITED_CLINIC_FAULT_EVIDENCE": "Limited clinic-fault evidence",
    "MIXED_OR_UNCLEAR_CASES": "Some mixed or unclear cases",
    "STRONG_INSURER_SIGNAL": "Strong insurer signal",
    "RECENT_COMPLAINT_CLUSTER": "Recent complaint cluster",
    "OBVIOUS_TARGET": "Obvious target",
    "SCORE_THRESHOLD": "Met score threshold",
    "INSUFFICIENT_INSURER_COMPLAINTS": "Insufficient insurer complaints",
    "INSUFFICIENT_UNIQUE_REVIEWERS": "Insufficient unique reviewers",
    "INCONSISTENT_ISSUE_PATTERN": "Inconsistent issue pattern",
    "LOW_COMPLAINT_RATE": "Low complaint rate",
    "CLINIC_FAULT_DOMINATES": "Clinic-fault evidence dominates",
    "BELOW_THRESHOLD": "Below threshold",
}


def _build_policy_result_response(row: ClinicPolicyResult, clinic_name: str) -> ClinicPolicyResultResponse:
    top_signals = _policy_top_signals(row)
    return ClinicPolicyResultResponse(
        clinic_id=row.clinic_id,
        clinic_name=clinic_name,
        rank=0,
        policy_version=row.policy_version,
        is_qualified=row.is_qualified,
        decision_reason=row.decision_reason,
        qualification_profile=row.qualification_profile,
        qualification_threshold=row.qualification_threshold,
        policy_config=row.policy_config,
        top_signals=top_signals,
        insurer_fault_reviews=row.insurer_fault_reviews,
        clinic_fault_reviews=row.clinic_fault_reviews,
        shared_fault_reviews=row.shared_fault_reviews,
        unique_insurer_reviewers=row.unique_insurer_reviewers,
        dominant_issue_category=row.dominant_issue_category,
        dominant_issue_category_reviews=row.dominant_issue_category_reviews,
        recent_insurer_fault_reviews=row.recent_insurer_fault_reviews,
        recent_month_cluster_peak=row.recent_month_cluster_peak,
        total_reviews_known=row.total_reviews_known,
        complaint_rate=row.complaint_rate,
        effective_insurer_signal=row.effective_insurer_signal,
        base_score=row.base_score,
        confidence_score=row.confidence_score,
        final_score=row.final_score,
        insurer_signal_score=row.insurer_signal_score,
        complaint_rate_score=row.complaint_rate_score,
        recency_score=row.recency_score,
        reviewer_uniqueness_score=row.reviewer_uniqueness_score,
        created_at=row.created_at,
    )


def _build_policy_config(profile: str, threshold: float) -> dict:
    rate_cap = round(config.COMPLAINT_RATE_THRESHOLD * config.RATE_SCORE_CAP_MULTIPLIER, 4)
    return {
        "policy_version": config.POLICY_VERSION,
        "profile": profile,
        "threshold": threshold,
        "weights": {
            "insurer": config.SCORE_WEIGHT_INSURER,
            "rate": config.SCORE_WEIGHT_RATE,
            "recency": config.SCORE_WEIGHT_RECENCY,
            "unique": config.SCORE_WEIGHT_UNIQUENESS,
        },
        "normalization": {
            "insurer_log_base": 10,
            "rate_cap": rate_cap,
            "rate_threshold": config.COMPLAINT_RATE_THRESHOLD,
            "recency_window": [30, 90, config.RECENT_REVIEW_WINDOW_DAYS],
        },
        "confidence_weights": {
            "evidence": config.CONFIDENCE_EVIDENCE_WEIGHT,
            "volume": config.CONFIDENCE_VOLUME_WEIGHT,
        },
        "confidence_formula": "v2",
        "final_score_damping": {
            "base": config.FINAL_SCORE_DAMP_BASE,
            "scale": config.FINAL_SCORE_DAMP_SCALE,
        },
        "shared_review_weight": config.SHARED_REVIEW_WEIGHT,
        "effective_signal_cap": config.EFFECTIVE_SIGNAL_CAP,
        "rate_score_cap_multiplier": config.RATE_SCORE_CAP_MULTIPLIER,
        "gray_zone": {
            "enabled": config.ENABLE_GRAY_ZONE_VALIDATION,
            "band": config.GRAY_ZONE_VALIDATION_BAND,
        },
    }


def _policy_reason_codes(row: ClinicPolicyResult) -> list[str]:
    codes: list[str] = []
    if row.insurer_fault_reviews >= 3:
        codes.append("HIGH_INSURER_COUNT")
    if row.recent_insurer_fault_reviews >= 2:
        codes.append("RECENT_SPIKE")
    if row.unique_insurer_reviewers >= 2:
        codes.append("MULTIPLE_INDEPENDENT_REVIEWERS")
    if row.complaint_rate >= config.COMPLAINT_RATE_THRESHOLD:
        codes.append("HIGH_COMPLAINT_RATE")
    if row.clinic_fault_reviews == 0:
        codes.append("LIMITED_CLINIC_FAULT_EVIDENCE")
    if row.shared_fault_reviews > 0:
        codes.append("MIXED_OR_UNCLEAR_CASES")
    if row.insurer_signal_score >= 0.7:
        codes.append("STRONG_INSURER_SIGNAL")
    if row.recency_score >= 0.6:
        codes.append("RECENT_COMPLAINT_CLUSTER")
    if row.decision_reason == "obvious_target":
        codes.append("OBVIOUS_TARGET")
    elif row.decision_reason == "score_threshold":
        codes.append("SCORE_THRESHOLD")
    elif row.decision_reason:
        codes.append(row.decision_reason.upper())
    return codes[:4]


def _policy_top_signals(row: ClinicPolicyResult) -> list[str]:
    return [REASON_CODE_LABELS.get(code, code.replace("_", " ").title()) for code in _policy_reason_codes(row)]


def _reason_code_rows(rows: list[ClinicPolicyResult]) -> list[PolicyReasonCodeResponse]:
    reason_counts = Counter()
    for row in rows:
        reason_counts.update(_policy_reason_codes(row))

    return [
        PolicyReasonCodeResponse(
            code=code,
            label=REASON_CODE_LABELS.get(code, code.replace("_", " ").title()),
            count=count,
        )
        for code, count in reason_counts.most_common(4)
    ]


def _policy_summary(rows: list[ClinicPolicyResult]) -> tuple[int, int, int, float, float, float, list[PolicyReasonCodeResponse]]:
    total = len(rows)
    qualified = sum(1 for row in rows if row.is_qualified)
    avg_score = sum((row.final_score or 0.0) for row in rows) / total if total else 0.0
    avg_confidence = sum((row.confidence_score or 0.0) for row in rows) / total if total else 0.0
    qualification_rate = (qualified / total) if total else 0.0
    reason_codes = _reason_code_rows(rows)
    return total, qualified, max(total - qualified, 0), qualification_rate, avg_score, avg_confidence, reason_codes


@router.get("", response_model=list[CityRunResponse])
def list_runs(db: Session = Depends(get_db)):
    return db.query(CityRun).order_by(CityRun.created_at.desc()).all()


@router.post("", response_model=CityRunResponse, status_code=201)
def create_run(payload: CityRunCreate, db: Session = Depends(get_db)):
    run = CityRun(
        city=payload.city,
        state=payload.state,
        max_reviews=payload.max_reviews,
        triggered_by=TriggeredBy.DASHBOARD,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    scrape_city_task.delay(str(run.id))
    return run


@router.get("/{run_id}", response_model=CityRunResponse)
def get_run(run_id: uuid.UUID, db: Session = Depends(get_db)):
    run = db.query(CityRun).filter_by(id=run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/{run_id}/diagnostics", response_model=RunDiagnosticsResponse)
def get_run_diagnostics(run_id: uuid.UUID, db: Session = Depends(get_db)):
    run = db.query(CityRun).filter_by(id=run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    clinics = db.query(Clinic).filter_by(city_run_id=run_id).all()
    clinic_ids = [c.id for c in clinics]

    stage_counts = {
        "scraped": sum(1 for c in clinics if c.status == ClinicStatus.SCRAPED),
        "filtered_out": sum(1 for c in clinics if c.status == ClinicStatus.FILTERED_OUT),
        "qualified": sum(1 for c in clinics if c.status == ClinicStatus.QUALIFIED),
        "enriched": sum(1 for c in clinics if c.status == ClinicStatus.ENRICHED),
        "drafted": sum(1 for c in clinics if c.status == ClinicStatus.DRAFTED),
    }

    clinics_with_rating = sum(1 for c in clinics if c.overall_rating is not None)
    clinics_with_review_count = sum(1 for c in clinics if c.total_reviews is not None)

    clinics_with_scraped_reviews = 0
    flagged_reviews = 0
    if clinic_ids:
        review_rows = db.query(Review.clinic_id, Review.insurance_flag, Review.fault_party).filter(Review.clinic_id.in_(clinic_ids)).all()
        clinics_with_scraped_reviews = len({clinic_id for clinic_id, _, _ in review_rows})
        flagged_reviews = sum(
            1
            for _, insurance_flag, fault_party in review_rows
            if insurance_flag or fault_party == FaultParty.INSURER
        )

    duration_seconds = None
    try:
        if run.completed_at:
            duration_seconds = int((run.completed_at - run.created_at).total_seconds())
        elif run.status == "running":
            # Keep this timezone-naive-safe since DB timestamps may be naive.
            duration_seconds = int((datetime.utcnow() - run.created_at.replace(tzinfo=None)).total_seconds())
    except Exception:
        duration_seconds = None

    return RunDiagnosticsResponse(
        run_id=run.id,
        status=run.status,
        duration_seconds=duration_seconds,
        total_clinics=len(clinics),
        clinics_with_rating=clinics_with_rating,
        clinics_with_review_count=clinics_with_review_count,
        clinics_with_scraped_reviews=clinics_with_scraped_reviews,
        flagged_reviews=flagged_reviews,
        stage_counts=stage_counts,
    )


@router.post("/{run_id}/policy-reevaluate", response_model=PolicyReevaluationResponse)
def policy_reevaluate_run(
    run_id: uuid.UUID,
    payload: PolicyReevaluationRequest,
    db: Session = Depends(get_db),
):
    run = db.query(CityRun).filter_by(id=run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    profile = payload.qualification_profile
    policy_version = payload.policy_version
    threshold = (
        payload.qualification_threshold
        if payload.qualification_threshold is not None
        else _qualification_threshold_for_profile(profile)
    )
    policy_config = _build_policy_config(profile, threshold)

    clinics = db.query(Clinic).filter_by(city_run_id=run_id).all()
    clinic_map = {clinic.id: clinic for clinic in clinics}

    (
        db.query(ClinicPolicyResult)
        .filter_by(city_run_id=run_id, qualification_profile=profile, policy_version=policy_version)
        .delete(synchronize_session=False)
    )

    persisted_rows: list[ClinicPolicyResult] = []
    qualified_count = 0

    for clinic in clinics:
        reviews = list(clinic.reviews)
        insurer_reviews = [
            review for review in reviews
            if review.fault_party == FaultParty.INSURER or review.insurance_flag
        ]
        clinic_fault_reviews = [review for review in reviews if review.fault_party == FaultParty.CLINIC]
        shared_reviews = [review for review in reviews if review.fault_party == FaultParty.SHARED]

        insurer_count = len(insurer_reviews)
        clinic_fault_count = len(clinic_fault_reviews)
        shared_count = len(shared_reviews)
        total_known = clinic.total_reviews or len(reviews)
        complaint_rate = (insurer_count / total_known) if total_known else 0.0

        unique_insurer_reviewers = _unique_named_reviewer_count(insurer_reviews)
        dominant_issue_category, dominant_issue_count = _dominant_issue_category(insurer_reviews)
        recent_insurer_count = _count_recent_reviews(insurer_reviews, config.RECENT_REVIEW_WINDOW_DAYS)
        recent_cluster_peak = _recent_month_cluster_peak(insurer_reviews, config.RECENT_REVIEW_WINDOW_DAYS)
        recency_override = _passes_recent_cluster_override(insurer_reviews, clinic_fault_reviews)

        score_details = _qualification_scores(
            insurer_count=insurer_count,
            shared_count=shared_count,
            total_known=total_known,
            complaint_rate=complaint_rate,
            recent_insurer_count=recent_insurer_count,
            recent_cluster_peak=recent_cluster_peak,
            unique_insurer_reviewers=unique_insurer_reviewers,
        )

        is_qualified = False
        decision_reason = "below_threshold"

        if insurer_count < config.MIN_CONFIRMED_COMPLAINTS:
            decision_reason = "insufficient_insurer_complaints"
        elif unique_insurer_reviewers and unique_insurer_reviewers < config.MIN_UNIQUE_INSURER_REVIEWERS:
            decision_reason = "insufficient_unique_reviewers"
        elif (
            dominant_issue_count > 0
            and dominant_issue_count < config.MIN_DOMINANT_ISSUE_CATEGORY_REVIEWS
            and insurer_count <= config.MIN_DOMINANT_ISSUE_CATEGORY_REVIEWS
        ):
            decision_reason = "inconsistent_issue_pattern"
        elif (
            total_known >= config.RATE_GUARD_MIN_REVIEWS
            and complaint_rate < config.COMPLAINT_RATE_THRESHOLD
            and not recency_override
        ):
            decision_reason = "low_complaint_rate"
        elif clinic_fault_count > insurer_count:
            decision_reason = "clinic_fault_dominates"
        elif _is_obvious_target(
            insurer_count=insurer_count,
            clinic_fault_count=clinic_fault_count,
            total_known=total_known,
            unique_insurer_reviewers=unique_insurer_reviewers,
            dominant_issue_count=dominant_issue_count,
            recency_override=recency_override,
        ):
            is_qualified = True
            decision_reason = "obvious_target"
        elif score_details["final_score"] >= threshold:
            is_qualified = True
            decision_reason = "score_threshold"

        if is_qualified:
            qualified_count += 1

        row = ClinicPolicyResult(
            city_run_id=run_id,
            clinic_id=clinic.id,
            policy_version=policy_version,
            qualification_profile=profile,
            qualification_threshold=threshold,
            policy_config=policy_config,
            is_qualified=is_qualified,
            decision_reason=decision_reason,
            insurer_fault_reviews=insurer_count,
            clinic_fault_reviews=clinic_fault_count,
            shared_fault_reviews=shared_count,
            unique_insurer_reviewers=unique_insurer_reviewers,
            dominant_issue_category=dominant_issue_category,
            dominant_issue_category_reviews=dominant_issue_count,
            recent_insurer_fault_reviews=recent_insurer_count,
            recent_month_cluster_peak=recent_cluster_peak,
            total_reviews_known=total_known,
            complaint_rate=complaint_rate,
            effective_insurer_signal=score_details["effective_signal"],
            base_score=score_details["base_score"],
            confidence_score=score_details["confidence"],
            final_score=score_details["final_score"],
            insurer_signal_score=score_details["insurer_signal_score"],
            complaint_rate_score=score_details["complaint_rate_score"],
            recency_score=score_details["recency_score"],
            reviewer_uniqueness_score=score_details["reviewer_uniqueness_score"],
        )
        db.add(row)
        persisted_rows.append(row)

    db.commit()

    for row in persisted_rows:
        db.refresh(row)

    persisted_rows.sort(key=lambda item: item.final_score, reverse=True)
    results = [
        _build_policy_result_response(row, clinic_map[row.clinic_id].name)
        for row in persisted_rows
    ]

    for index, result in enumerate(results, start=1):
        result.rank = index

    total, qualified, filtered_out, qualification_rate, avg_score, avg_confidence, reason_codes = _policy_summary(persisted_rows)

    return PolicyReevaluationResponse(
        run_id=run_id,
        policy_version=policy_version,
        qualification_profile=profile,
        qualification_threshold=threshold,
        policy_config=policy_config,
        summary={
            "total_clinics": total,
            "qualified": qualified,
            "filtered_out": filtered_out,
            "qualification_rate": qualification_rate,
            "avg_score": avg_score,
            "avg_confidence": avg_confidence,
            "reason_codes": reason_codes,
            "top_reasons": [reason.label for reason in reason_codes],
        },
        results=results,
    )


@router.get("/{run_id}/policy-results", response_model=PolicyReevaluationResponse)
def list_policy_results(
    run_id: uuid.UUID,
    qualification_profile: str | None = None,
    policy_version: str | None = None,
    db: Session = Depends(get_db),
):
    run = db.query(CityRun).filter_by(id=run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    query = (
        db.query(ClinicPolicyResult, Clinic.name)
        .join(Clinic, Clinic.id == ClinicPolicyResult.clinic_id)
        .filter(ClinicPolicyResult.city_run_id == run_id)
    )

    if qualification_profile:
        query = query.filter(ClinicPolicyResult.qualification_profile == qualification_profile.strip().lower())
    if policy_version:
        query = query.filter(ClinicPolicyResult.policy_version == policy_version.strip().lower())

    rows = (
        query
        .order_by(ClinicPolicyResult.created_at.desc(), ClinicPolicyResult.final_score.desc())
        .all()
    )

    rows = sorted(rows, key=lambda item: item[0].final_score, reverse=True)

    result_rows = [row for row, _ in rows]
    results = [_build_policy_result_response(row, clinic_name) for row, clinic_name in rows]
    for index, result in enumerate(results, start=1):
        result.rank = index

    total, qualified, filtered_out, qualification_rate, avg_score, avg_confidence, reason_codes = _policy_summary(result_rows)

    selected_profile = qualification_profile.strip().lower() if qualification_profile else (result_rows[0].qualification_profile if result_rows else (config.QUALIFICATION_PROFILE or "balanced"))
    selected_version = policy_version.strip().lower() if policy_version else (result_rows[0].policy_version if result_rows else config.POLICY_VERSION)
    threshold = result_rows[0].qualification_threshold if result_rows else _qualification_threshold_for_profile(selected_profile)

    return PolicyReevaluationResponse(
        run_id=run_id,
        policy_version=selected_version,
        qualification_profile=selected_profile,
        qualification_threshold=threshold,
        policy_config=result_rows[0].policy_config if result_rows else _build_policy_config(selected_profile, threshold),
        summary={
            "total_clinics": total,
            "qualified": qualified,
            "filtered_out": filtered_out,
            "qualification_rate": qualification_rate,
            "avg_score": avg_score,
            "avg_confidence": avg_confidence,
            "reason_codes": reason_codes,
            "top_reasons": [reason.label for reason in reason_codes],
        },
        results=results,
    )


@router.delete("/{run_id}", status_code=204)
def delete_run(run_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete a run and all associated clinic data (cascades)."""
    run = db.query(CityRun).filter_by(id=run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Cascade delete handled by SQLAlchemy foreign key constraints
    db.delete(run)
    db.commit()
    return None
