import pytest
from unittest.mock import patch, MagicMock
from enrichment.apollo_client import find_clinic_contacts, ApolloContact, PRIORITY_TITLES


def make_apollo_response(people: list[dict]) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"people": people}
    return mock_resp


def test_find_contacts_returns_office_manager_first():
    people = [
        {"email": "billing@dental.com", "first_name": "Bob", "last_name": "Smith",
         "title": "Billing Coordinator", "email_status": "verified"},
        {"email": "mgr@dental.com", "first_name": "Jane", "last_name": "Doe",
         "title": "Office Manager", "email_status": "verified"},
    ]
    with patch("enrichment.apollo_client.httpx.post", return_value=make_apollo_response(people)):
        contacts = find_clinic_contacts("Bright Smiles Dental", "Houston", "TX")

    assert len(contacts) > 0
    # Office Manager should rank higher
    assert contacts[0].title == "Office Manager"


def test_find_contacts_filters_low_confidence():
    people = [
        {"email": "x@dental.com", "first_name": "A", "last_name": "B",
         "title": "Office Manager", "email_status": "invalid"},
    ]
    with patch("enrichment.apollo_client.httpx.post", return_value=make_apollo_response(people)):
        contacts = find_clinic_contacts("Test Dental", "Houston", "TX")

    assert len(contacts) == 0


def test_find_contacts_returns_empty_on_no_people():
    with patch("enrichment.apollo_client.httpx.post", return_value=make_apollo_response([])):
        contacts = find_clinic_contacts("Unknown Dental", "Houston", "TX")
    assert contacts == []


def test_find_contacts_handles_api_error():
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.json.return_value = {"error": "rate limited"}
    with patch("enrichment.apollo_client.httpx.post", return_value=mock_resp):
        contacts = find_clinic_contacts("Test Dental", "Houston", "TX")
    assert contacts == []


def test_apollo_contact_is_dataclass():
    contact = ApolloContact(
        email="test@dental.com",
        first_name="Jane",
        last_name="Doe",
        title="Office Manager",
        confidence_score=0.92,
    )
    assert contact.email == "test@dental.com"
    assert contact.confidence_score == 0.92


def test_priority_titles_includes_office_manager():
    assert any("office manager" in t.lower() for t in PRIORITY_TITLES)
    assert any("billing" in t.lower() for t in PRIORITY_TITLES)
