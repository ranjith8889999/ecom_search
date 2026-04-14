"""Scraper for Amazon India product search results using Playwright."""

import urllib.parse

from app.browser import get_browser
from app.config import REQUEST_TIMEOUT, MAX_RESULTS_PER_SITE
from app.models import Product


async def search_amazon(query: str) -> list[Product]:
    """Search Amazon.in for the given query and return product list."""
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://www.amazon.in/s?k={encoded_query}"
    timeout_ms = int(REQUEST_TIMEOUT * 1000)

    browser = await get_browser()
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1366, "height": 768},
        locale="en-US",
    )
    page = await context.new_page()

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        # Wait for search result cards
        await page.wait_for_selector(
            'div[data-component-type="s-search-result"]',
            timeout=10000,
        )

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
