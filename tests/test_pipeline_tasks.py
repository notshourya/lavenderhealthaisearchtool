import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import uuid

from db.models import CityRunStatus, ClinicStatus


def make_db_run(session):
    from db.models import CityRun, TriggeredBy
    run = CityRun(city="Houston", state="TX", triggered_by=TriggeredBy.CLI, max_reviews=200)
    session.add(run)
    session.commit()
    return run


@pytest.fixture
def db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from db.models import Base
    engine = create_engine("postgresql://lavender:lavender@localhost:5433/lavenderhealth_test")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


def test_scrape_city_task_updates_run_status(db_session):
    from pipeline.tasks import scrape_city_task
    run = make_db_run(db_session)

    mock_clinic = MagicMock()
    mock_clinic.name = "Test Dental"
    mock_clinic.address = "123 Main"
    mock_clinic.city = "Houston"
    mock_clinic.state = "TX"
    mock_clinic.zip = None
    mock_clinic.phone = None
    mock_clinic.website = None
    mock_clinic.google_maps_url = "https://maps.google.com/test"
    mock_clinic.place_id = f"ChIJ_TASK_TEST_{uuid.uuid4().hex[:8]}"
    mock_clinic.overall_rating = 3.5
    mock_clinic.total_reviews = 42
    mock_clinic.reviews = []

    with patch("pipeline.tasks.scrape_city", new_callable=AsyncMock, return_value=[mock_clinic]):
        with patch("pipeline.tasks.SessionLocal") as mock_sl:
            mock_sl.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_sl.return_value.__exit__ = MagicMock(return_value=False)
            scrape_city_task(str(run.id))

    db_session.refresh(run)
    assert run.total_clinics_found == 1


def test_filter_clinics_task_marks_qualified(db_session):
    from pipeline.tasks import filter_clinics_task
    from db.models import CityRun, Clinic, Review, TriggeredBy

    run = CityRun(city="Houston", state="TX", triggered_by=TriggeredBy.CLI)
    db_session.add(run)
    db_session.flush()

    clinic = Clinic(
        city_run_id=run.id,
        name="Complaint Dental",
        city="Houston",
        state="TX",
        google_maps_url="https://maps.google.com/c",
        place_id=f"ChIJ_FILTER_{uuid.uuid4().hex[:8]}",
    )
    db_session.add(clinic)
    db_session.flush()

    # 2 Tier1 reviews → qualifies for LLM
    db_session.add(Review(clinic_id=clinic.id, text="Insurance claim was denied after 6 months."))
    db_session.add(Review(clinic_id=clinic.id, text="They refused my reimbursement request."))
    db_session.commit()

    with patch("pipeline.tasks.classify_reviews") as mock_classify:
        mock_verdict = MagicMock()
        mock_verdict.is_insurance_complaint = True
        mock_verdict.reasoning = "Clear insurance complaint."
        mock_classify.return_value = [mock_verdict, mock_verdict]

        with patch("pipeline.tasks.SessionLocal") as mock_sl:
            mock_sl.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_sl.return_value.__exit__ = MagicMock(return_value=False)
            filter_clinics_task(str(run.id))

    db_session.refresh(clinic)
    assert clinic.status == ClinicStatus.QUALIFIED
