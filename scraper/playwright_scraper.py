"""
Playwright scraper for Google Maps dental clinic listings.

Strategy:
  - Build geographic search cells from local ZIP centroid data
  - Search each cell with broad dental discovery queries
  - Deduplicate clinics by place_id across all cell batches
  - Within each cell search, scrape clinic detail pages concurrently (semaphore)

This gives comprehensive city coverage instead of the ~20-result cap
that a single city-level search returns.
"""

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from scraper.anti_detection import (
    get_random_user_agent,
    async_sleep_random,
    get_browser_launch_args,
)
import config

log = logging.getLogger(__name__)

# Clinic detail pages open simultaneously per browser context
_CLINIC_CONCURRENCY = 3
# Search-cell pages open simultaneously
_CELL_CONCURRENCY = 2

# Run multiple query styles so discovery does not get trapped in one category.
_SEARCH_PATTERNS = [
    "dentist",
    "dental clinic",
    "family dentist",
    "pediatric dentist",
    "dental billing",
    "dental insurance claim",
    "out of network dentist",
    "insurance denied dentist",
]

_REVIEW_TAB_TIMEOUT_MS = config.SCRAPER_REVIEW_TAB_TIMEOUT_MS
_REVIEW_METADATA_TIMEOUT_MS = config.SCRAPER_REVIEW_METADATA_TIMEOUT_MS
_PAGE_GOTO_TIMEOUT_MS = config.SCRAPER_PAGE_GOTO_TIMEOUT_MS
_RESULTS_FEED_WAIT_TIMEOUT_MS = config.SCRAPER_RESULTS_FEED_WAIT_TIMEOUT_MS


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


@dataclass
class ClinicReviewScrapeResult:
    overall_rating: float | None
    total_reviews: int | None
    reviews: list[ReviewData] = field(default_factory=list)


@dataclass(frozen=True)
class SearchCell:
    key: str
    label: str
    latitude: float
    longitude: float
    zoom: int


def parse_google_review_date(raw: str, now: datetime | None = None) -> datetime | None:
    now = now or datetime.now(timezone.utc)
    text = raw.strip()
    if not text:
        return None

    lower = text.lower()
    if lower == "today":
        return now
    if lower == "yesterday":
        return now - timedelta(days=1)

    relative_match = re.fullmatch(r"(?:(a|an|\d+))\s+(day|week|month|year)s?\s+ago", lower)
    if relative_match:
        qty_raw, unit = relative_match.groups()
        qty = 1 if qty_raw in {"a", "an"} else int(qty_raw)
        day_multiplier = {
            "day": 1,
            "week": 7,
            "month": 30,
            "year": 365,
        }[unit]
        return now - timedelta(days=qty * day_multiplier)

    for fmt in ("%b %d, %Y", "%B %d, %Y", "%b %d %Y", "%B %d %Y"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


def _snap_to_grid(value: float, cell_size: float) -> float:
    return round(value / cell_size) * cell_size


def get_search_cells(
    city: str,
    state: str,
    max_cells: int | None = None,
    cell_size_degrees: float | None = None,
    zoom: int | None = None,
) -> list[SearchCell]:
    """
    Build search cells from ZIP centroid data, snapped to a coarse grid so that
    nearby ZIPs share one discovery cell instead of causing duplicate searches.
    """
    try:
        import zipcodes

        max_cells = max_cells or config.DISCOVERY_MAX_SEARCH_CELLS
        cell_size_degrees = cell_size_degrees or config.DISCOVERY_CELL_SIZE_DEGREES
        zoom = zoom or config.DISCOVERY_CELL_ZOOM

        results = zipcodes.filter_by(city=city, state=state)
        results.sort(key=lambda row: int(row.get("population") or 0), reverse=True)

        cells: list[SearchCell] = []
        seen_keys: set[str] = set()

        for row in results:
            lat_raw = row.get("lat")
            lng_raw = row.get("long")
            if lat_raw in (None, "") or lng_raw in (None, ""):
                continue

            latitude = float(lat_raw)
            longitude = float(lng_raw)
            snapped_lat = _snap_to_grid(latitude, cell_size_degrees)
            snapped_lng = _snap_to_grid(longitude, cell_size_degrees)
            key = f"{snapped_lat:.4f},{snapped_lng:.4f}"

            if key in seen_keys:
                continue
            seen_keys.add(key)

            cells.append(
                SearchCell(
                    key=key,
                    label=f"{city}, {state} [{key}]",
                    latitude=snapped_lat,
                    longitude=snapped_lng,
                    zoom=zoom,
                )
            )

            if len(cells) >= max_cells:
                break

        return cells
    except Exception as e:
        log.warning(f"Could not build search cells for {city}, {state}: {e}")
        return []


def parse_place_id_from_url(url: str, fallback_name: str = "") -> str | None:
    match = re.search(r"0x[0-9a-f]+:0x[0-9a-f]+", url)
    if match:
        return match.group(0)
    if fallback_name:
        return "hash_" + hashlib.md5(fallback_name.encode()).hexdigest()[:16]
    return None


def _build_search_queries() -> list[str]:
    return list(_SEARCH_PATTERNS)


def _build_search_url(query: str, cell: SearchCell | None, city: str, state: str) -> str:
    query_slug = query.replace(" ", "+")
    if cell is None:
        return f"https://www.google.com/maps/search/{query_slug}+in+{city.replace(' ', '+')}+{state}"
    return (
        f"https://www.google.com/maps/search/{query_slug}"
        f"/@{cell.latitude},{cell.longitude},{cell.zoom}z"
    )


def build_search_query(city: str, state: str) -> str:
    """Compatibility helper for tests and simple callers."""
    return f"dental clinic near {city}, {state}"


async def _safe_navigate(
    page,
    url: str,
    phase_tag: str,
    wait_for_selector: str | None = None,
) -> bool:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=_PAGE_GOTO_TIMEOUT_MS)
    except Exception as exc:
        log.warning(f"{phase_tag}: navigation failed for {url}: {exc}")
        return False

    if wait_for_selector:
        try:
            await page.locator(wait_for_selector).first.wait_for(
                state="attached",
                timeout=_RESULTS_FEED_WAIT_TIMEOUT_MS,
            )
        except Exception as exc:
            log.warning(f"{phase_tag}: selector '{wait_for_selector}' not ready for {url}: {exc}")
            return False

    return True


async def scrape_city(city: str, state: str, max_reviews: int = 0) -> list[ClinicData]:
    from playwright.async_api import async_playwright

    review_cap = max_reviews if max_reviews > 0 else None
    discovery_newest_reviews = (
        min(review_cap, config.DISCOVERY_NEWEST_SAMPLE_REVIEWS)
        if review_cap is not None
        else config.DISCOVERY_NEWEST_SAMPLE_REVIEWS
    )
    discovery_lowest_reviews = (
        min(review_cap, config.DISCOVERY_LOWEST_SAMPLE_REVIEWS)
        if review_cap is not None
        else config.DISCOVERY_LOWEST_SAMPLE_REVIEWS
    )

    search_cells = get_search_cells(city, state)
    if not search_cells:
        search_cells = [None]
        log.warning(f"No search cells found for {city}, {state} — falling back to city search")
    else:
        log.info(f"Searching {len(search_cells)} search cells for {city}, {state}")

    seen_place_ids: set[str] = set()
    all_clinics: list[ClinicData] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=get_browser_launch_args(proxy_url=config.PROXY_URL),
        )

        clinic_sem = asyncio.Semaphore(_CLINIC_CONCURRENCY)
        cell_sem = asyncio.Semaphore(_CELL_CONCURRENCY)
        seen_lock = asyncio.Lock()

        async def scrape_cell(cell: SearchCell | None) -> list[ClinicData]:
            """Collect listing links from one search cell, then scrape each clinic."""
            context = await browser.new_context(
                user_agent=get_random_user_agent(),
                viewport={"width": 1280, "height": 800},
            )
            results: list[ClinicData] = []
            targets: list[tuple[str, str, str]] = []

            async with cell_sem:
                search_page = await context.new_page()
                try:
                    for query in _build_search_queries():
                        url = _build_search_url(query, cell, city, state)
                        log.info(f"Searching: {url}")
                        ok = await _safe_navigate(
                            search_page,
                            url,
                            phase_tag="[DISCOVERY_NAV]",
                            wait_for_selector='[role="feed"]',
                        )
                        if not ok:
                            continue
                        await async_sleep_random(1, 2)

                        # Scroll to load more results
                        try:
                            panel = search_page.locator('[role="feed"]')
                            prev = 0
                            for _ in range(12):
                                await panel.evaluate("el => el.scrollTo(0, el.scrollHeight)")
                                await async_sleep_random(1, 1.5)
                                items = await search_page.locator('[role="feed"] > div[jsaction]').all()
                                if len(items) == prev:
                                    break
                                prev = len(items)
                            log.info(f"  cell {cell.key if cell else 'city'} query '{query}': {prev} items in feed")
                        except Exception as e:
                            log.warning(f"  cell {cell.key if cell else 'city'} query '{query}': could not scroll feed: {e}")

                        listing_links = await search_page.locator('a[href*="/maps/place/"]').all()

                        # Collect new targets (deduplicated globally)
                        for link in listing_links:
                            href = await link.get_attribute("href") or ""
                            name = await link.get_attribute("aria-label") or ""
                            if not name:
                                continue
                            place_id = parse_place_id_from_url(href, fallback_name=name)
                            if not place_id:
                                continue
                            async with seen_lock:
                                if place_id in seen_place_ids:
                                    continue
                                seen_place_ids.add(place_id)
                            targets.append((href, name, place_id))

                    log.info(f"  cell {cell.key if cell else 'city'}: {len(targets)} total new clinics to scrape")
                finally:
                    await search_page.close()

                # Scrape each clinic detail page concurrently
                async def scrape_clinic(href: str, name: str, place_id: str) -> ClinicData:
                    clinic_data = ClinicData(
                        name=name.strip(),
                        address=None,
                        city=city,
                        state=state,
                        zip=None,
                        google_maps_url=href,
                        place_id=place_id,
                        overall_rating=None,
                        total_reviews=None,
                    )
                    async with clinic_sem:
                        page = await context.new_page()
                        try:
                            ok = await _safe_navigate(
                                page,
                                href,
                                phase_tag=f"[CLINIC_NAV] {clinic_data.name}",
                            )
                            if not ok:
                                return clinic_data
                            await async_sleep_random(1, 2)

                            clinic_data.overall_rating = await _extract_overall_rating(page)
                            clinic_data.total_reviews = await _extract_total_reviews(page)

                            revs = await _scrape_reviews(page, discovery_newest_reviews)
                            log.info(
                                f"[DISCOVERY_SAMPLE] {clinic_data.name}: "
                                f"{len(revs)} newest-sample reviews"
                            )
                            clinic_data.reviews.extend(revs)

                            if (
                                discovery_lowest_reviews > 0
                                and clinic_data.total_reviews
                                and clinic_data.total_reviews >= config.DISCOVERY_LOWEST_SAMPLE_THRESHOLD
                            ):
                                low = await _scrape_reviews(page, discovery_lowest_reviews, sort="lowest")
                                seen = {r.text for r in clinic_data.reviews}
                                for r in low:
                                    if r.text not in seen:
                                        clinic_data.reviews.append(r)
                                        seen.add(r.text)
                                log.info(
                                    f"[DISCOVERY_SAMPLE] {clinic_data.name}: "
                                    f"added {len(low)} locally-ranked low-star reviews "
                                    f"(total sampled {len(clinic_data.reviews)})"
                                )

                        except Exception as e:
                            log.warning(f"    Error scraping {clinic_data.name}: {e}")
                        finally:
                            try:
                                await page.close()
                            except Exception:
                                pass
                    return clinic_data

                clinic_results = await asyncio.gather(
                    *[scrape_clinic(href, name, pid) for href, name, pid in targets],
                    return_exceptions=True,
                )
                for item in clinic_results:
                    if isinstance(item, Exception):
                        log.warning(f"[DISCOVERY_SAMPLE] clinic scrape task failed: {item}")
                        continue
                    results.append(item)
                await context.close()

            return results

        cell_results = await asyncio.gather(*[scrape_cell(cell) for cell in search_cells], return_exceptions=True)
        for batch in cell_results:
            if isinstance(batch, Exception):
                log.warning(f"[DISCOVERY_NAV] cell scrape failed and was skipped: {batch}")
                continue
            all_clinics.extend(batch)

        await browser.close()

    log.info(f"Scraped {len(all_clinics)} clinics total across {len(search_cells)} search cells")
    return all_clinics


async def scrape_clinic_reviews(google_maps_url: str, max_reviews: int = 0) -> ClinicReviewScrapeResult:
    from playwright.async_api import async_playwright

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

        try:
            ok = await _safe_navigate(page, google_maps_url, phase_tag="[DEEP_NAV]")
            if not ok:
                return ClinicReviewScrapeResult(overall_rating=None, total_reviews=None, reviews=[])
            await async_sleep_random(1, 2)

            result = ClinicReviewScrapeResult(
                overall_rating=await _extract_overall_rating(page),
                total_reviews=await _extract_total_reviews(page),
                reviews=[],
            )

            reviews = await _scrape_reviews(page, max_reviews)
            result.reviews.extend(reviews)

            if result.total_reviews and result.total_reviews >= 200:
                lowest_reviews = await _scrape_reviews(page, max_reviews, sort="lowest")
                seen = {review.text for review in result.reviews}
                for review in lowest_reviews:
                    if review.text not in seen:
                        result.reviews.append(review)
                        seen.add(review.text)

            return result
        finally:
            try:
                await page.close()
            except Exception:
                pass
            await context.close()
            await browser.close()


async def _extract_overall_rating(page) -> float | None:
    try:
        for rating_sel in ['[aria-label*="stars"]', '[role="img"][aria-label*="star"]']:
            rating_el = page.locator(rating_sel).first
            rt = await rating_el.get_attribute("aria-label", timeout=_REVIEW_METADATA_TIMEOUT_MS)
            if rt:
                match = re.search(r"([\d.]+)\s*star", rt)
                if match:
                    return float(match.group(1))
    except Exception:
        return None
    return None


async def _extract_total_reviews(page) -> int | None:
    try:
        for sel in ['button[jsaction*="reviewDialog"]', 'button[aria-label*="reviews"]', 'span[aria-label*="reviews"]']:
            el = page.locator(sel).first
            if await el.count() > 0:
                text = await el.inner_text(timeout=_REVIEW_METADATA_TIMEOUT_MS)
                match = re.search(r"([\d,]+)", text)
                if match:
                    return int(match.group(1).replace(",", ""))
        page_text = await page.inner_text("body")
        match = re.search(r"([\d,]+)\s+reviews", page_text, re.IGNORECASE)
        if match:
            return int(match.group(1).replace(",", ""))
    except Exception:
        return None
    return None


def _sort_reviews_locally(reviews: list[ReviewData], sort: str) -> list[ReviewData]:
    if sort != "lowest":
        return reviews

    # Prefer known low ratings first. Unknown ratings are kept at the end.
    def key(review: ReviewData) -> tuple[int, int, float]:
        rating_rank = review.rating if review.rating is not None else 99
        has_rating_rank = 0 if review.rating is not None else 1
        date_rank = -review.date.timestamp() if review.date else float("inf")
        return (has_rating_rank, rating_rank, date_rank)

    return sorted(reviews, key=key)


async def _scrape_reviews(page, max_reviews: int, sort: str = "newest") -> list[ReviewData]:
    reviews: list[ReviewData] = []
    review_cap = max_reviews if max_reviews > 0 else None

    try:
        clicked_reviews = False
        for selector in [
            'button[aria-label*="reviews" i]',
            'button[data-tab-index="1"]',
            '[role="tab"]:has-text("Reviews")',
        ]:
            try:
                el = page.locator(selector).first
                if await el.count() > 0:
                    await el.click(timeout=_REVIEW_TAB_TIMEOUT_MS)
                    clicked_reviews = True
                    break
            except Exception:
                continue

        if not clicked_reviews:
            log.warning("Could not click reviews tab")
            return reviews

        await page.wait_for_load_state("networkidle")
        await async_sleep_random(0.5, 1)

        seen_texts: set[str] = set()
        no_new_count = 0

        for _ in range(30):
            review_els = []
            for selector in ['[data-review-id]', '[jslog*="review"]', 'div[class*="review"]']:
                els = await page.locator(selector).all()
                if els:
                    review_els = els
                    break

            for el in review_els:
                try:
                    for more_sel in ['[aria-label="See more"]', 'button:has-text("More")']:
                        more_btn = el.locator(more_sel)
                        if await more_btn.count() > 0:
                            await more_btn.first.click()
                            break

                    text = ""
                    for text_sel in ['.wiI7pd', '.MyEned', 'span[data-expandable-section]', '[class*="review-full-text"]']:
                        text_el = el.locator(text_sel)
                        if await text_el.count() > 0:
                            text = await text_el.first.inner_text()
                            if text.strip():
                                break

                    if not text.strip() or text in seen_texts:
                        continue
                    seen_texts.add(text)

                    author = None
                    for author_sel in ['.d4r55', '[class*="author"]', '[data-review-id] div:first-child']:
                        a_el = el.locator(author_sel)
                        if await a_el.count() > 0:
                            author = await a_el.first.inner_text()
                            break

                    rating = None
                    rating_el = el.locator('[aria-label*="star"]')
                    if await rating_el.count() > 0:
                        ra = await rating_el.first.get_attribute("aria-label")
                        m = re.search(r"(\d) star", ra or "")
                        if m:
                            rating = int(m.group(1))

                    review_date = None
                    for date_sel in ['.rsqaWe', 'span[class*="rsqaWe"]', '[class*="review-date"]']:
                        date_el = el.locator(date_sel)
                        if await date_el.count() > 0:
                            raw_date = await date_el.first.inner_text()
                            review_date = parse_google_review_date(raw_date)
                            if review_date is not None:
                                break

                    reviews.append(ReviewData(author=author, rating=rating, text=text.strip(), date=review_date))

                except Exception:
                    continue

            if review_cap is not None and len(reviews) >= review_cap:
                break

            prev_len = len(reviews)
            await page.evaluate("window.scrollBy(0, 1200)")
            await async_sleep_random(1, 1.5)

            if len(reviews) == prev_len:
                no_new_count += 1
                if no_new_count >= 3:
                    break
            else:
                no_new_count = 0

    except Exception as e:
        log.warning(f"Error in _scrape_reviews: {e}")

    ranked = _sort_reviews_locally(reviews, sort)
    if review_cap is None:
        return ranked
    return ranked[:review_cap]
