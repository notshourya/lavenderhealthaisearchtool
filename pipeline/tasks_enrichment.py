# Enrichment + Drafter tasks — implemented in Plan 03
from pipeline.celery_app import celery_app


@celery_app.task
def enrich_clinics_task(city_run_id: str) -> None:
    pass  # Placeholder — implemented in Plan 03
