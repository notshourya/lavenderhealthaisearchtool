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
    status = Column(Enum(CityRunStatus), nullable=False, default=CityRunStatus.PENDING)
    triggered_by = Column(Enum(TriggeredBy), nullable=False)
    max_reviews = Column(Integer, nullable=False, default=200)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    completed_at = Column(DateTime, nullable=True)
    total_clinics_found = Column(Integer, nullable=False, default=0)
    total_qualified = Column(Integer, nullable=False, default=0)
    total_enriched = Column(Integer, nullable=False, default=0)
    total_drafted = Column(Integer, nullable=False, default=0)

    clinics = relationship("Clinic", back_populates="city_run", cascade="all, delete-orphan", passive_deletes=True)


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
    status = Column(Enum(ClinicStatus), nullable=False, default=ClinicStatus.SCRAPED)

    city_run = relationship("CityRun", back_populates="clinics")
    reviews = relationship("Review", back_populates="clinic", cascade="all, delete-orphan", passive_deletes=True)
    contacts = relationship("Contact", back_populates="clinic", cascade="all, delete-orphan", passive_deletes=True)
    email_drafts = relationship("EmailDraft", back_populates="clinic", cascade="all, delete-orphan", passive_deletes=True)


class Review(Base):
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id = Column(UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    author = Column(String(255), nullable=True)
    rating = Column(Integer, nullable=True)
    date = Column(DateTime, nullable=True)
    text = Column(Text, nullable=False)
    insurance_flag = Column(Boolean, nullable=False, default=False)
    flag_reason = Column(Enum(FlagReason), nullable=True)
    keyword_matches = Column(JSONB, nullable=True)
    llm_reasoning = Column(Text, nullable=True)

    clinic = relationship("Clinic", back_populates="reviews")


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
    status = Column(Enum(DraftStatus), nullable=False, default=DraftStatus.DRAFT)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    exported_at = Column(DateTime, nullable=True)
    export_format = Column(Enum(ExportFormat), nullable=True)

    clinic = relationship("Clinic", back_populates="email_drafts")
    contact = relationship("Contact", back_populates="email_drafts")
