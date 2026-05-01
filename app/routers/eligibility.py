"""
Eligibility and schemes router.

Endpoints for checking eligibility, listing schemes, searching, and
retrieving individual scheme details. Integrates Redis caching and
auto-saves history for authenticated users.
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from jose import JWTError
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.security import decode_token
from app.database import get_db
from app.models.profile import EligibilityHistory
from app.models.scheme import Scheme, State
from app.schemas.scheme import (
    EligibilityCheckResponse,
    MatchedScheme,
    SchemeListResponse,
    SchemeResponse,
    UserProfileInput,
)
from app.services.cache_service import CacheService
from app.services.eligibility_engine import eligibility_engine

settings = get_settings()

router = APIRouter(tags=["Eligibility & Schemes"])


def _get_user_id_from_request(request: Request) -> Optional[int]:
    """
    Extract user ID from Authorization header if present.
    Returns None for unauthenticated requests (eligibility check is public).
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ", 1)[1]
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id and payload.get("type") == "access":
            return int(user_id)
    except (JWTError, ValueError):
        pass

    return None


# --- Eligibility Check ---

@router.post(
    "/eligibility/check",
    response_model=EligibilityCheckResponse,
    summary="Check which schemes a user profile is eligible for",
)
async def check_eligibility(
    profile: UserProfileInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a user profile and receive all matching government schemes.

    The engine evaluates each scheme's eligibility criteria against the
    provided profile fields. Missing fields are skipped, not penalized.

    Results are cached in Redis for 1 hour. The X-Cache header indicates
    whether the result was served from cache (HIT) or computed fresh (MISS).
    """
    profile_dict = profile.model_dump()
    cache_hit = False

    # Try cache first
    cache = CacheService(request.app.state.redis)
    cached_results = await cache.get(profile_dict)

    if cached_results is not None:
        matched = cached_results
        cache_hit = True
    else:
        matched = await eligibility_engine.get_eligible_schemes(
            profile=profile_dict,
            db=db,
            state_filter=profile.state,
            category_filter=None,
        )
        # Store in cache
        await cache.set(profile_dict, matched)

    # Build profile summary (only non-None fields)
    profile_summary = {k: v for k, v in profile_dict.items() if v is not None}
    for key, val in profile_summary.items():
        if hasattr(val, "value"):
            profile_summary[key] = val.value

    # Auto-save to history if user is authenticated
    user_id = _get_user_id_from_request(request)
    if user_id:
        history_entry = EligibilityHistory(
            user_id=user_id,
            profile_snapshot=json.dumps(profile_summary, default=str),
            results_snapshot=json.dumps(matched, default=str),
            total_matched=len(matched),
        )
        db.add(history_entry)
        await db.flush()

    response_data = EligibilityCheckResponse(
        profile_summary=profile_summary,
        total_matched=len(matched),
        schemes=[MatchedScheme(**s) for s in matched],
    )

    # Return with cache header
    response = JSONResponse(content=response_data.model_dump(mode="json"))
    response.headers["X-Cache"] = "HIT" if cache_hit else "MISS"
    return response


# --- Scheme Listing ---

@router.get(
    "/schemes",
    response_model=SchemeListResponse,
    summary="List all schemes with filters and pagination",
)
async def list_schemes(
    state: Optional[str] = Query(None, description="Filter by state name"),
    category: Optional[str] = Query(None, description="Filter by category"),
    gender: Optional[str] = Query(None, description="Filter by gender_specific"),
    scheme_type: Optional[str] = Query(None, description="Filter by scheme_type (central/state)"),
    is_active: bool = Query(True, description="Filter by active status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max records to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    List schemes with optional filtering and pagination.

    Supports filtering by state, category, gender, scheme type, and active status.
    """
    query = (
        select(Scheme)
        .where(Scheme.is_active == is_active)
        .options(selectinload(Scheme.criteria))
        .options(selectinload(Scheme.states))
    )

    if category:
        query = query.where(Scheme.category == category)
    if gender:
        query = query.where(Scheme.gender_specific == gender)
    if scheme_type:
        query = query.where(Scheme.scheme_type == scheme_type)
    if state:
        query = query.join(Scheme.states).where(State.name.ilike(f"%{state}%"))

    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    query = query.offset(skip).limit(limit).order_by(Scheme.id)
    result = await db.execute(query)
    schemes = result.scalars().unique().all()

    return SchemeListResponse(
        total=total,
        schemes=[_scheme_to_response(s) for s in schemes],
        skip=skip,
        limit=limit,
    )


# --- Scheme Search ---

@router.get(
    "/schemes/search",
    response_model=SchemeListResponse,
    summary="Search schemes by keyword",
)
async def search_schemes(
    q: str = Query(..., min_length=2, description="Search query"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Full-text search across scheme name, description, ministry, and category.
    """
    search_pattern = f"%{q}%"

    query = (
        select(Scheme)
        .where(Scheme.is_active == True)
        .where(
            or_(
                Scheme.name.ilike(search_pattern),
                Scheme.description.ilike(search_pattern),
                Scheme.ministry.ilike(search_pattern),
                Scheme.category.ilike(search_pattern),
            )
        )
        .options(selectinload(Scheme.criteria))
        .options(selectinload(Scheme.states))
    )

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.offset(skip).limit(limit).order_by(Scheme.name)
    result = await db.execute(query)
    schemes = result.scalars().unique().all()

    return SchemeListResponse(
        total=total,
        schemes=[_scheme_to_response(s) for s in schemes],
        skip=skip,
        limit=limit,
    )


# --- Single Scheme Detail ---

@router.get(
    "/schemes/{scheme_id}",
    response_model=SchemeResponse,
    summary="Get full details for a single scheme",
)
async def get_scheme(
    scheme_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve complete scheme details including eligibility criteria and states.
    """
    result = await db.execute(
        select(Scheme)
        .where(Scheme.id == scheme_id)
        .options(selectinload(Scheme.criteria))
        .options(selectinload(Scheme.states))
    )
    scheme = result.scalar_one_or_none()

    if not scheme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scheme with id {scheme_id} not found",
        )

    return _scheme_to_response(scheme)


# --- Helper ---

def _scheme_to_response(scheme: Scheme) -> SchemeResponse:
    """Convert a Scheme ORM object to a SchemeResponse, extracting state names."""
    return SchemeResponse(
        id=scheme.id,
        name=scheme.name,
        description=scheme.description,
        ministry=scheme.ministry,
        scheme_type=scheme.scheme_type,
        benefit_amount=scheme.benefit_amount,
        benefit_description=scheme.benefit_description,
        apply_link=scheme.apply_link,
        category=scheme.category,
        gender_specific=scheme.gender_specific,
        is_active=scheme.is_active,
        created_at=scheme.created_at,
        criteria=scheme.criteria,
        states=[s.name for s in scheme.states],
    )
