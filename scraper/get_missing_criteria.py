"""
Step 1: Get slugs of all schemes that have ZERO eligibility criteria in the DB.
"""
import asyncio
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://schemes_user:schemes_pass@localhost:5432/schemes_db"

async def get_missing():
    engine = create_async_engine(DATABASE_URL)
    async_session_factory = sessionmaker(engine, class_=AsyncSession)

    async with async_session_factory() as session:
        # Schemes that have NO criteria
        result = await session.execute(text("""
            SELECT s.id, s.name, s.apply_link
            FROM schemes s
            LEFT JOIN eligibility_criteria ec ON ec.scheme_id = s.id
            WHERE ec.id IS NULL
            ORDER BY s.id
        """))
        missing = result.fetchall()

    slugs = []
    for row in missing:
        if row[2]:  # apply_link exists
            slug = row[2].rstrip("/").split("/")[-1]
            slugs.append({"db_id": row[0], "slug": slug, "name": row[1]})

    with open("scraper/missing_criteria_slugs.json", "w", encoding="utf-8") as f:
        json.dump(slugs, f, indent=2, ensure_ascii=False)

    await engine.dispose()
    print(f"Schemes missing criteria: {len(slugs)}")

asyncio.run(get_missing())
