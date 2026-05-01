"""
User profile and eligibility history router.

Endpoints for saving/retrieving user profiles and viewing past
eligibility checks. All routes require authentication.
"""

import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user
from app.database import get_db
from app.models.profile import EligibilityHistory, UserProfile
from app.models.user import User
from app.schemas.profile import (
    EligibilityHistoryListResponse,
    EligibilityHistoryResponse,
    UserProfileCreate,
    UserProfileResponse,
)

router = APIRouter(tags=["User Profile & History"])


@router.post(
    "/profile",
    response_model=UserProfileResponse,
    summary="Save or update user profile",
)
async def save_profile(
    profile_data: UserProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create or update the authenticated user's saved profile.

    If a profile already exists, it is updated. Otherwise a new one is created.
    """
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    update_dict = profile_data.model_dump()

    if profile:
        for field, value in update_dict.items():
            setattr(profile, field, value)
    else:
        profile = UserProfile(user_id=current_user.id, **update_dict)
        db.add(profile)

    await db.flush()
    await db.refresh(profile)

    return profile


@router.get(
    "/profile",
    response_model=UserProfileResponse,
    summary="Get saved user profile",
)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve the authenticated user's saved profile.

    Returns 404 if no profile has been saved yet.
    """
    from fastapi import HTTPException, status

    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No saved profile found. Use POST /profile to create one.",
        )

    return profile


@router.get(
    "/eligibility/history",
    response_model=EligibilityHistoryListResponse,
    summary="View past eligibility checks",
)
async def get_eligibility_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve paginated history of past eligibility checks.

    Each entry includes the profile snapshot and results at the time of the check.
    """
    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(EligibilityHistory).where(
            EligibilityHistory.user_id == current_user.id
        )
    )
    total = count_result.scalar()

    # Fetch page
    result = await db.execute(
        select(EligibilityHistory)
        .where(EligibilityHistory.user_id == current_user.id)
        .order_by(EligibilityHistory.checked_at.desc())
        .offset(skip)
        .limit(limit)
    )
    entries = result.scalars().all()

    history = []
    for entry in entries:
        history.append(
            EligibilityHistoryResponse(
                id=entry.id,
                profile_snapshot=json.loads(entry.profile_snapshot),
                results_snapshot=json.loads(entry.results_snapshot),
                total_matched=entry.total_matched,
                checked_at=entry.checked_at,
            )
        )

    return EligibilityHistoryListResponse(
        total=total,
        history=history,
        skip=skip,
        limit=limit,
    )
