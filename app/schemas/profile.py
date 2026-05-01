"""
User profile and eligibility history Pydantic schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserProfileBase(BaseModel):
    """Base schema for user profile fields."""

    age: Optional[int] = None
    gender: Optional[str] = None
    annual_income: Optional[float] = None
    state: Optional[str] = None
    caste_category: Optional[str] = None
    occupation: Optional[str] = None
    is_disabled: bool = False
    is_minority: bool = False
    is_bpl: bool = False
    is_student: bool = False
    is_senior_citizen: bool = False
    land_owned_acres: Optional[float] = None
    num_children: Optional[int] = None


class UserProfileCreate(UserProfileBase):
    """Schema for creating/updating a user profile."""
    pass


class UserProfileResponse(UserProfileBase):
    """Schema for user profile in responses."""

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EligibilityHistoryResponse(BaseModel):
    """Schema for a single eligibility history entry."""

    id: int
    profile_snapshot: dict
    results_snapshot: dict
    total_matched: int
    checked_at: datetime

    model_config = {"from_attributes": True}


class EligibilityHistoryListResponse(BaseModel):
    """Paginated eligibility history."""

    total: int
    history: list[EligibilityHistoryResponse]
    skip: int
    limit: int
