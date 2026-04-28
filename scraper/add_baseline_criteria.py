"""Add a 'scheme_type=central' criterion for central schemes still missing criteria."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://schemes_user:schemes_pass@localhost:5432/schemes_db"

async def main():
    engine = create_async_engine(DATABASE_URL)
    sf = sessionmaker(engine, class_=AsyncSession)

    async with sf() as session:
        # Central schemes with no criteria at all
        result = await session.execute(text("""
            SELECT s.id, s.name, s.category
            FROM schemes s
            LEFT JOIN eligibility_criteria ec ON ec.scheme_id = s.id
            WHERE ec.id IS NULL AND s.scheme_type = 'central'
        """))
        missing = result.fetchall()
        print(f"Central schemes with no criteria: {len(missing)}")

        inserted = 0
        for row in missing:
            db_id = row[0]
            # All Indian citizens can apply for central schemes
            await session.execute(
                text("""INSERT INTO eligibility_criteria (scheme_id, field, operator, value, description)
                        VALUES (:sid, 'nationality', 'eq', 'indian', 'Must be an Indian citizen')"""),
                {"sid": db_id}
            )
            inserted += 1

        # State schemes with no criteria
        result2 = await session.execute(text("""
            SELECT s.id, s.ministry
            FROM schemes s
            LEFT JOIN eligibility_criteria ec ON ec.scheme_id = s.id
            WHERE ec.id IS NULL AND s.scheme_type = 'state'
        """))
        missing_state = result2.fetchall()
        print(f"State schemes with no criteria: {len(missing_state)}")

        for row in missing_state:
            db_id = row[0]
            await session.execute(
                text("""INSERT INTO eligibility_criteria (scheme_id, field, operator, value, description)
                        VALUES (:sid, 'nationality', 'eq', 'indian', 'Must be an Indian citizen')"""),
                {"sid": db_id}
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
        print(f"\nAdded baseline criteria for {inserted} schemes")
        print(f"\nFINAL DB STATE:")
        print(f"  Total criteria rows: {r1.scalar()}")
        print(f"  Schemes with criteria: {r2.scalar()}")
        print(f"  Schemes without criteria: {r3.scalar()}")

    await engine.dispose()

asyncio.run(main())
