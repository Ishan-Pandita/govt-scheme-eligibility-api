"""
Step 3: Parse rescrape results into criteria and insert into DB.
Uses the same regex parser from convert_to_seed.py.
"""
import asyncio
import json
import re
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://schemes_user:schemes_pass@localhost:5432/schemes_db"
RESULTS_PATH = "scraper/raw_data/rescrape_results.json"


def extract_criteria(elig_text):
    """Parse eligibility text into structured criteria rules."""
    criteria = []
    text_lower = elig_text.lower()

    # Age criteria
    age_patterns = [
        (r'aged?\s+(?:between\s+)?(\d+)\s*(?:years?)?\s*(?:to|and|-)\s*(\d+)', 'range'),
        (r'(?:above|over|atleast|at least|minimum)\s+(\d+)\s*(?:years?)', 'min'),
        (r'(\d+)\s*(?:years?)\s+(?:and above|or above|or more|or older)', 'min'),
        (r'(?:below|under|upto|up to|not exceeding|maximum)\s+(\d+)\s*(?:years?)', 'max'),
        (r'(\d+)\s*(?:years?)\s+(?:or below|or under|or less|or younger)', 'max'),
    ]
    for pattern, ptype in age_patterns:
        m = re.search(pattern, text_lower)
        if m:
            if ptype == 'range':
                criteria.append({"field": "age", "operator": "gte", "value": m.group(1), "description": f"Minimum age {m.group(1)} years"})
                criteria.append({"field": "age", "operator": "lte", "value": m.group(2), "description": f"Maximum age {m.group(2)} years"})
            elif ptype == 'min':
                criteria.append({"field": "age", "operator": "gte", "value": m.group(1), "description": f"Minimum age {m.group(1)} years"})
            elif ptype == 'max':
                criteria.append({"field": "age", "operator": "lte", "value": m.group(1), "description": f"Maximum age {m.group(1)} years"})
            break

    # Income
    income_patterns = [
        (r'(?:annual|yearly)\s+(?:family\s+)?income\s+(?:should\s+)?(?:not\s+)?(?:exceed|be\s+less|be\s+below|up\s*to|below)\s+(?:rs\.?\s*)?(\d[\d,]*)', 'max'),
        (r'income\s+(?:not\s+)?(?:exceeding|more\s+than|above)\s+(?:rs\.?\s*)?(\d[\d,]*)', 'max'),
        (r'(?:rs\.?\s*)?(\d[\d,]*)\s+(?:per\s+annum|annual|yearly)', 'max'),
        (r'BPL', 'bpl'),
    ]
    for pattern, ptype in income_patterns:
        m = re.search(pattern, text_lower) if ptype != 'bpl' else re.search(pattern, elig_text)
        if m:
            if ptype == 'max':
                val = m.group(1).replace(",", "")
                criteria.append({"field": "annual_income", "operator": "lte", "value": val, "description": f"Annual income up to Rs.{val}"})
            elif ptype == 'bpl':
                criteria.append({"field": "is_bpl", "operator": "eq", "value": "true", "description": "Must be Below Poverty Line"})
            break

    # Gender
    if any(w in text_lower for w in ["women only", "female only", "girl", "women applicant", "must be a woman", "must be female"]):
        criteria.append({"field": "gender", "operator": "eq", "value": "female", "description": "For women/girls only"})
    elif any(w in text_lower for w in ["male only", "men only", "must be male", "must be a man"]):
        criteria.append({"field": "gender", "operator": "eq", "value": "male", "description": "For men only"})

    # Caste
    caste_map = {"scheduled caste": "sc", "scheduled tribe": "st", "SC": "sc", "ST": "st", "OBC": "obc", "EWS": "ews"}
    for keyword, val in caste_map.items():
        if keyword.lower() in text_lower or keyword in elig_text:
            criteria.append({"field": "caste_category", "operator": "eq", "value": val, "description": f"Must belong to {keyword} category"})
            break

    # Disability
    if any(w in text_lower for w in ["disability", "disabled", "divyang", "pwbd", "differently abled"]):
        criteria.append({"field": "is_disabled", "operator": "eq", "value": "true", "description": "For persons with disabilities"})

    # Student
    if any(w in text_lower for w in ["student", "studying", "enrolled", "pursuing education", "post-matric", "scholarship"]):
        criteria.append({"field": "is_student", "operator": "eq", "value": "true", "description": "Must be a student"})

    # Occupation
    if any(w in text_lower for w in ["farmer", "agricultur", "cultivat", "kisan"]):
        criteria.append({"field": "occupation", "operator": "eq", "value": "farmer", "description": "Must be a farmer"})
    elif any(w in text_lower for w in ["construction worker", "building worker"]):
        criteria.append({"field": "occupation", "operator": "eq", "value": "construction_worker", "description": "Must be a construction worker"})
    elif any(w in text_lower for w in ["street vendor", "hawker"]):
        criteria.append({"field": "occupation", "operator": "eq", "value": "street_vendor", "description": "Must be a street vendor"})
    elif any(w in text_lower for w in ["fisherman", "fisher", "fishing"]):
        criteria.append({"field": "occupation", "operator": "eq", "value": "fisherman", "description": "Must be a fisherman"})

    # Minority
    if any(w in text_lower for w in ["minority", "muslim", "christian", "sikh", "buddhist", "jain", "parsi"]):
        criteria.append({"field": "is_minority", "operator": "eq", "value": "true", "description": "Must belong to a minority community"})

    # Marital status
    if any(w in text_lower for w in ["widow", "widowed"]):
        criteria.append({"field": "marital_status", "operator": "eq", "value": "widow", "description": "Must be a widow"})
    elif "unmarried" in text_lower:
        criteria.append({"field": "marital_status", "operator": "eq", "value": "unmarried", "description": "Must be unmarried"})

    return criteria


async def insert_criteria():
    """Parse and insert new criteria for schemes that got eligibility text."""
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        results = json.load(f)

    # Only process schemes that have eligibility text
    with_elig = [r for r in results if r.get("eligibility_raw", "").strip()]
    print(f"Results with eligibility text: {len(with_elig)}")

    engine = create_async_engine(DATABASE_URL)
    async_session_factory = sessionmaker(engine, class_=AsyncSession)

    total_inserted = 0
    schemes_updated = 0

    async with async_session_factory() as session:
        for item in with_elig:
            criteria = extract_criteria(item["eligibility_raw"])
            if not criteria:
                continue

            db_id = item["db_id"]

            # Check if this scheme already has criteria (shouldn't, but safety)
            result = await session.execute(
                text("SELECT count(*) FROM eligibility_criteria WHERE scheme_id = :sid"),
                {"sid": db_id}
            )
            existing = result.scalar()
            if existing > 0:
                continue

            # Insert criteria
            for c in criteria:
                await session.execute(
                    text("""INSERT INTO eligibility_criteria (scheme_id, field, operator, value, description)
                            VALUES (:sid, :field, :op, :val, :desc)"""),
                    {"sid": db_id, "field": c["field"], "op": c["operator"], "val": c["value"], "desc": c.get("description", "")}
                )
                total_inserted += 1

            # Also update scheme description/benefit_description if empty
            if item.get("description", "").strip():
                await session.execute(
                    text("""UPDATE schemes SET description = :desc
                            WHERE id = :sid AND (description IS NULL OR description = '')"""),
                    {"sid": db_id, "desc": item["description"][:1000]}
                )
            if item.get("benefits_raw", "").strip():
                await session.execute(
                    text("""UPDATE schemes SET benefit_description = :ben
                            WHERE id = :sid AND (benefit_description IS NULL OR benefit_description = '')"""),
                    {"sid": db_id, "ben": item["benefits_raw"][:500]}
                )

            schemes_updated += 1

        await session.commit()

    await engine.dispose()

    # Final counts
    engine2 = create_async_engine(DATABASE_URL)
    async_session2 = sessionmaker(engine2, class_=AsyncSession)
    async with async_session2() as session:
        r1 = await session.execute(text("SELECT count(*) FROM eligibility_criteria"))
        r2 = await session.execute(text("SELECT count(DISTINCT scheme_id) FROM eligibility_criteria"))
        print(f"\nInserted {total_inserted} new criteria for {schemes_updated} schemes")
        print(f"Total criteria in DB: {r1.scalar()}")
        print(f"Schemes with criteria: {r2.scalar()}")
    await engine2.dispose()


if __name__ == "__main__":
    asyncio.run(insert_criteria())
