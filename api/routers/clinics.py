import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas import ClinicResponse, ReviewResponse
from db.models import Clinic, Review

router = APIRouter(prefix="/api/clinics", tags=["clinics"])


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
        flag_count = sum(1 for r in clinic.reviews if r.insurance_flag)
        resp = ClinicResponse.model_validate(clinic)
        resp.insurance_flag_count = flag_count
        result.append(resp)
    return result


@router.get("/{clinic_id}/reviews", response_model=list[ReviewResponse])
def get_clinic_reviews(clinic_id: uuid.UUID, db: Session = Depends(get_db)):
    clinic = db.query(Clinic).filter_by(id=clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return clinic.reviews
