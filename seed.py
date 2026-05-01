"""
Database seed script.

Reads schemes_seed.json and inserts all schemes, criteria, and states
into PostgreSQL. Idempotent — can be run multiple times safely.

Usage:
    python seed.py
"""

import asyncio
import json
import os
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from app.database import async_session, engine, Base
from app.config import get_settings
from app.models import User, Scheme, State, EligibilityCriteria, scheme_state


# All 36 Indian states and union territories
INDIAN_STATES = [
    ("AN", "Andaman and Nicobar Islands"),
    ("AP", "Andhra Pradesh"),
    ("AR", "Arunachal Pradesh"),
    ("AS", "Assam"),
    ("BR", "Bihar"),
    ("CH", "Chandigarh"),
    ("CG", "Chhattisgarh"),
    ("DD", "Dadra and Nagar Haveli and Daman and Diu"),
    ("DL", "Delhi"),
    ("GA", "Goa"),
    ("GJ", "Gujarat"),
    ("HR", "Haryana"),
    ("HP", "Himachal Pradesh"),
    ("JK", "Jammu and Kashmir"),
    ("JH", "Jharkhand"),
    ("KA", "Karnataka"),
    ("KL", "Kerala"),
    ("LA", "Ladakh"),
    ("MP", "Madhya Pradesh"),
    ("MH", "Maharashtra"),
    ("MN", "Manipur"),
    ("ML", "Meghalaya"),
    ("MZ", "Mizoram"),
    ("NL", "Nagaland"),
    ("OD", "Odisha"),
    ("PY", "Puducherry"),
    ("PB", "Punjab"),
    ("RJ", "Rajasthan"),
    ("SK", "Sikkim"),
    ("TN", "Tamil Nadu"),
    ("TS", "Telangana"),
    ("TR", "Tripura"),
    ("UP", "Uttar Pradesh"),
    ("UK", "Uttarakhand"),
    ("WB", "West Bengal"),
]


async def seed_states(session: AsyncSession) -> dict[str, State]:
    """Insert all Indian states. Returns code->State mapping."""
    state_map = {}

    for code, name in INDIAN_STATES:
        # Check if already exists
        result = await session.execute(select(State).where(State.code == code))
        existing = result.scalar_one_or_none()

        if existing:
            state_map[code] = existing
        else:
            state = State(code=code, name=name)
            session.add(state)
            await session.flush()
            state_map[code] = state

    await session.commit()
    print(f"  States: {len(state_map)} loaded")
    return state_map


async def seed_schemes(session: AsyncSession, state_map: dict[str, State]):
    """Insert schemes from seed JSON file."""
    seed_path = os.path.join(os.path.dirname(__file__), "app", "data", "schemes_seed.json")

    with open(seed_path, "r", encoding="utf-8") as f:
        schemes_data = json.load(f)

    inserted = 0
    skipped = 0

    for s in schemes_data:
        # Check if scheme already exists by name
        result = await session.execute(select(Scheme).where(Scheme.name == s["name"]))
        if result.scalar_one_or_none():
            skipped += 1
            continue

        # Create scheme
        scheme = Scheme(
            name=s["name"],
            description=s.get("description"),
            ministry=s.get("ministry"),
            scheme_type=s.get("scheme_type"),
            benefit_amount=s.get("benefit_amount"),
            benefit_description=s.get("benefit_description"),
            apply_link=s.get("apply_link"),
            category=s.get("category"),
            gender_specific=s.get("gender_specific"),
            is_active=True,
        )
        session.add(scheme)
        await session.flush()  # Get the scheme ID

        # Add criteria
        for c in s.get("criteria", []):
            criterion = EligibilityCriteria(
                scheme_id=scheme.id,
                field=c["field"],
                operator=c["operator"],
                value=c["value"],
                description=c.get("description"),
            )
            session.add(criterion)

        # Link states
        for state_code in s.get("states", []):
            if state_code in state_map:
                await session.execute(
                    scheme_state.insert().values(
                        scheme_id=scheme.id,
                        state_id=state_map[state_code].id,
                    )
                )

        inserted += 1

    await session.commit()
    print(f"  Schemes: {inserted} inserted, {skipped} skipped (already exist)")


async def seed_admin_user(session: AsyncSession):
    """Create a default admin user if none exists."""
    from passlib.context import CryptContext

    settings = get_settings()
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        print("  Admin user: skipped (ADMIN_EMAIL/ADMIN_PASSWORD not configured)")
        return

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    result = await session.execute(select(User).where(User.role == "admin").order_by(User.id))
    existing_admin = result.scalars().first()

    if existing_admin:
        existing_admin.email = settings.ADMIN_EMAIL
        existing_admin.hashed_password = pwd_context.hash(settings.ADMIN_PASSWORD)
        existing_admin.is_active = True
        existing_admin.role = "admin"
        await session.commit()
        print(f"  Admin user: updated ({settings.ADMIN_EMAIL})")
        return

    admin = User(
        email=settings.ADMIN_EMAIL,
        hashed_password=pwd_context.hash(settings.ADMIN_PASSWORD),
        role="admin",
        is_active=True,
    )
    session.add(admin)
    await session.commit()
    print(f"  Admin user: created ({settings.ADMIN_EMAIL})")


async def verify_counts(session: AsyncSession):
    """Print table counts for verification."""
    from sqlalchemy import func

    for model, name in [(Scheme, "schemes"), (EligibilityCriteria, "criteria"), (State, "states"), (User, "users")]:
        result = await session.execute(select(func.count()).select_from(model))
        count = result.scalar()
        print(f"  {name}: {count} rows")


async def main():
    """Run all seed operations."""
    print("=" * 50)
    print("  Seeding Database")
    print("=" * 50)

    async with async_session() as session:
        print("\n1. Seeding states...")
        state_map = await seed_states(session)

        print("\n2. Seeding schemes and criteria...")
        await seed_schemes(session, state_map)

        print("\n3. Creating admin user...")
        await seed_admin_user(session)

        print("\n4. Verification counts:")
        await verify_counts(session)

    print("\n" + "=" * 50)
    print("  Seeding complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
