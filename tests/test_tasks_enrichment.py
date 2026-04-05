import pytest
import uuid
from unittest.mock import MagicMock, patch

from db.models import ClinicStatus, DraftStatus


@pytest.fixture
def db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from db.models import Base
    engine = create_engine("postgresql://lavender:lavender@localhost:5433/lavenderhealth_test")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


def make_qualified_clinic(session):
    from db.models import CityRun, Clinic, Review, TriggeredBy
    run = CityRun(city="Houston", state="TX", triggered_by=TriggeredBy.CLI)
    session.add(run)
    session.flush()
    clinic = Clinic(
        city_run_id=run.id,
        name="Test Dental",
        city="Houston",
        state="TX",
        google_maps_url="https://maps.google.com/td",
        place_id=f"ChIJ_ENRICH_{uuid.uuid4().hex[:8]}",
        status=ClinicStatus.QUALIFIED,
    )
    session.add(clinic)
    session.flush()
    session.add(Review(
        clinic_id=clinic.id,
        text="Insurance claim denied.",
        insurance_flag=True,
        llm_reasoning="Clear insurance complaint.",
    ))
    session.commit()
    return run, clinic


def test_enrich_clinics_task_creates_contact(db_session):
    from pipeline.tasks_enrichment import enrich_clinics_task
    from enrichment.apollo_client import ApolloContact

    run, clinic = make_qualified_clinic(db_session)

    mock_contacts = [
        ApolloContact(
            email="mgr@testdental.com",
            first_name="Jane",
            last_name="Doe",
            title="Office Manager",
            confidence_score=0.95,
        ),
        ApolloContact(
            email="billing@testdental.com",
            first_name="Bob",
            last_name="Smith",
            title="Billing Coordinator",
            confidence_score=0.9,
        ),
    ]

    with patch("pipeline.tasks_enrichment.find_clinic_contacts", return_value=mock_contacts):
        with patch("pipeline.tasks_enrichment.SessionLocal") as mock_sl:
            mock_sl.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_sl.return_value.__exit__ = MagicMock(return_value=False)
            enrich_clinics_task(str(run.id))

    db_session.refresh(clinic)
    assert clinic.status == ClinicStatus.ENRICHED
    assert len(clinic.contacts) == 2
    assert clinic.contacts[0].email == "mgr@testdental.com"


def test_enrich_clinics_task_uses_clinic_website_when_lookuping_contacts(db_session):
    from pipeline.tasks_enrichment import enrich_clinics_task
    from enrichment.apollo_client import ApolloContact

    run, clinic = make_qualified_clinic(db_session)
    clinic.website = "https://www.testdental.com"
    db_session.commit()

    mock_contact = ApolloContact(
        email="mgr@testdental.com",
        first_name="Jane",
        last_name="Doe",
        title="Office Manager",
        confidence_score=0.95,
    )

    with patch("pipeline.tasks_enrichment.find_clinic_contacts", return_value=[mock_contact]) as mock_lookup:
        with patch("pipeline.tasks_enrichment.SessionLocal") as mock_sl:
            mock_sl.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_sl.return_value.__exit__ = MagicMock(return_value=False)
            enrich_clinics_task(str(run.id))

    mock_lookup.assert_called_once_with("Test Dental", "Houston", "TX", "https://www.testdental.com")


def test_enrich_clinics_task_stays_qualified_when_no_contact(db_session):
    from pipeline.tasks_enrichment import enrich_clinics_task

    run, clinic = make_qualified_clinic(db_session)

    with patch("pipeline.tasks_enrichment.find_clinic_contacts", return_value=[]):
        with patch("pipeline.tasks_enrichment.SessionLocal") as mock_sl:
            mock_sl.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_sl.return_value.__exit__ = MagicMock(return_value=False)
            enrich_clinics_task(str(run.id))

    db_session.refresh(clinic)
    assert clinic.status == ClinicStatus.QUALIFIED  # Not failed, stays qualified


def test_draft_emails_task_creates_draft(db_session):
    from pipeline.tasks_enrichment import draft_emails_task
    from drafter.email_drafter import EmailDraftResult
    from db.models import CityRun, Clinic, Review, Contact, TriggeredBy

    run = CityRun(city="Houston", state="TX", triggered_by=TriggeredBy.CLI)
    db_session.add(run)
    db_session.flush()
    clinic = Clinic(
        city_run_id=run.id,
        name="Draft Dental",
        city="Houston",
        state="TX",
        google_maps_url="https://maps.google.com/dd",
        place_id=f"ChIJ_DRAFT_{uuid.uuid4().hex[:8]}",
        status=ClinicStatus.ENRICHED,
    )
    db_session.add(clinic)
    db_session.flush()
    contact = Contact(
        clinic_id=clinic.id,
        email="mgr@draftdental.com",
        first_name="Bob",
        title="Office Manager",
        confidence_score=0.9,
    )
    db_session.add(contact)
    db_session.add(Review(clinic_id=clinic.id, text="Claim denied.", insurance_flag=True))
    db_session.commit()

    mock_result = EmailDraftResult(
        subject="A concern about Draft Dental",
        subject_variants=["Subject A", "Subject B", "Subject C"],
        body="<p>Hi Bob,</p><p>We noticed...</p>",
    )

    with patch("pipeline.tasks_enrichment.draft_outreach_email", return_value=mock_result):
        with patch("pipeline.tasks_enrichment.SessionLocal") as mock_sl:
            mock_sl.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_sl.return_value.__exit__ = MagicMock(return_value=False)
            draft_emails_task(str(run.id))

    db_session.refresh(clinic)
    assert clinic.status == ClinicStatus.DRAFTED
    assert len(clinic.email_drafts) == 1
    assert clinic.email_drafts[0].status == DraftStatus.DRAFT
    assert clinic.email_drafts[0].subject == "A concern about Draft Dental"
