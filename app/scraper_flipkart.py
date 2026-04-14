"""Scraper for Flipkart product search results using Playwright."""

import urllib.parse

from app.browser import get_browser, new_stealth_context
from app.config import REQUEST_TIMEOUT, MAX_RESULTS_PER_SITE
from app.models import Product


async def search_flipkart(query: str) -> list[Product]:
    """Search Flipkart for the given query and return product list."""
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://www.flipkart.com/search?q={encoded_query}"
    timeout_ms = int(REQUEST_TIMEOUT * 1000)

    browser = await get_browser()
    context = await new_stealth_context(browser)
    page = await context.new_page()

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        # Close login popup if it appears
        try:
            close_btn = page.locator('button._2KpZ6l._2doB4z')
            if await close_btn.count() > 0:
                await close_btn.click(timeout=2000)
        except Exception:
            pass

        # Wait for product listings to appear (try multiple selectors)
        try:
            await page.wait_for_selector('div[data-id], a[href*="/p/"]', timeout=10000)
        except Exception:
            pass

        raw = await page.evaluate("""(maxResults) => {
            const results = [];
            // Use div[data-id] cards (the main product containers)
            const cards = document.querySelectorAll('div[data-id]');

            for (const card of cards) {
                if (results.length >= maxResults) break;
                try {
                    // Link – find the product link inside the card
                    const linkEl = card.querySelector('a[href*="/p/"]');
                    if (!linkEl) continue;
                    const href = linkEl.getAttribute('href') || '';
                    const link = href.startsWith('http') ? href : 'https://www.flipkart.com' + href;

                    // Title – best source is the <img> alt text, or specific class divs
                    let title = '';
                    const imgEl = card.querySelector('img[alt]');
                    if (imgEl) title = imgEl.getAttribute('alt') || '';
                    if (!title) {
                        // Try known title class patterns
                        const titleEl = card.querySelector(
                            'div[class*="KzDlHZ"], div[class*="syl9yP"], div[class*="_4rR01T"], ' +
                            'div[class*="RG5Slk"], a[class*="s1Q9rs"], a[title]'
                        );
                        if (titleEl) title = titleEl.getAttribute('title') || titleEl.textContent.trim();
                    }
                    if (!title) continue;

                    // Image
                    const image = imgEl ? (imgEl.getAttribute('src') || '') : '';

                    // Price – look for elements whose text starts with ₹
                    let price = 'Price not available';
                    const allDivs = card.querySelectorAll('div, span');
                    for (const d of allDivs) {
                        const txt = d.textContent.trim();
                        // Match ₹ followed by digits (price pattern)
                        if (/^₹[\\d,]+$/.test(txt) && txt.length < 15) {
                            price = txt;
                            break;
                        }
                    }

                    // Rating – look for small rating badges
                    let rating = '';
                    const ratingEl = card.querySelector(
                        'div[class*="XQDdHH"], div[class*="_3LWZlK"], span[class*="CjyrHS"]'
                    );
                    if (ratingEl) rating = ratingEl.textContent.trim();

                    results.push({ title, price, link, image, rating, source: 'Flipkart' });
                } catch(e) { continue; }
            }

            // Fallback: if no data-id cards found, try anchor-based approach
            if (results.length === 0) {
                const anchors = document.querySelectorAll('a[href*="/p/"]');
                const seen = new Set();
                for (const anchor of anchors) {
                    if (results.length >= maxResults) break;
                    const href = anchor.getAttribute('href') || '';
                    if (seen.has(href)) continue;
                    seen.add(href);

                    const imgEl = anchor.querySelector('img[alt]');
                    const title = imgEl ? (imgEl.getAttribute('alt') || '') : '';
                    if (!title) continue;

                    const link = href.startsWith('http') ? href : 'https://www.flipkart.com' + href;
                    const image = imgEl ? (imgEl.getAttribute('src') || '') : '';

                    let price = 'Price not available';
                    const parent = anchor.closest('div') || anchor;
                    const allText = parent.querySelectorAll('div, span');
                    for (const d of allText) {
                        const txt = d.textContent.trim();
                        if (/^₹[\\d,]+$/.test(txt) && txt.length < 15) {
                            price = txt;
                            break;
                        }
                    }

                    results.push({ title, price, link, image, rating: '', source: 'Flipkart' });
                }
            }

            return results;
        }""", MAX_RESULTS_PER_SITE)

        return [Product(**p) for p in raw]
    finally:
        await context.close()
