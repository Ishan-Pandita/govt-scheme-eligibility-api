"""
Task 1: Add PM Mudra Yojana + PM Awas Yojana Rural
Task 2: Check all 15 priority + TN schemes in DB
Task 3: Verify criteria for found schemes against official data
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://schemes_user:schemes_pass@localhost:5432/schemes_db"

MISSING_SCHEMES = [
    {
        "name": "PM Mudra Yojana",
        "description": "Pradhan Mantri MUDRA Yojana provides loans up to Rs.10 lakh to non-corporate, non-farm small/micro enterprises. Three products: Shishu (up to Rs.50,000), Kishore (Rs.50,001 to Rs.5 lakh), Tarun (Rs.5,00,001 to Rs.10 lakh).",
        "ministry": "Ministry of Finance",
        "scheme_type": "central",
        "benefit_description": "Shishu: up to Rs.50,000 | Kishore: Rs.50,001 to Rs.5 lakh | Tarun: Rs.5,00,001 to Rs.10 lakh. No collateral required.",
        "apply_link": "https://www.mudra.org.in",
        "category": "business_entrepreneurship",
        "criteria": [
            {"field": "nationality", "operator": "eq", "value": "indian", "description": "Must be an Indian citizen"},
            {"field": "occupation", "operator": "in", "value": "['self_employed', 'small_business']", "description": "Must be a non-farm small/micro enterprise owner"},
            {"field": "age", "operator": "gte", "value": "18", "description": "Minimum age 18 years"},
        ]
    },
    {
        "name": "PM Awas Yojana - Gramin (Rural)",
        "description": "Provides financial assistance for construction of pucca houses to eligible rural households who are houseless or living in kutcha/dilapidated houses. Assistance of Rs.1.20 lakh in plains and Rs.1.30 lakh in hilly/difficult areas.",
        "ministry": "Ministry of Rural Development",
        "scheme_type": "central",
        "benefit_description": "Rs.1.20 lakh in plains, Rs.1.30 lakh in hilly/difficult areas, plus 90 days of MGNREGA wages",
        "apply_link": "https://pmayg.nic.in",
        "category": "housing_shelter",
        "criteria": [
            {"field": "nationality", "operator": "eq", "value": "indian", "description": "Must be an Indian citizen"},
            {"field": "annual_income", "operator": "lte", "value": "300000", "description": "Must be from economically weaker section"},
            {"field": "is_bpl", "operator": "eq", "value": "true", "description": "Priority to BPL families"},
        ]
    },
    {
        "name": "Pradhan Mantri Matru Vandana Yojana",
        "description": "Cash incentive of Rs.5,000 in three installments to pregnant women and lactating mothers for the first living child to partially compensate wage loss during pregnancy and childbirth.",
        "ministry": "Ministry of Women and Child Development",
        "scheme_type": "central",
        "benefit_description": "Rs.5,000 in 3 installments during pregnancy and after delivery",
        "apply_link": "https://pmmvy.wcd.gov.in",
        "category": "women_and_child",
        "criteria": [
            {"field": "gender", "operator": "eq", "value": "female", "description": "For pregnant women and lactating mothers"},
            {"field": "age", "operator": "gte", "value": "19", "description": "Minimum age 19 years"},
            {"field": "nationality", "operator": "eq", "value": "indian", "description": "Must be an Indian citizen"},
        ]
    },
    {
        "name": "PM Garib Kalyan Ann Yojana",
        "description": "Free food grains (5 kg per person per month) to about 81.35 crore beneficiaries covered under the National Food Security Act. Rice, wheat, and coarse grains distributed through Fair Price Shops.",
        "ministry": "Ministry of Consumer Affairs, Food and Public Distribution",
        "scheme_type": "central",
        "benefit_description": "5 kg free food grains per person per month through Fair Price Shops",
        "apply_link": "https://dfpd.gov.in",
        "category": "social_welfare_empowerment",
        "criteria": [
            {"field": "is_bpl", "operator": "eq", "value": "true", "description": "Must hold ration card (BPL/AAY/PHH)"},
            {"field": "nationality", "operator": "eq", "value": "indian", "description": "Must be an Indian citizen"},
        ]
    },
]

# Priority + TN schemes to check
PRIORITY_SEARCHES = [
    "PM Kisan",
    "Ayushman Bharat",
    "PM Awas Yojana",
    "Sukanya Samriddhi",
    "PM Mudra",
    "Atal Pension",
    "PM SVANidhi",
    "National Scholarship",
    "Matru Vandana",
    "Garib Kalyan",
    "Suraksha Bima",
    "Kalaignar Magalir",
    "Breakfast Scheme",
    "CMCHIS",
    "Moovalur Ramamirtham",
    "Innuyir Kaapom",
    "Kanyashree",
    "Stand-Up India",
    "Beti Bachao",
    "Jan Dhan",
]


async def main():
    engine = create_async_engine(DATABASE_URL)
    sf = sessionmaker(engine, class_=AsyncSession)

    # Step 1: Add missing schemes
    print("=" * 60)
    print("  ADDING MISSING SCHEMES")
    print("=" * 60)

    async with sf() as session:
        for s in MISSING_SCHEMES:
            r = await session.execute(text("SELECT id FROM schemes WHERE name = :n"), {"n": s["name"]})
            if r.scalar():
                print(f"  Already exists: {s['name']}")
                continue

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

            for c in s["criteria"]:
                await session.execute(text("""
                    INSERT INTO eligibility_criteria (scheme_id, field, operator, value, description)
                    VALUES (:sid, :field, :op, :val, :desc)
                """), {"sid": scheme_id, "field": c["field"], "op": c["operator"],
                       "val": c["value"], "desc": c["description"]})

            print(f"  ADDED: {s['name']} (id={scheme_id})")

        await session.commit()

    # Step 2: Check all priority + TN schemes
    print(f"\n{'=' * 60}")
    print("  PRIORITY SCHEME VERIFICATION")
    print("=" * 60)

    async with sf() as session:
        for search in PRIORITY_SEARCHES:
            r = await session.execute(text("""
                SELECT s.id, s.name, s.description, s.apply_link,
                       (SELECT count(*) FROM eligibility_criteria WHERE scheme_id = s.id) as crit_count,
                       (SELECT string_agg(field || '=' || value, ', ')
                        FROM eligibility_criteria WHERE scheme_id = s.id AND field != 'nationality' AND field != 'state') as criteria_summary
                FROM schemes s
                WHERE s.name ILIKE :q
                LIMIT 1
            """), {"q": f"%{search}%"})
            row = r.fetchone()

            if row:
                name = row[1][:60]
                has_desc = "YES" if row[2] and row[2].strip() else "NO"
                print(f"\n  FOUND: {name}")
                print(f"    ID: {row[0]} | Criteria: {row[4]} | Has description: {has_desc}")
                print(f"    Link: {row[3]}")
                if row[5]:
                    print(f"    Rules: {row[5][:120]}")
            else:
                print(f"\n  MISSING: {search}")

    # Step 3: Final counts
    print(f"\n{'=' * 60}")
    print("  FINAL DATABASE STATE")
    print("=" * 60)
    async with sf() as session:
        queries = [
            ("Total schemes", "SELECT count(*) FROM schemes"),
            ("Total criteria", "SELECT count(*) FROM eligibility_criteria"),
            ("Central schemes", "SELECT count(*) FROM schemes WHERE scheme_type = 'central'"),
            ("State schemes", "SELECT count(*) FROM schemes WHERE scheme_type = 'state'"),
            ("With description", "SELECT count(*) FROM schemes WHERE description IS NOT NULL AND description != ''"),
        ]
        for label, q in queries:
            r = await session.execute(text(q))
            print(f"  {label}: {r.scalar()}")

    await engine.dispose()

asyncio.run(main())
