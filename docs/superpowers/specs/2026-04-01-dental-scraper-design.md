# Dental Clinic Insurance Complaint Scraper & Outreach Pipeline
**Date:** 2026-04-01  
**Project:** LavenderHealth  
**Status:** Approved

---

## Overview

A scalable web scraping and outreach pipeline that identifies dental clinics whose Google reviews indicate insurance claim problems, enriches those clinics with contact emails via Apollo, and generates personalized outreach email drafts — all managed through a CLI, web dashboard, and scheduler.

Initial target: Houston, TX. Designed to scale to any US city.

---

## Architecture

Three interfaces (CLI, Dashboard, Scheduler) all enqueue jobs to a single **Celery + Redis** task queue. The pipeline processes jobs through four sequential stages and persists all state to **PostgreSQL**.

```
┌─────────────────────────────────────────────────────────────┐
│                        INTERFACES                           │
│  CLI (click)          Dashboard (FastAPI+React)   Scheduler │
│  python run.py        localhost:8000              APScheduler│
└───────────────────────────┬─────────────────────────────────┘
                            │ enqueue job
                    ┌───────▼────────┐
                    │  Celery + Redis │  (task queue)
                    └───────┬────────┘
                            │
          ┌─────────────────┼──────────────────────┐
          ▼                 ▼                        ▼
   ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐
   │  Stage 1    │  │  Stage 2     │  │  Stage 3            │
   │  Scraper    │  │  Filter      │  │  Enrichment         │
   │  Playwright │  │  Keywords +  │  │  Apollo API         │
   │  Google Maps│  │  LLM verify  │  │  (find emails)      │
   └──────┬──────┘  └──────┬───────┘  └────────┬────────────┘
          │                │                    │
          └────────────────┼────────────────────┘
                           ▼
                  ┌─────────────────┐
                  │  Stage 4        │
                  │  Email Drafter  │
                  │  LLM-generated  │
                  │  per clinic     │
                  └────────┬────────┘
                           │
                  ┌────────▼────────┐
                  │   PostgreSQL    │
                  └─────────────────┘
```

**Key principle:** Stages are sequential within a single city run (1→2→3→4). Each stage is a discrete Celery task — independently retryable without re-running prior stages. Multiple city runs can execute in parallel across separate Celery workers.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Scraping | Playwright (headless Chromium) |
| Task Queue | Celery + Redis |
| Database | PostgreSQL |
| Backend API | FastAPI |
| Frontend | React + Tailwind CSS |
| Scheduling | APScheduler (embedded in FastAPI) |
| LLM | claude-haiku-4-5-20251001 (filter) + claude-sonnet-4-6 (email drafts) |
| Contact Enrichment | Apollo API |
| CLI | Click |
| PDF Export | WeasyPrint |

---

## Data Model

### CityRun
Tracks a single pipeline execution for a city.

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| city | string | e.g. "Houston" |
| state | string | e.g. "TX" |
| status | enum | pending / running / completed / failed |
| triggered_by | enum | cli / dashboard / scheduler |
| max_reviews | int | configurable per run, default 200 |
| created_at | timestamp | |
| completed_at | timestamp | nullable |
| total_clinics_found | int | |
| total_qualified | int | passed filter |
| total_enriched | int | email found |
| total_drafted | int | email draft created |

### Clinic
| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| city_run_id | UUID | FK → CityRun |
| name | string | |
| address | string | |
| city, state, zip | string | |
| phone | string | nullable |
| website | string | nullable |
| google_maps_url | string | |
| place_id | string | **dedup key** — globally unique constraint; re-running a city reuses the existing Clinic record |
| overall_rating | float | |
| total_reviews | int | |
| status | enum | scraped / filtered_out / qualified / enriched / drafted |

### Review
| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| clinic_id | UUID | FK → Clinic |
| author | string | |
| rating | int | 1–5 |
| date | date | |
| text | text | |
| insurance_flag | bool | set by Stage 2 |
| flag_reason | enum | keyword / llm / both |
| keyword_matches | jsonb | list of matched keywords/phrases |
| llm_reasoning | text | one-sentence LLM explanation |

### Contact
| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| clinic_id | UUID | FK → Clinic |
| email | string | |
| first_name, last_name | string | nullable |
| title | string | e.g. "Office Manager" |
| source | string | "apollo" |
| confidence_score | float | from Apollo |
| found_at | timestamp | |

### EmailDraft
| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| clinic_id | UUID | FK → Clinic |
| contact_id | UUID | FK → Contact |
| subject | string | |
| body | text | personalized HTML |
| subject_variants | jsonb | A/B test subject lines |
| status | enum | draft / approved / sent |
| created_at | timestamp | |
| exported_at | timestamp | nullable |
| export_format | enum | html / pdf |

---

## Pipeline Stages

### Stage 1 — Scraper

**Input:** city, state, max_reviews  
**Output:** Clinic + Review records in DB, status=`scraped`

1. Playwright opens Google Maps, searches `"dental clinics in {city}, {state}"`
2. Scrolls results panel until no new clinics load (captures all visible listings)
3. For each clinic:
   - Extracts name, address, rating, review count, Maps URL, place_id
   - Deduplicates against existing `place_id` records — skips if already exists for this city_run
   - Opens reviews panel, sorts by **"Newest"** — scrapes up to `max_reviews` (default 200)
   - For clinics with 200+ total reviews: runs a **second pass** sorted by **"Lowest Rated"** to surface buried complaints
4. Anti-detection: rotating user-agent headers, randomized 2–5s delays, optional proxy via env var `PROXY_URL`

### Stage 2 — Filter (Hybrid)

**Input:** Clinic records with status=`scraped`  
**Output:** Clinics updated to `qualified` or `filtered_out`; Review.insurance_flag set

**Keyword layer (fast pre-filter):**

```
Tier 1 — Direct insurance terms:
  "insurance claim", "insurance denied", "claim rejected", "claim not processed",
  "reimbursement", "EOB", "explanation of benefits", "out of pocket", 
  "overcharged", "insurance fraud", "billed incorrectly"

Tier 2 — Indirect billing complaints:
  "never paid", "still waiting", "where is my money", "billing issue",
  "charged wrong", "double charged", "won't submit", "didn't file",
  "insurance won't cover", "balance billing"

Tier 3 — Sentiment signals (require corroboration):
  "scam", "dishonest", "deceptive", "misleading", "stole", "theft"
```

**Qualification threshold for LLM review:**
- 2+ reviews hitting Tier 1, OR
- 4+ reviews across Tier 1 + Tier 2

**LLM layer (claude-haiku-4-5-20251001 for cost efficiency):**

Batches matched reviews and sends to LLM with strict prompt:
> "Does this review describe a problem with insurance claim processing, reimbursement, or billing fraud at a dental clinic? Answer YES or NO, then one sentence explaining why."

- Only clinics where LLM confirms 2+ YES reviews advance to `qualified`
- LLM reasoning stored in `Review.llm_reasoning` for auditability
- `Review.flag_reason` tracks whether keyword, LLM, or both triggered the flag

### Stage 3 — Apollo Enrichment

**Input:** Clinic records with status=`qualified`  
**Output:** Contact records created; Clinic status → `enriched`

1. Queries Apollo API: clinic name + city + "dental"
2. Target job titles (in priority order): Office Manager, Billing Coordinator, Front Desk Manager, Practice Manager
3. Stores email, name, title, and Apollo confidence score
4. Clinics with no email found remain at `qualified` (not failed) — flagged in dashboard for manual lookup
5. Respects Apollo rate limits via Celery rate_limit on this task

### Stage 4 — Email Drafter

**Input:** Clinic records with status=`enriched`  
**Output:** EmailDraft records created; Clinic status → `drafted`

LLM (claude-sonnet-4-6) generates personalized email with:
- Clinic name and contact's first name
- 1–2 anonymized review excerpts that mention the insurance issue
- Empathetic framing of the problem
- Soft pitch for LavenderHealth's solution
- 3 subject line variants for A/B testing

Draft stored with status=`draft`. Human reviews in dashboard before any send.

---

## Interfaces

### CLI
```bash
# Trigger a run
python run.py scrape --city "Houston" --state "TX" --max-reviews 200

# Check run status
python run.py status --run-id <uuid>

# Export approved drafts
python run.py export --run-id <uuid> --format pdf
```

### Dashboard (FastAPI + React)

**Backend endpoints:**
```
POST   /api/runs                    # trigger new run
GET    /api/runs                    # list all runs
GET    /api/runs/{id}               # run detail + stage progress
GET    /api/clinics                 # filterable list
GET    /api/clinics/{id}/reviews    # reviews with flags
GET    /api/drafts                  # drafts with status filter
PATCH  /api/drafts/{id}             # approve / edit draft
GET    /api/drafts/{id}/export      # export single draft (?format=html|pdf)
POST   /api/drafts/export-batch     # bulk export approved drafts
```

**Frontend pages:**
- **Runs** — table of city runs, progress bars per stage, "New Run" modal
- **Clinics** — filterable grid (city, status, insurance flag count), status badges
  - *Clinic Detail* — reviews with flagged sentences highlighted, contact info
- **Drafts** — review queue, inline editor, approve/export buttons, A/B subject line picker
- **Settings** — Apollo API key, LLM provider key, proxy URL, scheduler cadence

**Design:** Matches lavenderhealth.ai — `#4d65ff` primary blue, pink/magenta accents, Open Sans font, white backgrounds, GSAP animations, generous whitespace. Feels like a native LavenderHealth internal tool.

### Scheduler (APScheduler)
- Configured via Settings page in dashboard
- Supports per-city cadence (e.g., Houston every Monday 9am CT)
- Each scheduled run creates a `CityRun` with `triggered_by=scheduler`
- Missed runs (server down) are logged but not auto-retried

---

## Scalability

- **New city:** pass any `--city` + `--state` to CLI or dashboard — no code changes
- **Parallel cities:** multiple Celery workers can process different city runs simultaneously
- **Deduplication:** `place_id` ensures re-running a city never creates duplicate clinic records
- **Volume:** PostgreSQL handles millions of reviews; add indexes on `city_run_id`, `status`, `insurance_flag`
- **Proxy rotation:** pluggable via `PROXY_URL` env var — swap in a proxy pool when Google blocks scale

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Google blocks scraper | Retry with backoff (3x), then mark stage as failed, alert in dashboard |
| Apollo rate limit | Celery rate_limit on Stage 3; auto-resumes when limit resets |
| LLM API timeout | Retry 2x, then skip clinic and flag for manual review |
| No email found via Apollo | Clinic stays at `qualified`, surfaced in dashboard "No Contact" filter |
| Duplicate city run | Warn user in dashboard; existing clinic records reused via place_id dedup |

---

## Project Structure

```
lavenderhealth/
├── scraper/
│   ├── playwright_scraper.py     # Stage 1
│   └── anti_detection.py         # user agents, delays, proxy
├── filter/
│   ├── keyword_filter.py         # Tier 1/2/3 matching
│   └── llm_filter.py             # Claude API calls, batch processing
├── enrichment/
│   └── apollo_client.py          # Stage 3
├── drafter/
│   └── email_drafter.py          # Stage 4, LLM prompts
├── pipeline/
│   ├── tasks.py                  # Celery task definitions
│   └── celery_app.py             # Celery + Redis config
├── db/
│   ├── models.py                 # SQLAlchemy models
│   └── migrations/               # Alembic migrations
├── api/
│   ├── main.py                   # FastAPI app
│   └── routers/                  # runs, clinics, drafts, settings
├── dashboard/                    # React frontend
│   └── src/
│       ├── pages/                # Runs, Clinics, Drafts, Settings
│       └── components/
├── cli/
│   └── run.py                    # Click CLI
├── scheduler/
│   └── scheduler.py              # APScheduler setup
├── config.py                     # env vars, settings
├── docker-compose.yml            # PostgreSQL + Redis
└── requirements.txt
```

---

## Environment Variables

```
DATABASE_URL=postgresql://...
REDIS_URL=redis://localhost:6379
APOLLO_API_KEY=...
ANTHROPIC_API_KEY=...
PROXY_URL=                        # optional
MAX_REVIEWS_DEFAULT=200
```
