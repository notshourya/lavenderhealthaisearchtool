import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base, CityRun, TriggeredBy, Clinic, ClinicStatus, Review, FaultParty
from api.deps import get_db

TEST_DB_URL = "postgresql://lavender:lavender@localhost:5433/lavenderhealth_test"


@pytest.fixture(scope="module")
def test_engine():
    engine = create_engine(TEST_DB_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


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


def test_list_runs_empty(client, test_db):
    # Ensure test isolation when shared test DB contains existing records.
    test_db.query(CityRun).delete()
    test_db.commit()
    response = client.get("/api/runs")
    assert response.status_code == 200
    assert response.json() == []


def test_create_run(client):
    from unittest.mock import patch
    with patch("api.routers.runs.scrape_city_task") as mock_task:
        mock_task.delay.return_value = None
        response = client.post("/api/runs", json={
            "city": "Houston",
            "state": "TX",
            "max_reviews": 50,
        })
    assert response.status_code == 201
    data = response.json()
    assert data["city"] == "Houston"
    assert data["state"] == "TX"
    assert data["status"] == "pending"


def test_get_run_by_id(client, test_db):
    run = CityRun(city="Dallas", state="TX", triggered_by=TriggeredBy.CLI)
    test_db.add(run)
    test_db.commit()

    response = client.get(f"/api/runs/{run.id}")
    assert response.status_code == 200
    assert response.json()["city"] == "Dallas"


def test_get_run_not_found(client):
    import uuid
    response = client.get(f"/api/runs/{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_run_diagnostics(client, test_db):
    run = CityRun(city="Houston", state="TX", triggered_by=TriggeredBy.DASHBOARD)
    test_db.add(run)
    test_db.flush()

    clinic = Clinic(
        city_run_id=run.id,
        name="Test Clinic",
        city="Houston",
        state="TX",
        google_maps_url="https://maps.google.com/test",
        place_id="test_place_id_1",
        status=ClinicStatus.FILTERED_OUT,
        overall_rating=4.9,
        total_reviews=120,
    )
    test_db.add(clinic)
    test_db.flush()

    review = Review(
        clinic_id=clinic.id,
        text="They billed incorrectly and insurance denied the claim.",
        insurance_flag=True,
    )
    test_db.add(review)
    test_db.commit()

    response = client.get(f"/api/runs/{run.id}/diagnostics")
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == str(run.id)
    assert data["total_clinics"] == 1
    assert data["clinics_with_rating"] == 1
    assert data["clinics_with_review_count"] == 1
    assert data["clinics_with_scraped_reviews"] == 1
    assert data["flagged_reviews"] == 1
    assert data["stage_counts"]["filtered_out"] == 1


def test_policy_reevaluate_run_and_persist_results(client, test_db):
    run = CityRun(city="Austin", state="TX", triggered_by=TriggeredBy.DASHBOARD)
    test_db.add(run)
    test_db.flush()

    strong = Clinic(
        city_run_id=run.id,
        name="Strong Signal Dental",
        city="Austin",
        state="TX",
        google_maps_url="https://maps.google.com/strong",
        place_id="policy_place_id_strong",
        total_reviews=20,
        status=ClinicStatus.QUALIFIED,
    )
    weak = Clinic(
        city_run_id=run.id,
        name="Weak Signal Dental",
        city="Austin",
        state="TX",
        google_maps_url="https://maps.google.com/weak",
        place_id="policy_place_id_weak",
        total_reviews=20,
        status=ClinicStatus.FILTERED_OUT,
    )
    test_db.add_all([strong, weak])
    test_db.flush()

    now = datetime.now(timezone.utc)
    test_db.add_all([
        Review(
            clinic_id=strong.id,
            author="Alice",
            text="Insurance denied my claim twice and staff helped me fight it.",
            insurance_flag=True,
            fault_party=FaultParty.INSURER,
            classification_confidence=0.9,
            date=now,
        ),
        Review(
            clinic_id=strong.id,
            author="Bob",
            text="Coverage confusion caused billing issues with insurer.",
            insurance_flag=True,
            fault_party=FaultParty.INSURER,
            classification_confidence=0.85,
            date=now,
        ),
        Review(
            clinic_id=strong.id,
            author="Cara",
            text="Authorization delays by insurance again.",
            insurance_flag=True,
            fault_party=FaultParty.INSURER,
            classification_confidence=0.82,
            date=now,
        ),
        Review(
            clinic_id=weak.id,
            author="Dan",
            text="Insurance denied one claim but otherwise okay.",
            insurance_flag=True,
            fault_party=FaultParty.INSURER,
            classification_confidence=0.75,
            date=now,
        ),
        Review(
            clinic_id=weak.id,
            author="Eve",
            text="The clinic messed up billing and never fixed it.",
            insurance_flag=False,
            fault_party=FaultParty.CLINIC,
            classification_confidence=0.8,
            date=now,
        ),
        Review(
            clinic_id=weak.id,
            author="Frank",
            text="Front desk errors caused the claim to fail.",
            insurance_flag=False,
            fault_party=FaultParty.CLINIC,
            classification_confidence=0.8,
            date=now,
        ),
    ])
    test_db.commit()

    response = client.post(
        f"/api/runs/{run.id}/policy-reevaluate",
        json={"qualification_profile": "balanced"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["policy_version"] == "v1"
    assert payload["summary"]["total_clinics"] == 2
    assert payload["summary"]["qualified"] == 1
    assert payload["summary"]["filtered_out"] == 1
    assert payload["summary"]["qualification_rate"] == pytest.approx(0.5, rel=1e-6)
    assert payload["summary"]["reason_codes"][0]["code"] in {"HIGH_INSURER_COUNT", "MULTIPLE_INDEPENDENT_REVIEWERS", "HIGH_COMPLAINT_RATE"}
    assert payload["summary"]["reason_codes"][0]["label"]
    assert payload["policy_config"]["weights"]["insurer"] > 0
    assert payload["policy_config"]["normalization"]["insurer_log_base"] == 10
    assert payload["policy_config"]["confidence_formula"] == "v2"
    assert payload["results"][0]["clinic_name"] == "Strong Signal Dental"
    assert payload["results"][0]["rank"] == 1
    assert payload["results"][0]["is_qualified"] is True
    assert payload["results"][0]["policy_version"] == "v1"
    assert payload["results"][0]["top_signals"]

    list_response = client.get(f"/api/runs/{run.id}/policy-results?qualification_profile=balanced&policy_version=v1")
    assert list_response.status_code == 200
    listed = list_response.json()
    assert listed["summary"]["total_clinics"] == 2
    assert len(listed["results"]) == 2
    assert {row["clinic_name"] for row in listed["results"]} == {"Strong Signal Dental", "Weak Signal Dental"}


def test_policy_reevaluate_overwrites_same_profile_results(client, test_db):
    run = CityRun(city="Phoenix", state="AZ", triggered_by=TriggeredBy.DASHBOARD)
    test_db.add(run)
    test_db.flush()

    clinic = Clinic(
        city_run_id=run.id,
        name="Repeat Eval Dental",
        city="Phoenix",
        state="AZ",
        google_maps_url="https://maps.google.com/repeat",
        place_id="policy_place_id_repeat",
        total_reviews=10,
    )
    test_db.add(clinic)
    test_db.flush()

    now = datetime.now(timezone.utc)
    test_db.add_all([
        Review(
            clinic_id=clinic.id,
            author="User One",
            text="Insurer denied my claim.",
            insurance_flag=True,
            fault_party=FaultParty.INSURER,
            date=now,
        ),
        Review(
            clinic_id=clinic.id,
            author="User Two",
            text="Coverage confusion with insurance.",
            insurance_flag=True,
            fault_party=FaultParty.INSURER,
            date=now,
        ),
        Review(
            clinic_id=clinic.id,
            author="User Three",
            text="Authorization issue from insurer.",
            insurance_flag=True,
            fault_party=FaultParty.INSURER,
            date=now,
        ),
    ])
    test_db.commit()

    first = client.post(
        f"/api/runs/{run.id}/policy-reevaluate",
        json={"qualification_profile": "balanced"},
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/runs/{run.id}/policy-reevaluate",
        json={"qualification_profile": "balanced", "policy_version": "v2", "qualification_threshold": 0.9},
    )
    assert second.status_code == 200

    listed = client.get(f"/api/runs/{run.id}/policy-results?qualification_profile=balanced&policy_version=v1")
    assert listed.status_code == 200
    rows_v1 = listed.json()
    assert rows_v1["summary"]["total_clinics"] == 1
    assert rows_v1["results"][0]["qualification_threshold"] == pytest.approx(0.55, rel=1e-6)
    assert rows_v1["results"][0]["rank"] == 1

    listed_v2 = client.get(f"/api/runs/{run.id}/policy-results?qualification_profile=balanced&policy_version=v2")
    assert listed_v2.status_code == 200
    rows_v2 = listed_v2.json()
    assert rows_v2["summary"]["total_clinics"] == 1
    assert rows_v2["results"][0]["clinic_name"] == "Repeat Eval Dental"
    assert rows_v2["results"][0]["qualification_threshold"] == pytest.approx(0.9, rel=1e-6)
    assert rows_v2["results"][0]["rank"] == 1
