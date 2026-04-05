import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas import ClinicDetailResponse, ClinicFilterDiagnosticsResponse, ClinicResponse, ContactResponse, ReviewResponse
from db.models import Clinic, FaultParty
import config
from pipeline.tasks import (
    _count_recent_reviews,
    _dominant_issue_category,
    _qualification_scores,
    _qualification_threshold_for_profile,
    _recent_month_cluster_peak,
    _unique_named_reviewer_count,
)

router = APIRouter(prefix="/api/clinics", tags=["clinics"])


def _review_fault_counts(reviews) -> tuple[int, int, int]:
    insurer_faults = sum(
        1 for review in reviews if review.fault_party == FaultParty.INSURER or review.insurance_flag
    )
    clinic_faults = sum(1 for review in reviews if review.fault_party == FaultParty.CLINIC)
    shared_faults = sum(1 for review in reviews if review.fault_party == FaultParty.SHARED)
    return insurer_faults, clinic_faults, shared_faults


@router.get("", response_model=list[ClinicResponse])
def list_clinics(
    city: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Clinic)
    if city:
        query = query.filter(Clinic.city.ilike(f"%{city}%"))
    if status:
        query = query.filter(Clinic.status == status)
    clinics = query.order_by(Clinic.name).all()

    result = []
    for clinic in clinics:
        insurer_faults, clinic_faults, shared_faults = _review_fault_counts(clinic.reviews)
        resp = ClinicResponse.model_validate(clinic)
        resp.insurance_flag_count = insurer_faults
        resp.insurer_fault_count = insurer_faults
        resp.clinic_fault_count = clinic_faults
        resp.shared_fault_count = shared_faults
        result.append(resp)
    return result


@router.get("/{clinic_id}", response_model=ClinicDetailResponse)
def get_clinic_detail(clinic_id: uuid.UUID, db: Session = Depends(get_db)):
    clinic = db.query(Clinic).filter_by(id=clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    reviews = list(clinic.reviews)
    insurer_faults, clinic_faults, shared_faults = _review_fault_counts(reviews)
    insurer_reviews = [
        review for review in reviews
        if review.fault_party == FaultParty.INSURER or review.insurance_flag
    ]
    negative_reviews = sum(1 for r in reviews if (r.rating is not None and r.rating <= 2))
    total_reviews_known = clinic.total_reviews or len(reviews)
    complaint_rate = (insurer_faults / total_reviews_known) if total_reviews_known else 0.0
    unique_insurer_reviewers = _unique_named_reviewer_count(insurer_reviews)
    dominant_issue_category, dominant_issue_category_reviews = _dominant_issue_category(insurer_reviews)
    recent_insurer_fault_reviews = _count_recent_reviews(insurer_reviews, config.RECENT_REVIEW_WINDOW_DAYS)
    recent_month_cluster_peak = _recent_month_cluster_peak(insurer_reviews, config.RECENT_REVIEW_WINDOW_DAYS)
    score_details = _qualification_scores(
        insurer_count=insurer_faults,
        shared_count=shared_faults,
        total_known=total_reviews_known,
        complaint_rate=complaint_rate,
        recent_insurer_count=recent_insurer_fault_reviews,
        recent_cluster_peak=recent_month_cluster_peak,
        unique_insurer_reviewers=unique_insurer_reviewers,
    )
    qualification_profile = config.QUALIFICATION_PROFILE
    qualification_threshold = _qualification_threshold_for_profile(qualification_profile)

    clinic_resp = ClinicResponse.model_validate(clinic)
    clinic_resp.insurance_flag_count = insurer_faults
    clinic_resp.insurer_fault_count = insurer_faults
    clinic_resp.clinic_fault_count = clinic_faults
    clinic_resp.shared_fault_count = shared_faults

    diagnostics = ClinicFilterDiagnosticsResponse(
        confirmed_complaints=insurer_faults,
        insurer_fault_reviews=insurer_faults,
        clinic_fault_reviews=clinic_faults,
        shared_fault_reviews=shared_faults,
        unique_insurer_reviewers=unique_insurer_reviewers,
        dominant_issue_category=dominant_issue_category,
        dominant_issue_category_reviews=dominant_issue_category_reviews,
        recent_insurer_fault_reviews=recent_insurer_fault_reviews,
        recent_month_cluster_peak=recent_month_cluster_peak,
        negative_reviews=negative_reviews,
        total_reviews_known=total_reviews_known,
        complaint_rate=complaint_rate,
        min_confirmed_required=config.MIN_CONFIRMED_COMPLAINTS,
        min_reviews_for_rate_guard=config.RATE_GUARD_MIN_REVIEWS,
        min_complaint_rate_required=config.COMPLAINT_RATE_THRESHOLD,
        qualification_profile=qualification_profile,
        qualification_threshold=qualification_threshold,
        effective_insurer_signal=score_details["effective_signal"],
        base_score=score_details["base_score"],
        confidence_score=score_details["confidence"],
        final_score=score_details["final_score"],
        insurer_signal_score=score_details["insurer_signal_score"],
        complaint_rate_score=score_details["complaint_rate_score"],
        recency_score=score_details["recency_score"],
        reviewer_uniqueness_score=score_details["reviewer_uniqueness_score"],
    )

    return ClinicDetailResponse(
        clinic=clinic_resp,
        diagnostics=diagnostics,
        contacts=[ContactResponse.model_validate(contact) for contact in clinic.contacts],
        reviews=[ReviewResponse.model_validate(r) for r in reviews],
    )


@router.get("/{clinic_id}/reviews", response_model=list[ReviewResponse])
def get_clinic_reviews(clinic_id: uuid.UUID, db: Session = Depends(get_db)):
    clinic = db.query(Clinic).filter_by(id=clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return clinic.reviews
