# Day 3 — Fix Plan

## Current Status
- 4,584 schemes in DB ✅
- Only 617 (13%) have eligibility criteria ❌
- Target: 5,000+ criteria rows
- Root cause: detail pages needed 5+ sec to render but scraper only waited 3 sec

---

## Fix 1 — Re-run Detail Scraper (Only for Schemes Missing Criteria)

Do not re-scrape all 4,584 schemes. Only scrape the 3,967 schemes that have zero criteria.

### Step 1 — Get list of schemes with no criteria

```python
# scraper/get_missing_criteria_schemes.py

import asyncio
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import sessionmaker
from app.models.scheme import Scheme, EligibilityCriteria

DATABASE_URL = "postgresql+asyncpg://schemes_user:password@localhost:5432/schemes_db"

async def get_missing():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession)

    async with async_session() as session:
        # Get scheme IDs that have NO criteria
        subquery = select(EligibilityCriteria.scheme_id).distinct()
        result = await session.execute(
            select(Scheme.id, Scheme.name, Scheme.apply_link)
            .where(Scheme.id.not_in(subquery))
        )
        missing = result.fetchall()

    slugs = []
    for row in missing:
        # Extract slug from apply_link
        # apply_link format: https://myscheme.gov.in/schemes/pm-kisan
        if row.apply_link:
            slug = row.apply_link.rstrip("/").split("/")[-1]
            slugs.append({"db_id": row.id, "slug": slug, "name": row.name})

    with open("scraper/missing_criteria_slugs.json", "w") as f:
        json.dump(slugs, f, indent=2)

    print(f"Schemes missing criteria: {len(slugs)}")

asyncio.run(get_missing())
```

---

### Step 2 — Re-scrape Detail Pages with Longer Wait Time

Key fix: increase wait from 3 sec → 6 sec and add explicit wait for eligibility section to appear.

```python
# scraper/rescrape_eligibility.py

import asyncio
import json
from playwright.async_api import async_playwright

async def rescrape(slugs: list):
    results = []
    failed = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for i, item in enumerate(slugs):
            slug = item["slug"]
            db_id = item["db_id"]
            url = f"https://myscheme.gov.in/schemes/{slug}"

            try:
                await page.goto(url, timeout=20000)

                # Wait explicitly for eligibility section — not just a fixed timeout
                try:
                    await page.wait_for_selector(
                        ".eligibility, [class*='eligib'], [id*='eligib']",
                        timeout=8000
                    )
                except:
                    pass  # section might have a different selector — still try to extract

                await page.wait_for_timeout(2000)  # extra buffer after selector found

                # Try multiple possible selectors for eligibility
                eligibility = ""
                for selector in [
                    ".eligibility",
                    "[class*='eligib']",
                    "[id*='eligib']",
                    "section:has-text('Eligibility')",
                    "div:has-text('Who can apply')"
                ]:
                    try:
                        text = await page.locator(selector).first.inner_text()
                        if text and len(text) > 20:
                            eligibility = text
                            break
                    except:
                        continue

                # Try multiple possible selectors for benefits
                benefits = ""
                for selector in [
                    ".benefits",
                    "[class*='benefit']",
                    "section:has-text('Benefits')",
                    "div:has-text('What you get')"
                ]:
                    try:
                        text = await page.locator(selector).first.inner_text()
                        if text and len(text) > 10:
                            benefits = text
                            break
                    except:
                        continue

                if eligibility:
                    results.append({
                        "db_id": db_id,
                        "slug": slug,
                        "eligibility_raw": eligibility,
                        "benefits_raw": benefits
                    })
                    print(f"[{i+1}/{len(slugs)}] ✅ {slug}")
                else:
                    failed.append(item)
                    print(f"[{i+1}/{len(slugs)}] ❌ {slug} — no eligibility found")

                await asyncio.sleep(1.5)

            except Exception as e:
                failed.append(item)
                print(f"[{i+1}/{len(slugs)}] ❌ {slug} — {e}")

        await browser.close()

    with open("scraper/raw_data/rescrape_results.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    with open("scraper/raw_data/rescrape_failed.json", "w") as f:
        json.dump(failed, f, indent=2)

    print(f"\nDone. Success: {len(results)} | Failed: {len(failed)}")

with open("scraper/missing_criteria_slugs.json") as f:
    slugs = json.load(f)

asyncio.run(rescrape(slugs))
```

---

### Step 3 — Structure Raw Eligibility Text into Criteria Using AI

For each scheme in `rescrape_results.json`, send eligibility text to Claude API and get structured criteria back.

```python
# scraper/structure_eligibility.py

import asyncio
import json
import httpx

CLAUDE_API_KEY = "your-api-key"

PROMPT = """
Convert this eligibility text into a JSON array of criteria objects.
Each object must have exactly these fields: field, operator, value.

Allowed fields only:
- age
- gender (values: male, female, other)
- annual_income (in rupees, number)
- state (state name string or list)
- caste_category (values: General, OBC, SC, ST)
- occupation (values: farmer, student, self_employed, unemployed, government_employee, private_employee)
- is_disabled (values: true, false)
- marital_status (values: married, unmarried, widow, divorced)
- land_owned (in acres, number)

Allowed operators only:
- eq (equals)
- neq (not equals)
- gte (greater than or equal)
- lte (less than or equal)
- gt (greater than)
- lt (less than)
- in (value is in list)
- not_in (value not in list)

Return only a valid JSON array. No explanation. No markdown. No extra text.
If eligibility is unclear or cannot be structured, return an empty array [].

Eligibility text:
{text}
"""

async def structure_all():
    with open("scraper/raw_data/rescrape_results.json") as f:
        schemes = json.load(f)

    structured = []

    async with httpx.AsyncClient(timeout=30) as client:
        for i, scheme in enumerate(schemes):
            text = scheme.get("eligibility_raw", "")
            if not text:
                continue

            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": CLAUDE_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1000,
                    "messages": [
                        {"role": "user", "content": PROMPT.format(text=text)}
                    ]
                }
            )

            try:
                content = response.json()["content"][0]["text"].strip()
                criteria = json.loads(content)
                structured.append({
                    "db_id": scheme["db_id"],
                    "slug": scheme["slug"],
                    "criteria": criteria
                })
                print(f"[{i+1}/{len(schemes)}] ✅ {scheme['slug']} — {len(criteria)} criteria")
            except Exception as e:
                print(f"[{i+1}/{len(schemes)}] ❌ {scheme['slug']} — parse failed: {e}")

            await asyncio.sleep(0.3)  # rate limit buffer

    with open("scraper/raw_data/structured_criteria.json", "w") as f:
        json.dump(structured, f, indent=2)

    print(f"\nDone. Structured {len(structured)} schemes.")

asyncio.run(structure_all())
```

---

### Step 4 — Insert New Criteria into DB

```python
# scraper/insert_criteria.py

import asyncio
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.scheme import EligibilityCriteria

DATABASE_URL = "postgresql+asyncpg://schemes_user:password@localhost:5432/schemes_db"

async def insert():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession)

    with open("scraper/raw_data/structured_criteria.json") as f:
        schemes = json.load(f)

    total_inserted = 0

    async with async_session() as session:
        for scheme in schemes:
            for c in scheme.get("criteria", []):
                criterion = EligibilityCriteria(
                    scheme_id=scheme["db_id"],
                    field=c["field"],
                    operator=c["operator"],
                    value=str(c["value"])
                )
                session.add(criterion)
                total_inserted += 1

        await session.commit()

    print(f"Inserted {total_inserted} new criteria rows.")

asyncio.run(insert())
```

---

## Fix 2 — Manual Verification (30 Schemes)

Verify these priority schemes manually. Check official ministry site vs what's in your DB.

| Scheme | Official URL |
|---|---|
| PM Kisan Samman Nidhi | https://pmkisan.gov.in |
| Ayushman Bharat PM-JAY | https://pmjay.gov.in |
| PM Awas Yojana Urban | https://pmaymis.gov.in |
| PM Awas Yojana Rural | https://pmayg.nic.in |
| Sukanya Samriddhi Yojana | https://www.indiapost.gov.in |
| PM Mudra Yojana | https://www.mudra.org.in |
| Atal Pension Yojana | https://npscra.nsdl.co.in |
| PM Matru Vandana Yojana | https://pmmvy.wcd.gov.in |
| PM SVANidhi | https://pmsvanidhi.mohua.gov.in |
| National Scholarship Portal | https://scholarships.gov.in |

For each one:
- Open the official URL
- Check eligibility criteria on that site
- Open your Swagger UI → GET /schemes/{id}
- Compare — if wrong, update directly in DB

---

## Fix 3 — data.gov.in Download

Go to each URL below. Download every dataset as CSV. Save in `scraper/raw_data/data_gov/`.

```
https://data.gov.in/search?title=scheme
https://data.gov.in/search?title=yojana
https://data.gov.in/search?title=pradhan+mantri
https://data.gov.in/search?title=welfare
https://data.gov.in/search?title=scholarship
https://data.gov.in/search?title=pension
```

These are government uploaded official files. Use them to cross-verify your DB data.

---

## Run Order

```
Step 1: python scraper/get_missing_criteria_schemes.py
           ↓
Step 2: python scraper/rescrape_eligibility.py
           ↓
Step 3: python scraper/structure_eligibility.py
           ↓
Step 4: python scraper/insert_criteria.py
           ↓
Step 5: Manual verification of 30 priority schemes
           ↓
Step 6: Download data.gov.in CSVs
```

---

## End of Day 3 Final Check

```sql
SELECT count(*) FROM schemes;
-- Target: 4,584 ✅ (already done)

SELECT count(*) FROM eligibility_criteria;
-- Target: 5,000+ (currently 1,212 — fix above solves this)

SELECT count(DISTINCT scheme_id) FROM eligibility_criteria;
-- Target: 2,000+ schemes with at least 1 criterion
```

---

## Expected Result After Fix

| Metric | Before Fix | After Fix |
|---|---|---|
| Total schemes | 4,584 | 4,584 |
| Schemes with criteria | 617 (13%) | 2,500+ (55%+) |
| Total criteria rows | 1,212 | 6,000+ |
| Manually verified | 0 | 30 |
