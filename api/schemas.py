import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CityRunCreate(BaseModel):
    city: str
    state: str
    # 0 means uncapped review scraping.
    max_reviews: int = Field(default=0, ge=0)
    triggered_by: str = "dashboard"

    @field_validator("state")
    @classmethod
    def state_must_be_two_chars(cls, v: str) -> str:
        if len(v) != 2:
            raise ValueError("state must be a 2-letter abbreviation")
        return v.upper()


class CityRunResponse(BaseModel):
    id: uuid.UUID
    city: str
    state: str
    status: str
    triggered_by: str
    max_reviews: int
    created_at: datetime
    completed_at: datetime | None
    total_clinics_found: int
    total_qualified: int
    total_enriched: int
    total_drafted: int

    class Config:
        from_attributes = True


class RunDiagnosticsResponse(BaseModel):
    run_id: uuid.UUID
    status: str
    duration_seconds: int | None
    total_clinics: int
    clinics_with_rating: int
    clinics_with_review_count: int
    clinics_with_scraped_reviews: int
    flagged_reviews: int
    stage_counts: dict[str, int]


class PolicyReevaluationRequest(BaseModel):
    qualification_profile: str = Field(default="balanced")
    qualification_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    policy_version: str = Field(default="v1")

    @field_validator("qualification_profile")
    @classmethod
    def qualification_profile_must_be_valid(cls, v: str) -> str:
        normalized = (v or "").strip().lower()
        if normalized not in {"strict", "balanced", "recall"}:
            raise ValueError("qualification_profile must be one of: strict, balanced, recall")
        return normalized

    @field_validator("policy_version")
    @classmethod
    def policy_version_must_be_valid(cls, v: str) -> str:
        normalized = (v or "").strip().lower()
        if not normalized:
            raise ValueError("policy_version is required")
        return normalized


class PolicyReasonCodeResponse(BaseModel):
    code: str
    label: str
    count: int


class PolicyResultSummaryResponse(BaseModel):
    total_clinics: int
    qualified: int
    filtered_out: int
    qualification_rate: float
    avg_score: float
    avg_confidence: float
    reason_codes: list[PolicyReasonCodeResponse]
    top_reasons: list[str]


class ClinicPolicyResultResponse(BaseModel):
    clinic_id: uuid.UUID
    clinic_name: str
    rank: int
    policy_version: str
    is_qualified: bool
    decision_reason: str
    qualification_profile: str
    qualification_threshold: float
    policy_config: dict[str, Any]
    top_signals: list[str]
    insurer_fault_reviews: int
    clinic_fault_reviews: int
    shared_fault_reviews: int
    unique_insurer_reviewers: int
    dominant_issue_category: str | None
    dominant_issue_category_reviews: int
    recent_insurer_fault_reviews: int
    recent_month_cluster_peak: int
    total_reviews_known: int
    complaint_rate: float
    effective_insurer_signal: float
    base_score: float
    confidence_score: float
    final_score: float
    insurer_signal_score: float
    complaint_rate_score: float
    recency_score: float
    reviewer_uniqueness_score: float
    created_at: datetime


class PolicyReevaluationResponse(BaseModel):
    run_id: uuid.UUID
    policy_version: str
    qualification_profile: str
    qualification_threshold: float
    policy_config: dict[str, Any]
    summary: PolicyResultSummaryResponse
    results: list[ClinicPolicyResultResponse]


class ReviewResponse(BaseModel):
    id: uuid.UUID
    author: str | None
    rating: int | None
    date: datetime | None
    text: str
    insurance_flag: bool
    flag_reason: str | None
    fault_party: str | None = None
    issue_category: str | None = None
    classification_confidence: float | None = None
    llm_severity_score: int | None = None
    explicit_insurance_mention: bool | None = None
    keyword_matches: list[str] | None
    llm_reasoning: str | None

    class Config:
        from_attributes = True


class ClinicResponse(BaseModel):
    id: uuid.UUID
    name: str
    address: str | None
    city: str
    state: str
    phone: str | None
    website: str | None
    overall_rating: float | None
    total_reviews: int | None
    status: str
    insurance_flag_count: int = 0
    insurer_fault_count: int = 0
    clinic_fault_count: int = 0
    shared_fault_count: int = 0

    class Config:
        from_attributes = True


class ClinicFilterDiagnosticsResponse(BaseModel):
    confirmed_complaints: int
    insurer_fault_reviews: int
    clinic_fault_reviews: int
    shared_fault_reviews: int
    unique_insurer_reviewers: int
    dominant_issue_category: str | None
    dominant_issue_category_reviews: int
    recent_insurer_fault_reviews: int
    recent_month_cluster_peak: int
    negative_reviews: int
    total_reviews_known: int
    complaint_rate: float
    min_confirmed_required: int
    min_reviews_for_rate_guard: int
    min_complaint_rate_required: float
    qualification_profile: str
    qualification_threshold: float
    effective_insurer_signal: float
    base_score: float
    confidence_score: float
    final_score: float
    insurer_signal_score: float
    complaint_rate_score: float
    recency_score: float
    reviewer_uniqueness_score: float


class ContactResponse(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str | None
    last_name: str | None
    title: str | None
    confidence_score: float | None

    class Config:
        from_attributes = True


class ClinicDetailResponse(BaseModel):
    clinic: ClinicResponse
    diagnostics: ClinicFilterDiagnosticsResponse
    contacts: list[ContactResponse]
    reviews: list[ReviewResponse]


class DraftResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    contact_id: uuid.UUID
    subject: str
    body: str
    subject_variants: list[str] | None
    status: str
    created_at: datetime
    exported_at: datetime | None

    class Config:
        from_attributes = True


class DraftPatch(BaseModel):
    subject: str | None = None
    body: str | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def status_must_be_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in ("draft", "approved", "sent"):
            raise ValueError("status must be draft, approved, or sent")
        return v
