"""
Scheme and eligibility Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional
from enum import Enum

from pydantic import BaseModel, field_validator


# --- Enums ---

class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"


class CasteCategory(str, Enum):
    general = "general"
    obc = "obc"
    sc = "sc"
    st = "st"
    ews = "ews"


class Occupation(str, Enum):
    farmer = "farmer"
    student = "student"
    salaried = "salaried"
    self_employed = "self_employed"
    unemployed = "unemployed"
    government_employee = "government_employee"
    daily_wage = "daily_wage"
    street_vendor = "street_vendor"
    other = "other"


# --- User Profile for Eligibility Check ---

class UserProfileInput(BaseModel):
    """
    User profile submitted for eligibility checking.
    All fields are optional — the engine skips checks for missing fields.
    """

    age: Optional[int] = None
    gender: Optional[Gender] = None
    annual_income: Optional[float] = None
    state: Optional[str] = None
    caste_category: Optional[CasteCategory] = None
    occupation: Optional[Occupation] = None
    is_disabled: bool = False
    is_minority: bool = False
    is_bpl: bool = False  # Below Poverty Line
    is_student: bool = False
    is_senior_citizen: bool = False
    land_owned_acres: Optional[float] = None
    num_children: Optional[int] = None

    @field_validator("age")
    @classmethod
    def age_must_be_valid(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 0 or v > 120):
            raise ValueError("Age must be between 0 and 120")
        return v

    @field_validator("annual_income")
    @classmethod
    def income_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Annual income cannot be negative")
        return v


# --- Eligibility Criteria Schemas ---

class EligibilityCriteriaBase(BaseModel):
    """Base schema for eligibility criteria."""

    field: str
    operator: str
    value: str
    description: Optional[str] = None

    @field_validator("operator")
    @classmethod
    def valid_operator(cls, v: str) -> str:
        allowed = {"eq", "neq", "gte", "lte", "gt", "lt", "in", "not_in", "contains"}
        if v not in allowed:
            raise ValueError(f"Operator must be one of: {', '.join(allowed)}")
        return v


class EligibilityCriteriaCreate(EligibilityCriteriaBase):
    """Schema for creating a new eligibility criterion."""
    pass


class EligibilityCriteriaResponse(EligibilityCriteriaBase):
    """Schema for eligibility criteria in responses."""

    id: int
    scheme_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Scheme Schemas ---

class SchemeBase(BaseModel):
    """Base schema for scheme data."""

    name: str
    description: Optional[str] = None
    ministry: Optional[str] = None
    scheme_type: Optional[str] = None
    benefit_amount: Optional[str] = None
    benefit_description: Optional[str] = None
    apply_link: Optional[str] = None
    category: Optional[str] = None
    gender_specific: Optional[str] = None


class SchemeCreate(SchemeBase):
    """Schema for creating a new scheme."""

    criteria: list[EligibilityCriteriaCreate] = []
    state_codes: list[str] = []  # List of state codes: ["TN", "KA"]


class SchemeUpdate(BaseModel):
    """Schema for updating a scheme (all fields optional)."""

    name: Optional[str] = None
    description: Optional[str] = None
    ministry: Optional[str] = None
    scheme_type: Optional[str] = None
    benefit_amount: Optional[str] = None
    benefit_description: Optional[str] = None
    apply_link: Optional[str] = None
    category: Optional[str] = None
    gender_specific: Optional[str] = None
    is_active: Optional[bool] = None


class SchemeResponse(SchemeBase):
    """Schema for scheme data in responses."""

    id: int
    is_active: bool
    created_at: datetime
    criteria: list[EligibilityCriteriaResponse] = []
    states: list[str] = []  # State names

    model_config = {"from_attributes": True}


class SchemeListResponse(BaseModel):
    """Schema for paginated scheme list."""

    total: int
    schemes: list[SchemeResponse]
    skip: int
    limit: int


# --- Eligibility Check Response ---

class MatchedScheme(BaseModel):
    """A scheme that matched a user profile, with reasons."""

    id: int
    name: str
    ministry: Optional[str] = None
    benefit_amount: Optional[str] = None
    benefit_description: Optional[str] = None
    apply_link: Optional[str] = None
    category: Optional[str] = None
    matched_because: list[str] = []  # e.g., ["age gte 18 ✓", "gender eq female ✓"]


class EligibilityCheckResponse(BaseModel):
    """Response for POST /eligibility/check."""

    profile_summary: dict
    total_matched: int
    schemes: list[MatchedScheme]
