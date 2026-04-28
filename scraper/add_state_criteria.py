"""Add at minimum a state criteria for state-level schemes that still have zero criteria."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://schemes_user:schemes_pass@localhost:5432/schemes_db"

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

async def main():
    engine = create_async_engine(DATABASE_URL)
    sf = sessionmaker(engine, class_=AsyncSession)

    async with sf() as session:
        result = await session.execute(text("""
            SELECT s.id, s.ministry
            FROM schemes s
            LEFT JOIN eligibility_criteria ec ON ec.scheme_id = s.id
            WHERE ec.id IS NULL AND s.ministry LIKE 'Government of%%'
        """))
        missing = result.fetchall()
        print(f"State schemes still missing any criteria: {len(missing)}")

        inserted = 0
        for row in missing:
            db_id, ministry = row
            state_name = ministry.replace("Government of", "").strip()
            if state_name in STATE_CODES:
                await session.execute(
                    text("""INSERT INTO eligibility_criteria (scheme_id, field, operator, value, description)
                            VALUES (:sid, 'state', 'eq', :val, :desc)"""),
                    {"sid": db_id, "val": state_name, "desc": f"Resident of {state_name}"}
                )
                inserted += 1

        await session.commit()

        r1 = await session.execute(text("SELECT count(*) FROM eligibility_criteria"))
        r2 = await session.execute(text("SELECT count(DISTINCT scheme_id) FROM eligibility_criteria"))
        r3 = await session.execute(text("""
            SELECT count(*) FROM schemes s
            LEFT JOIN eligibility_criteria ec ON ec.scheme_id = s.id
            WHERE ec.id IS NULL
        """))
        print(f"Added state criteria for {inserted} schemes")
        print(f"\nFinal counts:")
        print(f"  Total criteria: {r1.scalar()}")
        print(f"  Schemes with criteria: {r2.scalar()}")
        print(f"  Schemes still empty: {r3.scalar()}")

    await engine.dispose()

asyncio.run(main())
