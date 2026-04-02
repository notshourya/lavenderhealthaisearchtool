from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any

router = APIRouter(prefix="/api/settings", tags=["settings"])

# In-memory store — keys are set at startup via env vars
_settings: dict = {
    "apollo_api_key": "",
    "gemini_api_key": "",
    "proxy_url": "",
    "max_reviews_default": 200,
}


class SettingsPayload(BaseModel):
    apollo_api_key: str | None = None
    gemini_api_key: str | None = None
    proxy_url: str | None = None
    max_reviews_default: int | None = None


@router.get("")
def get_settings():
    return {
        **_settings,
        "apollo_api_key": "***" if _settings["apollo_api_key"] else "",
        "gemini_api_key": "***" if _settings["gemini_api_key"] else "",
    }


@router.put("")
def update_settings(payload: SettingsPayload):
    if payload.apollo_api_key is not None:
        _settings["apollo_api_key"] = payload.apollo_api_key
    if payload.gemini_api_key is not None:
        _settings["gemini_api_key"] = payload.gemini_api_key
    if payload.proxy_url is not None:
        _settings["proxy_url"] = payload.proxy_url
    if payload.max_reviews_default is not None:
        _settings["max_reviews_default"] = payload.max_reviews_default
    return {"ok": True}


# --- Scheduler endpoints ---

class ScheduleCreate(BaseModel):
    city: str
    state: str
    cron: str  # e.g. "0 9 * * 1" = every Monday 9am
    max_reviews: int = 200


@router.get("/schedules")
def list_schedules():
    from scheduler.scheduler import list_schedules as _list
    return _list()


@router.post("/schedules")
def add_schedule(payload: ScheduleCreate):
    from scheduler.scheduler import add_city_schedule
    job_id = add_city_schedule(
        city=payload.city,
        state=payload.state,
        cron=payload.cron,
        max_reviews=payload.max_reviews,
    )
    return {"job_id": job_id}


@router.delete("/schedules/{job_id}")
def remove_schedule(job_id: str):
    from scheduler.scheduler import remove_schedule as _remove
    _remove(job_id)
    return {"ok": True}
