# Day 3 — MyScheme.gov.in Scraping Fix

---

## The Problem Summary

MyScheme.gov.in is a React app. It calls an internal authenticated API:

```
GET api.myscheme.gov.in/search/v6/schemes?from=0&size=10
```

The auth token is generated inside React's JavaScript bundle at runtime — stored in memory, attached to every API call via Authorization header. You can't get it from outside.

---

## What Was Tried and Why It Failed

| Approach | Why it failed |
|---|---|
| Direct API call via httpx | 401 Unauthorized — API requires React's runtime auth token |
| Browser cookies + httpx | Still 401 — auth is in request headers, not cookies |
| page.evaluate(fetch(...)) | Empty data — script's fetch doesn't carry React's auth context |
| URL params (?keyword=pension) | React ignores URL params — search controlled by internal state |
| Route interception (size=10→200) | Response capture breaks after modification |
| Click pagination in headless | Buttons not found — React renders them based on viewport/scroll |

---

## The Core Issue

```
React boots → generates auth token in memory
           → attaches token to every API call
           → token never exposed to outside world
```

Without reverse-engineering React's minified JavaScript bundle, you cannot call the API directly.

---

## The Fix — Response Interception + UI Automation

Don't call the API yourself. **Let React call it and intercept what comes back.**

Playwright opens a real browser. React boots normally and generates its own token. You click Next Page — React makes the authenticated request itself. You just listen to the response.

```
Playwright opens browser
        ↓
React boots, generates auth token in memory
        ↓
You click Next → React calls API with its own token
        ↓
Playwright intercepts the RESPONSE (not the request)
        ↓
You collect the data
        ↓
Repeat for all 467 pages
```

---

## The Scraper Code

```python
# scraper/myscheme_scraper.py

import asyncio
import json
from playwright.async_api import async_playwright

all_schemes = []

async def scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # keep visible so you can debug
        page = await browser.new_page()

        # Intercept every API response — React makes the call, we just listen
        async def handle_response(response):
            if "api.myscheme.gov.in/search/v6/schemes" in response.url:
                try:
                    data = await response.json()
                    schemes = data.get("data", {}).get("hits", [])
                    all_schemes.extend(schemes)
                    print(f"Collected {len(all_schemes)} schemes so far...")
                except:
                    pass

        page.on("response", handle_response)

        await page.goto("https://myscheme.gov.in/search")
        await page.wait_for_timeout(3000)  # wait for React to fully boot

        # Keep clicking Next — React handles auth internally
        while True:
            try:
                next_btn = page.locator("button[aria-label='Next page']")
                if not await next_btn.is_visible():
                    break
                await next_btn.click()
                await page.wait_for_timeout(2000)  # wait for React to fetch next batch
            except:
                break

        await browser.close()

        # Save everything to JSON
        with open("scraper/raw_schemes.json", "w") as f:
            json.dump(all_schemes, f, indent=2, ensure_ascii=False)

        print(f"Done. Total: {len(all_schemes)} schemes collected")

asyncio.run(scrape())
```

---

## If the Next Button Selector Is Wrong

The `aria-label='Next page'` selector might differ. To find the correct one:

1. Open myscheme.gov.in/search in Chrome
2. Right click the Next Page button → Inspect
3. Look for a unique attribute — `aria-label`, `data-testid`, or a class name
4. Update the locator in the scraper accordingly

```python
# Examples of alternative selectors
page.locator("button[aria-label='Next page']")     # aria label
page.locator("[data-testid='pagination-next']")     # test id
page.locator("button.pagination-next")              # class name
```

---

## Practical Numbers

| Metric | Value |
|---|---|
| Total schemes on MyScheme | 4,666 |
| Schemes per page | 10 |
| Total pages | 467 |
| Wait per page | 2 seconds |
| Total time | ~16 minutes |

Run it once. Save `raw_schemes.json`. Never run again unless you want to refresh data.

---

## Backup — data.gov.in (Run in Parallel)

While the scraper runs, download CSVs from data.gov.in simultaneously. No scraping needed — direct downloads.

- Go to **data.gov.in**
- Search `pradhan mantri yojana`
- Search `state government schemes`
- Search `social welfare schemes india`
- Download all available CSVs

Use these to cross-verify scraper data.

---

## Full Day 3 Pipeline

```
Run myscheme_scraper.py (~16 min, one time only)
            +
Download CSVs from data.gov.in
            ↓
Merge both into one raw dataset
            ↓
Use AI to structure eligibility rules into JSON format
            ↓
Manually spot check 20-30 schemes against ministry sites
            ↓
Final schemes_seed.json
            ↓
Run seed.py → inserts into PostgreSQL
```

---

## End of Day 3 Check

- [ ] `raw_schemes.json` exists with 1000+ schemes
- [ ] data.gov.in CSVs downloaded
- [ ] `schemes_seed.json` structured and verified
- [ ] `seed.py` runs without errors
- [ ] `SELECT count(*) FROM schemes;` returns 500+

---

## Note on Being Respectful

- Keep `wait_for_timeout` at minimum 2000ms — don't hammer the server
- Run the scraper once and save the output — don't re-run repeatedly
- This is for educational purposes only
