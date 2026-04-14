"""Quick test for scrapers."""
import asyncio
from app.browser import shutdown_browser
from app.scraper_amazon import search_amazon
from app.scraper_flipkart import search_flipkart


async def test():
    print("Testing Amazon...")
    try:
        results = await search_amazon("laptop")
        print(f"Amazon: {len(results)} results")
        for r in results[:3]:
            print(f"  - {r.title[:55]} | {r.price} | {r.rating[:20]}")
    except Exception as e:
        print(f"Amazon error: {e}")

    print("\nTesting Flipkart...")
    try:
        results = await search_flipkart("laptop")
        print(f"Flipkart: {len(results)} results")
        for r in results[:3]:
            print(f"  - {r.title[:55]} | {r.price} | {r.rating}")
    except Exception as e:
        print(f"Flipkart error: {e}")

    await shutdown_browser()
    print("\nDone!")


asyncio.run(test())
