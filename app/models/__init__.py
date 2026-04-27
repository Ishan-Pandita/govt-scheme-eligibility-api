"""
Database models package.

All models are imported here so Alembic autogenerate can detect them
and so other modules can import from app.models directly.
"""

from app.models.user import User
from app.models.scheme import Scheme, State, scheme_state
from app.models.eligibility import EligibilityCriteria

__all__ = [
    "User",
    "Scheme",
    "State",
    "scheme_state",
    "EligibilityCriteria",
]
