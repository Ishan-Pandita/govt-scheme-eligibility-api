"""
Use Kaggle CSV to enrich our DB:
1. Update descriptions/benefits for 3,199 existing schemes
2. Add 201 new schemes
3. Parse eligibility text into criteria for schemes that only have nationality/state
"""
import csv
import re
import sys
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

sys.stdout.reconfigure(encoding='utf-8')

DATABASE_URL = "postgresql+asyncpg://schemes_user:schemes_pass@localhost:5432/schemes_db"


def extract_criteria(elig_text):
    """Parse eligibility text into structured criteria."""
    criteria = []
    t = elig_text.lower()

    # Age
    age_patterns = [
        (r'(\d+)\s*(?:years?)?\s*(?:to|and|-)\s*(\d+)\s*years?', 'range'),
        (r'(?:above|over|atleast|at least|minimum|min)\s+(\d+)\s*years?', 'min'),
        (r'(\d+)\s*years?\s+(?:and above|or above|or more|or older)', 'min'),
        (r'(?:below|under|upto|up to|maximum|max|not exceed)\s+(\d+)\s*years?', 'max'),
        (r'(\d+)\s*years?\s+(?:or below|or under|or less|or younger)', 'max'),
        (r'age\s*(?:of|:)?\s*(\d+)\s*(?:to|-)\s*(\d+)', 'range'),
    ]
    for pat, ptype in age_patterns:
        m = re.search(pat, t)
        if m:
            if ptype == 'range':
                criteria.append({"field": "age", "operator": "gte", "value": m.group(1), "description": f"Min age {m.group(1)}"})
                criteria.append({"field": "age", "operator": "lte", "value": m.group(2), "description": f"Max age {m.group(2)}"})
            elif ptype == 'min':
                criteria.append({"field": "age", "operator": "gte", "value": m.group(1), "description": f"Min age {m.group(1)}"})
            elif ptype == 'max':
                criteria.append({"field": "age", "operator": "lte", "value": m.group(1), "description": f"Max age {m.group(1)}"})
            break

    # Income
    income_pats = [
        r'(?:annual|yearly)\s+(?:family\s+)?income\s+.*?(?:rs\.?|inr|₹)\s*([\d,]+)',
        r'income\s+.*?(?:not\s+)?(?:exceed|less|below|up\s*to)\s+.*?(?:rs\.?|inr|₹)\s*([\d,]+)',
        r'(?:rs\.?|inr|₹)\s*([\d,]+)\s*(?:per\s+annum|annual|yearly)',
    ]
    for pat in income_pats:
        m = re.search(pat, t)
        if m:
            val = m.group(1).replace(",", "")
            if val and int(val) > 1000:  # sanity check
                criteria.append({"field": "annual_income", "operator": "lte", "value": val, "description": f"Income up to Rs.{val}"})
            break

    # Gender
    if any(w in t for w in ["women only", "female only", "girl child", "must be a woman", "must be female", "should be a woman"]):
        criteria.append({"field": "gender", "operator": "eq", "value": "female", "description": "For women/girls"})

    # Caste
    castes_found = []
    if "scheduled caste" in t or re.search(r'\bsc\b', t): castes_found.append("sc")
    if "scheduled tribe" in t or re.search(r'\bst\b', t): castes_found.append("st")
    if re.search(r'\bobc\b', t) or "other backward" in t: castes_found.append("obc")
    if re.search(r'\bews\b', t) or "economically weaker" in t: castes_found.append("ews")
    if castes_found:
        if len(castes_found) == 1:
            criteria.append({"field": "caste_category", "operator": "eq", "value": castes_found[0], "description": f"For {castes_found[0].upper()} category"})
        else:
            criteria.append({"field": "caste_category", "operator": "in", "value": str(castes_found), "description": f"For {'/'.join(c.upper() for c in castes_found)}"})

    # Disability
    if any(w in t for w in ["disability", "disabled", "divyang", "differently abled", "pwd"]):
        criteria.append({"field": "is_disabled", "operator": "eq", "value": "true", "description": "For PwD"})

    # Student
    if any(w in t for w in ["student", "studying", "enrolled", "scholarship", "pursuing"]):
        criteria.append({"field": "is_student", "operator": "eq", "value": "true", "description": "Must be a student"})

    # Occupation
    if any(w in t for w in ["farmer", "kisan", "agriculture", "cultivat"]):
        criteria.append({"field": "occupation", "operator": "eq", "value": "farmer", "description": "Must be a farmer"})
    elif any(w in t for w in ["construction worker", "building worker"]):
        criteria.append({"field": "occupation", "operator": "eq", "value": "construction_worker", "description": "Construction worker"})
    elif any(w in t for w in ["fisherm", "fisher"]):
        criteria.append({"field": "occupation", "operator": "eq", "value": "fisherman", "description": "Must be a fisherman"})

    # BPL
    if "bpl" in t or "below poverty" in t:
        criteria.append({"field": "is_bpl", "operator": "eq", "value": "true", "description": "BPL family"})

    # Minority
    if any(w in t for w in ["minority community", "minority"]):
        criteria.append({"field": "is_minority", "operator": "eq", "value": "true", "description": "Minority community"})

    # Widow
    if "widow" in t:
        criteria.append({"field": "marital_status", "operator": "eq", "value": "widow", "description": "Must be a widow"})
    elif "unmarried" in t:
        criteria.append({"field": "marital_status", "operator": "eq", "value": "unmarried", "description": "Must be unmarried"})

    return criteria


async def main():
    # Read CSV
    with open("updated_data.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        csv_rows = list(reader)

    csv_by_slug = {r["slug"].strip(): r for r in csv_rows if r.get("slug", "").strip()}

    engine = create_async_engine(DATABASE_URL)
    sf = sessionmaker(engine, class_=AsyncSession)

    # Step 1: Enrich existing schemes with descriptions/benefits
    print("=" * 60)
    print("  STEP 1: ENRICHING DESCRIPTIONS")
    print("=" * 60)

    async with sf() as session:
        result = await session.execute(text(
            "SELECT id, apply_link, description, benefit_description FROM schemes"
        ))
        db_schemes = result.fetchall()

        enriched = 0
        for row in db_schemes:
            sid, link, desc, benefit = row
            if not link:
                continue
            slug = link.rstrip("/").split("/")[-1]
            csv_row = csv_by_slug.get(slug)
            if not csv_row:
                continue

            updates = {}
            if (not desc or not desc.strip()) and csv_row.get("details", "").strip():
                updates["desc"] = csv_row["details"][:1500]
            if (not benefit or not benefit.strip()) and csv_row.get("benefits", "").strip():
                updates["benefit"] = csv_row["benefits"][:1000]

            if updates:
                if "desc" in updates and "benefit" in updates:
                    await session.execute(text(
                        "UPDATE schemes SET description = :d, benefit_description = :b WHERE id = :sid"
                    ), {"d": updates["desc"], "b": updates["benefit"], "sid": sid})
                elif "desc" in updates:
                    await session.execute(text(
                        "UPDATE schemes SET description = :d WHERE id = :sid"
                    ), {"d": updates["desc"], "sid": sid})
                elif "benefit" in updates:
                    await session.execute(text(
                        "UPDATE schemes SET benefit_description = :b WHERE id = :sid"
                    ), {"b": updates["benefit"], "sid": sid})
                enriched += 1

        await session.commit()
        print(f"  Enriched {enriched} schemes with descriptions/benefits")

    # Step 2: Parse eligibility and add criteria for schemes missing real criteria
    print(f"\n{'=' * 60}")
    print("  STEP 2: PARSING ELIGIBILITY INTO CRITERIA")
    print("=" * 60)

    async with sf() as session:
        # Get schemes that only have nationality/state criteria
        result = await session.execute(text("""
            SELECT s.id, s.apply_link FROM schemes s
            WHERE NOT EXISTS (
                SELECT 1 FROM eligibility_criteria ec
                WHERE ec.scheme_id = s.id
                AND ec.field NOT IN ('nationality', 'state')
            )
        """))
        weak_schemes = result.fetchall()
        print(f"  Schemes with only nationality/state criteria: {len(weak_schemes)}")

        criteria_added = 0
        schemes_improved = 0

        for row in weak_schemes:
            sid, link = row
            if not link:
                continue
            slug = link.rstrip("/").split("/")[-1]
            csv_row = csv_by_slug.get(slug)
            if not csv_row or not csv_row.get("eligibility", "").strip():
                continue

            criteria = extract_criteria(csv_row["eligibility"])
            if criteria:
                for c in criteria:
                    await session.execute(text("""
                        INSERT INTO eligibility_criteria (scheme_id, field, operator, value, description)
                        VALUES (:sid, :field, :op, :val, :desc)
                    """), {"sid": sid, "field": c["field"], "op": c["operator"],
                           "val": c["value"], "desc": c.get("description", "")})
                    criteria_added += 1
                schemes_improved += 1

        await session.commit()
        print(f"  Added {criteria_added} criteria to {schemes_improved} schemes")

    # Step 3: Add 201 new schemes from CSV
    print(f"\n{'=' * 60}")
    print("  STEP 3: ADDING NEW SCHEMES FROM CSV")
    print("=" * 60)

    async with sf() as session:
        result = await session.execute(text("SELECT apply_link FROM schemes"))
        db_slugs = set()
        for row in result.fetchall():
            if row[0]:
                db_slugs.add(row[0].rstrip("/").split("/")[-1])

        added = 0
        for slug, csv_row in csv_by_slug.items():
            if slug in db_slugs:
                continue

            stype = "central" if csv_row.get("level", "").lower() == "central" else "state"
            cat_raw = csv_row.get("schemeCategory", "").split(",")[0].strip().lower().replace(" & ", "_").replace(" ", "_")

            r = await session.execute(text("""
                INSERT INTO schemes (name, description, ministry, scheme_type, benefit_description, apply_link, is_active, category)
                VALUES (:name, :desc, '', :stype, :benefit, :link, true, :cat)
                RETURNING id
            """), {
                "name": csv_row["scheme_name"][:500],
                "desc": csv_row.get("details", "")[:1500],
                "stype": stype,
                "benefit": csv_row.get("benefits", "")[:1000],
                "link": f"https://www.myscheme.gov.in/schemes/{slug}",
                "cat": cat_raw[:50] if cat_raw else None,
            })
            new_id = r.scalar()

            # Parse and add criteria
            criteria = extract_criteria(csv_row.get("eligibility", ""))
            if not criteria:
                criteria = [{"field": "nationality", "operator": "eq", "value": "indian", "description": "Indian citizen"}]
            for c in criteria:
                await session.execute(text("""
                    INSERT INTO eligibility_criteria (scheme_id, field, operator, value, description)
                    VALUES (:sid, :field, :op, :val, :desc)
                """), {"sid": new_id, "field": c["field"], "op": c["operator"],
                       "val": c["value"], "desc": c.get("description", "")})

            added += 1

        await session.commit()
        print(f"  Added {added} new schemes")

    # Final counts
    print(f"\n{'=' * 60}")
    print("  FINAL STATE")
    print("=" * 60)
    async with sf() as session:
        for label, q in [
            ("Total schemes", "SELECT count(*) FROM schemes"),
            ("Total criteria", "SELECT count(*) FROM eligibility_criteria"),
            ("With description", "SELECT count(*) FROM schemes WHERE description IS NOT NULL AND description != ''"),
            ("With benefit_description", "SELECT count(*) FROM schemes WHERE benefit_description IS NOT NULL AND benefit_description != ''"),
            ("Deep criteria (not nationality/state)", "SELECT count(*) FROM eligibility_criteria WHERE field NOT IN ('nationality', 'state')"),
            ("Schemes with deep criteria", "SELECT count(DISTINCT scheme_id) FROM eligibility_criteria WHERE field NOT IN ('nationality', 'state')"),
            ("Income criteria", "SELECT count(*) FROM eligibility_criteria WHERE field = 'annual_income'"),
            ("Age criteria", "SELECT count(*) FROM eligibility_criteria WHERE field = 'age'"),
        ]:
            r = await session.execute(text(q))
            print(f"  {label}: {r.scalar()}")

    await engine.dispose()

asyncio.run(main())
