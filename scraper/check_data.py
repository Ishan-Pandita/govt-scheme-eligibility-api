"""Complete data inventory — what exactly is in the database right now."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://schemes_user:schemes_pass@localhost:5432/schemes_db"

async def audit():
    engine = create_async_engine(DATABASE_URL)
    sf = sessionmaker(engine, class_=AsyncSession)

    async with sf() as session:
        print("=" * 70)
        print("  COMPLETE DATA INVENTORY")
        print("=" * 70)

        # ── TABLE: schemes ──
        r = await session.execute(text("SELECT count(*) FROM schemes"))
        print(f"\n1. SCHEMES TABLE: {r.scalar()} rows")

        r = await session.execute(text("SELECT count(*) FROM schemes WHERE scheme_type = 'central'"))
        central = r.scalar()
        r = await session.execute(text("SELECT count(*) FROM schemes WHERE scheme_type = 'state'"))
        state = r.scalar()
        print(f"   Central: {central} | State: {state}")

        r = await session.execute(text("SELECT count(*) FROM schemes WHERE description != '' AND description IS NOT NULL"))
        print(f"   With description: {r.scalar()}")
        r = await session.execute(text("SELECT count(*) FROM schemes WHERE benefit_description != '' AND benefit_description IS NOT NULL"))
        print(f"   With benefit_description: {r.scalar()}")
        r = await session.execute(text("SELECT count(*) FROM schemes WHERE apply_link != '' AND apply_link IS NOT NULL"))
        print(f"   With apply_link: {r.scalar()}")
        r = await session.execute(text("SELECT count(*) FROM schemes WHERE category IS NOT NULL"))
        print(f"   With category: {r.scalar()}")

        # Sample 5
        print("\n   Sample schemes:")
        r = await session.execute(text("""
            SELECT name, ministry, scheme_type, category
            FROM schemes ORDER BY id LIMIT 5
        """))
        for row in r.fetchall():
            n = row[0][:55] if row[0] else ""
            m = row[1][:35] if row[1] else ""
            print(f"     - {n:<55} | {m:<35} | {row[2]} | {row[3]}")

        # ── TABLE: eligibility_criteria ──
        r = await session.execute(text("SELECT count(*) FROM eligibility_criteria"))
        print(f"\n2. ELIGIBILITY_CRITERIA TABLE: {r.scalar()} rows")

        r = await session.execute(text("""
            SELECT field, count(*) as cnt FROM eligibility_criteria
            GROUP BY field ORDER BY cnt DESC
        """))
        print("   By field:")
        for row in r.fetchall():
            print(f"     {row[0]:<20} {row[1]:>5}")

        # Sample criteria for PM Kisan
        print("\n   Sample — PM Kisan Samman Nidhi criteria:")
        r = await session.execute(text("""
            SELECT ec.field, ec.operator, ec.value, ec.description
            FROM eligibility_criteria ec
            JOIN schemes s ON s.id = ec.scheme_id
            WHERE s.name = 'PM Kisan Samman Nidhi'
        """))
        for row in r.fetchall():
            print(f"     {row[0]} {row[1]} {row[2]} -- {row[3]}")

        # Sample criteria for Sukanya
        print("\n   Sample — Sukanya Samriddhi Yojana criteria:")
        r = await session.execute(text("""
            SELECT ec.field, ec.operator, ec.value, ec.description
            FROM eligibility_criteria ec
            JOIN schemes s ON s.id = ec.scheme_id
            WHERE s.name = 'Sukanya Samriddhi Yojana'
        """))
        for row in r.fetchall():
            print(f"     {row[0]} {row[1]} {row[2]} -- {row[3]}")

        # Schemes with real criteria (not just nationality)
        r = await session.execute(text("""
            SELECT count(DISTINCT scheme_id) FROM eligibility_criteria
            WHERE field NOT IN ('nationality')
        """))
        print(f"\n   Schemes with real criteria (not just nationality): {r.scalar()}")

        r = await session.execute(text("""
            SELECT count(DISTINCT scheme_id) FROM eligibility_criteria
            WHERE field NOT IN ('nationality', 'state')
        """))
        print(f"   Schemes with deep criteria (age/gender/income/caste etc): {r.scalar()}")

        # ── TABLE: states ──
        r = await session.execute(text("SELECT count(*) FROM states"))
        print(f"\n3. STATES TABLE: {r.scalar()} rows")
        r = await session.execute(text("SELECT name, code FROM states ORDER BY name LIMIT 10"))
        print("   Sample: " + ", ".join([f"{row[0]}({row[1]})" for row in r.fetchall()]))

        # ── TABLE: scheme_states ──
        r = await session.execute(text("SELECT count(*) FROM scheme_states"))
        print(f"\n4. SCHEME_STATES (junction): {r.scalar()} links")
        r = await session.execute(text("""
            SELECT st.name, count(*) as cnt FROM scheme_states ss
            JOIN states st ON st.id = ss.state_id
            GROUP BY st.name ORDER BY cnt DESC LIMIT 10
        """))
        print("   Top states by scheme count:")
        for row in r.fetchall():
            print(f"     {row[0]:<25} {row[1]:>5} schemes")

        # ── TABLE: users ──
        r = await session.execute(text("SELECT count(*) FROM users"))
        print(f"\n5. USERS TABLE: {r.scalar()} rows")
        r = await session.execute(text("SELECT email, role, is_active FROM users"))
        for row in r.fetchall():
            print(f"   {row[0]} | role={row[1]} | active={row[2]}")

        # ── CATEGORY BREAKDOWN ──
        print(f"\n6. CATEGORY BREAKDOWN:")
        r = await session.execute(text("""
            SELECT category, count(*) as cnt FROM schemes
            WHERE category IS NOT NULL
            GROUP BY category ORDER BY cnt DESC
        """))
        for row in r.fetchall():
            print(f"     {row[0]:<35} {row[1]:>5}")

        # ── DATA QUALITY ──
        print(f"\n7. DATA QUALITY SUMMARY:")
        r = await session.execute(text("SELECT count(*) FROM schemes"))
        total = r.scalar()
        checks = [
            ("Schemes with name", "SELECT count(*) FROM schemes WHERE name IS NOT NULL AND name != ''"),
            ("Schemes with ministry", "SELECT count(*) FROM schemes WHERE ministry IS NOT NULL AND ministry != ''"),
            ("Schemes with apply_link", "SELECT count(*) FROM schemes WHERE apply_link IS NOT NULL AND apply_link != ''"),
            ("Schemes with description", "SELECT count(*) FROM schemes WHERE description IS NOT NULL AND description != ''"),
            ("Schemes with >=1 criterion", "SELECT count(DISTINCT scheme_id) FROM eligibility_criteria"),
            ("Schemes with >=2 criteria", "SELECT count(*) FROM (SELECT scheme_id, count(*) c FROM eligibility_criteria GROUP BY scheme_id HAVING count(*) >= 2) t"),
            ("Schemes with >=3 criteria", "SELECT count(*) FROM (SELECT scheme_id, count(*) c FROM eligibility_criteria GROUP BY scheme_id HAVING count(*) >= 3) t"),
        ]
        for label, q in checks:
            r = await session.execute(text(q))
            val = r.scalar()
            pct = val * 100 // total
            print(f"     {label:<35} {val:>5} ({pct}%)")

    await engine.dispose()

asyncio.run(audit())
