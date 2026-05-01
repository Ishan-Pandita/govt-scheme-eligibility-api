"""
Core eligibility engine.

Data-driven rule engine that evaluates user profiles against scheme criteria
stored in the database. No hardcoded rules — all logic flows from
EligibilityCriteria rows.

Supported operators: eq, neq, gte, lte, gt, lt, in, not_in, contains
"""

import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.eligibility import EligibilityCriteria
from app.models.scheme import Scheme


class EligibilityEngine:
    """
    Evaluates user profiles against scheme eligibility criteria.

    Each scheme has multiple EligibilityCriteria rows. A user matches a scheme
    only if ALL criteria pass (AND logic). Fields not present in the user
    profile are skipped — missing data never disqualifies.
    """

    OPERATORS = {
        "eq": lambda a, b: a == b,
        "neq": lambda a, b: a != b,
        "gte": lambda a, b: float(a) >= float(b),
        "lte": lambda a, b: float(a) <= float(b),
        "gt": lambda a, b: float(a) > float(b),
        "lt": lambda a, b: float(a) < float(b),
        "in": lambda a, b: str(a).lower() in [v.strip().lower() for v in b],
        "not_in": lambda a, b: str(a).lower() not in [v.strip().lower() for v in b],
        "contains": lambda a, b: str(b).lower() in str(a).lower(),
    }

    @staticmethod
    def _parse_criterion_value(value: str, operator: str):
        """
        Parse criterion value from its stored string representation.

        For 'in' and 'not_in' operators, the value is a JSON list or
        comma-separated string. For numeric operators, it stays as-is
        (comparison functions handle casting).
        """
        if operator in ("in", "not_in"):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(v) for v in parsed]
            except (json.JSONDecodeError, TypeError):
                pass
            # Fallback: comma-separated
            return [v.strip() for v in value.split(",")]

        return value

    @staticmethod
    def _get_profile_value(profile: dict, field: str):
        """
        Extract a field value from the user profile dict.

        Handles boolean fields (is_disabled, is_bpl, etc.) and converts
        enum values to their string representation.
        """
        value = profile.get(field)
        if value is None:
            return None

        # Convert booleans to string for comparison
        if isinstance(value, bool):
            return str(value).lower()

        # Convert enums to their value
        if hasattr(value, "value"):
            return value.value

        return value

    def evaluate_criterion(
        self, profile: dict, criterion: EligibilityCriteria
    ) -> tuple[bool, str]:
        """
        Evaluate a single criterion against a user profile.

        Args:
            profile: User profile as a dict.
            criterion: An EligibilityCriteria record.

        Returns:
            Tuple of (passed: bool, reason: str).
            If the profile field is missing, returns (True, skip_reason).
        """
        user_value = self._get_profile_value(profile, criterion.field)

        # Missing field — skip this criterion (don't penalize incomplete profiles)
        if user_value is None:
            return True, f"{criterion.field}: not provided (skipped)"

        criterion_value = self._parse_criterion_value(criterion.value, criterion.operator)
        op_fn = self.OPERATORS.get(criterion.operator)

        if op_fn is None:
            # Unknown operator — skip rather than crash
            return True, f"{criterion.field}: unknown operator '{criterion.operator}' (skipped)"

        try:
            passed = op_fn(user_value, criterion_value)
        except (ValueError, TypeError):
            # Type mismatch during comparison — treat as not matching
            return False, f"{criterion.field} {criterion.operator} {criterion.value}: type error"

        symbol = "pass" if passed else "fail"
        reason = f"{criterion.field} {criterion.operator} {criterion.value}: {symbol}"
        return passed, reason

    def evaluate_scheme(
        self, profile: dict, criteria: list[EligibilityCriteria]
    ) -> tuple[bool, list[str]]:
        """
        Evaluate all criteria for a single scheme.

        All criteria must pass (AND logic) for the scheme to match.

        Returns:
            Tuple of (matched: bool, reasons: list[str]).
        """
        reasons = []
        all_passed = True

        for criterion in criteria:
            passed, reason = self.evaluate_criterion(profile, criterion)
            reasons.append(reason)
            if not passed:
                all_passed = False
                break  # Short-circuit on first failure

        return all_passed, reasons

    async def get_eligible_schemes(
        self,
        profile: dict,
        db: AsyncSession,
        state_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
    ) -> list[dict]:
        """
        Find all schemes matching a user profile.

        Args:
            profile: User profile dict with fields like age, gender, income, etc.
            db: Async database session.
            state_filter: Optional state name to filter schemes.
            category_filter: Optional category to filter schemes.

        Returns:
            List of matched scheme dicts with reasons.
        """
        # Build query — load criteria eagerly to avoid N+1
        query = (
            select(Scheme)
            .where(Scheme.is_active == True)
            .options(selectinload(Scheme.criteria))
            .options(selectinload(Scheme.states))
        )

        if category_filter:
            query = query.where(Scheme.category == category_filter)

        result = await db.execute(query)
        schemes = result.scalars().all()

        matched_schemes = []

        for scheme in schemes:
            # State filtering: if user specified a state, skip schemes that
            # are state-specific and don't include that state
            if state_filter and scheme.states:
                scheme_state_names = [s.name.lower() for s in scheme.states]
                if state_filter.lower() not in scheme_state_names:
                    continue

            # Gender filtering: skip schemes targeting a different gender
            user_gender = profile.get("gender")
            if user_gender and hasattr(user_gender, "value"):
                user_gender = user_gender.value
            if (
                scheme.gender_specific
                and user_gender
                and scheme.gender_specific.lower() != str(user_gender).lower()
            ):
                continue

            # Evaluate eligibility criteria
            matched, reasons = self.evaluate_scheme(profile, scheme.criteria)

            if matched:
                matched_schemes.append({
                    "id": scheme.id,
                    "name": scheme.name,
                    "ministry": scheme.ministry,
                    "benefit_amount": scheme.benefit_amount,
                    "benefit_description": scheme.benefit_description,
                    "apply_link": scheme.apply_link,
                    "category": scheme.category,
                    "matched_because": [r for r in reasons if "skipped" not in r],
                })

        return matched_schemes


# Singleton instance
eligibility_engine = EligibilityEngine()
