"""
Debug script: run scraper for ONE clinic in NON-HEADLESS mode so you can
see what Google Maps actually renders and which selectors fail.

Usage:
    PYTHONPATH=. python debug_scraper.py
"""
import asyncio
import logging
import re

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("debug_scraper")


async def main():
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)  # VISIBLE browser
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        # ── Step 1: search page ──────────────────────────────────────────────
        url = "https://www.google.com/maps/search/dental+clinics+in+Houston,+TX"
        log.info(f"Navigating to {url}")
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)

        listing_links = await page.locator('a[href*="/maps/place/"]').all()
        log.info(f"Found {len(listing_links)} listing links")

        if not listing_links:
            log.error("No listing links found — Google may be blocking or showing CAPTCHA")
            input("Browser is open. Press Enter to close...")
            await browser.close()
            return

        # ── Step 2: open first clinic ────────────────────────────────────────
        first_link = listing_links[0]
        href = await first_link.get_attribute("href") or ""
        name = await first_link.get_attribute("aria-label") or "unknown"
        log.info(f"Opening clinic: {name}")
        log.info(f"URL: {href}")

        clinic_page = await context.new_page()
        await clinic_page.goto(href)
        await clinic_page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)

        # ── Step 3: try each reviews-tab selector ────────────────────────────
        review_tab_selectors = [
            'button[aria-label*="reviews" i]',
            'button[data-tab-index="1"]',
            '[role="tab"]:has-text("Reviews")',
            'button:has-text("Reviews")',
        ]
        for sel in review_tab_selectors:
            els = await clinic_page.locator(sel).all()
            log.info(f"  reviews-tab selector '{sel}': {len(els)} match(es)")

        # ── Step 4: try clicking the reviews tab ─────────────────────────────
        clicked = False
        for sel in review_tab_selectors:
            try:
                el = clinic_page.locator(sel).first
                if await el.count() > 0:
                    await el.click(timeout=5000)
                    log.info(f"  Clicked reviews tab with: {sel}")
                    clicked = True
                    await asyncio.sleep(2)
                    break
            except Exception as e:
                log.warning(f"  Could not click '{sel}': {e}")

        if not clicked:
            log.error("  Could NOT click reviews tab with any selector")
            input("Browser is open. Press Enter to close (check what you see)...")
            await browser.close()
            return

        # ── Step 5: check review element selectors ───────────────────────────
        review_selectors = [
            '[data-review-id]',
            '[jslog*="review"]',
            'div[class*="review"]',
            '.jftiEf',
            '.WMbnJf',
        ]
        for sel in review_selectors:
            count = await clinic_page.locator(sel).count()
            log.info(f"  review container '{sel}': {count} match(es)")

        # ── Step 6: check text selectors ─────────────────────────────────────
        text_selectors = ['.wiI7pd', '.MyEned', 'span[data-expandable-section]', '[class*="review-full-text"]']
        for sel in text_selectors:
            count = await clinic_page.locator(sel).count()
            log.info(f"  review text '{sel}': {count} match(es)")

        input("\nBrowser is open. Check the reviews tab visually. Press Enter to close...")
        await browser.close()


asyncio.run(main())
