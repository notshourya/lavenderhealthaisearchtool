import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator


class CityRunCreate(BaseModel):
    city: str
    state: str
    max_reviews: int = 200
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


class ReviewResponse(BaseModel):
    id: uuid.UUID
    author: str | None
    rating: int | None
    text: str
    insurance_flag: bool
    flag_reason: str | None
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

    class Config:
        from_attributes = True


class ContactResponse(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str | None
    last_name: str | None
    title: str | None
    confidence_score: float | None

    class Config:
        from_attributes = True


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
