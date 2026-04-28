"""Reset database and re-seed with verified scraped data."""
import asyncio
import json
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.dirname(__file__))
from app.database import async_session, engine, Base
from app.models import Scheme, State, EligibilityCriteria, User, scheme_state
from seed import seed_states, seed_schemes, seed_admin_user, verify_counts


async def main():
    print("=" * 50)
    print("  Resetting and re-seeding with verified data")
    print("=" * 50)

    async with async_session() as session:
        # Clear existing data
        print("\n1. Clearing existing data...")
        await session.execute(text("DELETE FROM scheme_states"))
        await session.execute(text("DELETE FROM eligibility_criteria"))
        await session.execute(text("DELETE FROM schemes"))
        await session.commit()
        print("  Cleared all schemes, criteria, and state links")

        # Re-seed
        print("\n2. Seeding states...")
        state_map = await seed_states(session)

        print("\n3. Seeding 504 verified schemes...")
        await seed_schemes(session, state_map)

        print("\n4. Ensuring admin user exists...")
        await seed_admin_user(session)

        print("\n5. Verification:")
        await verify_counts(session)

    print("\n" + "=" * 50)
    print("  Re-seeding complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
