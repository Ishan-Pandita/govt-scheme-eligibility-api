"""
Profile and eligibility history endpoint tests.

These cover the source-of-truth Day 8 flows: saving a user profile,
retrieving it, and recording authenticated eligibility checks in history.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestUserProfile:
    """Tests for POST/GET /api/v1/profile."""

    async def test_get_profile_before_save_returns_404(
        self,
        client: AsyncClient,
        test_user,
        user_headers,
    ):
        response = await client.get("/api/v1/profile", headers=user_headers)
        assert response.status_code == 404

    async def test_save_and_get_profile(
        self,
        client: AsyncClient,
        test_user,
        user_headers,
    ):
        payload = {
            "age": 28,
            "gender": "female",
            "annual_income": 180000,
            "state": "Tamil Nadu",
            "caste_category": "obc",
            "occupation": "student",
            "is_student": True,
        }

        save_response = await client.post(
            "/api/v1/profile",
            json=payload,
            headers=user_headers,
        )
        assert save_response.status_code == 200
        assert save_response.json()["state"] == "Tamil Nadu"

        get_response = await client.get("/api/v1/profile", headers=user_headers)
        assert get_response.status_code == 200
        assert get_response.json()["occupation"] == "student"


@pytest.mark.asyncio
class TestEligibilityHistory:
    """Tests for GET /api/v1/eligibility/history."""

    async def test_authenticated_check_is_saved_to_history(
        self,
        client: AsyncClient,
        test_user,
        user_headers,
        seeded_schemes,
    ):
        check_response = await client.post(
            "/api/v1/eligibility/check",
            json={
                "age": 30,
                "annual_income": 150000,
                "occupation": "farmer",
            },
            headers=user_headers,
        )
        assert check_response.status_code == 200

        history_response = await client.get(
            "/api/v1/eligibility/history",
            headers=user_headers,
        )
        assert history_response.status_code == 200

        data = history_response.json()
        assert data["total"] == 1
        assert data["history"][0]["total_matched"] == check_response.json()["total_matched"]
        assert data["history"][0]["profile_snapshot"]["occupation"] == "farmer"

    async def test_history_requires_authentication(self, client: AsyncClient):
        response = await client.get("/api/v1/eligibility/history")
        assert response.status_code == 401
