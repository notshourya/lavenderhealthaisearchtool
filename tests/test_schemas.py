import pytest
from api.schemas import (
    CityRunCreate, CityRunResponse,
    ClinicResponse, ReviewResponse,
    DraftPatch, DraftResponse,
)
import uuid
from datetime import datetime


def test_city_run_create_validates_state():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        CityRunCreate(city="Houston", state="TEXAS", max_reviews=200)  # state must be 2 chars


def test_city_run_create_default_max_reviews():
    run = CityRunCreate(city="Houston", state="TX")
    assert run.max_reviews == 0


def test_draft_patch_status_enum():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        DraftPatch(status="invalid_status")
