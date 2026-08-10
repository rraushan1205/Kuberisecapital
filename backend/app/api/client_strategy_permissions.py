"""
Client API endpoints for strategy permission and assignment management.

Users can:
- Grant/revoke admin trading permission with risk limits
- View their own strategy assignments
- See strategies available to them
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.models.domain import (
    StrategyDefinition,
    User,
    UserStrategyAssignment,
    UserStrategyPermission,
)
from app.schemas.strategy_management import (
    StrategyDefinitionListResponse,
    UserStrategyAssignmentDetailResponse,
    UserStrategyPermissionResponse,
    UserStrategyPermissionUpdate,
)

router = APIRouter(prefix="/client/strategies", tags=["client-strategies"])


# ============================================================================
# User Permission Management
# ============================================================================

@router.get("/permissions/me", response_model=UserStrategyPermissionResponse | None)
async def get_my_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get current user's strategy permission settings.
    
    Returns None if user hasn't set up permissions yet.
    """
    result = await db.execute(
        select(UserStrategyPermission).where(UserStrategyPermission.user_id == current_user.id)
    )
    permission = result.scalar_one_or_none()
    
    return permission


@router.put("/permissions/me", response_model=UserStrategyPermissionResponse)
async def update_my_permissions(
    data: UserStrategyPermissionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update current user's strategy permission settings.
    
    Users control:
    - Whether to allow admin trading on their behalf
    - Maximum daily loss limit (safety threshold)
    - Maximum position size (risk control)
    
    These settings give users control over automated trading risk.
    """
    # Get or create permission
    result = await db.execute(
        select(UserStrategyPermission).where(UserStrategyPermission.user_id == current_user.id)
    )
    permission = result.scalar_one_or_none()
    
    if not permission:
        permission = UserStrategyPermission(user_id=current_user.id)
        db.add(permission)
    
    # Update fields
    permission.allow_admin_trading = data.allow_admin_trading
    permission.max_daily_loss = data.max_daily_loss
    permission.max_position_size = data.max_position_size
    
    await db.commit()
    await db.refresh(permission)
    
    return permission


# ============================================================================
# View Strategy Assignments
# ============================================================================

@router.get("/assignments/me", response_model=list[UserStrategyAssignmentDetailResponse])
async def get_my_assignments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all strategies assigned to the current user.
    
    Returns assignments with strategy details, configuration, and status.
    """
    result = await db.execute(
        select(
            UserStrategyAssignment,
            StrategyDefinition.name.label("strategy_name"),
            StrategyDefinition.description.label("strategy_description"),
        )
        .join(StrategyDefinition, UserStrategyAssignment.strategy_def_id == StrategyDefinition.id)
        .where(UserStrategyAssignment.user_id == current_user.id)
        .order_by(UserStrategyAssignment.assigned_at.desc())
    )
    rows = result.all()
    
    # Build response with strategy details
    assignments = []
    for assignment, strategy_name, strategy_description in rows:
        assignment_dict = {
            "id": assignment.id,
            "user_id": assignment.user_id,
            "strategy_def_id": assignment.strategy_def_id,
            "config": assignment.config,
            "assigned_by": assignment.assigned_by,
            "assigned_at": assignment.assigned_at,
            "is_active": assignment.is_active,
            "started_at": assignment.started_at,
            "stopped_at": assignment.stopped_at,
            "strategy_name": strategy_name,
            "strategy_description": strategy_description,
        }
        assignments.append(UserStrategyAssignmentDetailResponse(**assignment_dict))
    
    return assignments


@router.get("/assignments/me/{assignment_id}", response_model=UserStrategyAssignmentDetailResponse)
async def get_my_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get details of a specific assignment belonging to current user.
    """
    result = await db.execute(
        select(
            UserStrategyAssignment,
            StrategyDefinition.name.label("strategy_name"),
            StrategyDefinition.description.label("strategy_description"),
        )
        .join(StrategyDefinition, UserStrategyAssignment.strategy_def_id == StrategyDefinition.id)
        .where(
            UserStrategyAssignment.id == assignment_id,
            UserStrategyAssignment.user_id == current_user.id,
        )
    )
    row = result.one_or_none()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found or does not belong to you",
        )
    
    assignment, strategy_name, strategy_description = row
    
    return UserStrategyAssignmentDetailResponse(
        id=assignment.id,
        user_id=assignment.user_id,
        strategy_def_id=assignment.strategy_def_id,
        config=assignment.config,
        assigned_by=assignment.assigned_by,
        assigned_at=assignment.assigned_at,
        is_active=assignment.is_active,
        started_at=assignment.started_at,
        stopped_at=assignment.stopped_at,
        strategy_name=strategy_name,
        strategy_description=strategy_description,
    )


# ============================================================================
# View Available Strategies (Read-only)
# ============================================================================

@router.get("/available", response_model=list[StrategyDefinitionListResponse])
async def get_available_strategies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of all active strategies that could be assigned.
    
    This is informational - users cannot self-assign strategies.
    Only admins can make assignments.
    """
    result = await db.execute(
        select(StrategyDefinition)
        .where(StrategyDefinition.is_active == True)
        .order_by(StrategyDefinition.name)
    )
    strategies = result.scalars().all()
    
    return strategies


@router.get("/available/{strategy_id}", response_model=StrategyDefinitionListResponse)
async def get_strategy_info(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get information about a specific strategy (without the code).
    
    Users can see strategy name, description, and config schema
    but not the actual implementation code.
    """
    result = await db.execute(
        select(StrategyDefinition).where(
            StrategyDefinition.id == strategy_id,
            StrategyDefinition.is_active == True,
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found or not active",
        )
    
    return StrategyDefinitionListResponse(
        id=strategy.id,
        name=strategy.name,
        description=strategy.description,
        is_active=strategy.is_active,
        created_at=strategy.created_at,
    )
