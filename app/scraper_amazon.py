"""Scraper for Amazon India product search results using Playwright."""

import logging
import urllib.parse

from app.browser import get_browser, new_stealth_context
from app.config import REQUEST_TIMEOUT, MAX_RESULTS_PER_SITE
from app.models import Product

logger = logging.getLogger(__name__)


async def search_amazon(query: str) -> list[Product]:
    """Search Amazon.in for the given query and return product list."""
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://www.amazon.in/s?k={encoded_query}"
    timeout_ms = int(REQUEST_TIMEOUT * 1000)

    browser = await get_browser()
    context = await new_stealth_context(browser)
    page = await context.new_page()

    try:
        # Navigate and wait for full load
        await page.goto(url, wait_until="networkidle", timeout=timeout_ms)

        # Log page title for diagnostics (helps identify CAPTCHA pages)
        title = await page.title()
        logger.info("Amazon page title: %s", title)

        # Check if Amazon is showing a CAPTCHA
        captcha = await page.query_selector('form[action*="validateCaptcha"], input#captchacharacters')
        if captcha:
            logger.warning("Amazon CAPTCHA detected — attempting to work around")
            # Try reloading once
            await page.reload(wait_until="networkidle", timeout=timeout_ms)
            captcha = await page.query_selector('form[action*="validateCaptcha"], input#captchacharacters')
            if captcha:
                return []  # still blocked, return empty

        # Wait for search result cards
        try:
            await page.wait_for_selector(
                'div[data-component-type="s-search-result"]',
                timeout=15000,
            )
        except Exception:
            logger.warning("Primary Amazon selector not found, trying fallback")
            # Could be a different page layout (no results, different region, etc.)
            pass

        raw = await page.evaluate("""(maxResults) => {
            const cards = document.querySelectorAll('div[data-component-type="s-search-result"]');
            const results = [];
            for (let i = 0; i < Math.min(cards.length, maxResults); i++) {
                const card = cards[i];
                try {
                    const titleEl = card.querySelector('h2');
                    const title = titleEl ? titleEl.textContent.trim() : '';
                    if (!title) continue;

                    // Link: try h2 a first, then any a with /dp/ pattern
                    const linkEl = card.querySelector('h2 a') || card.querySelector('a[href*="/dp/"]') || card.querySelector('a.a-link-normal');
                    let href = linkEl ? (linkEl.getAttribute('href') || '') : '';
                    if (href && !href.startsWith('http')) href = 'https://www.amazon.in' + href;

                    const priceEl = card.querySelector('span.a-price span.a-offscreen');
                    const price = priceEl ? priceEl.textContent.trim() : 'Price not available';

                    const imgEl = card.querySelector('img.s-image');
                    const image = imgEl ? imgEl.getAttribute('src') : '';

                    const ratingEl = card.querySelector('span.a-icon-alt');
                    const rating = ratingEl ? ratingEl.textContent.trim() : '';

                    results.push({ title, price, link: href || '', image: image || '', rating: rating || '', source: 'Amazon' });
                } catch(e) { continue; }
            }
            return results;
        }""", MAX_RESULTS_PER_SITE)

        return [Product(**p) for p in raw]
    finally:
        await context.close()
