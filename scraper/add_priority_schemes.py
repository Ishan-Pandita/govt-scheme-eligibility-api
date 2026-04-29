"""Add 3 missing priority schemes manually with verified data."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://schemes_user:schemes_pass@localhost:5432/schemes_db"

PRIORITY_SCHEMES = [
    {
        "name": "PM Kisan Samman Nidhi",
        "description": "Income support of Rs.6000 per year to farmer families across the country in three equal installments of Rs.2000 each, directly transferred to their bank accounts.",
        "ministry": "Ministry of Agriculture and Farmers Welfare",
        "scheme_type": "central",
        "benefit_description": "Rs.6000 per year in 3 installments of Rs.2000 each",
        "apply_link": "https://pmkisan.gov.in",
        "category": "agriculture",
        "criteria": [
            {"field": "occupation", "operator": "eq", "value": "farmer", "description": "Must be a farmer"},
            {"field": "annual_income", "operator": "lte", "value": "200000", "description": "Annual family income up to Rs.2 lakh"},
            {"field": "nationality", "operator": "eq", "value": "indian", "description": "Must be an Indian citizen"},
        ]
    },
    {
        "name": "PM Awas Yojana - Urban",
        "description": "Housing for All mission providing financial assistance to urban poor belonging to EWS/LIG/MIG categories for construction, enhancement or purchase of houses.",
        "ministry": "Ministry of Housing and Urban Affairs",
        "scheme_type": "central",
        "benefit_description": "Subsidy up to Rs.2.67 lakh for EWS/LIG, Rs.2.35 lakh for MIG-I, Rs.2.30 lakh for MIG-II",
        "apply_link": "https://pmaymis.gov.in",
        "category": "housing_shelter",
        "criteria": [
            {"field": "annual_income", "operator": "lte", "value": "1800000", "description": "Annual household income up to Rs.18 lakh"},
            {"field": "nationality", "operator": "eq", "value": "indian", "description": "Must be an Indian citizen"},
        ]
    },
    {
        "name": "Sukanya Samriddhi Yojana",
        "description": "Government-backed small savings scheme for girl child offering 8.2% annual interest rate. Account can be opened for a girl child below 10 years with tax benefits under Section 80C.",
        "ministry": "Ministry of Finance",
        "scheme_type": "central",
        "benefit_description": "8.2% annual interest rate, tax benefits under Section 80C, maturity after 21 years",
        "apply_link": "https://www.indiapost.gov.in/Financial/Pages/Content/Sukanya-Samridhi-Accounts.aspx",
        "category": "banking_financial_insurance",
        "criteria": [
            {"field": "gender", "operator": "eq", "value": "female", "description": "For girl child only"},
            {"field": "age", "operator": "lte", "value": "10", "description": "Girl child must be below 10 years"},
            {"field": "nationality", "operator": "eq", "value": "indian", "description": "Must be an Indian citizen"},
        ]
    },
]

async def main():
    engine = create_async_engine(DATABASE_URL)
    sf = sessionmaker(engine, class_=AsyncSession)

    async with sf() as session:
        for s in PRIORITY_SCHEMES:
            # Check if exists
            r = await session.execute(text("SELECT id FROM schemes WHERE name = :n"), {"n": s["name"]})
            if r.scalar():
                print(f"Already exists: {s['name']}")
                continue

            # Insert scheme
            r = await session.execute(text("""
                INSERT INTO schemes (name, description, ministry, scheme_type, benefit_description, apply_link, is_active, category)
                VALUES (:name, :desc, :ministry, :stype, :benefit, :link, true, :cat)
                RETURNING id
            """), {
                "name": s["name"], "desc": s["description"], "ministry": s["ministry"],
                "stype": s["scheme_type"], "benefit": s["benefit_description"],
                "link": s["apply_link"], "cat": s["category"],
            })
            scheme_id = r.scalar()

            # Insert criteria
            for c in s["criteria"]:
                await session.execute(text("""
                    INSERT INTO eligibility_criteria (scheme_id, field, operator, value, description)
                    VALUES (:sid, :field, :op, :val, :desc)
                """), {"sid": scheme_id, "field": c["field"], "op": c["operator"], "val": c["value"], "desc": c["description"]})

            print(f"Added: {s['name']} (id={scheme_id}, {len(s['criteria'])} criteria)")

        await session.commit()

    await engine.dispose()
    print("Done!")

asyncio.run(main())
