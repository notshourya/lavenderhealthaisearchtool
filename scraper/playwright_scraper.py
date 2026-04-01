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
