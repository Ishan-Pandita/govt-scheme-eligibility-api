"""
Eligibility engine and API endpoint tests.

Tests the rule engine logic, the /eligibility/check endpoint,
scheme listing, searching, and individual scheme retrieval.
"""

import pytest
from httpx import AsyncClient

from app.services.eligibility_engine import EligibilityEngine
from app.models.eligibility import EligibilityCriteria


@pytest.mark.asyncio
class TestEligibilityEngine:
    """Unit tests for the EligibilityEngine class."""

    def setup_method(self):
        self.engine = EligibilityEngine()

    def _make_criterion(self, field, operator, value):
        """Create a mock EligibilityCriteria-like object."""
        c = type("Criterion", (), {})()
        c.field = field
        c.operator = operator
        c.value = value
        return c

    async def test_eq_operator(self):
        profile = {"gender": "female"}
        c = self._make_criterion("gender", "eq", "female")
        passed, reason = self.engine.evaluate_criterion(profile, c)
        assert passed is True

    async def test_eq_operator_fail(self):
        profile = {"gender": "male"}
        c = self._make_criterion("gender", "eq", "female")
        passed, reason = self.engine.evaluate_criterion(profile, c)
        assert passed is False

    async def test_gte_operator(self):
        profile = {"age": 25}
        c = self._make_criterion("age", "gte", "18")
        passed, reason = self.engine.evaluate_criterion(profile, c)
        assert passed is True

    async def test_lte_operator(self):
        profile = {"annual_income": 150000}
        c = self._make_criterion("annual_income", "lte", "200000")
        passed, reason = self.engine.evaluate_criterion(profile, c)
        assert passed is True

    async def test_lte_operator_fail(self):
        profile = {"annual_income": 300000}
        c = self._make_criterion("annual_income", "lte", "200000")
        passed, reason = self.engine.evaluate_criterion(profile, c)
        assert passed is False

    async def test_in_operator_json_list(self):
        profile = {"state": "Tamil Nadu"}
        c = self._make_criterion("state", "in", '["Tamil Nadu", "Kerala"]')
        passed, reason = self.engine.evaluate_criterion(profile, c)
        assert passed is True

    async def test_in_operator_csv(self):
        profile = {"caste_category": "sc"}
        c = self._make_criterion("caste_category", "in", "sc, st, obc")
        passed, reason = self.engine.evaluate_criterion(profile, c)
        assert passed is True

    async def test_not_in_operator(self):
        profile = {"occupation": "farmer"}
        c = self._make_criterion("occupation", "not_in", '["government_employee"]')
        passed, reason = self.engine.evaluate_criterion(profile, c)
        assert passed is True

    async def test_missing_field_skipped(self):
        profile = {}  # No fields provided
        c = self._make_criterion("age", "gte", "18")
        passed, reason = self.engine.evaluate_criterion(profile, c)
        assert passed is True  # Missing fields are skipped
        assert "skipped" in reason

    async def test_contains_operator(self):
        profile = {"occupation": "self_employed"}
        c = self._make_criterion("occupation", "contains", "employed")
        passed, reason = self.engine.evaluate_criterion(profile, c)
        assert passed is True

    async def test_boolean_field(self):
        profile = {"is_disabled": True}
        c = self._make_criterion("is_disabled", "eq", "true")
        passed, reason = self.engine.evaluate_criterion(profile, c)
        assert passed is True

    async def test_scheme_all_criteria_pass(self):
        profile = {"age": 25, "occupation": "farmer", "annual_income": 150000}
        criteria = [
            self._make_criterion("age", "gte", "18"),
            self._make_criterion("occupation", "eq", "farmer"),
            self._make_criterion("annual_income", "lte", "200000"),
        ]
        matched, reasons = self.engine.evaluate_scheme(profile, criteria)
        assert matched is True

    async def test_scheme_one_criterion_fails(self):
        profile = {"age": 15, "occupation": "farmer", "annual_income": 150000}
        criteria = [
            self._make_criterion("age", "gte", "18"),  # Fails: 15 < 18
            self._make_criterion("occupation", "eq", "farmer"),
            self._make_criterion("annual_income", "lte", "200000"),
        ]
        matched, reasons = self.engine.evaluate_scheme(profile, criteria)
        assert matched is False

    async def test_scheme_no_criteria_matches_everyone(self):
        profile = {"age": 50}
        matched, reasons = self.engine.evaluate_scheme(profile, [])
        assert matched is True


@pytest.mark.asyncio
class TestEligibilityEndpoint:
    """Tests for POST /api/v1/eligibility/check."""

    async def test_check_eligible_farmer(self, client: AsyncClient, seeded_schemes):
        response = await client.post("/api/v1/eligibility/check", json={
            "age": 30,
            "gender": "male",
            "annual_income": 150000,
            "occupation": "farmer",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["total_matched"] >= 2  # PM Kisan + Universal
        scheme_names = [s["name"] for s in data["schemes"]]
        assert "PM Kisan Samman Nidhi" in scheme_names
        assert "Universal Basic Scheme" in scheme_names
        # Inactive scheme should not appear
        assert "Discontinued Scheme" not in scheme_names

    async def test_check_no_matches(self, client: AsyncClient, seeded_schemes):
        response = await client.post("/api/v1/eligibility/check", json={
            "age": 10,
            "gender": "male",
            "annual_income": 500000,
            "occupation": "student",
        })
        assert response.status_code == 200
        data = response.json()
        # Should still match Universal scheme
        assert data["total_matched"] >= 1

    async def test_check_empty_profile(self, client: AsyncClient, seeded_schemes):
        response = await client.post("/api/v1/eligibility/check", json={})
        assert response.status_code == 200
        data = response.json()
        # Empty profile skips all criteria, so matches broadly
        assert data["total_matched"] >= 1

    async def test_check_invalid_age(self, client: AsyncClient):
        response = await client.post("/api/v1/eligibility/check", json={
            "age": -5,
        })
        assert response.status_code == 422

    async def test_cache_header_present(self, client: AsyncClient, seeded_schemes):
        response = await client.post("/api/v1/eligibility/check", json={
            "age": 30,
            "occupation": "farmer",
        })
        assert response.status_code == 200
        # X-Cache header should be present
        assert "X-Cache" in response.headers


@pytest.mark.asyncio
class TestSchemeEndpoints:
    """Tests for scheme listing, search, and detail endpoints."""

    async def test_list_schemes(self, client: AsyncClient, seeded_schemes):
        response = await client.get("/api/v1/schemes")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "schemes" in data
        assert data["total"] >= 3  # 3 active schemes
        # Inactive should not appear by default
        names = [s["name"] for s in data["schemes"]]
        assert "Discontinued Scheme" not in names

    async def test_list_with_pagination(self, client: AsyncClient, seeded_schemes):
        response = await client.get("/api/v1/schemes?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["schemes"]) <= 2

    async def test_list_filter_by_category(self, client: AsyncClient, seeded_schemes):
        response = await client.get("/api/v1/schemes?category=agriculture")
        assert response.status_code == 200
        data = response.json()
        for s in data["schemes"]:
            assert s["category"] == "agriculture"

    async def test_search_schemes(self, client: AsyncClient, seeded_schemes):
        response = await client.get("/api/v1/schemes/search?q=Kisan")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any("Kisan" in s["name"] for s in data["schemes"])

    async def test_search_min_length(self, client: AsyncClient):
        response = await client.get("/api/v1/schemes/search?q=a")
        assert response.status_code == 422  # min_length=2

    async def test_get_scheme_detail(self, client: AsyncClient, seeded_schemes):
        scheme_id = seeded_schemes[0].id
        response = await client.get(f"/api/v1/schemes/{scheme_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == scheme_id
        assert "criteria" in data

    async def test_get_nonexistent_scheme(self, client: AsyncClient):
        response = await client.get("/api/v1/schemes/99999")
        assert response.status_code == 404


@pytest.mark.asyncio
class TestAdminEndpoints:
    """Tests for admin scheme management."""

    async def test_create_scheme_as_admin(self, client: AsyncClient, admin_headers):
        response = await client.post("/api/v1/admin/schemes", json={
            "name": "New Test Scheme",
            "description": "Created via test",
            "ministry": "Test Ministry",
            "scheme_type": "central",
            "category": "test",
            "criteria": [
                {"field": "age", "operator": "gte", "value": "18"}
            ],
        }, headers=admin_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Test Scheme"
        assert len(data["criteria"]) == 1

    async def test_create_scheme_as_user_forbidden(self, client: AsyncClient, user_headers):
        response = await client.post("/api/v1/admin/schemes", json={
            "name": "Forbidden Scheme",
        }, headers=user_headers)
        assert response.status_code == 403

    async def test_create_scheme_unauthenticated(self, client: AsyncClient):
        response = await client.post("/api/v1/admin/schemes", json={
            "name": "No Auth Scheme",
        })
        assert response.status_code == 401

    async def test_update_scheme(self, client: AsyncClient, admin_headers, seeded_schemes):
        scheme_id = seeded_schemes[0].id
        response = await client.put(f"/api/v1/admin/schemes/{scheme_id}", json={
            "benefit_amount": "Rs 10,000/year",
        }, headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["benefit_amount"] == "Rs 10,000/year"

    async def test_soft_delete_scheme(self, client: AsyncClient, admin_headers, seeded_schemes):
        scheme_id = seeded_schemes[0].id
        response = await client.delete(
            f"/api/v1/admin/schemes/{scheme_id}",
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert "deactivated" in response.json()["message"]

    async def test_add_criterion(self, client: AsyncClient, admin_headers, seeded_schemes):
        scheme_id = seeded_schemes[0].id
        response = await client.post(
            f"/api/v1/admin/schemes/{scheme_id}/criteria",
            json={
                "field": "is_bpl",
                "operator": "eq",
                "value": "true",
                "description": "Must be below poverty line",
            },
            headers=admin_headers,
        )
        assert response.status_code == 201
        assert response.json()["field"] == "is_bpl"
