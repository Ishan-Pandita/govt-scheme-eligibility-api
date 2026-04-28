"""
Generate eligibility criteria from scheme name, category, and ministry
for schemes that still have zero criteria after scraping.

Uses name-based heuristics — if a scheme name contains "scholarship", "pension",
"women", "disability", "farmer" etc., we know the target demographic.
"""
import asyncio
import json
import re
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://schemes_user:schemes_pass@localhost:5432/schemes_db"

# Category-based default criteria
CATEGORY_CRITERIA = {
    "education_learning": [{"field": "is_student", "operator": "eq", "value": "true", "description": "Must be a student or in education"}],
    "agriculture_rural_environment": [{"field": "occupation", "operator": "eq", "value": "farmer", "description": "Must be a farmer/agricultural worker"}],
    "health_wellness": [],
    "social_welfare_empowerment": [],
    "business_entrepreneurship": [],
    "sports_culture": [],
    "housing_shelter": [],
    "utility_sanitation": [],
    "travel_tourism": [],
    "transport_infrastructure": [],
    "skill_employment": [],
    "science_it_communication": [],
    "women_child": [{"field": "gender", "operator": "eq", "value": "female", "description": "For women/girls"}],
    "banking_financial_insurance": [],
    "public_safety_law_justice": [],
}

# Name-based keyword → criteria mapping
NAME_KEYWORDS = [
    # Gender
    (["women", "mahila", "girl", "stree", "nari", "daughter", "mother", "maternity", "pregnant", "widow", "ammaiyar"],
     {"field": "gender", "operator": "eq", "value": "female", "description": "For women/girls"}),
    # Age - senior
    (["old age", "senior citizen", "elderly", "vridha", "vayo", "pension scheme"],
     {"field": "age", "operator": "gte", "value": "60", "description": "Minimum age 60 years"}),
    # Age - youth
    (["youth", "yuva"],
     {"field": "age", "operator": "lte", "value": "35", "description": "Maximum age 35 years"}),
    # Disability
    (["disability", "disabled", "divyang", "divyangjan", "handicapped", "blind", "deaf", "impaired"],
     {"field": "is_disabled", "operator": "eq", "value": "true", "description": "For persons with disabilities"}),
    # Caste - SC
    (["scheduled caste", " sc ", "sc/st", "dalit"],
     {"field": "caste_category", "operator": "eq", "value": "sc", "description": "For SC category"}),
    # Caste - ST
    (["scheduled tribe", "tribal", "adivasi"],
     {"field": "caste_category", "operator": "eq", "value": "st", "description": "For ST category"}),
    # Caste - OBC
    ([" obc ", "other backward"],
     {"field": "caste_category", "operator": "eq", "value": "obc", "description": "For OBC category"}),
    # Caste - Minority
    (["minority", "madrasa", "waqf"],
     {"field": "is_minority", "operator": "eq", "value": "true", "description": "For minority communities"}),
    # Occupation - farmer
    (["farmer", "kisan", "krishi", "agriculture", "crop", "paddy", "dairy", "fisherm", "fisher", "poultry", "livestock", "horticulture", "sericulture"],
     {"field": "occupation", "operator": "eq", "value": "farmer", "description": "Must be a farmer/agricultural worker"}),
    # Occupation - construction worker
    (["construction worker", "building worker", "bocw", "labour welfare"],
     {"field": "occupation", "operator": "eq", "value": "construction_worker", "description": "Must be a construction worker"}),
    # Student
    (["scholarship", "student", "school", "college", "university", "pre-matric", "post-matric", "merit", "education grant", "fellowship", "phd", "research"],
     {"field": "is_student", "operator": "eq", "value": "true", "description": "Must be a student"}),
    # BPL
    (["bpl", "below poverty", "garib", "poor"],
     {"field": "is_bpl", "operator": "eq", "value": "true", "description": "Must be Below Poverty Line"}),
    # Widow
    (["widow", "vidhwa"],
     {"field": "marital_status", "operator": "eq", "value": "widow", "description": "Must be a widow"}),
    # Transgender
    (["transgender", "kinnar"],
     {"field": "gender", "operator": "eq", "value": "transgender", "description": "For transgender persons"}),
    # Ex-servicemen
    (["ex-servicem", "veteran", "defence personnel", "army", "navy", "air force"],
     {"field": "occupation", "operator": "eq", "value": "ex_servicemen", "description": "Must be an ex-serviceman"}),
]

STATE_CODES = {
    "Gujarat": "GJ", "Maharashtra": "MH", "Tamil Nadu": "TN", "Karnataka": "KA",
    "Kerala": "KL", "Rajasthan": "RJ", "Bihar": "BR", "Uttar Pradesh": "UP",
    "Madhya Pradesh": "MP", "Odisha": "OD", "West Bengal": "WB", "Assam": "AS",
    "Punjab": "PB", "Haryana": "HR", "Jharkhand": "JH", "Chhattisgarh": "CG",
    "Uttarakhand": "UK", "Himachal Pradesh": "HP", "Goa": "GA", "Sikkim": "SK",
    "Tripura": "TR", "Meghalaya": "ML", "Mizoram": "MZ", "Nagaland": "NL",
    "Manipur": "MN", "Arunachal Pradesh": "AR", "Delhi": "DL", "Puducherry": "PY",
    "Jammu and Kashmir": "JK", "Ladakh": "LA", "Chandigarh": "CH",
    "Andhra Pradesh": "AP", "Telangana": "TS",
}


def generate_criteria_from_name(name, category, ministry):
    """Generate criteria from scheme name and category signals."""
    criteria = []
    name_lower = name.lower()
    seen_fields = set()

    # Name-based keywords
    for keywords, criterion in NAME_KEYWORDS:
        for kw in keywords:
            if kw.lower() in name_lower:
                if criterion["field"] not in seen_fields:
                    criteria.append(criterion)
                    seen_fields.add(criterion["field"])
                break

    # Category-based
    if category:
        cat_key = category.lower().replace(" ", "_")
        for k, v in CATEGORY_CRITERIA.items():
            if k in cat_key or cat_key in k:
                for c in v:
                    if c["field"] not in seen_fields:
                        criteria.append(c)
                        seen_fields.add(c["field"])
                break

    # State from ministry
    if "Government of" in ministry:
        state_name = ministry.replace("Government of", "").strip()
        if state_name in STATE_CODES and "state" not in seen_fields:
            criteria.append({"field": "state", "operator": "eq", "value": state_name,
                             "description": f"Resident of {state_name}"})

    return criteria


async def main():
    engine = create_async_engine(DATABASE_URL)
    async_session_factory = sessionmaker(engine, class_=AsyncSession)

    async with async_session_factory() as session:
        # Get schemes with NO criteria
        result = await session.execute(text("""
            SELECT s.id, s.name, s.category, s.ministry
            FROM schemes s
            LEFT JOIN eligibility_criteria ec ON ec.scheme_id = s.id
            WHERE ec.id IS NULL
        """))
        missing = result.fetchall()
        print(f"Schemes still missing criteria: {len(missing)}")

        total_inserted = 0
        schemes_updated = 0

        for row in missing:
            db_id, name, category, ministry = row
            criteria = generate_criteria_from_name(name or "", category or "", ministry or "")

            if criteria:
                for c in criteria:
                    await session.execute(
                        text("""INSERT INTO eligibility_criteria (scheme_id, field, operator, value, description)
                                VALUES (:sid, :field, :op, :val, :desc)"""),
                        {"sid": db_id, "field": c["field"], "op": c["operator"],
                         "val": c["value"], "desc": c.get("description", "")}
                    )
                    total_inserted += 1
                schemes_updated += 1

        await session.commit()

        # Final counts
        r1 = await session.execute(text("SELECT count(*) FROM eligibility_criteria"))
        r2 = await session.execute(text("SELECT count(DISTINCT scheme_id) FROM eligibility_criteria"))
        print(f"\nInserted {total_inserted} criteria for {schemes_updated} schemes")
        print(f"Total criteria in DB: {r1.scalar()}")
        print(f"Schemes with criteria: {r2.scalar()}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
