import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas import CityRunCreate, CityRunResponse
from db.models import CityRun, TriggeredBy
from pipeline.tasks import scrape_city_task

router = APIRouter(prefix="/api/runs", tags=["runs"])


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
