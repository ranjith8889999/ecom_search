"""Shared Playwright browser manager – reuses a single browser instance."""

import logging
from playwright.async_api import async_playwright, Browser, BrowserContext, Playwright

logger = logging.getLogger(__name__)

_playwright: Playwright | None = None
_browser: Browser | None = None

# JavaScript to inject into every page to hide automation signals
STEALTH_JS = """
// Overwrite the navigator.webdriver property
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// Fake plugins array
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

// Fake languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
});

// Remove automation-related properties from window
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;

// Override chrome.runtime to avoid detection
window.chrome = { runtime: {} };

// Prevent permission query from revealing automation
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) =>
    parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters);
"""


async def get_browser() -> Browser:
    """Return a shared headless Chromium browser, launching it on first call."""
    global _playwright, _browser
    if _browser is None or not _browser.is_connected():
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        logger.info("Browser launched.")
    return _browser


async def new_stealth_context(browser: Browser, **kwargs) -> BrowserContext:
    """Create a new browser context with stealth scripts pre-injected."""
    defaults = dict(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1366, "height": 768},
        locale="en-IN",
        timezone_id="Asia/Kolkata",
        extra_http_headers={
            "Accept-Language": "en-IN,en;q=0.9",
        },
    )
    defaults.update(kwargs)
    context = await browser.new_context(**defaults)
    # Inject stealth script before any page JavaScript runs
    await context.add_init_script(STEALTH_JS)
    return context


async def shutdown_browser() -> None:
    """Gracefully close the shared browser (called on app shutdown)."""
    global _playwright, _browser
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None
