# LavenderHealth Dental Outreach Pipeline

A production-oriented pipeline that discovers clinics from Google Maps, classifies insurer-vs-clinic fault signals from reviews using Gemini, enriches contact data, and generates outreach drafts.

## What This Project Does

- Scrapes clinics and reviews by city/state.
- Applies hybrid filtering (keyword + LLM classification).
- Persists all run/clinic/review state in PostgreSQL.
- Uses Celery + Redis for asynchronous stage execution.
- Provides API + dashboard for monitoring runs, diagnostics, and drafts.

## Stack

- Python 3.12
- FastAPI
- SQLAlchemy + Alembic
- Celery + Redis
- PostgreSQL
- Playwright (scraping)
- Vite + React dashboard

## Repository Layout

- `api/` FastAPI routes and response schemas
- `cli/` CLI commands to start/check runs
- `db/` models and migrations
- `pipeline/` Celery app and pipeline tasks
- `scraper/` Google Maps scraping logic
- `filter/` keyword and Gemini filtering
- `enrichment/` contact enrichment integrations
- `drafter/` outreach draft generation
- `dashboard/` frontend UI
- `tests/` pytest coverage

## Local Setup

1. Create and activate a Python environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables in `.env`.
4. Start infrastructure:

```bash
docker compose up -d postgres redis
```

5. Run database migrations:

```bash
alembic upgrade head
```

## Running The Backend

Start API server:

```bash
PYTHONPATH=. uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Start Celery worker:

```bash
PYTHONPATH=. celery -A pipeline.celery_app worker --loglevel=info
```

## Running The Dashboard

```bash
cd dashboard
npm install
npm run dev
```

## Triggering Runs

Run a city pipeline from CLI:

```bash
PYTHONPATH=. python3 cli/run.py scrape --city "Austin" --state TX --max-reviews 1
```

Check run status:

```bash
PYTHONPATH=. python3 cli/run.py status --run-id <RUN_ID>
```

## Testing

```bash
PYTHONPATH=. pytest -q
```

## Notes

- `max-reviews=0` means uncapped scrape depth.
- If Gemini calls intermittently fail, verify network/DNS stability and project rate limits.
