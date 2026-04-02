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

# Max clinic pages open simultaneously
_CONCURRENCY = 3


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
    match = re.search(r"0x[0-9a-f]+:0x[0-9a-f]+", url)
    if match:
        return match.group(0)
    if fallback_name:
        return "hash_" + hashlib.md5(fallback_name.encode()).hexdigest()[:16]
    return None


async def scrape_city(city: str, state: str, max_reviews: int = 200) -> list[ClinicData]:
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

        query = build_search_query(city, state)
        url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
        log.info(f"Navigating to: {url}")
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        sleep_random(1, 2)

        # Scroll results panel
        try:
            results_panel = page.locator('[role="feed"]')
            prev_count = 0
            for _ in range(10):
                await results_panel.evaluate("el => el.scrollTo(0, el.scrollHeight)")
                sleep_random(1, 2)
                items = await page.locator('[role="feed"] > div[jsaction]').all()
                if len(items) == prev_count:
                    break
                prev_count = len(items)
            log.info(f"Found {prev_count} listing items in feed")
        except Exception as e:
            log.warning(f"Could not scroll results panel: {e}")

        listing_links = await page.locator('a[href*="/maps/place/"]').all()
        log.info(f"Found {len(listing_links)} listing links")

        # Build list of (href, name) to scrape
        targets: list[tuple[str, str]] = []
        for link in listing_links:
            href = await link.get_attribute("href") or ""
            name = await link.get_attribute("aria-label") or ""
            if name and parse_place_id_from_url(href, fallback_name=name):
                targets.append((href, name))

        await page.close()

        # Scrape clinics concurrently with a semaphore
        semaphore = asyncio.Semaphore(_CONCURRENCY)

        async def scrape_one(href: str, name: str) -> ClinicData | None:
            place_id = parse_place_id_from_url(href, fallback_name=name)
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
            async with semaphore:
                clinic_page = await context.new_page()
                try:
                    await clinic_page.goto(href)
                    await clinic_page.wait_for_load_state("networkidle")
                    sleep_random(1, 2)

                    # Extract rating
                    try:
                        rating_el = clinic_page.locator('[aria-label*="stars"]').first
                        rating_text = await rating_el.get_attribute("aria-label", timeout=3000)
                        if rating_text:
                            m = re.search(r"([\d.]+) stars", rating_text)
                            if m:
                                clinic_data.overall_rating = float(m.group(1))
                    except Exception:
                        pass

                    # Extract review count
                    try:
                        for selector in ['button[jsaction*="reviewDialog"]', 'button[aria-label*="reviews"]', 'span[aria-label*="reviews"]']:
                            el = clinic_page.locator(selector).first
                            if await el.count() > 0:
                                text = await el.inner_text(timeout=3000)
                                m = re.search(r"([\d,]+)", text)
                                if m:
                                    clinic_data.total_reviews = int(m.group(1).replace(",", ""))
                                    break
                    except Exception:
                        pass

                    reviews = await _scrape_reviews(clinic_page, max_reviews)
                    log.info(f"  {clinic_data.name}: scraped {len(reviews)} reviews")
                    clinic_data.reviews.extend(reviews)

                    if clinic_data.total_reviews and clinic_data.total_reviews >= 200:
                        low_rated = await _scrape_reviews(clinic_page, max_reviews, sort="lowest")
                        seen = {r.text for r in clinic_data.reviews}
                        for r in low_rated:
                            if r.text not in seen:
                                clinic_data.reviews.append(r)
                                seen.add(r.text)

                except Exception as e:
                    log.warning(f"  Error scraping {clinic_data.name}: {e}")
                finally:
                    await clinic_page.close()

            return clinic_data

        results = await asyncio.gather(*[scrape_one(href, name) for href, name in targets])
        clinics = [r for r in results if r is not None]

        await browser.close()

    log.info(f"Scraped {len(clinics)} clinics total")
    return clinics


async def _scrape_reviews(page, max_reviews: int, sort: str = "newest") -> list[ReviewData]:
    reviews: list[ReviewData] = []

    try:
        # Click Reviews tab — try multiple selectors
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

        # Sort reviews
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

        # Collect reviews by scrolling
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
                    # Expand "More"
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
