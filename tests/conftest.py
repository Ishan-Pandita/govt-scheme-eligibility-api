"""
Pytest configuration and shared fixtures.

Provides test database session, test client, and pre-created
test users (regular + admin) for all test modules.
"""

import asyncio
import json
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Override settings before importing app
os.environ["DATABASE_URL"] = "postgresql+asyncpg://schemes_user:schemes_pass@localhost:5432/schemes_test_db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"  # Use DB 1 for tests
os.environ["ENVIRONMENT"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"

from app.database import Base, get_db
from app.main import app
from app.core.security import hash_password, create_access_token
from app.models import User, Scheme, State, EligibilityCriteria


# Test database engine
TEST_DATABASE_URL = os.environ["DATABASE_URL"]
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a clean database session for each test.
    Creates all tables before the test and drops them after.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_session_factory() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an async HTTP test client with the test DB injected.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a regular test user."""
    user = User(
        email="testuser@example.com",
        hashed_password=hash_password("TestPass123"),
        role="user",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create a test admin user."""
    user = User(
        email="admin@example.com",
        hashed_password=hash_password("AdminPass123"),
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
def user_token(test_user: User) -> str:
    """Generate a valid access token for the test user."""
    return create_access_token({"sub": str(test_user.id)})


@pytest_asyncio.fixture
def admin_token(admin_user: User) -> str:
    """Generate a valid access token for the admin user."""
    return create_access_token({"sub": str(admin_user.id)})


@pytest_asyncio.fixture
def user_headers(user_token: str) -> dict:
    """Authorization headers for a regular user."""
    return {"Authorization": f"Bearer {user_token}"}


@pytest_asyncio.fixture
def admin_headers(admin_token: str) -> dict:
    """Authorization headers for an admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest_asyncio.fixture
async def seeded_schemes(db_session: AsyncSession) -> list[Scheme]:
    """
    Seed a few test schemes with criteria for eligibility testing.
    """
    # Create a state
    tn = State(code="TN", name="Tamil Nadu")
    mh = State(code="MH", name="Maharashtra")
    db_session.add_all([tn, mh])
    await db_session.flush()

    schemes = []

    # Scheme 1: PM Kisan (farmer, income < 200000, age >= 18)
    s1 = Scheme(
        name="PM Kisan Samman Nidhi",
        description="Income support for farmers",
        ministry="Ministry of Agriculture",
        scheme_type="central",
        benefit_amount="Rs 6,000/year",
        category="agriculture",
        is_active=True,
    )
    db_session.add(s1)
    await db_session.flush()

    for field, op, val, desc in [
        ("occupation", "eq", "farmer", "Must be a farmer"),
        ("annual_income", "lte", "200000", "Income must be below 2 lakh"),
        ("age", "gte", "18", "Must be 18 or older"),
    ]:
        db_session.add(EligibilityCriteria(
            scheme_id=s1.id, field=field, operator=op, value=val, description=desc
        ))
    schemes.append(s1)

    # Scheme 2: Female-only scheme (gender=female, state=Tamil Nadu)
    s2 = Scheme(
        name="Moovalur Scheme",
        description="Education support for women",
        ministry="TN State Government",
        scheme_type="state",
        benefit_amount="Rs 25,000",
        category="education",
        gender_specific="female",
        is_active=True,
    )
    db_session.add(s2)
    await db_session.flush()

    db_session.add(EligibilityCriteria(
        scheme_id=s2.id, field="gender", operator="eq", value="female",
        description="Must be female"
    ))
    # Link to Tamil Nadu
    from app.models.scheme import scheme_state
    await db_session.execute(
        scheme_state.insert().values(scheme_id=s2.id, state_id=tn.id)
    )
    schemes.append(s2)

    # Scheme 3: Universal scheme (no criteria — everyone qualifies)
    s3 = Scheme(
        name="Universal Basic Scheme",
        description="Available to all citizens",
        ministry="Ministry of Social Justice",
        scheme_type="central",
        category="social",
        is_active=True,
    )
    db_session.add(s3)
    await db_session.flush()
    schemes.append(s3)

    # Scheme 4: Inactive scheme (should not appear in results)
    s4 = Scheme(
        name="Discontinued Scheme",
        description="No longer active",
        ministry="Ministry of Finance",
        scheme_type="central",
        category="finance",
        is_active=False,
    )
    db_session.add(s4)
    await db_session.flush()
    schemes.append(s4)

    await db_session.commit()
    return schemes
