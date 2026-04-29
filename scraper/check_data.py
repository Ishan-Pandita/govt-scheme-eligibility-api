"""Full Day 3 audit — check everything against requirements."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://schemes_user:schemes_pass@localhost:5432/schemes_db"

async def audit():
    engine = create_async_engine(DATABASE_URL)
    sf = sessionmaker(engine, class_=AsyncSession)

    async with sf() as session:
        queries = {
            "Total schemes": "SELECT count(*) FROM schemes",
            "Total criteria": "SELECT count(*) FROM eligibility_criteria",
            "Schemes WITH criteria": "SELECT count(DISTINCT scheme_id) FROM eligibility_criteria",
            "Schemes WITHOUT criteria": """SELECT count(*) FROM schemes s LEFT JOIN eligibility_criteria ec ON ec.scheme_id = s.id WHERE ec.id IS NULL""",
            "Total states": "SELECT count(*) FROM states",
            "Total users": "SELECT count(*) FROM users",
            "Central schemes": "SELECT count(*) FROM schemes WHERE scheme_type = 'central'",
            "State schemes": "SELECT count(*) FROM schemes WHERE scheme_type = 'state'",
            "Schemes with description": "SELECT count(*) FROM schemes WHERE description IS NOT NULL AND description != ''",
            "Schemes with apply_link": "SELECT count(*) FROM schemes WHERE apply_link IS NOT NULL AND apply_link != ''",
            "Schemes with benefit_description": "SELECT count(*) FROM schemes WHERE benefit_description IS NOT NULL AND benefit_description != ''",
            "Criteria field: age": "SELECT count(*) FROM eligibility_criteria WHERE field = 'age'",
            "Criteria field: gender": "SELECT count(*) FROM eligibility_criteria WHERE field = 'gender'",
            "Criteria field: caste_category": "SELECT count(*) FROM eligibility_criteria WHERE field = 'caste_category'",
            "Criteria field: is_disabled": "SELECT count(*) FROM eligibility_criteria WHERE field = 'is_disabled'",
            "Criteria field: is_student": "SELECT count(*) FROM eligibility_criteria WHERE field = 'is_student'",
            "Criteria field: occupation": "SELECT count(*) FROM eligibility_criteria WHERE field = 'occupation'",
            "Criteria field: annual_income": "SELECT count(*) FROM eligibility_criteria WHERE field = 'annual_income'",
            "Criteria field: state": "SELECT count(*) FROM eligibility_criteria WHERE field = 'state'",
            "Criteria field: nationality": "SELECT count(*) FROM eligibility_criteria WHERE field = 'nationality'",
            "Criteria field: is_bpl": "SELECT count(*) FROM eligibility_criteria WHERE field = 'is_bpl'",
            "Criteria field: marital_status": "SELECT count(*) FROM eligibility_criteria WHERE field = 'marital_status'",
            "Criteria field: is_minority": "SELECT count(*) FROM eligibility_criteria WHERE field = 'is_minority'",
        }

        # Priority schemes check
        priority = [
            "PM Kisan", "Ayushman Bharat", "PM Awas Yojana", "Sukanya Samriddhi",
            "PM Mudra", "Atal Pension", "PM SVANidhi", "Kanyashree", "Stand-Up India",
            "Pradhan Mantri Suraksha Bima"
        ]

        print("=" * 60)
        print("  DAY 3 FULL AUDIT")
        print("=" * 60)

        print("\n--- Database Counts ---")
        for label, query in queries.items():
            r = await session.execute(text(query))
            val = r.scalar()
            print(f"  {label}: {val}")

        print("\n--- Priority Schemes in DB ---")
        for name in priority:
            r = await session.execute(text(
                f"SELECT s.id, s.name, (SELECT count(*) FROM eligibility_criteria WHERE scheme_id = s.id) as crit_count FROM schemes s WHERE s.name ILIKE :q LIMIT 1"
            ), {"q": f"%{name}%"})
            row = r.fetchone()
            if row:
                print(f"  FOUND: {row[1][:60]} (criteria: {row[2]})")
            else:
                print(f"  MISSING: {name}")

        # Category distribution
        print("\n--- Category Distribution (top 10) ---")
        r = await session.execute(text(
            "SELECT category, count(*) as cnt FROM schemes WHERE category IS NOT NULL GROUP BY category ORDER BY cnt DESC LIMIT 10"
        ))
        for row in r.fetchall():
            print(f"  {row[0]}: {row[1]}")

        # State distribution (top 10)
        print("\n--- State Scheme Distribution (top 10 by ministry) ---")
        r = await session.execute(text(
            "SELECT ministry, count(*) as cnt FROM schemes WHERE scheme_type = 'state' GROUP BY ministry ORDER BY cnt DESC LIMIT 10"
        ))
        for row in r.fetchall():
            print(f"  {row[0]}: {row[1]}")

    await engine.dispose()

asyncio.run(audit())
