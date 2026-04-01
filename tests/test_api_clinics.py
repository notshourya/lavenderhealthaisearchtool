import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base, CityRun, Clinic, Review, TriggeredBy, ClinicStatus
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


def test_get_clinic_reviews_not_found(client):
    response = client.get(f"/api/clinics/{uuid.uuid4()}/reviews")
    assert response.status_code == 404
