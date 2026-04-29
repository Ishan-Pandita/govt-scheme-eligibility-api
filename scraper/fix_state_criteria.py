"""Copy state data from scheme_states junction table into eligibility_criteria."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://schemes_user:schemes_pass@localhost:5432/schemes_db"

async def main():
    engine = create_async_engine(DATABASE_URL)
    sf = sessionmaker(engine, class_=AsyncSession)

    async with sf() as session:
        # Get all scheme-state relationships
        result = await session.execute(text("""
            SELECT ss.scheme_id, s.name as state_name
            FROM scheme_states ss
            JOIN states s ON ss.state_id = s.id
        """))
        rows = result.fetchall()

        # Group by scheme_id
        scheme_states = {}
        for row in rows:
            scheme_states.setdefault(row[0], []).append(row[1])

        print(f"Schemes with state links: {len(scheme_states)}")

        # Check which ones already have state criteria
        existing = await session.execute(text(
            "SELECT DISTINCT scheme_id FROM eligibility_criteria WHERE field = 'state'"
        ))
        already_done = set(r[0] for r in existing.fetchall())

        inserted = 0
        for scheme_id, states in scheme_states.items():
            if scheme_id in already_done:
                continue
            if len(states) >= 35:  # All states = central, skip
                continue

            if len(states) == 1:
                await session.execute(text("""
                    INSERT INTO eligibility_criteria (scheme_id, field, operator, value, description)
                    VALUES (:sid, 'state', 'eq', :val, :desc)
                """), {"sid": scheme_id, "val": states[0], "desc": f"Resident of {states[0]}"})
            else:
                await session.execute(text("""
                    INSERT INTO eligibility_criteria (scheme_id, field, operator, value, description)
                    VALUES (:sid, 'state', 'in', :val, :desc)
                """), {"sid": scheme_id, "val": str(states), "desc": f"Resident of {', '.join(states)}"})
            inserted += 1

        await session.commit()

        # Final count
        r = await session.execute(text("SELECT count(*) FROM eligibility_criteria WHERE field = 'state'"))
        print(f"Inserted {inserted} state criteria")
        print(f"Total state criteria now: {r.scalar()}")

    await engine.dispose()

asyncio.run(main())
