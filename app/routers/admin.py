"""
Admin router for scheme management.

All routes require admin role. Provides CRUD for schemes and
individual eligibility criteria without touching the database directly.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import require_admin
from app.database import get_db
from app.models.eligibility import EligibilityCriteria
from app.models.scheme import Scheme, State, scheme_state
from app.models.user import User
from app.schemas.scheme import (
    EligibilityCriteriaCreate,
    EligibilityCriteriaResponse,
    SchemeCreate,
    SchemeResponse,
    SchemeUpdate,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


# --- Scheme CRUD ---

@router.post(
    "/schemes",
    response_model=SchemeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new scheme with criteria",
)
async def create_scheme(
    scheme_data: SchemeCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """
    Create a new scheme with optional eligibility criteria and state links.
    """
    scheme = Scheme(
        name=scheme_data.name,
        description=scheme_data.description,
        ministry=scheme_data.ministry,
        scheme_type=scheme_data.scheme_type,
        benefit_amount=scheme_data.benefit_amount,
        benefit_description=scheme_data.benefit_description,
        apply_link=scheme_data.apply_link,
        category=scheme_data.category,
        gender_specific=scheme_data.gender_specific,
        is_active=True,
    )
    db.add(scheme)
    await db.flush()

    # Add criteria
    for c in scheme_data.criteria:
        criterion = EligibilityCriteria(
            scheme_id=scheme.id,
            field=c.field,
            operator=c.operator,
            value=c.value,
            description=c.description,
        )
        db.add(criterion)

    # Link states by code
    if scheme_data.state_codes:
        result = await db.execute(
            select(State).where(State.code.in_(scheme_data.state_codes))
        )
        states = result.scalars().all()
        for state in states:
            await db.execute(
                scheme_state.insert().values(
                    scheme_id=scheme.id,
                    state_id=state.id,
                )
            )

    await db.flush()

    # Reload with relationships
    result = await db.execute(
        select(Scheme)
        .where(Scheme.id == scheme.id)
        .options(selectinload(Scheme.criteria))
        .options(selectinload(Scheme.states))
    )
    scheme = result.scalar_one()

    return _admin_scheme_response(scheme)


@router.put(
    "/schemes/{scheme_id}",
    response_model=SchemeResponse,
    summary="Update scheme details",
)
async def update_scheme(
    scheme_id: int,
    update_data: SchemeUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """
    Update an existing scheme's metadata. Only provided fields are changed.
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

    # Apply partial update
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(scheme, field, value)

    await db.flush()

    return _admin_scheme_response(scheme)


@router.delete(
    "/schemes/{scheme_id}",
    status_code=status.HTTP_200_OK,
    summary="Soft-delete a scheme",
)
async def delete_scheme(
    scheme_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """
    Soft-delete a scheme by setting is_active to False.
    The data remains in the database for audit purposes.
    """
    result = await db.execute(select(Scheme).where(Scheme.id == scheme_id))
    scheme = result.scalar_one_or_none()

    if not scheme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scheme with id {scheme_id} not found",
        )

    scheme.is_active = False
    await db.flush()

    return {"message": f"Scheme '{scheme.name}' deactivated", "id": scheme_id}


# --- Criteria Management ---

@router.post(
    "/schemes/{scheme_id}/criteria",
    response_model=EligibilityCriteriaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a criterion to a scheme",
)
async def add_criterion(
    scheme_id: int,
    criterion_data: EligibilityCriteriaCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """
    Add a new eligibility criterion to an existing scheme.
    """
    # Verify scheme exists
    result = await db.execute(select(Scheme).where(Scheme.id == scheme_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scheme with id {scheme_id} not found",
        )

    criterion = EligibilityCriteria(
        scheme_id=scheme_id,
        field=criterion_data.field,
        operator=criterion_data.operator,
        value=criterion_data.value,
        description=criterion_data.description,
    )
    db.add(criterion)
    await db.flush()
    await db.refresh(criterion)

    return criterion


@router.delete(
    "/criteria/{criterion_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove a criterion",
)
async def delete_criterion(
    criterion_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """
    Permanently delete an eligibility criterion.
    """
    result = await db.execute(
        select(EligibilityCriteria).where(EligibilityCriteria.id == criterion_id)
    )
    criterion = result.scalar_one_or_none()

    if not criterion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Criterion with id {criterion_id} not found",
        )

    await db.delete(criterion)
    await db.flush()

    return {"message": "Criterion deleted", "id": criterion_id}


# --- Cache Management ---

@router.delete(
    "/cache/clear",
    status_code=status.HTTP_200_OK,
    summary="Flush eligibility cache",
)
async def clear_cache(
    request: Request,
    _admin: User = Depends(require_admin),
):
    """
    Flush all cached eligibility results.
    Use after bulk scheme updates to ensure fresh results.
    """
    from app.services.cache_service import CacheService

    cache = CacheService(request.app.state.redis)
    deleted = await cache.flush_all()

    return {"message": f"Cache cleared: {deleted} entries removed"}


# --- Helper ---

def _admin_scheme_response(scheme: Scheme) -> SchemeResponse:
    """Convert Scheme ORM object to response with state names."""
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
