# 🛒 Product Search – Amazon & Flipkart

A real-time product search tool that scrapes live results from **Amazon India** and **Flipkart** concurrently and displays them in a clean, responsive web UI.

> **No static/hardcoded data** – every result is fetched live from the actual websites.

---

## 📸 How It Works

1. User types a product name (e.g., "laptop", "iPhone 15", "headphones")
2. Backend launches **two parallel scrapers** (Amazon + Flipkart)
3. A headless Chromium browser (via Playwright) loads each site's search page
4. Product cards are extracted using JavaScript DOM evaluation
5. Results are returned as JSON and rendered in a two-column UI

---

## 🏗️ Project Structure

```
websearch/
├── app/
│   ├── __init__.py            # Package marker
│   ├── config.py              # Timeout & result limit settings
│   ├── models.py              # Product & SearchResponse dataclasses
│   ├── browser.py             # Shared Playwright browser manager (singleton)
│   ├── scraper_amazon.py      # Amazon.in search scraper
│   ├── scraper_flipkart.py    # Flipkart search scraper
│   └── main.py                # FastAPI app (API + serves UI)
├── static/
│   └── index.html             # Frontend search UI (HTML/CSS/JS)
├── requirements.txt           # Python dependencies
├── test_scrapers.py           # Standalone test script
└── README.md                  # This file
```

---

## 🛠️ Tech Stack & Components

| Component | Technology | Purpose |
|---|---|---|
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) | Async Python web framework for the API server |
| **ASGI Server** | [Uvicorn](https://www.uvicorn.org/) | High-performance async server to run FastAPI |
| **Browser Automation** | [Playwright](https://playwright.dev/python/) | Headless Chromium browser to bypass anti-bot protections |
| **HTML Parsing** | [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) + [lxml](https://lxml.de/) | Available as fallback parsers (primary parsing is via Playwright's `page.evaluate()`) |
| **Frontend** | Vanilla HTML/CSS/JavaScript | Responsive search UI – no frameworks needed |
| **Concurrency** | Python `asyncio` | Amazon & Flipkart are scraped in parallel via `asyncio.gather()` |
| **Data Models** | Python `dataclasses` | `Product` and `SearchResponse` models |

### Why Playwright Instead of HTTP Requests?

Initially, the project used `httpx` for direct HTTP requests. Both Amazon and Flipkart returned **403 Forbidden** / **503 Service Unavailable** errors due to anti-bot protections (CAPTCHAs, WAF). Playwright solves this by running a real Chromium browser that behaves like a genuine user.

---

## 🚀 Setup & Run

### Prerequisites

- **Python 3.10+** (tested with 3.12)
- **Windows/macOS/Linux**

### Installation

```bash
# 1. Navigate to project directory
cd websearch

# 2. Create virtual environment
python -m venv .venv

# 3. Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Install Chromium browser for Playwright
python -m playwright install chromium
```

### Run the Server

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then open **http://127.0.0.1:8000** in your browser.

---

## 📡 API Endpoint

### `GET /api/search?q=<query>`

| Parameter | Type | Description |
|---|---|---|
| `q` | string (required) | Product search term (1–200 chars) |

### Example Response

```json
{
  "query": "headphones",
  "amazon_results": [
    {
      "title": "Sony WH-CH520 Wireless Bluetooth Headphones...",
      "price": "₹3,989",
      "link": "https://www.amazon.in/dp/B0CHX1W1XY/...",
      "image": "https://m.media-amazon.com/images/I/...",
      "rating": "4.2 out of 5 stars",
      "source": "Amazon"
    }
  ],
  "flipkart_results": [
    {
      "title": "boAt Rockerz 411...",
      "price": "₹1,099",
      "link": "https://www.flipkart.com/...",
      "image": "https://rukminim2.flixcart.com/...",
      "rating": "3.9",
      "source": "Flipkart"
    }
  ],
  "amazon_error": "",
  "flipkart_error": "",
  "total_results": 20
}
```

---

## ⚠️ Common Errors & Troubleshooting

### 1. `NotImplementedError` on startup (Windows)

**Cause:** Playwright needs `WindowsProactorEventLoopPolicy` to spawn subprocesses on Windows. Uvicorn's `--reload` flag uses a different event loop that conflicts.

**Fix:** Run **without** `--reload`:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
The app already sets the correct policy in `main.py`:
```python
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

### 2. `[Errno 10048] port already in use`

**Cause:** Another process is using port 8000.

**Fix:**
```bash
# Find & kill the process (Windows)
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Or use a different port
python -m uvicorn app.main:app --port 8080
```

### 3. `h2 package not installed`

**Cause:** HTTP/2 was enabled but missing dependency.

**Fix:** Already resolved – the project uses Playwright instead of httpx.

### 4. Amazon returns 503 / Flipkart returns 403

**Cause:** Direct HTTP requests (httpx/requests) are blocked by anti-bot systems.

**Fix:** Already resolved – Playwright headless Chromium bypasses these protections.

### 5. Flipkart returns 0 results

**Cause:** Flipkart frequently changes their CSS class names (e.g., `KzDlHZ`, `Nx9bqj`, `XQDdHH`). If classes change, selectors break.

**Fix:** The scraper uses multiple strategies:
- Primary: `div[data-id]` cards with `img[alt]` for titles (more stable)
- Fallback: `a[href*="/p/"]` anchor-based extraction
- Price detection via regex `₹` pattern instead of class names

If results are still 0, you may need to inspect Flipkart's current HTML and update the selectors in `scraper_flipkart.py`.

### 6. Browser launch fails / Chromium not found

**Cause:** Playwright browser binaries not installed.

**Fix:**
```bash
python -m playwright install chromium
```

### 7. Slow first request

**Cause:** Browser is being launched on first request.

**Fix:** The app pre-warms the browser on startup (via the `lifespan` handler). If pre-warm fails, the first search request will launch it (adds ~2-3 seconds).

### 8. `Event loop is closed` warnings

**Cause:** Playwright subprocess cleanup race condition on script exit. This is a cosmetic warning and does **not** affect results.

**Fix:** No action needed. It only appears in test scripts, not during server operation.

---

## ⚙️ Configuration

Edit `app/config.py`:

```python
REQUEST_TIMEOUT = 20.0   # seconds per page load (increase if on slow network)
MAX_RESULTS_PER_SITE = 10 # max products to extract per site
```

---

## 📦 Dependencies

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.115.0 | Web framework |
| `uvicorn` | 0.30.6 | ASGI server |
| `playwright` | latest | Headless browser automation |
| `beautifulsoup4` | 4.12.3 | HTML parser (fallback) |
| `lxml` | 5.3.0 | Fast XML/HTML parser |

---

## 📌 Key Design Decisions

1. **Playwright over httpx** – Both Amazon and Flipkart aggressively block automated HTTP requests. Playwright renders pages like a real browser.
2. **Shared browser instance** – A single Chromium process is reused across requests. Each search creates a fresh browser context (isolated cookies/state) then closes it.
3. **Parallel scraping** – `asyncio.gather()` runs both scrapers concurrently, cutting total response time roughly in half.
4. **Graceful error handling** – If one site fails, the other still returns results. Errors are shown per-source in the UI.
5. **No static data** – All product titles, prices, images, ratings, and links come from live page scraping.
