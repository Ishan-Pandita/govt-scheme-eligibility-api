"""
MyScheme.gov.in — Full data collector using stolen API key.

Captures x-api-key from browser request, then calls API directly
to get ALL 4,666 schemes in ~2 minutes.
"""
import asyncio
import json
import os
import time
import httpx
from playwright.async_api import async_playwright

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
RAW_DIR = os.path.join(os.path.dirname(__file__), "raw_data")
API_URL = "https://api.myscheme.gov.in/search/v6/schemes"


async def steal_api_key():
    """Capture x-api-key from the browser's request to the API."""
    api_key = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, channel="chrome")
        page = await browser.new_page()

        async def handle_request(request):
            nonlocal api_key
            if "api.myscheme.gov.in" in request.url and not api_key:
                key = request.headers.get("x-api-key", "")
                if key:
                    api_key = key
                    print(f"  API key captured: {key}")

        page.on("request", handle_request)

        print("Step 1: Stealing API key from browser...")
        await page.goto("https://www.myscheme.gov.in/search")
        await page.wait_for_timeout(10000)
        await browser.close()

    return api_key


async def collect_all_schemes(api_key):
    """Use the API key to call the API directly for ALL schemes."""
    print(f"\nStep 2: Collecting ALL schemes via direct API...")
    all_items = []
    size = 50

    headers = {
        "x-api-key": api_key,
        "accept": "application/json",
        "origin": "https://www.myscheme.gov.in",
        "referer": "https://www.myscheme.gov.in/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        # First request to get total count
        resp = await client.get(API_URL, params={"lang": "en", "q": "[]", "keyword": "", "sort": "", "from": 0, "size": 1})
        if resp.status_code != 200:
            print(f"  First request failed: HTTP {resp.status_code}")
            print(f"  Response: {resp.text[:200]}")
            return []
        total = resp.json().get("data", {}).get("summary", {}).get("total", 0)
        print(f"  Total schemes available: {total}")

        # Paginate through all
        for offset in range(0, total + 50, size):
            try:
                resp = await client.get(
                    API_URL,
                    params={"lang": "en", "q": "[]", "keyword": "", "sort": "", "from": offset, "size": size},
                )

                if resp.status_code == 401:
                    print(f"  API key expired at offset {offset}. Got {len(all_items)} schemes.")
                    break
                if resp.status_code != 200:
                    print(f"  HTTP {resp.status_code} at offset {offset}")
                    break

                data = resp.json()
                items = data.get("data", {}).get("hits", {}).get("items", [])
                if not items:
                    print(f"  No more items at offset {offset}")
                    break

                all_items.extend(items)

                if offset % 500 == 0:
                    print(f"  Offset {offset}: {len(all_items)} / {total}")

            except Exception as e:
                print(f"  Error at offset {offset}: {e}")
                break

            await asyncio.sleep(0.3)

    return all_items


async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)
    start = time.time()

    # Step 1: Steal API key
    api_key = await steal_api_key()
    if not api_key:
        print("Failed to capture API key!")
        return

    # Step 2: Collect ALL scheme IDs
    all_items = await collect_all_schemes(api_key)
    if not all_items:
        return

    # Save raw
    ids_path = os.path.join(RAW_DIR, "myscheme_ids.json")
    with open(ids_path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, indent=2, ensure_ascii=False)

    # Extract listings
    listings = []
    slugs = []
    seen = set()
    for item in all_items:
        fields = item.get("fields", {})
        slug = fields.get("slug", "")
        name = fields.get("schemeName", "")
        if not slug or slug in seen:
            continue
        seen.add(slug)
        slugs.append(slug)
        states = fields.get("beneficiaryState", [])
        if isinstance(states, str):
            states = [states]
        categories = fields.get("schemeCategory", [])
        if isinstance(categories, str):
            categories = [categories]
        listings.append({
            "name": name,
            "slug": slug,
            "ministry": fields.get("nodalMinistryName", ""),
            "scheme_type": "central" if fields.get("level", "").lower() == "central" else "state",
            "category": ", ".join(categories),
            "states": [s for s in states if s != "All"],
        })

    listings_path = os.path.join(OUTPUT_DIR, "scheme_listings_full.json")
    with open(listings_path, "w", encoding="utf-8") as f:
        json.dump(listings, f, indent=2, ensure_ascii=False)

    elapsed = (time.time() - start) / 60
    print(f"\n{'='*60}")
    print(f"  {len(listings)} unique schemes collected in {elapsed:.1f} min")
    print(f"  Slugs saved for detail scraping")
    print(f"{'='*60}")

    # Save slugs for detail scraper
    with open(os.path.join(OUTPUT_DIR, "all_slugs.json"), "w") as f:
        json.dump(slugs, f, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
