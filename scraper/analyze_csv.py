"""Analyze Kaggle CSV and cross-reference with our DB."""
import csv
import sys
import json
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

sys.stdout.reconfigure(encoding='utf-8')

DATABASE_URL = "postgresql+asyncpg://schemes_user:schemes_pass@localhost:5432/schemes_db"

async def main():
    # Read CSV
    with open("updated_data.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    headers = list(rows[0].keys()) if rows else []
    print(f"COLUMNS: {headers}")
    print(f"TOTAL ROWS: {len(rows)}")

    # Data quality
    print("\n--- DATA QUALITY ---")
    for h in headers:
        if not h.strip():
            continue
        filled = sum(1 for r in rows if r.get(h, "").strip())
        pct = filled * 100 // len(rows)
        print(f"  {h}: {filled}/{len(rows)} ({pct}%)")

    # Sample
    print("\n--- SAMPLE ROW ---")
    r = rows[0]
    for h in headers:
        if not h.strip():
            continue
        val = r.get(h, "")[:200]
        print(f"  {h}: {val}")

    # Check eligibility quality
    has_elig = sum(1 for r in rows if len(r.get("eligibility", "")) > 50)
    has_details = sum(1 for r in rows if len(r.get("details", "")) > 50)
    has_benefits = sum(1 for r in rows if len(r.get("benefits", "")) > 50)
    print(f"\n--- CONTENT RICHNESS ---")
    print(f"  Eligibility text > 50 chars: {has_elig} ({has_elig*100//len(rows)}%)")
    print(f"  Details text > 50 chars: {has_details} ({has_details*100//len(rows)}%)")
    print(f"  Benefits text > 50 chars: {has_benefits} ({has_benefits*100//len(rows)}%)")

    # Cross-reference with DB
    engine = create_async_engine(DATABASE_URL)
    sf = sessionmaker(engine, class_=AsyncSession)

    csv_slugs = set(r.get("slug", "").strip() for r in rows if r.get("slug", "").strip())
    print(f"\n--- CROSS-REFERENCE WITH DB ---")
    print(f"  CSV unique slugs: {len(csv_slugs)}")

    async with sf() as session:
        # Get all DB slugs (extracted from apply_link)
        result = await session.execute(text("SELECT apply_link FROM schemes"))
        db_slugs = set()
        for row in result.fetchall():
            if row[0]:
                slug = row[0].rstrip("/").split("/")[-1]
                db_slugs.add(slug)

        in_both = csv_slugs & db_slugs
        only_csv = csv_slugs - db_slugs
        only_db = db_slugs - csv_slugs

        print(f"  DB slugs: {len(db_slugs)}")
        print(f"  In BOTH: {in_both and len(in_both)}")
        print(f"  Only in CSV (NEW): {len(only_csv)}")
        print(f"  Only in DB: {len(only_db)}")

        # Check how many CSV schemes have rich eligibility that we're missing
        # Find CSV rows where slug is in DB but our DB has no description
        can_enrich = 0
        for r in rows:
            slug = r.get("slug", "").strip()
            if slug in db_slugs and len(r.get("details", "")) > 50:
                can_enrich += 1
        print(f"\n  CSV rows that can ENRICH our DB (have details we're missing): {can_enrich}")

        # How many CSV rows have eligibility we can parse
        csv_with_elig = [r for r in rows if r.get("slug", "").strip() in db_slugs and len(r.get("eligibility", "")) > 50]
        print(f"  CSV rows with rich eligibility for existing DB schemes: {len(csv_with_elig)}")

    await engine.dispose()

asyncio.run(main())
