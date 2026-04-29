"""
Add 4 missing schemes (Kalaignar Magalir, CMCHIS, Innuyir Kaapom, Beti Bachao)
+ Fix wrong criteria found during manual verification:
  - Atal Pension: had caste_category=sc (WRONG — it's for all citizens 18-40)
  - PM SVANidhi: had gender=female (WRONG — it's for all street vendors)
  - PM Suraksha Bima: had caste=sc, student=true (WRONG — for anyone 18-70)
  - PM Matru Vandana: had no real criteria (needs gender=female, age>=19)
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://schemes_user:schemes_pass@localhost:5432/schemes_db"

MISSING_SCHEMES = [
    {
        "name": "Kalaignar Magalir Urimai Thogai Thittam",
        "description": "Tamil Nadu government scheme providing Rs.1,000 per month to women heads of eligible families. The amount is directly credited to the bank account of the woman head of the family.",
        "ministry": "Government of Tamil Nadu",
        "scheme_type": "state",
        "benefit_description": "Rs.1,000 per month to the woman head of the family",
        "apply_link": "https://www.tn.gov.in",
        "category": "women_and_child",
        "criteria": [
            {"field": "gender", "operator": "eq", "value": "female", "description": "For women heads of families"},
            {"field": "state", "operator": "eq", "value": "Tamil Nadu", "description": "Resident of Tamil Nadu"},
            {"field": "age", "operator": "gte", "value": "21", "description": "Minimum age 21 years"},
            {"field": "annual_income", "operator": "lte", "value": "250000", "description": "Annual family income up to Rs.2.5 lakh"},
        ]
    },
    {
        "name": "Chief Minister's Comprehensive Health Insurance Scheme (CMCHIS)",
        "description": "Tamil Nadu government health insurance scheme providing cashless treatment up to Rs.5 lakh per family per year at empaneled hospitals for families with annual income below Rs.1.2 lakh.",
        "ministry": "Government of Tamil Nadu",
        "scheme_type": "state",
        "benefit_description": "Cashless treatment up to Rs.5 lakh per family per year at empaneled hospitals",
        "apply_link": "https://www.cmchistn.com",
        "category": "health_wellness",
        "criteria": [
            {"field": "state", "operator": "eq", "value": "Tamil Nadu", "description": "Resident of Tamil Nadu"},
            {"field": "annual_income", "operator": "lte", "value": "120000", "description": "Annual family income up to Rs.1.2 lakh"},
        ]
    },
    {
        "name": "Innuyir Kaapom - Chief Minister's Road Safety Scheme",
        "description": "Tamil Nadu road accident victim relief scheme providing financial assistance of Rs.1 lakh for death, Rs.50,000 for grievous injury, and Rs.25,000 for minor injuries in road accidents.",
        "ministry": "Government of Tamil Nadu",
        "scheme_type": "state",
        "benefit_description": "Rs.1 lakh for death, Rs.50,000 for grievous injury, Rs.25,000 for minor injury in road accidents",
        "apply_link": "https://www.tn.gov.in",
        "category": "social_welfare_empowerment",
        "criteria": [
            {"field": "state", "operator": "eq", "value": "Tamil Nadu", "description": "Accident must occur in Tamil Nadu"},
        ]
    },
    {
        "name": "Beti Bachao Beti Padhao",
        "description": "Centrally sponsored scheme to address declining Child Sex Ratio and related issues of empowerment of women. Focuses on prevention of gender-biased sex selective elimination, ensuring survival and protection of girl child, and education of girl child.",
        "ministry": "Ministry of Women and Child Development",
        "scheme_type": "central",
        "benefit_description": "Awareness campaigns, multi-sectoral action for girl child protection and education",
        "apply_link": "https://wcd.nic.in/bbbp-schemes",
        "category": "women_and_child",
        "criteria": [
            {"field": "gender", "operator": "eq", "value": "female", "description": "For girl child"},
            {"field": "nationality", "operator": "eq", "value": "indian", "description": "Must be an Indian citizen"},
        ]
    },
]

# Criteria corrections based on manual verification against official sites
CRITERIA_FIXES = [
    {
        "scheme_name": "Atal Pension Yojana",
        "delete_wrong": True,  # remove wrong caste_category=sc
        "correct_criteria": [
            {"field": "age", "operator": "gte", "value": "18", "description": "Minimum age 18 years"},
            {"field": "age", "operator": "lte", "value": "40", "description": "Maximum age 40 years"},
            {"field": "nationality", "operator": "eq", "value": "indian", "description": "Must be an Indian citizen"},
        ]
    },
    {
        "scheme_name": "PM Street Vendor",  # partial match
        "delete_wrong": True,
        "correct_criteria": [
            {"field": "occupation", "operator": "eq", "value": "street_vendor", "description": "Must be a street vendor"},
            {"field": "age", "operator": "gte", "value": "18", "description": "Minimum age 18 years"},
            {"field": "nationality", "operator": "eq", "value": "indian", "description": "Must be an Indian citizen"},
        ]
    },
    {
        "scheme_name": "Pradhan Mantri Suraksha Bima Yojana",
        "delete_wrong": True,
        "correct_criteria": [
            {"field": "age", "operator": "gte", "value": "18", "description": "Minimum age 18 years"},
            {"field": "age", "operator": "lte", "value": "70", "description": "Maximum age 70 years"},
            {"field": "nationality", "operator": "eq", "value": "indian", "description": "Must have a bank account"},
        ]
    },
    {
        "scheme_name": "Pradhan Mantri Matru Vandana Yojana",
        "delete_wrong": True,
        "correct_criteria": [
            {"field": "gender", "operator": "eq", "value": "female", "description": "For pregnant women and lactating mothers"},
            {"field": "age", "operator": "gte", "value": "19", "description": "Minimum age 19 years"},
            {"field": "nationality", "operator": "eq", "value": "indian", "description": "Must be an Indian citizen"},
        ]
    },
    {
        "scheme_name": "Pradhan Mantri Jan Dhan Yojana",
        "delete_wrong": True,
        "correct_criteria": [
            {"field": "age", "operator": "gte", "value": "10", "description": "Minimum age 10 years"},
            {"field": "nationality", "operator": "eq", "value": "indian", "description": "Must be an Indian citizen"},
        ]
    },
]


async def main():
    engine = create_async_engine(DATABASE_URL)
    sf = sessionmaker(engine, class_=AsyncSession)

    # Step 1: Add missing schemes
    print("=" * 60)
    print("  ADDING 4 MISSING SCHEMES")
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
            """), {"name": s["name"], "desc": s["description"], "ministry": s["ministry"],
                   "stype": s["scheme_type"], "benefit": s["benefit_description"],
                   "link": s["apply_link"], "cat": s["category"]})
            sid = r.scalar()
            for c in s["criteria"]:
                await session.execute(text("""
                    INSERT INTO eligibility_criteria (scheme_id, field, operator, value, description)
                    VALUES (:sid, :field, :op, :val, :desc)
                """), {"sid": sid, "field": c["field"], "op": c["operator"], "val": c["value"], "desc": c["description"]})
            print(f"  ADDED: {s['name']} (id={sid}, {len(s['criteria'])} criteria)")
        await session.commit()

    # Step 2: Fix wrong criteria
    print(f"\n{'=' * 60}")
    print("  FIXING WRONG CRITERIA (MANUAL VERIFICATION)")
    print("=" * 60)
    async with sf() as session:
        for fix in CRITERIA_FIXES:
            r = await session.execute(text(
                "SELECT id, name FROM schemes WHERE name ILIKE :q LIMIT 1"
            ), {"q": f"%{fix['scheme_name']}%"})
            row = r.fetchone()
            if not row:
                print(f"  NOT FOUND: {fix['scheme_name']}")
                continue

            sid, name = row
            print(f"\n  Fixing: {name} (id={sid})")

            if fix["delete_wrong"]:
                r = await session.execute(text(
                    "SELECT field, operator, value FROM eligibility_criteria WHERE scheme_id = :sid"
                ), {"sid": sid})
                old = r.fetchall()
                print(f"    OLD: {', '.join([f'{r[0]}={r[2]}' for r in old])}")

                await session.execute(text("DELETE FROM eligibility_criteria WHERE scheme_id = :sid"), {"sid": sid})

            for c in fix["correct_criteria"]:
                await session.execute(text("""
                    INSERT INTO eligibility_criteria (scheme_id, field, operator, value, description)
                    VALUES (:sid, :field, :op, :val, :desc)
                """), {"sid": sid, "field": c["field"], "op": c["operator"], "val": c["value"], "desc": c["description"]})

            print(f"    NEW: {', '.join([f'{c['field']}={c['value']}' for c in fix['correct_criteria']])}")

        await session.commit()

    # Final verification
    print(f"\n{'=' * 60}")
    print("  FINAL VERIFICATION — ALL 20 PRIORITY SCHEMES")
    print("=" * 60)
    async with sf() as session:
        searches = [
            "PM Kisan Samman", "Ayushman Bharat", "PM Awas Yojana - Urban", "PM Awas Yojana - Gramin",
            "Sukanya Samriddhi", "PM Mudra", "Atal Pension", "PM SVANidhi", "Matru Vandana",
            "Garib Kalyan Ann", "Suraksha Bima", "Kalaignar Magalir", "Breakfast Scheme",
            "CMCHIS", "Moovalur Ramamirtham", "Innuyir Kaapom", "Kanyashree", "Stand-Up India",
            "Beti Bachao", "Jan Dhan",
        ]
        found = 0
        for s in searches:
            r = await session.execute(text("""
                SELECT s.name, s.apply_link,
                       (SELECT count(*) FROM eligibility_criteria WHERE scheme_id = s.id) as cnt
                FROM schemes s WHERE s.name ILIKE :q LIMIT 1
            """), {"q": f"%{s}%"})
            row = r.fetchone()
            if row:
                found += 1
                print(f"  OK  {row[0][:55]:<55} | {row[2]} criteria")
            else:
                print(f"  MISS {s}")

        print(f"\n  Result: {found}/20 priority schemes found")

        r = await session.execute(text("SELECT count(*) FROM schemes"))
        print(f"  Total schemes: {r.scalar()}")
        r = await session.execute(text("SELECT count(*) FROM eligibility_criteria"))
        print(f"  Total criteria: {r.scalar()}")

    await engine.dispose()

asyncio.run(main())
