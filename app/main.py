"""Main FastAPI application – product search across Amazon & Flipkart."""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.browser import get_browser, shutdown_browser
from app.scraper_amazon import search_amazon
from app.scraper_flipkart import search_flipkart
from app.models import SearchResponse

# Fix: On Windows, Playwright needs ProactorEventLoop for subprocess creation
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
PREWARM_BROWSER = os.getenv("PREWARM_BROWSER", "0").strip().lower() in {"1", "true", "yes", "on"}


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup / shutdown lifecycle – manages browser."""
    logger.info("Starting up application...")
    if PREWARM_BROWSER:
        logger.info("Browser pre-warm enabled.")
        try:
            await get_browser()  # optional pre-launch so first request is fast
            logger.info("Browser ready.")
        except Exception as exc:
            logger.warning("Browser pre-warm failed (will retry on first request): %s", exc)
    else:
        logger.info("Browser pre-warm disabled for faster container startup.")
    yield
    logger.info("Shutting down – closing browser…")
    await shutdown_browser()


app = FastAPI(title="Product Search – Amazon & Flipkart", lifespan=lifespan)

# Serve static frontend
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the main search UI."""
    index_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))


@app.api_route("/health", methods=["GET", "HEAD"])
async def healthcheck():
    """Lightweight health endpoint for container platforms."""
    return {"status": "ok"}


@app.get("/api/search")
async def api_search(q: str = Query(..., min_length=1, max_length=200)):
    """Search both Amazon and Flipkart concurrently and return results."""
    query = q.strip()
    resp = SearchResponse(query=query)

    # Run both scrapers concurrently
    amazon_task = asyncio.create_task(_safe_amazon(query))
    flipkart_task = asyncio.create_task(_safe_flipkart(query))

    amazon_result, flipkart_result = await asyncio.gather(amazon_task, flipkart_task)

    if isinstance(amazon_result, list):
        resp.amazon_results = amazon_result
    else:
        resp.amazon_error = str(amazon_result)

    if isinstance(flipkart_result, list):
        resp.flipkart_results = flipkart_result
    else:
        resp.flipkart_error = str(flipkart_result)

    return JSONResponse(content=resp.to_dict())


async def _safe_amazon(query: str):
    """Wrapper that catches exceptions so one failure doesn't block the other."""
    try:
        return await search_amazon(query)
    except Exception as exc:
        logger.exception("Amazon search failed for %r", query)
        return f"Amazon search failed: {exc}"


async def _safe_flipkart(query: str):
    """Wrapper that catches exceptions so one failure doesn't block the other."""
    try:
        return await search_flipkart(query)
    except Exception as exc:
        logger.exception("Flipkart search failed for %r", query)
        return f"Flipkart search failed: {exc}"
