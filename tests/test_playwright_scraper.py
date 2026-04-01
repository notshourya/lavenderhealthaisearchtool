import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from scraper.playwright_scraper import (
    parse_place_id_from_url,
    build_search_query,
    ClinicData,
    ReviewData,
)


def test_build_search_query():
    query = build_search_query("Houston", "TX")
    assert "dental" in query.lower()
    assert "Houston" in query
    assert "TX" in query


def test_parse_place_id_from_url_standard():
    url = "https://www.google.com/maps/place/Bright+Smiles/@29.74,-95.37,17z/data=!3m1!4b1!4m6!3m5!1s0x8640b8b4ae:0x12345abcde!8m2!3d29.74!4d-95.37"
    place_id = parse_place_id_from_url(url)
    assert place_id is not None
    assert len(place_id) > 0


def test_parse_place_id_falls_back_to_name_hash():
    url = "https://www.google.com/maps/place/Some+Dental+Office/"
    place_id = parse_place_id_from_url(url, fallback_name="Some Dental Office")
    assert place_id is not None


def test_clinic_data_is_dataclass():
    clinic = ClinicData(
        name="Test Dental",
        address="123 Main St",
        city="Houston",
        state="TX",
        google_maps_url="https://maps.google.com/test",
        place_id="ChIJ123",
        overall_rating=4.2,
        total_reviews=150,
    )
    assert clinic.name == "Test Dental"
    assert clinic.reviews == []


def test_review_data_is_dataclass():
    review = ReviewData(
        author="John D.",
        rating=1,
        text="They denied my claim.",
        date=None,
    )
    assert review.author == "John D."
    assert review.rating == 1
