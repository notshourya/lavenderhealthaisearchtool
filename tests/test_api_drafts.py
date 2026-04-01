import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base, CityRun, Clinic, Contact, EmailDraft, Review, TriggeredBy, ClinicStatus, DraftStatus
from api.deps import get_db

TEST_DB_URL = "postgresql://lavender:lavender@localhost:5433/lavenderhealth_test"


@pytest.fixture(scope="module")
def test_engine():
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(engine)
    yield engine


@pytest.fixture
def test_db(test_engine):
    Session = sessionmaker(bind=test_engine)
    db = Session()
    yield db
    db.rollback()
    db.close()


@pytest.fixture
def client(test_db):
    from api.main import app
    app.dependency_overrides[get_db] = lambda: test_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def seed_draft(db):
    run = CityRun(city="Houston", state="TX", triggered_by=TriggeredBy.CLI)
    db.add(run)
    db.flush()
    clinic = Clinic(
        city_run_id=run.id, name="Draft Dental", city="Houston", state="TX",
        google_maps_url="https://maps.google.com/d",
        place_id=f"ChIJ_DRAFT_{uuid.uuid4().hex[:8]}",
        status=ClinicStatus.DRAFTED,
    )
    db.add(clinic)
    db.flush()
    contact = Contact(
        clinic_id=clinic.id, email="mgr@draft.com",
        first_name="Jane", confidence_score=0.9,
    )
    db.add(contact)
    db.flush()
    draft = EmailDraft(
        clinic_id=clinic.id, contact_id=contact.id,
        subject="Test Subject", body="<p>Test body</p>",
        subject_variants=["A", "B", "C"],
    )
    db.add(draft)
    db.commit()
    return draft


def test_list_drafts(client, test_db):
    seed_draft(test_db)
    response = client.get("/api/drafts")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_list_drafts_filter_by_status(client, test_db):
    response = client.get("/api/drafts?status=draft")
    assert response.status_code == 200


def test_patch_draft_approve(client, test_db):
    draft = seed_draft(test_db)
    response = client.patch(f"/api/drafts/{draft.id}", json={"status": "approved"})
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_patch_draft_edit_subject(client, test_db):
    draft = seed_draft(test_db)
    response = client.patch(f"/api/drafts/{draft.id}", json={"subject": "New Subject"})
    assert response.status_code == 200
    assert response.json()["subject"] == "New Subject"


def test_export_draft_html(client, test_db):
    draft = seed_draft(test_db)
    response = client.get(f"/api/drafts/{draft.id}/export?format=html")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_export_draft_pdf(client, test_db):
    draft = seed_draft(test_db)
    response = client.get(f"/api/drafts/{draft.id}/export?format=pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"
