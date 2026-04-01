import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from db.models import (
    Base, CityRun, Clinic, Review, Contact, EmailDraft,
    CityRunStatus, TriggeredBy, ClinicStatus, FlagReason, DraftStatus,
)

TEST_DB_URL = "postgresql://lavender:lavender@localhost:5433/lavenderhealth_test"


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(TEST_DB_URL)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    db = Session()
    yield db
    db.close()
    transaction.rollback()
    connection.close()


def make_run(session, city="Houston", state="TX"):
    run = CityRun(city=city, state=state, triggered_by=TriggeredBy.CLI)
    session.add(run)
    session.flush()
    return run


def make_clinic(session, run, place_id="ChIJ_TEST_001"):
    clinic = Clinic(
        city_run_id=run.id,
        name="Bright Smiles Dental",
        city=run.city,
        state=run.state,
        google_maps_url="https://maps.google.com/?cid=123",
        place_id=place_id,
    )
    session.add(clinic)
    session.flush()
    return clinic


def test_city_run_defaults(session):
    run = make_run(session)
    assert run.id is not None
    assert run.status == CityRunStatus.PENDING
    assert run.max_reviews == 200
    assert run.total_clinics_found == 0
    assert run.triggered_by == TriggeredBy.CLI


def test_clinic_defaults(session):
    run = make_run(session)
    clinic = make_clinic(session, run)
    assert clinic.id is not None
    assert clinic.status == ClinicStatus.SCRAPED


def test_place_id_unique_constraint(session):
    run = make_run(session)
    make_clinic(session, run, place_id="ChIJ_DUPE")

    duplicate = Clinic(
        city_run_id=run.id,
        name="Other Dental",
        city="Houston",
        state="TX",
        google_maps_url="https://maps.google.com/?cid=999",
        place_id="ChIJ_DUPE",
    )
    session.add(duplicate)
    with pytest.raises(IntegrityError):
        session.flush()


def test_review_defaults(session):
    run = make_run(session)
    clinic = make_clinic(session, run)
    review = Review(
        clinic_id=clinic.id,
        text="They denied my insurance claim and never explained why.",
        rating=1,
    )
    session.add(review)
    session.flush()
    assert review.id is not None
    assert review.insurance_flag is False
    assert review.flag_reason is None


def test_contact_creation(session):
    run = make_run(session)
    clinic = make_clinic(session, run)
    contact = Contact(
        clinic_id=clinic.id,
        email="manager@brightsmiles.com",
        first_name="Jane",
        last_name="Doe",
        title="Office Manager",
        confidence_score=0.92,
    )
    session.add(contact)
    session.flush()
    assert contact.id is not None
    assert contact.source == "apollo"


def test_email_draft_defaults(session):
    run = make_run(session)
    clinic = make_clinic(session, run)
    contact = Contact(
        clinic_id=clinic.id,
        email="mgr@dental.com",
        confidence_score=0.85,
    )
    session.add(contact)
    session.flush()

    draft = EmailDraft(
        clinic_id=clinic.id,
        contact_id=contact.id,
        subject="A concern we noticed about Bright Smiles Dental",
        body="<p>Dear Jane,</p><p>We noticed some patterns...</p>",
        subject_variants=["Subject A", "Subject B", "Subject C"],
    )
    session.add(draft)
    session.flush()
    assert draft.id is not None
    assert draft.status == DraftStatus.DRAFT
    assert draft.exported_at is None


def test_clinic_relationships(session):
    run = make_run(session)
    clinic = make_clinic(session, run)

    session.add(Review(clinic_id=clinic.id, text="Insurance denied.", rating=1))
    session.add(Review(clinic_id=clinic.id, text="Great experience!", rating=5))
    session.flush()

    assert len(clinic.reviews) == 2
    assert clinic.city_run.city == "Houston"


def test_get_session_yields_and_closes(monkeypatch):
    from unittest.mock import MagicMock, patch
    import db.session as session_module

    mock_db = MagicMock()
    mock_session_cls = MagicMock(return_value=mock_db)

    with patch.object(session_module, "SessionLocal", mock_session_cls):
        gen = session_module.get_session()
        db = next(gen)
        assert db is mock_db
        try:
            next(gen)
        except StopIteration:
            pass
    mock_db.close.assert_called_once()
