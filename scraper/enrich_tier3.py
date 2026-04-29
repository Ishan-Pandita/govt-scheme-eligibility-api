"""
Enrich Tier 3 schemes (nationality-only) using non-headless Chrome.
Scrapes detail pages with visible browser for better JS rendering.
Uses 2 tabs for parallel scraping.
"""
import asyncio
import json
import re
import os
from playwright.async_api import async_playwright
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://schemes_user:schemes_pass@localhost:5432/schemes_db"
CHECKPOINT = "scraper/raw_data/tier3_checkpoint.json"


def parse_eligibility(text_content):
    """Extract criteria from page text."""
    criteria = []
    t = text_content.lower()

    # Age
    m = re.search(r'(\d+)\s*(?:years?)?\s*(?:to|and|-)\s*(\d+)\s*years?', t)
    if m:
        criteria.append({"field": "age", "operator": "gte", "value": m.group(1), "description": f"Min age {m.group(1)}"})
        criteria.append({"field": "age", "operator": "lte", "value": m.group(2), "description": f"Max age {m.group(2)}"})
    else:
        m2 = re.search(r'(?:above|at least|minimum)\s+(\d+)\s*years?', t)
        if m2:
            criteria.append({"field": "age", "operator": "gte", "value": m2.group(1), "description": f"Min age {m2.group(1)}"})
        m3 = re.search(r'(?:below|under|up to|maximum)\s+(\d+)\s*years?', t)
        if m3:
            criteria.append({"field": "age", "operator": "lte", "value": m3.group(1), "description": f"Max age {m3.group(1)}"})

    # Income
    m = re.search(r'(?:income|annual income).*?(?:rs\.?|inr)\s*([\d,]+)', t)
    if m:
        val = m.group(1).replace(",", "")
        criteria.append({"field": "annual_income", "operator": "lte", "value": val, "description": f"Income up to Rs.{val}"})

    # Gender
    if any(w in t for w in ["women only", "female only", "girl child", "must be a woman", "must be female"]):
        criteria.append({"field": "gender", "operator": "eq", "value": "female", "description": "For women/girls"})

    # Caste
    if "scheduled caste" in t or " sc " in t:
        criteria.append({"field": "caste_category", "operator": "eq", "value": "sc", "description": "SC category"})
    elif "scheduled tribe" in t:
        criteria.append({"field": "caste_category", "operator": "eq", "value": "st", "description": "ST category"})
    elif " obc " in t:
        criteria.append({"field": "caste_category", "operator": "eq", "value": "obc", "description": "OBC category"})

    # Disability
    if any(w in t for w in ["disability", "disabled", "divyang"]):
        criteria.append({"field": "is_disabled", "operator": "eq", "value": "true", "description": "For PwD"})

    # Student
    if any(w in t for w in ["student", "studying", "enrolled", "scholarship"]):
        criteria.append({"field": "is_student", "operator": "eq", "value": "true", "description": "Must be a student"})

    # Farmer
    if any(w in t for w in ["farmer", "kisan", "agriculture"]):
        criteria.append({"field": "occupation", "operator": "eq", "value": "farmer", "description": "Must be a farmer"})

    # BPL
    if "bpl" in t or "below poverty" in t:
        criteria.append({"field": "is_bpl", "operator": "eq", "value": "true", "description": "BPL family"})

    return criteria


async def main():
    engine = create_async_engine(DATABASE_URL)
    sf = sessionmaker(engine, class_=AsyncSession)

    # Get Tier 3 scheme slugs
    async with sf() as session:
        result = await session.execute(text("""
            SELECT s.id, s.name, s.apply_link
            FROM schemes s
            JOIN eligibility_criteria ec ON ec.scheme_id = s.id
            WHERE ec.field = 'nationality'
            AND NOT EXISTS (
                SELECT 1 FROM eligibility_criteria ec2
                WHERE ec2.scheme_id = s.id AND ec2.field != 'nationality' AND ec2.field != 'state'
            )
        """))
        tier3 = []
        for row in result.fetchall():
            slug = row[2].rstrip("/").split("/")[-1] if row[2] else ""
            if slug:
                tier3.append({"id": row[0], "name": row[1], "slug": slug})

    print(f"Tier 3 schemes to enrich: {len(tier3)}")

    # Load checkpoint
    done_slugs = set()
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT, "r") as f:
            done_slugs = set(json.load(f))
    remaining = [s for s in tier3 if s["slug"] not in done_slugs]
    print(f"Already done: {len(done_slugs)}, Remaining: {len(remaining)}")

    enriched = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, channel="chrome")
        pages = [await browser.new_page() for _ in range(2)]

        async def scrape_one(page, item):
            url = f"https://www.myscheme.gov.in/schemes/{item['slug']}"
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(5000)
                body = await page.query_selector("body")
                return await body.inner_text() if body else ""
            except:
                return ""

        async with sf() as session:
            for i in range(0, len(remaining), 2):
                batch = remaining[i:i+2]
                tasks = [scrape_one(pages[j % 2], item) for j, item in enumerate(batch)]
                texts = await asyncio.gather(*tasks)

                for item, page_text in zip(batch, texts):
                    done_slugs.add(item["slug"])
                    if not page_text.strip():
                        continue

                    criteria = parse_eligibility(page_text)
                    if criteria:
                        for c in criteria:
                            await session.execute(text("""
                                INSERT INTO eligibility_criteria (scheme_id, field, operator, value, description)
                                VALUES (:sid, :field, :op, :val, :desc)
                            """), {"sid": item["id"], "field": c["field"], "op": c["operator"],
                                   "val": c["value"], "desc": c.get("description", "")})
                        enriched += 1

                if (i + 2) % 100 == 0 or i + 2 >= len(remaining):
                    await session.commit()
                    with open(CHECKPOINT, "w") as f:
                        json.dump(list(done_slugs), f)
                    print(f"  [{len(done_slugs)}/{len(tier3)}] enriched: {enriched}")

                await asyncio.sleep(0.5)

            await session.commit()

        await browser.close()

    # Save final checkpoint
    with open(CHECKPOINT, "w") as f:
        json.dump(list(done_slugs), f)

    # Final stats
    async with sf() as session:
        r1 = await session.execute(text("SELECT count(*) FROM eligibility_criteria"))
        r2 = await session.execute(text("SELECT count(DISTINCT scheme_id) FROM eligibility_criteria WHERE field != 'nationality'"))
        print(f"\nEnriched {enriched} Tier 3 schemes")
        print(f"Total criteria: {r1.scalar()}")
        print(f"Schemes with real criteria: {r2.scalar()}")

    await engine.dispose()

asyncio.run(main())
