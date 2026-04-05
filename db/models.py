import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum


def utcnow() -> datetime:
    return datetime.now(timezone.utc)

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class CityRunStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TriggeredBy(str, PyEnum):
    CLI = "cli"
    DASHBOARD = "dashboard"
    SCHEDULER = "scheduler"


class ClinicStatus(str, PyEnum):
    SCRAPED = "scraped"
    FILTERED_OUT = "filtered_out"
    QUALIFIED = "qualified"
    ENRICHED = "enriched"
    DRAFTED = "drafted"


class FlagReason(str, PyEnum):
    KEYWORD = "keyword"
    LLM = "llm"
    BOTH = "both"


class FaultParty(str, PyEnum):
    INSURER = "insurer"
    CLINIC = "clinic"
    SHARED = "shared"
    UNCLEAR = "unclear"
    NONE = "none"


class IssueCategory(str, PyEnum):
    CLAIM_DENIAL = "claim_denial"
    COVERAGE_CONFUSION = "coverage_confusion"
    REIMBURSEMENT_DELAY = "reimbursement_delay"
    AUTHORIZATION_ISSUE = "authorization_issue"
    BILLING_ERROR = "billing_error"
    OTHER = "other"


class DraftStatus(str, PyEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    SENT = "sent"


class ExportFormat(str, PyEnum):
    HTML = "html"
    PDF = "pdf"


class CityRun(Base):
    __tablename__ = "city_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    city = Column(String(100), nullable=False)
    state = Column(String(2), nullable=False)
    status = Column(Enum(CityRunStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=CityRunStatus.PENDING)
    triggered_by = Column(Enum(TriggeredBy, values_callable=lambda x: [e.value for e in x]), nullable=False)
    # 0 means uncapped review scraping.
    max_reviews = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    completed_at = Column(DateTime, nullable=True)
    total_clinics_found = Column(Integer, nullable=False, default=0)
    total_qualified = Column(Integer, nullable=False, default=0)
    total_enriched = Column(Integer, nullable=False, default=0)
    total_drafted = Column(Integer, nullable=False, default=0)

    clinics = relationship("Clinic", back_populates="city_run", cascade="all, delete-orphan", passive_deletes=True)
    policy_results = relationship("ClinicPolicyResult", back_populates="city_run", cascade="all, delete-orphan", passive_deletes=True)


class Clinic(Base):
    __tablename__ = "clinics"
    __table_args__ = (UniqueConstraint("place_id", name="uq_clinic_place_id"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    city_run_id = Column(UUID(as_uuid=True), ForeignKey("city_runs.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(2), nullable=False)
    zip = Column(String(10), nullable=True)
    phone = Column(String(20), nullable=True)
    website = Column(String(500), nullable=True)
    google_maps_url = Column(String(1000), nullable=False)
    place_id = Column(String(255), nullable=False)
    overall_rating = Column(Float, nullable=True)
    total_reviews = Column(Integer, nullable=True)
    status = Column(Enum(ClinicStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=ClinicStatus.SCRAPED)

    city_run = relationship("CityRun", back_populates="clinics")
    reviews = relationship("Review", back_populates="clinic", cascade="all, delete-orphan", passive_deletes=True)
    contacts = relationship("Contact", back_populates="clinic", cascade="all, delete-orphan", passive_deletes=True)
    email_drafts = relationship("EmailDraft", back_populates="clinic", cascade="all, delete-orphan", passive_deletes=True)
    policy_results = relationship("ClinicPolicyResult", back_populates="clinic", cascade="all, delete-orphan", passive_deletes=True)


class Review(Base):
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id = Column(UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    author = Column(String(255), nullable=True)
    rating = Column(Integer, nullable=True)
    date = Column(DateTime, nullable=True)
    text = Column(Text, nullable=False)
    insurance_flag = Column(Boolean, nullable=False, default=False)
    flag_reason = Column(Enum(FlagReason, values_callable=lambda x: [e.value for e in x]), nullable=True)
    fault_party = Column(
        Enum(FaultParty, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=FaultParty.NONE,
    )
    issue_category = Column(
        Enum(IssueCategory, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    classification_confidence = Column(Float, nullable=True)
    llm_severity_score = Column(Integer, nullable=True)
    explicit_insurance_mention = Column(Boolean, nullable=True)
    keyword_matches = Column(JSONB, nullable=True)
    llm_reasoning = Column(Text, nullable=True)

    clinic = relationship("Clinic", back_populates="reviews")


class ClinicPolicyResult(Base):
    __tablename__ = "clinic_policy_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    city_run_id = Column(UUID(as_uuid=True), ForeignKey("city_runs.id", ondelete="CASCADE"), nullable=False)
    clinic_id = Column(UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    policy_version = Column(String(16), nullable=False, default="v1")
    qualification_profile = Column(String(32), nullable=False)
    qualification_threshold = Column(Float, nullable=False)
    policy_config = Column(JSONB, nullable=False)
    is_qualified = Column(Boolean, nullable=False)
    decision_reason = Column(String(100), nullable=False)
    insurer_fault_reviews = Column(Integer, nullable=False, default=0)
    clinic_fault_reviews = Column(Integer, nullable=False, default=0)
    shared_fault_reviews = Column(Integer, nullable=False, default=0)
    unique_insurer_reviewers = Column(Integer, nullable=False, default=0)
    dominant_issue_category = Column(String(64), nullable=True)
    dominant_issue_category_reviews = Column(Integer, nullable=False, default=0)
    recent_insurer_fault_reviews = Column(Integer, nullable=False, default=0)
    recent_month_cluster_peak = Column(Integer, nullable=False, default=0)
    total_reviews_known = Column(Integer, nullable=False, default=0)
    complaint_rate = Column(Float, nullable=False, default=0.0)
    effective_insurer_signal = Column(Float, nullable=False, default=0.0)
    base_score = Column(Float, nullable=False, default=0.0)
    confidence_score = Column(Float, nullable=False, default=0.0)
    final_score = Column(Float, nullable=False, default=0.0)
    insurer_signal_score = Column(Float, nullable=False, default=0.0)
    complaint_rate_score = Column(Float, nullable=False, default=0.0)
    recency_score = Column(Float, nullable=False, default=0.0)
    reviewer_uniqueness_score = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    city_run = relationship("CityRun", back_populates="policy_results")
    clinic = relationship("Clinic", back_populates="policy_results")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id = Column(UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    title = Column(String(255), nullable=True)
    source = Column(String(50), nullable=False, default="apollo")
    confidence_score = Column(Float, nullable=True)
    found_at = Column(DateTime, nullable=False, default=utcnow)

    clinic = relationship("Clinic", back_populates="contacts")
    email_drafts = relationship("EmailDraft", back_populates="contact")


class EmailDraft(Base):
    __tablename__ = "email_drafts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id = Column(UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    subject_variants = Column(JSONB, nullable=True)
    status = Column(Enum(DraftStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=DraftStatus.DRAFT)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    exported_at = Column(DateTime, nullable=True)
    export_format = Column(Enum(ExportFormat, values_callable=lambda x: [e.value for e in x]), nullable=True)

    clinic = relationship("Clinic", back_populates="email_drafts")
    contact = relationship("Contact", back_populates="email_drafts")
