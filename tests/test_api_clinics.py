import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base, CityRun, Clinic, Review, Contact, TriggeredBy, ClinicStatus, FaultParty, IssueCategory
from api.deps import get_db

TEST_DB_URL = "postgresql://lavender:lavender@localhost:5433/lavenderhealth_test"


@pytest.fixture(scope="module")
def test_engine():
    engine = create_engine(TEST_DB_URL)
    Base.metadata.drop_all(engine)
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


def seed_clinic(db, status=ClinicStatus.QUALIFIED):
    run = CityRun(city="Houston", state="TX", triggered_by=TriggeredBy.CLI)
    db.add(run)
    db.flush()
    clinic = Clinic(
        city_run_id=run.id,
        name="Test Dental",
        city="Houston",
        state="TX",
        google_maps_url="https://maps.google.com/test",
        place_id=f"ChIJ_API_{uuid.uuid4().hex[:8]}",
        status=status,
    )
    db.add(clinic)
    db.flush()
    db.add(Review(
        clinic_id=clinic.id,
        text="Insurance claim denied.",
        insurance_flag=True,
        fault_party=FaultParty.INSURER,
        issue_category=IssueCategory.CLAIM_DENIAL,
        llm_severity_score=4,
        explicit_insurance_mention=True,
    ))
    db.add(Contact(
        clinic_id=clinic.id,
        email="mgr@testdental.com",
        first_name="Jane",
        last_name="Doe",
        title="Office Manager",
        confidence_score=0.95,
    ))
    db.commit()
    return clinic


def test_list_clinics(client, test_db):
    seed_clinic(test_db)
    response = client.get("/api/clinics")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_list_clinics_filter_by_status(client, test_db):
    seed_clinic(test_db, status=ClinicStatus.DRAFTED)
    response = client.get("/api/clinics?status=drafted")
    assert response.status_code == 200
    for c in response.json():
        assert c["status"] == "drafted"


def test_get_clinic_reviews(client, test_db):
    clinic = seed_clinic(test_db)
    response = client.get(f"/api/clinics/{clinic.id}/reviews")
    assert response.status_code == 200
    reviews = response.json()
    assert len(reviews) >= 1
    assert reviews[0]["insurance_flag"] is True
    assert reviews[0]["fault_party"] == "insurer"
    assert reviews[0]["llm_severity_score"] == 4
    assert reviews[0]["explicit_insurance_mention"] is True


def test_get_clinic_detail_includes_diagnostics(client, test_db):
    clinic = seed_clinic(test_db)
    response = client.get(f"/api/clinics/{clinic.id}")
    assert response.status_code == 200
    payload = response.json()

    assert payload["clinic"]["id"] == str(clinic.id)
    assert payload["clinic"]["insurance_flag_count"] >= 1
    assert payload["clinic"]["insurer_fault_count"] >= 1
    assert len(payload["contacts"]) >= 1
    assert payload["contacts"][0]["email"] == "mgr@testdental.com"
    assert payload["diagnostics"]["confirmed_complaints"] >= 1
    assert payload["diagnostics"]["insurer_fault_reviews"] >= 1
    assert "min_complaint_rate_required" in payload["diagnostics"]
    assert payload["diagnostics"]["qualification_profile"] in {"strict", "balanced", "recall"}
    assert payload["diagnostics"]["qualification_threshold"] > 0
    assert 0.0 <= payload["diagnostics"]["base_score"] <= 1.0
    assert 0.0 <= payload["diagnostics"]["confidence_score"] <= 1.0
    assert payload["diagnostics"]["final_score"] >= 0.0
    assert len(payload["reviews"]) >= 1


def test_get_clinic_reviews_not_found(client):
    response = client.get(f"/api/clinics/{uuid.uuid4()}/reviews")
    assert response.status_code == 404
