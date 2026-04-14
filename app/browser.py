"""Shared Playwright browser manager – reuses a single browser instance."""

from playwright.async_api import async_playwright, Browser, Playwright

_playwright: Playwright | None = None
_browser: Browser | None = None


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
    return _browser


async def shutdown_browser() -> None:
    """Gracefully close the shared browser (called on app shutdown)."""
    global _playwright, _browser
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None
