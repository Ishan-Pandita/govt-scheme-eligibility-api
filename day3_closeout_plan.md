# Day 3 — Close Out Plan (100% Free)

## Priority Order
1. Add 3 missing priority schemes manually
2. Fix Tier 3 (1,688 placeholder schemes) using non-headless Chrome
3. Fix income + state criteria
4. Manual verify 30 schemes
5. data.gov.in CSVs

---

## Task 1 — Add 3 Missing Priority Schemes Manually

These 3 schemes are too important to skip. Add them directly via a script.
No scraping needed — data taken from official government sites.

```python
# scraper/add_priority_schemes.py

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.scheme import Scheme, EligibilityCriteria, SchemeState
from sqlalchemy import select
from app.models.scheme import State

DATABASE_URL = "postgresql+asyncpg://schemes_user:password@localhost:5432/schemes_db"

PRIORITY_SCHEMES = [
    {
        "name": "PM Kisan Samman Nidhi",
        "description": "Income support of Rs.6000 per year to farmer families across the country in three equal installments of Rs.2000 each.",
        "ministry": "Ministry of Agriculture and Farmers Welfare",
        "benefit_amount": 6000.0,
        "apply_link": "https://pmkisan.gov.in",
        "is_central": True,
        "criteria": [
            {"field": "occupation", "operator": "eq", "value": "farmer"},
            {"field": "annual_income", "operator": "lte", "value": "200000"},
        ]
    },
    {
        "name": "PM Awas Yojana - Urban",
        "description": "Housing for All by providing financial assistance to urban poor for construction or enhancement of their houses.",
        "ministry": "Ministry of Housing and Urban Affairs",
        "benefit_amount": 250000.0,
        "apply_link": "https://pmaymis.gov.in",
        "is_central": True,
        "criteria": [
            {"field": "annual_income", "operator": "lte", "value": "1800000"},
            {"field": "occupation", "operator": "not_in", "value": "['government_employee']"},
        ]
    },
    {
        "name": "Sukanya Samriddhi Yojana",
        "description": "Small savings scheme for the girl child offering 8.2% annual interest rate with tax benefits under Section 80C.",
        "ministry": "Ministry of Finance",
        "benefit_amount": 0.0,
        "apply_link": "https://www.indiapost.gov.in/Financial/Pages/Content/Sukanya-Samridhi-Accounts.aspx",
        "is_central": True,
        "criteria": [
            {"field": "gender", "operator": "eq", "value": "female"},
            {"field": "age", "operator": "lte", "value": "10"},
        ]
    }
]

async def add_priority():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession)

    async with async_session() as session:
        for s in PRIORITY_SCHEMES:
            # Check if already exists
            result = await session.execute(
                select(Scheme).where(Scheme.name == s["name"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                print(f"Already exists: {s['name']}")
                continue

            scheme = Scheme(
                name=s["name"],
                description=s["description"],
                ministry=s["ministry"],
                benefit_amount=s["benefit_amount"],
                apply_link=s["apply_link"],
                is_active=True
            )
            session.add(scheme)
            await session.flush()

            for c in s["criteria"]:
                criterion = EligibilityCriteria(
                    scheme_id=scheme.id,
                    field=c["field"],
                    operator=c["operator"],
                    value=c["value"]
                )
                session.add(criterion)

            print(f"Added: {s['name']}")

        await session.commit()
    print("Priority schemes added.")

asyncio.run(add_priority())
```

**Run:**
```bash
python scraper/add_priority_schemes.py
```

---

## Task 2 — Fix Tier 3 (1,688 Placeholder Schemes) — Free

### Why They Are Empty
Headless Chrome renders pages differently than real Chrome. JavaScript-heavy pages like MyScheme detail pages don't fully render in headless mode — eligibility sections load late via JS and were missed.

### Fix — Non-Headless + Smarter Waiting (Free, No API Needed)

```python
# scraper/enrich_tier3.py

import asyncio
import json
import re
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, and_
from playwright.async_api import async_playwright
from app.models.scheme import Scheme, EligibilityCriteria

DATABASE_URL = "postgresql+asyncpg://schemes_user:password@localhost:5432/schemes_db"

# Simple regex-based parser — free, no API needed
def parse_eligibility_text(text: str, scheme_id: int) -> list:
    criteria = []
    text_lower = text.lower()

    # Age patterns
    age_match = re.search(r'(\d+)\s*(?:to|-)\s*(\d+)\s*years', text_lower)
    if age_match:
        criteria.append({"scheme_id": scheme_id, "field": "age", "operator": "gte", "value": age_match.group(1)})
        criteria.append({"scheme_id": scheme_id, "field": "age", "operator": "lte", "value": age_match.group(2)})

    min_age = re.search(r'(?:above|above the age of|minimum age)\s*(\d+)', text_lower)
    if min_age:
        criteria.append({"scheme_id": scheme_id, "field": "age", "operator": "gte", "value": min_age.group(1)})

    max_age = re.search(r'(?:below|below the age of|maximum age|not exceed)\s*(\d+)\s*years', text_lower)
    if max_age:
        criteria.append({"scheme_id": scheme_id, "field": "age", "operator": "lte", "value": max_age.group(1)})

    # Gender patterns
    if re.search(r'\b(women|woman|female|girl)\b', text_lower):
        criteria.append({"scheme_id": scheme_id, "field": "gender", "operator": "eq", "value": "female"})
    elif re.search(r'\b(men|man|male|boy)\b', text_lower):
        criteria.append({"scheme_id": scheme_id, "field": "gender", "operator": "eq", "value": "male"})

    # Income patterns
    income_match = re.search(r'(?:income|annual income).*?(?:rs\.?|inr|₹)\s*([\d,]+)', text_lower)
    if income_match:
        income = income_match.group(1).replace(",", "")
        criteria.append({"scheme_id": scheme_id, "field": "annual_income", "operator": "lte", "value": income})

    # Caste patterns
    castes = []
    if "sc" in text_lower or "scheduled caste" in text_lower: castes.append("SC")
    if "st" in text_lower or "scheduled tribe" in text_lower: castes.append("ST")
    if "obc" in text_lower or "other backward" in text_lower: castes.append("OBC")
    if castes:
        criteria.append({"scheme_id": scheme_id, "field": "caste_category", "operator": "in", "value": str(castes)})

    # Occupation patterns
    if re.search(r'\bfarmer|agriculture|kisan\b', text_lower):
        criteria.append({"scheme_id": scheme_id, "field": "occupation", "operator": "eq", "value": "farmer"})
    elif re.search(r'\bstudent|studying|school|college\b', text_lower):
        criteria.append({"scheme_id": scheme_id, "field": "occupation", "operator": "eq", "value": "student"})

    # Disability
    if re.search(r'\bdisab|differently abled|handicap\b', text_lower):
        criteria.append({"scheme_id": scheme_id, "field": "is_disabled", "operator": "eq", "value": "true"})

    return criteria


async def enrich():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession)

    # Get Tier 3 schemes — only nationality criterion
    async with async_session() as session:
        result = await session.execute(
            select(Scheme.id, Scheme.name, Scheme.apply_link)
        )
        all_schemes = result.fetchall()

        # Find schemes where only nationality criterion exists
        tier3 = []
        for scheme in all_schemes:
            crit_result = await session.execute(
                select(EligibilityCriteria).where(
                    EligibilityCriteria.scheme_id == scheme.id
                )
            )
            criteria = crit_result.scalars().all()
            if len(criteria) == 1 and criteria[0].field == "nationality":
                tier3.append({
                    "id": scheme.id,
                    "name": scheme.name,
                    "slug": scheme.apply_link.rstrip("/").split("/")[-1] if scheme.apply_link else ""
                })

    print(f"Tier 3 schemes to enrich: {len(tier3)}")

    enriched_count = 0

    async with async_playwright() as p:
        # Use headless=False — renders JS properly
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        async with async_session() as session:
            for i, scheme in enumerate(tier3):
                if not scheme["slug"]:
                    continue

                url = f"https://myscheme.gov.in/schemes/{scheme['slug']}"
                try:
                    await page.goto(url, timeout=20000)

                    # Wait for page to fully render
                    await page.wait_for_load_state("networkidle")
                    await page.wait_for_timeout(3000)

                    # Grab all visible text from page
                    full_text = await page.locator("body").inner_text()

                    # Parse criteria from full text
                    new_criteria = parse_eligibility_text(full_text, scheme["id"])

                    if new_criteria:
                        for c in new_criteria:
                            criterion = EligibilityCriteria(
                                scheme_id=c["scheme_id"],
                                field=c["field"],
                                operator=c["operator"],
                                value=c["value"]
                            )
                            session.add(criterion)

                        await session.commit()
                        enriched_count += 1
                        print(f"[{i+1}/{len(tier3)}] ✅ {scheme['name']} — {len(new_criteria)} criteria added")
                    else:
                        print(f"[{i+1}/{len(tier3)}] ⚠️  {scheme['name']} — no new criteria found")

                    await asyncio.sleep(1)

                except Exception as e:
                    print(f"[{i+1}/{len(tier3)}] ❌ {scheme['name']} — {e}")

        await browser.close()

    print(f"\nEnriched {enriched_count} Tier 3 schemes.")

asyncio.run(enrich())
```

**Run:**
```bash
python scraper/enrich_tier3.py
```

---

## Task 3 — Fix State Criteria (Currently 0 in eligibility_criteria)

State data is in `scheme_states` junction table but not in `eligibility_criteria`. Copy it over.

```python
# scraper/fix_state_criteria.py

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from app.models.scheme import EligibilityCriteria

DATABASE_URL = "postgresql+asyncpg://schemes_user:password@localhost:5432/schemes_db"

async def fix_states():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession)

    async with async_session() as session:
        # Get all scheme-state relationships
        result = await session.execute(
            text("""
                SELECT ss.scheme_id, s.name as state_name
                FROM scheme_states ss
                JOIN states s ON ss.state_id = s.id
            """)
        )
        rows = result.fetchall()

        # Group by scheme_id
        scheme_states = {}
        for row in rows:
            if row.scheme_id not in scheme_states:
                scheme_states[row.scheme_id] = []
            scheme_states[row.scheme_id].append(row.state_name)

        # Insert state criteria
        inserted = 0
        for scheme_id, states in scheme_states.items():
            if len(states) < 35:  # skip central schemes (all states)
                criterion = EligibilityCriteria(
                    scheme_id=scheme_id,
                    field="state",
                    operator="in",
                    value=str(states)
                )
                session.add(criterion)
                inserted += 1

        await session.commit()
        print(f"Inserted {inserted} state criteria rows.")

asyncio.run(fix_states())
```

**Run:**
```bash
python scraper/fix_state_criteria.py
```

---

## Task 4 — Manual Verification (30 Schemes, Free)

Open your Swagger UI at `http://localhost:8000/docs`.
Check these schemes one by one against official URLs.

| # | Scheme | Official URL | Check |
|---|---|---|---|
| 1 | PM Kisan Samman Nidhi | https://pmkisan.gov.in | |
| 2 | Ayushman Bharat PM-JAY | https://pmjay.gov.in | |
| 3 | PM Awas Yojana Urban | https://pmaymis.gov.in | |
| 4 | PM Awas Yojana Rural | https://pmayg.nic.in | |
| 5 | Sukanya Samriddhi Yojana | https://www.indiapost.gov.in | |
| 6 | PM Mudra Yojana | https://www.mudra.org.in | |
| 7 | Atal Pension Yojana | https://npscra.nsdl.co.in | |
| 8 | PM Matru Vandana Yojana | https://pmmvy.wcd.gov.in | |
| 9 | PM SVANidhi | https://pmsvanidhi.mohua.gov.in | |
| 10 | National Scholarship Portal | https://scholarships.gov.in | |
| 11 | Kalaignar Magalir Urimai | https://www.tn.gov.in | |
| 12 | CMCHIS Tamil Nadu | https://www.cmchistn.com | |
| 13 | PM Garib Kalyan Ann Yojana | https://dfpd.gov.in | |
| 14 | Beti Bachao Beti Padhao | https://wcd.nic.in | |
| 15 | PM Scholarship Scheme | https://scholarships.gov.in | |
| 16-30 | Pick from your DB | Cross check with ministry sites | |

For each one:
- Call `GET /schemes/{id}` in Swagger
- Compare eligibility criteria with official site
- If wrong → run direct SQL update

```sql
UPDATE eligibility_criteria
SET value = 'correct_value'
WHERE scheme_id = X AND field = 'field_name';
```

---

## Task 5 — data.gov.in (Free Official Download)

Go to these URLs. Click Download → CSV. Save in `scraper/raw_data/data_gov/`.

```
https://data.gov.in/search?title=scheme
https://data.gov.in/search?title=yojana
https://data.gov.in/search?title=pradhan+mantri
https://data.gov.in/search?title=welfare
https://data.gov.in/search?title=scholarship
https://data.gov.in/search?title=pension
```

Use downloaded CSVs to cross-verify your existing DB data. No code needed for this step.

---

## Run Order

```bash
# 1. Add 3 priority schemes
python scraper/add_priority_schemes.py

# 2. Fix state criteria
python scraper/fix_state_criteria.py

# 3. Enrich Tier 3 (run overnight if needed — opens browser)
python scraper/enrich_tier3.py

# 4. Manual verification (no code — use Swagger UI + official sites)

# 5. data.gov.in downloads (no code — manual download)
```

---

## Final Check After All Tasks

```sql
-- Schemes
SELECT count(*) FROM schemes;
-- Expected: 4,587 (4,584 + 3 priority)

-- Total criteria
SELECT count(*) FROM eligibility_criteria;
-- Expected: 8,000+

-- Schemes with real criteria (more than just nationality)
SELECT count(DISTINCT scheme_id)
FROM eligibility_criteria
WHERE field != 'nationality';
-- Expected: 3,000+

-- State criteria now populated
SELECT count(*) FROM eligibility_criteria WHERE field = 'state';
-- Expected: 1,000+

-- Income criteria improved
SELECT count(*) FROM eligibility_criteria WHERE field = 'annual_income';
-- Expected: 200+
```

---

## Cost Breakdown

| Task | Tool | Cost |
|---|---|---|
| Add priority schemes | Python script | Free |
| Enrich Tier 3 | Playwright non-headless + regex | Free |
| Fix state criteria | SQL migration script | Free |
| Manual verification | Swagger UI + browser | Free |
| data.gov.in download | Browser download | Free |
| **Total** | | **₹0** |
