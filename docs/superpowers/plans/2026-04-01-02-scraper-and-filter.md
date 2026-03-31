# Scraper + Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Stage 1 (Playwright Google Maps scraper) and Stage 2 (hybrid keyword + LLM filter) as independently testable modules wired into Celery tasks.

**Architecture:** `anti_detection.py` provides rotating headers and delays used by `playwright_scraper.py`. The scraper writes `Clinic` and `Review` records to the DB. `keyword_filter.py` scores reviews against tiered keyword lists. `llm_filter.py` sends flagged reviews in batches to Claude and returns YES/NO verdicts. `pipeline/tasks.py` wires both into Celery tasks that advance `Clinic.status`.

**Tech Stack:** Playwright, SQLAlchemy, Anthropic SDK (claude-haiku-4-5-20251001), pytest, pytest-asyncio

**Prerequisite:** Plan 01 (Foundation) fully implemented and all tests passing.

---

## File Map

| File | Responsibility |
|---|---|
| `scraper/anti_detection.py` | Rotating user-agents, randomized delays, proxy config |
| `scraper/playwright_scraper.py` | Playwright scraper: search → listings → reviews |
| `filter/keyword_filter.py` | Tier 1/2/3 keyword matching, returns matched terms per review |
| `filter/llm_filter.py` | Batch Claude API calls, returns YES/NO + reasoning per review |
| `pipeline/tasks.py` | Celery tasks: `scrape_city`, `filter_clinics` |
| `tests/test_anti_detection.py` | User-agent rotation + delay range tests |
| `tests/test_keyword_filter.py` | Keyword matching tests against known review strings |
| `tests/test_llm_filter.py` | LLM filter tests with mocked Anthropic client |
| `tests/test_pipeline_tasks.py` | Celery task tests with mocked scraper + filter |

---

### Task 1: Anti-Detection Utilities

**Files:**
- Create: `scraper/anti_detection.py`
- Create: `tests/test_anti_detection.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_anti_detection.py`:

```python
import pytest
from scraper.anti_detection import get_random_user_agent, get_random_delay, get_browser_launch_args


def test_user_agent_rotates():
    agents = {get_random_user_agent() for _ in range(20)}
    assert len(agents) > 1, "Expected multiple different user agents"


def test_user_agent_looks_real():
    agent = get_random_user_agent()
    assert "Mozilla" in agent
    assert "Chrome" in agent or "Firefox" in agent or "Safari" in agent


def test_delay_within_range():
    for _ in range(50):
        delay = get_random_delay(min_seconds=2.0, max_seconds=5.0)
        assert 2.0 <= delay <= 5.0


def test_delay_default_range():
    delay = get_random_delay()
    assert 2.0 <= delay <= 5.0


def test_browser_launch_args_returns_list():
    args = get_browser_launch_args(proxy_url=None)
    assert isinstance(args, list)
    assert "--no-sandbox" in args


def test_browser_launch_args_with_proxy():
    args = get_browser_launch_args(proxy_url="http://proxy:8080")
    assert any("proxy" in arg for arg in args)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_anti_detection.py -v
```

Expected: FAIL — `scraper.anti_detection` does not exist.

- [ ] **Step 3: Create scraper/anti_detection.py**

```python
import random
import time

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]


def get_random_user_agent() -> str:
    return random.choice(USER_AGENTS)


def get_random_delay(min_seconds: float = 2.0, max_seconds: float = 5.0) -> float:
    return random.uniform(min_seconds, max_seconds)


def sleep_random(min_seconds: float = 2.0, max_seconds: float = 5.0) -> None:
    time.sleep(get_random_delay(min_seconds, max_seconds))


def get_browser_launch_args(proxy_url: str | None = None) -> list[str]:
    args = [
        "--no-sandbox",
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--disable-dev-shm-usage",
        "--disable-extensions",
    ]
    if proxy_url:
        args.append(f"--proxy-server={proxy_url}")
    return args
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_anti_detection.py -v
```

Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add scraper/anti_detection.py tests/test_anti_detection.py
git commit -m "feat: add anti-detection utilities for scraper"
```

---

### Task 2: Keyword Filter

**Files:**
- Create: `filter/keyword_filter.py`
- Create: `tests/test_keyword_filter.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_keyword_filter.py`:

```python
import pytest
from filter.keyword_filter import (
    score_review,
    qualifies_for_llm,
    TIER1, TIER2, TIER3,
    ReviewScore,
)


def test_tier1_direct_match():
    result = score_review("They denied my insurance claim without any reason.")
    assert result.tier1_hits > 0
    assert "insurance claim" in result.matched_keywords or "insurance denied" in result.matched_keywords


def test_tier2_indirect_match():
    result = score_review("I was double charged and they never fixed it.")
    assert result.tier2_hits > 0
    assert "double charged" in result.matched_keywords


def test_tier3_sentiment_only():
    result = score_review("This place is a complete scam.")
    assert result.tier3_hits > 0
    assert result.tier1_hits == 0


def test_no_match():
    result = score_review("Great dentist, very friendly staff and clean office.")
    assert result.tier1_hits == 0
    assert result.tier2_hits == 0
    assert result.tier3_hits == 0
    assert result.matched_keywords == []


def test_qualifies_with_two_tier1():
    reviews = [
        "Insurance claim denied.",
        "They never submitted my reimbursement.",
        "Great cleaning today.",
    ]
    assert qualifies_for_llm(reviews) is True


def test_does_not_qualify_with_one_tier1():
    reviews = [
        "Insurance claim denied.",
        "Waited a long time.",
        "Staff was rude.",
    ]
    assert qualifies_for_llm(reviews) is False


def test_qualifies_with_four_tier1_plus_tier2():
    reviews = [
        "Insurance claim denied.",      # tier1
        "Billing issue with my visit.", # tier2
        "Double charged twice.",        # tier2
        "Never paid me back.",          # tier2
        "Good parking.",
    ]
    assert qualifies_for_llm(reviews) is True


def test_case_insensitive_matching():
    result = score_review("INSURANCE CLAIM was rejected by this office.")
    assert result.tier1_hits > 0


def test_review_score_is_dataclass():
    result = score_review("test")
    assert hasattr(result, "tier1_hits")
    assert hasattr(result, "tier2_hits")
    assert hasattr(result, "tier3_hits")
    assert hasattr(result, "matched_keywords")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_keyword_filter.py -v
```

Expected: FAIL — `filter.keyword_filter` does not exist.

- [ ] **Step 3: Create filter/keyword_filter.py**

```python
from dataclasses import dataclass, field

TIER1: list[str] = [
    "insurance claim",
    "insurance denied",
    "claim rejected",
    "claim not processed",
    "reimbursement",
    "eob",
    "explanation of benefits",
    "out of pocket",
    "overcharged",
    "insurance fraud",
    "billed incorrectly",
    "insurance won't pay",
    "insurance didn't pay",
]

TIER2: list[str] = [
    "never paid",
    "still waiting",
    "where is my money",
    "billing issue",
    "charged wrong",
    "double charged",
    "won't submit",
    "didn't file",
    "insurance won't cover",
    "balance billing",
    "unexpected charge",
    "hidden fee",
    "wrong amount",
]

TIER3: list[str] = [
    "scam",
    "dishonest",
    "deceptive",
    "misleading",
    "stole",
    "theft",
    "fraud",
    "lie",
    "lied",
]


@dataclass
class ReviewScore:
    tier1_hits: int = 0
    tier2_hits: int = 0
    tier3_hits: int = 0
    matched_keywords: list[str] = field(default_factory=list)


def score_review(text: str) -> ReviewScore:
    lowered = text.lower()
    score = ReviewScore()

    for phrase in TIER1:
        if phrase in lowered:
            score.tier1_hits += 1
            score.matched_keywords.append(phrase)

    for phrase in TIER2:
        if phrase in lowered:
            score.tier2_hits += 1
            score.matched_keywords.append(phrase)

    for phrase in TIER3:
        if phrase in lowered:
            score.tier3_hits += 1
            score.matched_keywords.append(phrase)

    return score


def qualifies_for_llm(review_texts: list[str]) -> bool:
    """Return True if this clinic's reviews warrant LLM analysis."""
    tier1_total = 0
    tier2_total = 0

    for text in review_texts:
        s = score_review(text)
        tier1_total += s.tier1_hits
        tier2_total += s.tier2_hits

    if tier1_total >= 2:
        return True
    if (tier1_total + tier2_total) >= 4:
        return True
    return False
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_keyword_filter.py -v
```

Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add filter/keyword_filter.py tests/test_keyword_filter.py
git commit -m "feat: add tiered keyword filter for insurance complaint detection"
```

---

### Task 3: LLM Filter

**Files:**
- Create: `filter/llm_filter.py`
- Create: `tests/test_llm_filter.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_llm_filter.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from filter.llm_filter import classify_reviews, LLMVerdict, CLASSIFICATION_PROMPT


def make_mock_response(text: str):
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    return msg


def test_classify_yes_response():
    with patch("filter.llm_filter.anthropic_client") as mock_client:
        mock_client.messages.create.return_value = make_mock_response(
            "YES. The reviewer explicitly states their insurance claim was denied and they were charged out of pocket."
        )
        verdicts = classify_reviews(["They denied my insurance claim and I had to pay $500 out of pocket."])

    assert len(verdicts) == 1
    assert verdicts[0].is_insurance_complaint is True
    assert verdicts[0].reasoning != ""


def test_classify_no_response():
    with patch("filter.llm_filter.anthropic_client") as mock_client:
        mock_client.messages.create.return_value = make_mock_response(
            "NO. The reviewer mentions waiting time and staff attitude but nothing about insurance claims."
        )
        verdicts = classify_reviews(["The wait was too long and the staff seemed rude."])

    assert len(verdicts) == 1
    assert verdicts[0].is_insurance_complaint is False


def test_classify_batch_of_reviews():
    responses = [
        "YES. Clear insurance billing complaint.",
        "NO. General service complaint.",
        "YES. Mentions denied reimbursement.",
    ]
    call_count = 0

    def side_effect(**kwargs):
        nonlocal call_count
        resp = make_mock_response(responses[call_count])
        call_count += 1
        return resp

    with patch("filter.llm_filter.anthropic_client") as mock_client:
        mock_client.messages.create.side_effect = side_effect
        verdicts = classify_reviews([
            "They denied my insurance claim.",
            "The wait was terrible.",
            "Reimbursement was never processed.",
        ])

    assert len(verdicts) == 3
    assert verdicts[0].is_insurance_complaint is True
    assert verdicts[1].is_insurance_complaint is False
    assert verdicts[2].is_insurance_complaint is True


def test_llm_verdict_is_dataclass():
    verdict = LLMVerdict(is_insurance_complaint=True, reasoning="Test")
    assert verdict.is_insurance_complaint is True
    assert verdict.reasoning == "Test"


def test_classification_prompt_contains_dental_context():
    assert "dental" in CLASSIFICATION_PROMPT.lower()
    assert "insurance" in CLASSIFICATION_PROMPT.lower()
    assert "YES" in CLASSIFICATION_PROMPT
    assert "NO" in CLASSIFICATION_PROMPT
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_llm_filter.py -v
```

Expected: FAIL — `filter.llm_filter` does not exist.

- [ ] **Step 3: Create filter/llm_filter.py**

```python
from dataclasses import dataclass

import anthropic

import config

anthropic_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

CLASSIFICATION_PROMPT = """You are reviewing Google reviews for a dental clinic.

Does the following review describe a problem with insurance claim processing, reimbursement, or billing fraud at a dental clinic?

Answer with exactly: YES or NO, then one sentence explaining why.

Review:
{review_text}"""


@dataclass
class LLMVerdict:
    is_insurance_complaint: bool
    reasoning: str


def classify_review(review_text: str) -> LLMVerdict:
    response = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[
            {
                "role": "user",
                "content": CLASSIFICATION_PROMPT.format(review_text=review_text),
            }
        ],
    )
    raw = response.content[0].text.strip()
    is_yes = raw.upper().startswith("YES")
    reasoning = raw.split(".", 1)[1].strip() if "." in raw else raw
    return LLMVerdict(is_insurance_complaint=is_yes, reasoning=reasoning)


def classify_reviews(review_texts: list[str]) -> list[LLMVerdict]:
    """Classify each review individually. Returns one verdict per input."""
    return [classify_review(text) for text in review_texts]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_llm_filter.py -v
```

Expected: All PASS (all use mocked Anthropic client)

- [ ] **Step 5: Commit**

```bash
git add filter/llm_filter.py tests/test_llm_filter.py
git commit -m "feat: add LLM filter using claude-haiku for insurance complaint verification"
```

---

### Task 4: Playwright Scraper

**Files:**
- Create: `scraper/playwright_scraper.py`
- Create: `tests/test_playwright_scraper.py`

Note: The scraper talks to live Google Maps — unit tests mock Playwright; integration test is manual.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_playwright_scraper.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_playwright_scraper.py -v
```

Expected: FAIL — `scraper.playwright_scraper` does not exist.

- [ ] **Step 3: Create scraper/playwright_scraper.py**

```python
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime

from scraper.anti_detection import (
    get_random_user_agent,
    sleep_random,
    get_browser_launch_args,
)
import config


@dataclass
class ReviewData:
    author: str | None
    rating: int | None
    text: str
    date: datetime | None


@dataclass
class ClinicData:
    name: str
    address: str | None
    city: str
    state: str
    google_maps_url: str
    place_id: str
    overall_rating: float | None
    total_reviews: int | None
    phone: str | None = None
    website: str | None = None
    zip: str | None = None
    reviews: list[ReviewData] = field(default_factory=list)


def build_search_query(city: str, state: str) -> str:
    return f"dental clinics in {city}, {state}"


def parse_place_id_from_url(url: str, fallback_name: str = "") -> str | None:
    # Try to extract the hex ID from the data parameter
    match = re.search(r"0x[0-9a-f]+:0x[0-9a-f]+", url)
    if match:
        return match.group(0)
    # Fall back to a hash of the name
    if fallback_name:
        return "hash_" + hashlib.md5(fallback_name.encode()).hexdigest()[:16]
    return None


async def scrape_city(city: str, state: str, max_reviews: int = 200) -> list[ClinicData]:
    """
    Scrapes Google Maps for dental clinics in the given city.
    Returns a list of ClinicData with reviews populated.
    """
    from playwright.async_api import async_playwright

    clinics: list[ClinicData] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=get_browser_launch_args(proxy_url=config.PROXY_URL),
        )
        context = await browser.new_context(
            user_agent=get_random_user_agent(),
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        # Navigate to Google Maps search
        query = build_search_query(city, state)
        await page.goto(f"https://www.google.com/maps/search/{query.replace(' ', '+')}")
        await page.wait_for_load_state("networkidle")
        sleep_random(2, 4)

        # Scroll results panel to load all listings
        results_panel = page.locator('[role="feed"]')
        prev_count = 0
        while True:
            await results_panel.evaluate("el => el.scrollTo(0, el.scrollHeight)")
            sleep_random(1.5, 3)
            items = await page.locator('[role="feed"] > div[jsaction]').all()
            if len(items) == prev_count:
                break
            prev_count = len(items)

        listing_links = await page.locator('a[href*="/maps/place/"]').all()

        for link in listing_links:
            href = await link.get_attribute("href") or ""
            name = await link.get_attribute("aria-label") or ""
            if not name:
                continue

            place_id = parse_place_id_from_url(href, fallback_name=name)
            if not place_id:
                continue

            clinic_data = ClinicData(
                name=name.strip(),
                address=None,
                city=city,
                state=state,
                google_maps_url=href,
                place_id=place_id,
                overall_rating=None,
                total_reviews=None,
            )

            # Visit clinic page and scrape reviews
            clinic_page = await context.new_page()
            await clinic_page.goto(href)
            await clinic_page.wait_for_load_state("networkidle")
            sleep_random(2, 4)

            # Extract rating and review count
            try:
                rating_text = await clinic_page.locator('[aria-label*="stars"]').first.get_attribute("aria-label")
                if rating_text:
                    rating_match = re.search(r"([\d.]+) stars", rating_text)
                    if rating_match:
                        clinic_data.overall_rating = float(rating_match.group(1))
            except Exception:
                pass

            try:
                review_count_el = await clinic_page.locator('button[jsaction*="reviewDialog"]').first.inner_text()
                count_match = re.search(r"([\d,]+)", review_count_el)
                if count_match:
                    clinic_data.total_reviews = int(count_match.group(1).replace(",", ""))
            except Exception:
                pass

            # Scrape reviews — newest sort first
            reviews = await _scrape_reviews(clinic_page, max_reviews)
            clinic_data.reviews.extend(reviews)

            # Second pass for high-volume clinics: lowest rated sort
            if clinic_data.total_reviews and clinic_data.total_reviews >= 200:
                low_rated = await _scrape_reviews(clinic_page, max_reviews, sort="lowest")
                seen_texts = {r.text for r in clinic_data.reviews}
                for r in low_rated:
                    if r.text not in seen_texts:
                        clinic_data.reviews.append(r)
                        seen_texts.add(r.text)

            await clinic_page.close()
            sleep_random(2, 5)
            clinics.append(clinic_data)

        await browser.close()

    return clinics


async def _scrape_reviews(
    page,
    max_reviews: int,
    sort: str = "newest",
) -> list[ReviewData]:
    """Scrape up to max_reviews reviews from the currently open clinic page."""
    reviews: list[ReviewData] = []

    try:
        # Click the Reviews tab
        reviews_tab = page.locator('button[aria-label*="reviews"]').first
        await reviews_tab.click()
        await page.wait_for_load_state("networkidle")
        sleep_random(1, 2)

        # Sort reviews
        sort_button = page.locator('[data-value="Sort"]').first
        await sort_button.click()
        sleep_random(0.5, 1)

        if sort == "newest":
            await page.locator('[data-index="1"]').click()  # Newest
        else:
            await page.locator('[data-index="3"]').click()  # Lowest rated
        sleep_random(1.5, 3)

        # Scroll and collect reviews
        review_panel = page.locator('[data-review-id]')
        while len(reviews) < max_reviews:
            review_els = await review_panel.all()
            for el in review_els[len(reviews):]:
                try:
                    # Expand "More" if present
                    more_btn = el.locator('[aria-label="See more"]')
                    if await more_btn.count() > 0:
                        await more_btn.click()
                        sleep_random(0.2, 0.5)

                    text_el = el.locator(".MyEned")
                    text = await text_el.inner_text() if await text_el.count() > 0 else ""
                    if not text:
                        continue

                    author_el = el.locator(".d4r55")
                    author = await author_el.inner_text() if await author_el.count() > 0 else None

                    rating_el = el.locator('[aria-label*="stars"]')
                    rating = None
                    if await rating_el.count() > 0:
                        ra = await rating_el.get_attribute("aria-label")
                        m = re.search(r"(\d) star", ra or "")
                        if m:
                            rating = int(m.group(1))

                    reviews.append(ReviewData(author=author, rating=rating, text=text, date=None))
                except Exception:
                    continue

            if len(reviews) >= max_reviews:
                break

            # Scroll down to load more
            await page.evaluate("window.scrollBy(0, 800)")
            sleep_random(1, 2)

            new_count = len(await review_panel.all())
            if new_count <= len(reviews):
                break  # No more reviews loaded

    except Exception:
        pass

    return reviews[:max_reviews]
```

- [ ] **Step 4: Run unit tests to verify they pass**

```bash
pytest tests/test_playwright_scraper.py -v
```

Expected: All PASS (no Playwright browser launched in these tests)

- [ ] **Step 5: Commit**

```bash
git add scraper/playwright_scraper.py tests/test_playwright_scraper.py
git commit -m "feat: add playwright scraper for google maps dental clinics"
```

---

### Task 5: Celery Pipeline Tasks (Stages 1 & 2)

**Files:**
- Modify: `pipeline/tasks.py`
- Create: `tests/test_pipeline_tasks.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_pipeline_tasks.py`:

```python
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import uuid

from db.models import CityRunStatus, ClinicStatus


def make_db_run(session):
    from db.models import CityRun, TriggeredBy
    run = CityRun(city="Houston", state="TX", triggered_by=TriggeredBy.CLI, max_reviews=200)
    session.add(run)
    session.commit()
    return run


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


def test_scrape_city_task_updates_run_status(db_session):
    from pipeline.tasks import scrape_city_task
    run = make_db_run(db_session)

    mock_clinic = MagicMock()
    mock_clinic.name = "Test Dental"
    mock_clinic.address = "123 Main"
    mock_clinic.city = "Houston"
    mock_clinic.state = "TX"
    mock_clinic.zip = None
    mock_clinic.phone = None
    mock_clinic.website = None
    mock_clinic.google_maps_url = "https://maps.google.com/test"
    mock_clinic.place_id = f"ChIJ_TASK_TEST_{uuid.uuid4().hex[:8]}"
    mock_clinic.overall_rating = 3.5
    mock_clinic.total_reviews = 42
    mock_clinic.reviews = []

    with patch("pipeline.tasks.scrape_city", new_callable=AsyncMock, return_value=[mock_clinic]):
        with patch("pipeline.tasks.SessionLocal") as mock_sl:
            mock_sl.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_sl.return_value.__exit__ = MagicMock(return_value=False)
            scrape_city_task(str(run.id))

    db_session.refresh(run)
    assert run.total_clinics_found == 1


def test_filter_clinics_task_marks_qualified(db_session):
    from pipeline.tasks import filter_clinics_task
    from db.models import CityRun, Clinic, Review, TriggeredBy

    run = CityRun(city="Houston", state="TX", triggered_by=TriggeredBy.CLI)
    db_session.add(run)
    db_session.flush()

    clinic = Clinic(
        city_run_id=run.id,
        name="Complaint Dental",
        city="Houston",
        state="TX",
        google_maps_url="https://maps.google.com/c",
        place_id=f"ChIJ_FILTER_{uuid.uuid4().hex[:8]}",
    )
    db_session.add(clinic)
    db_session.flush()

    # 2 Tier1 reviews → qualifies for LLM
    db_session.add(Review(clinic_id=clinic.id, text="Insurance claim was denied after 6 months."))
    db_session.add(Review(clinic_id=clinic.id, text="They refused my reimbursement request."))
    db_session.commit()

    with patch("pipeline.tasks.classify_reviews") as mock_classify:
        mock_verdict = MagicMock()
        mock_verdict.is_insurance_complaint = True
        mock_verdict.reasoning = "Clear insurance complaint."
        mock_classify.return_value = [mock_verdict, mock_verdict]

        with patch("pipeline.tasks.SessionLocal") as mock_sl:
            mock_sl.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_sl.return_value.__exit__ = MagicMock(return_value=False)
            filter_clinics_task(str(run.id))

    db_session.refresh(clinic)
    assert clinic.status == ClinicStatus.QUALIFIED
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_pipeline_tasks.py -v
```

Expected: FAIL — `pipeline.tasks` has no task implementations.

- [ ] **Step 3: Implement pipeline/tasks.py**

```python
import asyncio
from contextlib import contextmanager

from celery import chain

from db.models import (
    CityRun, Clinic, Review, ClinicStatus, CityRunStatus,
    FlagReason, TriggeredBy,
)
from db.session import SessionLocal as _SessionLocal
from filter.keyword_filter import score_review, qualifies_for_llm
from filter.llm_filter import classify_reviews
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


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def scrape_city_task(self, city_run_id: str) -> None:
    from scraper.playwright_scraper import scrape_city

    with SessionLocal() as db:
        run = db.query(CityRun).filter_by(id=city_run_id).first()
        if not run:
            return
        run.status = CityRunStatus.RUNNING

    try:
        clinic_data_list = asyncio.run(
            scrape_city(run.city, run.state, run.max_reviews)
        )
    except Exception as exc:
        with SessionLocal() as db:
            run = db.query(CityRun).filter_by(id=city_run_id).first()
            if run:
                run.status = CityRunStatus.FAILED
        raise self.retry(exc=exc)

    with SessionLocal() as db:
        run = db.query(CityRun).filter_by(id=city_run_id).first()
        if not run:
            return

        for cd in clinic_data_list:
            existing = db.query(Clinic).filter_by(place_id=cd.place_id).first()
            if existing:
                # Reassign to current run so filter_clinics_task finds it
                existing.city_run_id = city_run_id
                clinic = existing
            else:
                clinic = Clinic(
                    city_run_id=city_run_id,
                    name=cd.name,
                    address=cd.address,
                    city=cd.city,
                    state=cd.state,
                    zip=cd.zip,
                    phone=cd.phone,
                    website=cd.website,
                    google_maps_url=cd.google_maps_url,
                    place_id=cd.place_id,
                    overall_rating=cd.overall_rating,
                    total_reviews=cd.total_reviews,
                )
                db.add(clinic)
                db.flush()

            for rd in cd.reviews:
                db.add(Review(
                    clinic_id=clinic.id,
                    author=rd.author,
                    rating=rd.rating,
                    text=rd.text,
                    date=rd.date,
                ))

        run.total_clinics_found = len(clinic_data_list)

    # Chain to filter stage
    filter_clinics_task.delay(city_run_id)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def filter_clinics_task(self, city_run_id: str) -> None:
    with SessionLocal() as db:
        clinics = (
            db.query(Clinic)
            .filter_by(city_run_id=city_run_id, status=ClinicStatus.SCRAPED)
            .all()
        )

        qualified_count = 0
        for clinic in clinics:
            review_texts = [r.text for r in clinic.reviews]

            if not qualifies_for_llm(review_texts):
                clinic.status = ClinicStatus.FILTERED_OUT
                continue

            # Run keyword scoring on individual reviews
            candidate_reviews = []
            for review in clinic.reviews:
                score = score_review(review.text)
                if score.tier1_hits > 0 or score.tier2_hits > 0:
                    review.keyword_matches = score.matched_keywords
                    candidate_reviews.append(review)

            # LLM verification
            texts_to_classify = [r.text for r in candidate_reviews]
            try:
                verdicts = classify_reviews(texts_to_classify)
            except Exception as exc:
                raise self.retry(exc=exc)

            confirmed = 0
            for review, verdict in zip(candidate_reviews, verdicts):
                if verdict.is_insurance_complaint:
                    confirmed += 1
                    review.insurance_flag = True
                    review.llm_reasoning = verdict.reasoning
                    review.flag_reason = (
                        FlagReason.BOTH if review.keyword_matches else FlagReason.LLM
                    )
                else:
                    review.flag_reason = FlagReason.KEYWORD if review.keyword_matches else None

            if confirmed >= 2:
                clinic.status = ClinicStatus.QUALIFIED
                qualified_count += 1
            else:
                clinic.status = ClinicStatus.FILTERED_OUT

        run = db.query(CityRun).filter_by(id=city_run_id).first()
        if run:
            run.total_qualified = qualified_count

    # Chain to enrichment stage (implemented in Plan 03)
    from pipeline.tasks_enrichment import enrich_clinics_task
    enrich_clinics_task.delay(city_run_id)
```

- [ ] **Step 4: Create pipeline/tasks_enrichment.py as placeholder**

```python
# Enrichment + Drafter tasks — implemented in Plan 03
from pipeline.celery_app import celery_app


@celery_app.task
def enrich_clinics_task(city_run_id: str) -> None:
    pass  # Placeholder — implemented in Plan 03
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_pipeline_tasks.py -v
```

Expected: All PASS

- [ ] **Step 6: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add pipeline/tasks.py pipeline/tasks_enrichment.py tests/test_pipeline_tasks.py
git commit -m "feat: add celery tasks for scrape and filter pipeline stages"
```

---

### Task 6: Manual Integration Test (Scraper)

This task verifies the scraper works end-to-end against real Google Maps. Not automated — run manually.

- [ ] **Step 1: Ensure Docker services are running**

```bash
docker-compose up -d
alembic upgrade head
```

- [ ] **Step 2: Run a small scrape in Python shell**

```python
import asyncio
from scraper.playwright_scraper import scrape_city

# Small test — limit to 20 reviews to verify structure
clinics = asyncio.run(scrape_city("Houston", "TX", max_reviews=20))
print(f"Found {len(clinics)} clinics")
print(f"First clinic: {clinics[0].name}")
print(f"First clinic reviews: {len(clinics[0].reviews)}")
print(f"Sample review: {clinics[0].reviews[0].text[:100] if clinics[0].reviews else 'none'}")
```

Expected: Finds 20+ clinics, each with reviews.

- [ ] **Step 3: Commit any fixes found during manual test**

```bash
git add -A
git commit -m "fix: scraper adjustments after manual integration test"
```
