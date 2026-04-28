import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def fix():
    e = create_async_engine("postgresql+asyncpg://schemes_user:schemes_pass@localhost:5432/schemes_db")
    async with e.begin() as c:
        await c.execute(text("ALTER TABLE schemes ALTER COLUMN name TYPE VARCHAR(500)"))
        print("Column resized to VARCHAR(500)")
    await e.dispose()

asyncio.run(fix())
