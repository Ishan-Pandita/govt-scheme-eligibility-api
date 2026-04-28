# Full Plan — Getting All Verified Government Schemes

---

## The Strategy

Three sources. Each fills what the other misses. Together they give you a complete, verified dataset.

```
Source 1: data.gov.in      → Official CSV downloads (fastest, most verified)
Source 2: MyScheme API     → 4,666 scheme IDs + basic info
Source 3: Detail Scraping  → Full eligibility for what's missing
          ↓
    Merge + Deduplicate
          ↓
    AI structures eligibility rules
          ↓
    Manual spot check
          ↓
    schemes_seed.json → PostgreSQL
```

---

## Source 1 — data.gov.in (Do This First)

**Why first:** Official government uploaded data. No scraping. No auth. Direct download. Already verified.

**Step 1:** Go to these URLs and download every dataset you find:

```
https://data.gov.in/search?title=scheme
https://data.gov.in/search?title=yojana
https://data.gov.in/search?title=pradhan+mantri
https://data.gov.in/search?title=welfare+scheme
https://data.gov.in/search?title=scholarship
https://data.gov.in/search?title=pension
```

**Step 2:** For each dataset click "Download" → CSV format

**Step 3:** Save all CSVs inside `scraper/raw_data/data_gov/`

**What you'll get:** 2,000-3,000 schemes with official details, ministry names, benefit amounts, eligibility in plain English.

**Time taken:** 30 minutes max.

---

## Source 2 — MyScheme API (Token Steal Method)

**Why:** Gets all 4,666 scheme IDs and slugs. Even if details are missing, you have the complete list to work from.

**Step 1:** Run this script to steal the auth token and collect all scheme IDs:

```python
# scraper/myscheme_id_collector.py

import asyncio
import json
import httpx
from playwright.async_api import async_playwright

async def collect_all_ids():
    auth_token = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        async def handle_request(request):
            nonlocal auth_token
            if "api.myscheme.gov.in/search/v6/schemes" in request.url:
                headers = request.headers
                if "authorization" in headers and not auth_token:
                    auth_token = headers["authorization"]
                    print(f"Token captured.")

        page.on("request", handle_request)
        await page.goto("https://myscheme.gov.in/search")
        await page.wait_for_timeout(5000)
        await browser.close()

    if not auth_token:
        print("Token not found. Try again.")
        return

    all_schemes = []
    size = 50

    async with httpx.AsyncClient() as client:
        for offset in range(0, 4700, size):
            response = await client.get(
                "https://api.myscheme.gov.in/search/v6/schemes",
                params={
                    "lang": "en",
                    "q": "[]",
                    "keyword": "",
                    "sort": "",
                    "from": offset,
                    "size": size
                },
                headers={
                    "authorization": auth_token,
                    "origin": "https://myscheme.gov.in",
                    "referer": "https://myscheme.gov.in/"
                }
            )

            if response.status_code == 401:
                print(f"Token expired at offset {offset}. Saving what we have.")
                break

            data = response.json()
            schemes = data.get("data", {}).get("hits", [])
            all_schemes.extend(schemes)
            print(f"Collected {len(all_schemes)} scheme IDs...")
            await asyncio.sleep(0.5)

    with open("scraper/raw_data/myscheme_ids.json", "w") as f:
        json.dump(all_schemes, f, indent=2, ensure_ascii=False)

    print(f"Done. {len(all_schemes)} scheme IDs saved.")

asyncio.run(collect_all_ids())
```

**What you'll get:** JSON file with all 4,666 scheme IDs, slugs, tags, and basic info.

**Time taken:** ~2 minutes.

---

## Source 3 — MyScheme Detail Pages (For Missing Schemes Only)

**Why:** For schemes that exist in MyScheme but not in data.gov.in, you scrape the detail page to get full eligibility.

**Step 1:** After merging Source 1 and Source 2, find schemes with missing eligibility details.

**Step 2:** Run this scraper only for those schemes:

```python
# scraper/myscheme_detail_scraper.py

import asyncio
import json
from playwright.async_api import async_playwright

async def scrape_detail_pages(scheme_slugs: list):
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for slug in scheme_slugs:
            url = f"https://myscheme.gov.in/schemes/{slug}"
            try:
                await page.goto(url, timeout=15000)
                await page.wait_for_timeout(2000)

                name = await page.title()

                # Adjust selectors based on actual page structure
                try:
                    eligibility = await page.locator(".eligibility").inner_text()
                except:
                    eligibility = ""

                try:
                    benefits = await page.locator(".benefits").inner_text()
                except:
                    benefits = ""

                try:
                    apply_link = await page.locator("a:has-text('Apply')").get_attribute("href")
                except:
                    apply_link = f"https://myscheme.gov.in/schemes/{slug}"

                results.append({
                    "slug": slug,
                    "name": name,
                    "eligibility_raw": eligibility,
                    "benefits_raw": benefits,
                    "apply_link": apply_link,
                    "source": "myscheme_detail"
                })

                print(f"Scraped: {slug}")
                await asyncio.sleep(1.5)  # be respectful

            except Exception as e:
                print(f"Failed: {slug} — {e}")

        await browser.close()

    with open("scraper/raw_data/myscheme_details.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Done. {len(results)} detail pages scraped.")

# Only run for schemes missing from data.gov.in
with open("scraper/missing_slugs.json") as f:
    slugs = json.load(f)

asyncio.run(scrape_detail_pages(slugs))
```

**Time taken:** ~1.5 seconds per scheme. For 1,000 missing schemes = ~25 minutes.

---

## Step 4 — Merge All Three Sources

```python
# scraper/merger.py

import json
import csv
import os

all_schemes = {}

# Load data.gov.in CSVs
for filename in os.listdir("scraper/raw_data/data_gov/"):
    if filename.endswith(".csv"):
        with open(f"scraper/raw_data/data_gov/{filename}", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("Scheme Name") or row.get("scheme_name") or ""
                if name:
                    all_schemes[name.lower().strip()] = {
                        "name": name,
                        "source": "data_gov",
                        "raw": row
                    }

# Load MyScheme IDs
with open("scraper/raw_data/myscheme_ids.json") as f:
    myscheme_data = json.load(f)
    for scheme in myscheme_data:
        name = scheme.get("title", "")
        key = name.lower().strip()
        if key in all_schemes:
            all_schemes[key]["slug"] = scheme.get("id")
            all_schemes[key]["tags"] = scheme.get("tags", [])
        else:
            all_schemes[key] = {
                "name": name,
                "slug": scheme.get("id"),
                "tags": scheme.get("tags", []),
                "source": "myscheme_only"
            }

# Load detail pages for missing ones
with open("scraper/raw_data/myscheme_details.json") as f:
    details = json.load(f)
    for d in details:
        key = d["name"].lower().strip()
        if key in all_schemes:
            all_schemes[key].update({
                "eligibility_raw": d.get("eligibility_raw"),
                "benefits_raw": d.get("benefits_raw"),
                "apply_link": d.get("apply_link")
            })

# Save merged output
merged = list(all_schemes.values())
with open("scraper/raw_data/merged_schemes.json", "w") as f:
    json.dump(merged, f, indent=2, ensure_ascii=False)

print(f"Merged total: {len(merged)} unique schemes")
```

---

## Step 5 — AI Structures Eligibility Rules

Raw eligibility text looks like this:

```
"The applicant must be a resident of India. Age between 18 and 60 years.
Annual family income should not exceed Rs. 2,00,000. Only for SC/ST/OBC categories."
```

You need it structured like this:

```json
[
  {"field": "age", "operator": "gte", "value": 18},
  {"field": "age", "operator": "lte", "value": 60},
  {"field": "annual_income", "operator": "lte", "value": 200000},
  {"field": "caste_category", "operator": "in", "value": ["SC", "ST", "OBC"]}
]
```

**How to do it:**

Take `merged_schemes.json`, pass each scheme's eligibility text to Claude/ChatGPT with this prompt:

```
Convert this eligibility text into a JSON array of criteria objects.
Each object must have: field, operator, value.
Allowed fields: age, gender, annual_income, state, caste_category, occupation, is_disabled, marital_status, land_owned.
Allowed operators: eq, neq, gte, lte, gt, lt, in, not_in.
Return only valid JSON. No explanation.

Eligibility text:
{eligibility_raw}
```

Save output as `schemes_seed.json`.

---

## Step 6 — Manual Spot Check

Pick 30 schemes randomly from `schemes_seed.json`.
For each one, verify against the official ministry website.

**Official sources to verify against:**
- Central schemes → https://www.pmindia.gov.in/en
- Agriculture → https://agricoop.gov.in
- Education → https://scholarship.gov.in
- Health → https://pmjay.gov.in
- Tamil Nadu → https://www.tn.gov.in/scheme/data_view/6

If something is wrong, fix it manually. This is the verification step.

---

## Step 7 — Seed PostgreSQL

```python
# scraper/seed.py

import asyncio
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.scheme import Scheme, EligibilityCriteria

DATABASE_URL = "postgresql+asyncpg://schemes_user:password@localhost:5432/schemes_db"

async def seed():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession)

    with open("scraper/schemes_seed.json") as f:
        schemes = json.load(f)

    async with async_session() as session:
        for s in schemes:
            scheme = Scheme(
                name=s["name"],
                description=s.get("description", ""),
                ministry=s.get("ministry", ""),
                benefit_amount=s.get("benefit_amount"),
                apply_link=s.get("apply_link", ""),
                is_active=True
            )
            session.add(scheme)
            await session.flush()

            for c in s.get("criteria", []):
                criterion = EligibilityCriteria(
                    scheme_id=scheme.id,
                    field=c["field"],
                    operator=c["operator"],
                    value=str(c["value"])
                )
                session.add(criterion)

        await session.commit()
        print(f"Seeded {len(schemes)} schemes successfully.")

asyncio.run(seed())
```

---

## Full Timeline

| Step | Task | Time |
|---|---|---|
| 1 | Download data.gov.in CSVs | 30 min |
| 2 | Run MyScheme ID collector | 2 min |
| 3 | Merge both sources | 10 min |
| 4 | Run detail scraper for missing schemes | 25 min |
| 5 | AI structures eligibility rules | 45 min |
| 6 | Manual spot check 30 schemes | 30 min |
| 7 | Run seed.py | 5 min |
| **Total** | | **~2.5 hours** |

---

## End of Day 3 Check

- [ ] `data.gov.in` CSVs downloaded and saved
- [ ] `myscheme_ids.json` has 4,000+ entries
- [ ] `merged_schemes.json` exists
- [ ] `myscheme_details.json` fills the gaps
- [ ] `schemes_seed.json` has structured eligibility criteria
- [ ] 30 schemes manually verified
- [ ] `SELECT count(*) FROM schemes;` returns 2,000+
- [ ] `SELECT count(*) FROM eligibility_criteria;` returns 5,000+

---

## Folder Structure After Day 3

```
scraper/
├── myscheme_id_collector.py
├── myscheme_detail_scraper.py
├── merger.py
├── seed.py
├── missing_slugs.json
└── raw_data/
    ├── data_gov/
    │   ├── central_schemes.csv
    │   ├── state_schemes.csv
    │   └── ...
    ├── myscheme_ids.json
    ├── myscheme_details.json
    ├── merged_schemes.json
    └── schemes_seed.json
```
