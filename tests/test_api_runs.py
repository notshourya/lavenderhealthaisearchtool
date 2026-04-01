import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base, CityRun, TriggeredBy
from api.deps import get_db

TEST_DB_URL = "postgresql://lavender:lavender@localhost:5433/lavenderhealth_test"


@pytest.fixture(scope="module")
def test_engine():
    engine = create_engine(TEST_DB_URL)
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


def test_list_runs_empty(client):
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
