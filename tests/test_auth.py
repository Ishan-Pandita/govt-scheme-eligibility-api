"""
Authentication endpoint tests.

Tests registration, login, token refresh, /me endpoint, and error cases.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestRegistration:
    """Tests for POST /api/v1/auth/register."""

    async def test_register_success(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "password": "SecurePass123",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["role"] == "user"
        assert "id" in data

    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        response = await client.post("/api/v1/auth/register", json={
            "email": "testuser@example.com",
            "password": "AnotherPass123",
        })
        assert response.status_code == 409
        assert "already registered" in response.json()["detail"]

    async def test_register_weak_password(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "email": "weak@example.com",
            "password": "short",
        })
        assert response.status_code == 422  # Validation error

    async def test_register_invalid_email(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "ValidPass123",
        })
        assert response.status_code == 422


@pytest.mark.asyncio
class TestLogin:
    """Tests for POST /api/v1/auth/login."""

    async def test_login_success(self, client: AsyncClient, test_user):
        response = await client.post("/api/v1/auth/login", json={
            "email": "testuser@example.com",
            "password": "TestPass123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        response = await client.post("/api/v1/auth/login", json={
            "email": "testuser@example.com",
            "password": "WrongPassword",
        })
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    async def test_login_nonexistent_user(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com",
            "password": "SomePass123",
        })
        assert response.status_code == 401


@pytest.mark.asyncio
class TestTokenRefresh:
    """Tests for POST /api/v1/auth/refresh."""

    async def test_refresh_success(self, client: AsyncClient, test_user):
        # Login first to get a refresh token
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "testuser@example.com",
            "password": "TestPass123",
        })
        refresh_token = login_resp.json()["refresh_token"]

        # Use refresh token
        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_with_access_token_fails(self, client: AsyncClient, test_user):
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "testuser@example.com",
            "password": "TestPass123",
        })
        access_token = login_resp.json()["access_token"]

        # Try using access token as refresh token (should fail)
        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": access_token,
        })
        assert response.status_code == 401

    async def test_refresh_invalid_token(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid.jwt.token",
        })
        assert response.status_code == 401


@pytest.mark.asyncio
class TestMe:
    """Tests for GET /api/v1/auth/me."""

    async def test_me_authenticated(self, client: AsyncClient, test_user, user_headers):
        response = await client.get("/api/v1/auth/me", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "testuser@example.com"
        assert data["role"] == "user"

    async def test_me_no_token(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_me_invalid_token(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401
