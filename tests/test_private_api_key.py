"""Tests for project-level private API key protection."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_api_endpoint_requires_private_api_key(db_session):
    async def override_get_db():
        yield db_session

    from app.database import get_db
    from app.services.memory_redis import MemoryRedis

    app.dependency_overrides[get_db] = override_get_db
    app.state.redis = MemoryRedis()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/eligibility/check", json={})

    app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"
