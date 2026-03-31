# Enrichment + Email Drafter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Stage 3 (Apollo API contact enrichment) and Stage 4 (LLM-powered personalized email drafting) as tested modules wired into Celery tasks.

**Architecture:** `apollo_client.py` queries the Apollo API for contact emails by clinic name + city. `email_drafter.py` sends clinic + review data to claude-sonnet-4-6 and returns a structured email draft with 3 subject variants. `pipeline/tasks_enrichment.py` replaces the placeholder from Plan 02, wiring both stages into the Celery pipeline.

**Tech Stack:** Apollo API (httpx), Anthropic SDK (claude-sonnet-4-6), SQLAlchemy, Celery, pytest

**Prerequisite:** Plans 01 and 02 fully implemented.

---

## File Map

| File | Responsibility |
|---|---|
| `enrichment/apollo_client.py` | Query Apollo API, return ranked contacts |
| `drafter/email_drafter.py` | Generate personalized email draft via Claude |
| `pipeline/tasks_enrichment.py` | Replace placeholder: `enrich_clinics_task`, `draft_emails_task` |
| `tests/test_apollo_client.py` | Apollo client tests with mocked httpx |
| `tests/test_email_drafter.py` | Email drafter tests with mocked Anthropic client |
| `tests/test_tasks_enrichment.py` | Celery enrichment + drafter task tests |

---

### Task 1: Apollo Client

**Files:**
- Create: `enrichment/apollo_client.py`
- Create: `tests/test_apollo_client.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_apollo_client.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_apollo_client.py -v
```

Expected: FAIL — `enrichment.apollo_client` does not exist.

- [ ] **Step 3: Create enrichment/apollo_client.py**

```python
from dataclasses import dataclass

import httpx

import config

APOLLO_PEOPLE_URL = "https://api.apollo.io/v1/mixed_people/search"

PRIORITY_TITLES = [
    "office manager",
    "billing coordinator",
    "front desk manager",
    "practice manager",
    "billing manager",
    "insurance coordinator",
    "revenue cycle manager",
]

VALID_EMAIL_STATUSES = {"verified", "likely to engage"}


@dataclass
class ApolloContact:
    email: str
    first_name: str | None
    last_name: str | None
    title: str | None
    confidence_score: float


def _title_priority(title: str | None) -> int:
    """Lower number = higher priority."""
    if not title:
        return 999
    lower = title.lower()
    for idx, priority_title in enumerate(PRIORITY_TITLES):
        if priority_title in lower:
            return idx
    return 998


def find_clinic_contacts(name: str, city: str, state: str) -> list[ApolloContact]:
    """
    Query Apollo API for contacts at the given clinic.
    Returns contacts sorted by title priority, filtered to verified emails only.
    """
    payload = {
        "api_key": config.APOLLO_API_KEY,
        "q_organization_name": f"{name} dental",
        "q_organization_locations": [f"{city}, {state}"],
        "titles": PRIORITY_TITLES,
        "per_page": 10,
    }

    try:
        response = httpx.post(APOLLO_PEOPLE_URL, json=payload, timeout=30)
    except httpx.RequestError:
        return []

    if response.status_code != 200:
        return []

    data = response.json()
    people = data.get("people", [])

    contacts = []
    for person in people:
        email = person.get("email", "")
        status = person.get("email_status", "")
        if not email or status not in VALID_EMAIL_STATUSES:
            continue

        contacts.append(ApolloContact(
            email=email,
            first_name=person.get("first_name"),
            last_name=person.get("last_name"),
            title=person.get("title"),
            confidence_score=1.0 if status == "verified" else 0.7,
        ))

    contacts.sort(key=lambda c: _title_priority(c.title))
    return contacts
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_apollo_client.py -v
```

Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add enrichment/apollo_client.py tests/test_apollo_client.py
git commit -m "feat: add apollo api client for clinic contact enrichment"
```

---

### Task 2: Email Drafter

**Files:**
- Create: `drafter/email_drafter.py`
- Create: `tests/test_email_drafter.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_email_drafter.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from drafter.email_drafter import draft_outreach_email, EmailDraftResult, SYSTEM_PROMPT


def make_mock_response(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = [MagicMock(text=content)]
    return msg


SAMPLE_LLM_OUTPUT = """SUBJECT: A pattern we noticed about Bright Smiles Dental
SUBJECT_ALT_1: Helping Bright Smiles resolve patient insurance complaints
SUBJECT_ALT_2: We noticed something in your reviews, Bright Smiles

BODY:
<p>Hi Jane,</p>

<p>We came across some reviews for Bright Smiles Dental that mentioned challenges with insurance claims — patients expressing frustration about denied claims and unreceived reimbursements.</p>

<p>We help dental practices resolve exactly these types of billing issues faster and with less administrative burden. I'd love to share how we've helped similar practices in Houston.</p>

<p>Would you have 15 minutes this week?</p>

<p>Best,<br>LavenderHealth Team</p>"""


def test_draft_returns_email_draft_result():
    with patch("drafter.email_drafter.anthropic_client") as mock_client:
        mock_client.messages.create.return_value = make_mock_response(SAMPLE_LLM_OUTPUT)
        result = draft_outreach_email(
            clinic_name="Bright Smiles Dental",
            contact_first_name="Jane",
            flagged_review_excerpts=["Insurance claim denied.", "Reimbursement never came."],
        )
    assert isinstance(result, EmailDraftResult)


def test_draft_extracts_subject():
    with patch("drafter.email_drafter.anthropic_client") as mock_client:
        mock_client.messages.create.return_value = make_mock_response(SAMPLE_LLM_OUTPUT)
        result = draft_outreach_email(
            clinic_name="Bright Smiles Dental",
            contact_first_name="Jane",
            flagged_review_excerpts=["Claim denied."],
        )
    assert "Bright Smiles" in result.subject


def test_draft_extracts_three_subject_variants():
    with patch("drafter.email_drafter.anthropic_client") as mock_client:
        mock_client.messages.create.return_value = make_mock_response(SAMPLE_LLM_OUTPUT)
        result = draft_outreach_email(
            clinic_name="Bright Smiles Dental",
            contact_first_name="Jane",
            flagged_review_excerpts=["Claim denied."],
        )
    assert len(result.subject_variants) == 3


def test_draft_body_contains_html():
    with patch("drafter.email_drafter.anthropic_client") as mock_client:
        mock_client.messages.create.return_value = make_mock_response(SAMPLE_LLM_OUTPUT)
        result = draft_outreach_email(
            clinic_name="Bright Smiles Dental",
            contact_first_name="Jane",
            flagged_review_excerpts=["Claim denied."],
        )
    assert "<p>" in result.body


def test_system_prompt_mentions_lavenderhealth():
    assert "LavenderHealth" in SYSTEM_PROMPT or "lavenderhealth" in SYSTEM_PROMPT.lower()


def test_system_prompt_instructs_empathy():
    assert "empat" in SYSTEM_PROMPT.lower() or "understand" in SYSTEM_PROMPT.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_email_drafter.py -v
```

Expected: FAIL — `drafter.email_drafter` does not exist.

- [ ] **Step 3: Create drafter/email_drafter.py**

```python
import re
from dataclasses import dataclass, field

import anthropic

import config

anthropic_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are a professional outreach writer for LavenderHealth, a company that helps dental practices resolve insurance billing issues and improve their revenue cycle management.

Your tone is empathetic, professional, and non-accusatory. You acknowledge patient frustration without sensationalizing it. Your goal is to open a conversation, not make a hard sell.

Write emails that feel personal and specific — reference the clinic by name, use the contact's first name, and briefly acknowledge the pattern you noticed. Keep it concise (under 150 words for the body)."""

EMAIL_PROMPT = """Write a cold outreach email to a dental clinic whose online reviews show a pattern of insurance claim complaints.

Clinic: {clinic_name}
Contact first name: {contact_first_name}
Flagged review excerpts (anonymized):
{review_excerpts}

Format your response EXACTLY as:
SUBJECT: <primary subject line>
SUBJECT_ALT_1: <alternative subject line 1>
SUBJECT_ALT_2: <alternative subject line 2>

BODY:
<email body in HTML with <p> tags>"""


@dataclass
class EmailDraftResult:
    subject: str
    subject_variants: list[str]
    body: str


def draft_outreach_email(
    clinic_name: str,
    contact_first_name: str | None,
    flagged_review_excerpts: list[str],
) -> EmailDraftResult:
    excerpts_text = "\n".join(f'- "{e}"' for e in flagged_review_excerpts[:3])
    first_name = contact_first_name or "there"

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": EMAIL_PROMPT.format(
                    clinic_name=clinic_name,
                    contact_first_name=first_name,
                    review_excerpts=excerpts_text,
                ),
            }
        ],
    )

    raw = response.content[0].text.strip()
    return _parse_email_response(raw)


def _parse_email_response(raw: str) -> EmailDraftResult:
    subject_match = re.search(r"^SUBJECT:\s*(.+)$", raw, re.MULTILINE)
    alt1_match = re.search(r"^SUBJECT_ALT_1:\s*(.+)$", raw, re.MULTILINE)
    alt2_match = re.search(r"^SUBJECT_ALT_2:\s*(.+)$", raw, re.MULTILINE)
    body_match = re.search(r"BODY:\s*\n([\s\S]+)$", raw)

    subject = subject_match.group(1).strip() if subject_match else "Following up"
    alt1 = alt1_match.group(1).strip() if alt1_match else subject
    alt2 = alt2_match.group(1).strip() if alt2_match else subject
    body = body_match.group(1).strip() if body_match else raw

    return EmailDraftResult(
        subject=subject,
        subject_variants=[subject, alt1, alt2],
        body=body,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_email_drafter.py -v
```

Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add drafter/email_drafter.py tests/test_email_drafter.py
git commit -m "feat: add llm email drafter with 3 subject line variants"
```

---

### Task 3: Enrichment + Drafter Celery Tasks

**Files:**
- Modify: `pipeline/tasks_enrichment.py` (replace placeholder)
- Create: `tests/test_tasks_enrichment.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_tasks_enrichment.py`:

```python
import pytest
import uuid
from unittest.mock import MagicMock, patch

from db.models import ClinicStatus, DraftStatus


@pytest.fixture
def db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from db.models import Base
    engine = create_engine("postgresql://lavender:lavender@localhost:5433/lavenderhealth_test")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


def make_qualified_clinic(session):
    from db.models import CityRun, Clinic, Review, TriggeredBy
    run = CityRun(city="Houston", state="TX", triggered_by=TriggeredBy.CLI)
    session.add(run)
    session.flush()
    clinic = Clinic(
        city_run_id=run.id,
        name="Test Dental",
        city="Houston",
        state="TX",
        google_maps_url="https://maps.google.com/td",
        place_id=f"ChIJ_ENRICH_{uuid.uuid4().hex[:8]}",
        status=ClinicStatus.QUALIFIED,
    )
    session.add(clinic)
    session.flush()
    session.add(Review(
        clinic_id=clinic.id,
        text="Insurance claim denied.",
        insurance_flag=True,
        llm_reasoning="Clear insurance complaint.",
    ))
    session.commit()
    return run, clinic


def test_enrich_clinics_task_creates_contact(db_session):
    from pipeline.tasks_enrichment import enrich_clinics_task
    from enrichment.apollo_client import ApolloContact

    run, clinic = make_qualified_clinic(db_session)

    mock_contact = ApolloContact(
        email="mgr@testdental.com",
        first_name="Jane",
        last_name="Doe",
        title="Office Manager",
        confidence_score=0.95,
    )

    with patch("pipeline.tasks_enrichment.find_clinic_contacts", return_value=[mock_contact]):
        with patch("pipeline.tasks_enrichment.SessionLocal") as mock_sl:
            mock_sl.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_sl.return_value.__exit__ = MagicMock(return_value=False)
            enrich_clinics_task(str(run.id))

    db_session.refresh(clinic)
    assert clinic.status == ClinicStatus.ENRICHED
    assert len(clinic.contacts) == 1
    assert clinic.contacts[0].email == "mgr@testdental.com"


def test_enrich_clinics_task_stays_qualified_when_no_contact(db_session):
    from pipeline.tasks_enrichment import enrich_clinics_task

    run, clinic = make_qualified_clinic(db_session)

    with patch("pipeline.tasks_enrichment.find_clinic_contacts", return_value=[]):
        with patch("pipeline.tasks_enrichment.SessionLocal") as mock_sl:
            mock_sl.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_sl.return_value.__exit__ = MagicMock(return_value=False)
            enrich_clinics_task(str(run.id))

    db_session.refresh(clinic)
    assert clinic.status == ClinicStatus.QUALIFIED  # Not failed, stays qualified


def test_draft_emails_task_creates_draft(db_session):
    from pipeline.tasks_enrichment import draft_emails_task
    from drafter.email_drafter import EmailDraftResult
    from db.models import CityRun, Clinic, Review, Contact, TriggeredBy

    run = CityRun(city="Houston", state="TX", triggered_by=TriggeredBy.CLI)
    db_session.add(run)
    db_session.flush()
    clinic = Clinic(
        city_run_id=run.id,
        name="Draft Dental",
        city="Houston",
        state="TX",
        google_maps_url="https://maps.google.com/dd",
        place_id=f"ChIJ_DRAFT_{uuid.uuid4().hex[:8]}",
        status=ClinicStatus.ENRICHED,
    )
    db_session.add(clinic)
    db_session.flush()
    contact = Contact(
        clinic_id=clinic.id,
        email="mgr@draftdental.com",
        first_name="Bob",
        title="Office Manager",
        confidence_score=0.9,
    )
    db_session.add(contact)
    db_session.add(Review(clinic_id=clinic.id, text="Claim denied.", insurance_flag=True))
    db_session.commit()

    mock_result = EmailDraftResult(
        subject="A concern about Draft Dental",
        subject_variants=["Subject A", "Subject B", "Subject C"],
        body="<p>Hi Bob,</p><p>We noticed...</p>",
    )

    with patch("pipeline.tasks_enrichment.draft_outreach_email", return_value=mock_result):
        with patch("pipeline.tasks_enrichment.SessionLocal") as mock_sl:
            mock_sl.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_sl.return_value.__exit__ = MagicMock(return_value=False)
            draft_emails_task(str(run.id))

    db_session.refresh(clinic)
    assert clinic.status == ClinicStatus.DRAFTED
    assert len(clinic.email_drafts) == 1
    assert clinic.email_drafts[0].status == DraftStatus.DRAFT
    assert clinic.email_drafts[0].subject == "A concern about Draft Dental"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_tasks_enrichment.py -v
```

Expected: FAIL — placeholder `enrich_clinics_task` does nothing.

- [ ] **Step 3: Replace pipeline/tasks_enrichment.py**

```python
from contextlib import contextmanager

from db.models import (
    CityRun, Clinic, Contact, EmailDraft,
    ClinicStatus, DraftStatus,
)
from enrichment.apollo_client import find_clinic_contacts
from drafter.email_drafter import draft_outreach_email
from pipeline.celery_app import celery_app
import config


@contextmanager
def SessionLocal():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=5, default_retry_delay=120, rate_limit="30/m")
def enrich_clinics_task(self, city_run_id: str) -> None:
    with SessionLocal() as db:
        clinics = (
            db.query(Clinic)
            .filter_by(city_run_id=city_run_id, status=ClinicStatus.QUALIFIED)
            .all()
        )

        enriched_count = 0
        for clinic in clinics:
            try:
                contacts = find_clinic_contacts(clinic.name, clinic.city, clinic.state)
            except Exception as exc:
                raise self.retry(exc=exc)

            if not contacts:
                continue  # Stay at QUALIFIED — surfaced in dashboard

            top_contact = contacts[0]
            db.add(Contact(
                clinic_id=clinic.id,
                email=top_contact.email,
                first_name=top_contact.first_name,
                last_name=top_contact.last_name,
                title=top_contact.title,
                confidence_score=top_contact.confidence_score,
            ))
            clinic.status = ClinicStatus.ENRICHED
            enriched_count += 1

        run = db.query(CityRun).filter_by(id=city_run_id).first()
        if run:
            run.total_enriched = enriched_count

    draft_emails_task.delay(city_run_id)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def draft_emails_task(self, city_run_id: str) -> None:
    with SessionLocal() as db:
        clinics = (
            db.query(Clinic)
            .filter_by(city_run_id=city_run_id, status=ClinicStatus.ENRICHED)
            .all()
        )

        drafted_count = 0
        for clinic in clinics:
            if not clinic.contacts:
                continue

            contact = clinic.contacts[0]
            flagged_excerpts = [
                r.text for r in clinic.reviews if r.insurance_flag
            ][:3]

            try:
                result = draft_outreach_email(
                    clinic_name=clinic.name,
                    contact_first_name=contact.first_name,
                    flagged_review_excerpts=flagged_excerpts,
                )
            except Exception as exc:
                raise self.retry(exc=exc)

            db.add(EmailDraft(
                clinic_id=clinic.id,
                contact_id=contact.id,
                subject=result.subject,
                body=result.body,
                subject_variants=result.subject_variants,
            ))
            clinic.status = ClinicStatus.DRAFTED
            drafted_count += 1

        run = db.query(CityRun).filter_by(id=city_run_id).first()
        if run:
            run.total_drafted = drafted_count
            from db.models import CityRunStatus
            from datetime import datetime
            run.status = CityRunStatus.COMPLETED
            run.completed_at = datetime.utcnow()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_tasks_enrichment.py -v
```

Expected: All PASS

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add pipeline/tasks_enrichment.py tests/test_tasks_enrichment.py
git commit -m "feat: implement enrichment and email drafter celery tasks"
```

---

### Task 4: End-to-End Pipeline Smoke Test

Manual test — verifies all 4 stages run against real services.

- [ ] **Step 1: Start all services and a Celery worker**

```bash
docker-compose up -d
alembic upgrade head
celery -A pipeline.celery_app worker --loglevel=info &
```

- [ ] **Step 2: Trigger a mini pipeline run from Python shell**

```python
from db.models import CityRun, TriggeredBy
from db.session import SessionLocal
from pipeline.tasks import scrape_city_task

with SessionLocal() as db:
    run = CityRun(city="Houston", state="TX", triggered_by=TriggeredBy.CLI, max_reviews=20)
    db.add(run)
    db.commit()
    run_id = str(run.id)

scrape_city_task.delay(run_id)
print(f"Run ID: {run_id}")
```

- [ ] **Step 3: Monitor progress**

```bash
# Watch Celery worker logs
# After a few minutes, check DB:
python -c "
from db.session import SessionLocal
from db.models import CityRun, Clinic
with SessionLocal() as db:
    run = db.query(CityRun).order_by(CityRun.created_at.desc()).first()
    print('Run status:', run.status)
    print('Clinics found:', run.total_clinics_found)
    print('Qualified:', run.total_qualified)
    print('Enriched:', run.total_enriched)
    print('Drafted:', run.total_drafted)
"
```

Expected: Status progresses through RUNNING → COMPLETED with counts > 0.

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix: pipeline e2e smoke test adjustments"
```
