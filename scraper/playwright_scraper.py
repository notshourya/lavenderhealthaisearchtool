"""
Playwright scraper for Google Maps dental clinic listings.

Strategy:
  - Look up zip codes for the target city (via the `zipcodes` package)
  - Search "dental clinics near {zipcode}" for each zip in parallel
  - Deduplicate clinics by place_id across all zip batches
  - Within each zip search, scrape clinic detail pages concurrently (semaphore)

This gives comprehensive city coverage instead of the ~20-result cap
that a single city-level search returns.
"""

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime

from scraper.anti_detection import (
    get_random_user_agent,
    sleep_random,
    get_browser_launch_args,
)
import config

log = logging.getLogger(__name__)

# Clinic detail pages open simultaneously per browser context
_CLINIC_CONCURRENCY = 3
# Zip-code search pages open simultaneously
_ZIP_CONCURRENCY = 2
# Max zip codes to search per city (sample most-populated ones)
_MAX_ZIPS = 40


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


def get_zip_codes(city: str, state: str, max_zips: int = _MAX_ZIPS) -> list[str]:
    """Return up to max_zips zip codes for the city, sorted by population desc."""
    try:
        import zipcodes
        results = zipcodes.filter_by(city=city, state=state)
        # Sort by population descending so we prioritise denser areas
        results.sort(key=lambda z: int(z.get("population") or 0), reverse=True)
        return [z["zip_code"] for z in results[:max_zips]]
    except Exception as e:
        log.warning(f"Could not look up zip codes for {city}, {state}: {e}")
        return []


def parse_place_id_from_url(url: str, fallback_name: str = "") -> str | None:
    match = re.search(r"0x[0-9a-f]+:0x[0-9a-f]+", url)
    if match:
        return match.group(0)
    if fallback_name:
        return "hash_" + hashlib.md5(fallback_name.encode()).hexdigest()[:16]
    return None


async def scrape_city(city: str, state: str, max_reviews: int = 200) -> list[ClinicData]:
    from playwright.async_api import async_playwright

    zip_codes = get_zip_codes(city, state)
    if not zip_codes:
        # Fallback: single city-level search
        zip_codes = [None]
        log.warning(f"No zip codes found for {city}, {state} — falling back to city search")
    else:
        log.info(f"Searching {len(zip_codes)} zip codes for {city}, {state}")

    seen_place_ids: set[str] = set()
    all_clinics: list[ClinicData] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=get_browser_launch_args(proxy_url=config.PROXY_URL),
        )

        clinic_sem = asyncio.Semaphore(_CLINIC_CONCURRENCY)
        zip_sem = asyncio.Semaphore(_ZIP_CONCURRENCY)
        seen_lock = asyncio.Lock()

        async def scrape_zip(zipcode: str | None) -> list[ClinicData]:
            """Collect listing links from one zip-code search, then scrape each clinic."""
            context = await browser.new_context(
                user_agent=get_random_user_agent(),
                viewport={"width": 1280, "height": 800},
            )
            results: list[ClinicData] = []

            async with zip_sem:
                search_page = await context.new_page()
                try:
                    query = (
                        f"dental clinics near {zipcode}"
                        if zipcode
                        else f"dental clinics in {city}, {state}"
                    )
                    url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
                    log.info(f"Searching: {url}")
                    await search_page.goto(url)
                    await search_page.wait_for_load_state("networkidle")
                    sleep_random(1, 2)

                    # Scroll to load more results
                    try:
                        panel = search_page.locator('[role="feed"]')
                        prev = 0
                        for _ in range(8):
                            await panel.evaluate("el => el.scrollTo(0, el.scrollHeight)")
                            sleep_random(1, 1.5)
                            items = await search_page.locator('[role="feed"] > div[jsaction]').all()
                            if len(items) == prev:
                                break
                            prev = len(items)
                        log.info(f"  zip {zipcode}: {prev} items in feed")
                    except Exception as e:
                        log.warning(f"  zip {zipcode}: could not scroll feed: {e}")

                    listing_links = await search_page.locator('a[href*="/maps/place/"]').all()

                    # Collect new targets (deduplicated globally)
                    targets: list[tuple[str, str]] = []
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

                    log.info(f"  zip {zipcode}: {len(targets)} new clinics to scrape")
                finally:
                    await search_page.close()

                # Scrape each clinic detail page concurrently
                async def scrape_clinic(href: str, name: str, place_id: str) -> ClinicData:
                    clinic_data = ClinicData(
                        name=name.strip(),
                        address=None,
                        city=city,
                        state=state,
                        zip=zipcode,
                        google_maps_url=href,
                        place_id=place_id,
                        overall_rating=None,
                        total_reviews=None,
                    )
                    async with clinic_sem:
                        page = await context.new_page()
                        try:
                            await page.goto(href)
                            await page.wait_for_load_state("networkidle")
                            sleep_random(1, 2)

                            # Rating
                            try:
                                rating_el = page.locator('[aria-label*="stars"]').first
                                rt = await rating_el.get_attribute("aria-label", timeout=3000)
                                if rt:
                                    m = re.search(r"([\d.]+) stars", rt)
                                    if m:
                                        clinic_data.overall_rating = float(m.group(1))
                            except Exception:
                                pass

                            # Review count
                            try:
                                for sel in ['button[jsaction*="reviewDialog"]', 'button[aria-label*="reviews"]', 'span[aria-label*="reviews"]']:
                                    el = page.locator(sel).first
                                    if await el.count() > 0:
                                        t = await el.inner_text(timeout=3000)
                                        m = re.search(r"([\d,]+)", t)
                                        if m:
                                            clinic_data.total_reviews = int(m.group(1).replace(",", ""))
                                            break
                            except Exception:
                                pass

                            revs = await _scrape_reviews(page, max_reviews)
                            log.info(f"    {clinic_data.name}: {len(revs)} reviews")
                            clinic_data.reviews.extend(revs)

                            if clinic_data.total_reviews and clinic_data.total_reviews >= 200:
                                low = await _scrape_reviews(page, max_reviews, sort="lowest")
                                seen = {r.text for r in clinic_data.reviews}
                                for r in low:
                                    if r.text not in seen:
                                        clinic_data.reviews.append(r)
                                        seen.add(r.text)

                        except Exception as e:
                            log.warning(f"    Error scraping {clinic_data.name}: {e}")
                        finally:
                            await page.close()
                    return clinic_data

                clinic_results = await asyncio.gather(
                    *[scrape_clinic(href, name, pid) for href, name, pid in targets]
                )
                results.extend(clinic_results)
                await context.close()

            return results

        zip_results = await asyncio.gather(*[scrape_zip(z) for z in zip_codes])
        for batch in zip_results:
            all_clinics.extend(batch)

        await browser.close()

    log.info(f"Scraped {len(all_clinics)} clinics total across {len(zip_codes)} zip codes")
    return all_clinics


async def _scrape_reviews(page, max_reviews: int, sort: str = "newest") -> list[ReviewData]:
    reviews: list[ReviewData] = []

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
                    await el.click(timeout=5000)
                    clicked_reviews = True
                    break
            except Exception:
                continue

        if not clicked_reviews:
            log.warning("Could not click reviews tab")
            return reviews

        await page.wait_for_load_state("networkidle")
        sleep_random(0.5, 1)

        try:
            for selector in ['[aria-label="Sort reviews"]', '[data-value="Sort"]', 'button[aria-label*="Sort" i]']:
                el = page.locator(selector).first
                if await el.count() > 0:
                    await el.click(timeout=3000)
                    sleep_random(0.3, 0.7)
                    if sort == "newest":
                        await page.locator('li[role="menuitemradio"]:has-text("Newest")').first.click(timeout=3000)
                    else:
                        await page.locator('li[role="menuitemradio"]:has-text("Lowest")').first.click(timeout=3000)
                    sleep_random(0.5, 1)
                    break
        except Exception as e:
            log.warning(f"Could not sort reviews: {e}")

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

                    reviews.append(ReviewData(author=author, rating=rating, text=text.strip(), date=None))

                except Exception:
                    continue

            if len(reviews) >= max_reviews:
                break

            prev_len = len(reviews)
            await page.evaluate("window.scrollBy(0, 1200)")
            sleep_random(1, 1.5)

            if len(reviews) == prev_len:
                no_new_count += 1
                if no_new_count >= 3:
                    break
            else:
                no_new_count = 0

    except Exception as e:
        log.warning(f"Error in _scrape_reviews: {e}")

    return reviews[:max_reviews]
