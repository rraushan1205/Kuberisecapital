"""
Admin API endpoints for strategy management.

Admins can:
- Upload and manage strategy definitions
- Assign strategies to users (individually or in bulk)
- Start/stop user strategies
- View usage statistics
- Manage user permissions (with user consent)
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_admin_user, get_db
from app.models.domain import (
    StrategyDefinition,
    User,
    UserStrategyAssignment,
    UserStrategyPermission,
)
from app.schemas.strategy_management import (
    BulkAssignmentRequest,
    BulkAssignmentResponse,
    StrategyControlRequest,
    StrategyControlResponse,
    StrategyDefinitionCreate,
    StrategyDefinitionListResponse,
    StrategyDefinitionResponse,
    StrategyDefinitionUpdate,
    StrategyUsageStats,
    UserStrategyAssignmentCreate,
    UserStrategyAssignmentDetailResponse,
    UserStrategyAssignmentResponse,
    UserStrategyAssignmentUpdate,
    UserStrategyOverview,
    UserStrategyPermissionResponse,
    UserStrategyPermissionUpdate,
)

router = APIRouter(prefix="/admin/strategies", tags=["admin-strategies"])


# ============================================================================
# Strategy Definition Management
# ============================================================================

@router.post("/definitions", response_model=StrategyDefinitionResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy_definition(
    data: StrategyDefinitionCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Upload a new strategy definition.
    
    Admin uploads Python strategy code along with a JSON schema that defines
    the configuration parameters users can customize.
    """
    try:
        strategy_def = StrategyDefinition(
            name=data.name,
            description=data.description,
            code=data.code,
            config_schema=data.config_schema,
            created_by=admin.id,
        )
        db.add(strategy_def)
        await db.commit()
        await db.refresh(strategy_def)
        return strategy_def
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Strategy with name '{data.name}' already exists",
        )


@router.get("/definitions", response_model=list[StrategyDefinitionListResponse])
async def list_strategy_definitions(
    active_only: bool = Query(False, description="Filter to active strategies only"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    List all strategy definitions.
    
    Returns a paginated list with summary information.
    """
    query = select(StrategyDefinition).order_by(StrategyDefinition.created_at.desc())
    
    if active_only:
        query = query.where(StrategyDefinition.is_active == True)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    strategies = result.scalars().all()
    
    return strategies


@router.get("/definitions/{strategy_id}", response_model=StrategyDefinitionResponse)
async def get_strategy_definition(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Get full details of a strategy definition including code.
    """
    result = await db.execute(
        select(StrategyDefinition).where(StrategyDefinition.id == strategy_id)
    )
    strategy_def = result.scalar_one_or_none()
    
    if not strategy_def:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy definition {strategy_id} not found",
        )
    
    return strategy_def


@router.put("/definitions/{strategy_id}", response_model=StrategyDefinitionResponse)
async def update_strategy_definition(
    strategy_id: int,
    data: StrategyDefinitionUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Update a strategy definition.
    
    Can update name, description, code, config schema, or active status.
    Use caution when updating code for strategies with active assignments.
    """
    result = await db.execute(
        select(StrategyDefinition).where(StrategyDefinition.id == strategy_id)
    )
    strategy_def = result.scalar_one_or_none()
    
    if not strategy_def:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy definition {strategy_id} not found",
        )
    
    # Update fields if provided
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(strategy_def, field, value)
    
    try:
        await db.commit()
        await db.refresh(strategy_def)
        return strategy_def
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Strategy with name '{data.name}' already exists",
        )


@router.delete("/definitions/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_strategy_definition(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Deactivate a strategy definition (soft delete).
    
    Sets is_active=False. Existing assignments remain but strategy cannot
    be assigned to new users. Does not stop running strategies.
    """
    result = await db.execute(
        select(StrategyDefinition).where(StrategyDefinition.id == strategy_id)
    )
    strategy_def = result.scalar_one_or_none()
    
    if not strategy_def:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy definition {strategy_id} not found",
        )
    
    strategy_def.is_active = False
    await db.commit()


# ============================================================================
# User Strategy Assignment Management
# ============================================================================

@router.post("/assignments", response_model=UserStrategyAssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    data: UserStrategyAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Assign a strategy to a user.
    
    Prerequisites:
    - User must have granted admin trading permission
    - Strategy must be active
    - User must not already have this strategy assigned
    """
    # Check if user exists and has permission
    user_result = await db.execute(
        select(User, UserStrategyPermission)
        .outerjoin(UserStrategyPermission, User.id == UserStrategyPermission.user_id)
        .where(User.id == data.user_id)
    )
    user_row = user_result.one_or_none()
    
    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {data.user_id} not found",
        )
    
    user, permission = user_row
    
    if not permission or not permission.allow_admin_trading:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User {data.user_id} has not granted admin trading permission",
        )
    
    # Check if strategy exists and is active
    strategy_result = await db.execute(
        select(StrategyDefinition).where(StrategyDefinition.id == data.strategy_def_id)
    )
    strategy_def = strategy_result.scalar_one_or_none()
    
    if not strategy_def:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy definition {data.strategy_def_id} not found",
        )
    
    if not strategy_def.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Strategy '{strategy_def.name}' is not active",
        )
    
    # TODO: Validate config against strategy's config_schema
    
    # Create assignment
    try:
        assignment = UserStrategyAssignment(
            user_id=data.user_id,
            strategy_def_id=data.strategy_def_id,
            config=data.config,
            assigned_by=admin.id,
        )
        db.add(assignment)
        await db.commit()
        await db.refresh(assignment)
        return assignment
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User {data.user_id} already has strategy {data.strategy_def_id} assigned",
        )


@router.post("/assignments/bulk", response_model=BulkAssignmentResponse)
async def bulk_assign_strategy(
    data: BulkAssignmentRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Assign a strategy to multiple users at once.
    
    Returns success/failure counts and error details for failed assignments.
    """
    # Check if strategy exists and is active
    strategy_result = await db.execute(
        select(StrategyDefinition).where(StrategyDefinition.id == data.strategy_def_id)
    )
    strategy_def = strategy_result.scalar_one_or_none()
    
    if not strategy_def:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy definition {data.strategy_def_id} not found",
        )
    
    if not strategy_def.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Strategy '{strategy_def.name}' is not active",
        )
    
    # Fetch all users with permissions
    users_result = await db.execute(
        select(User, UserStrategyPermission)
        .outerjoin(UserStrategyPermission, User.id == UserStrategyPermission.user_id)
        .where(User.id.in_(data.user_ids))
    )
    users_data = users_result.all()
    
    successful = 0
    failed = 0
    errors = []
    
    for user, permission in users_data:
        try:
            # Check permission
            if not permission or not permission.allow_admin_trading:
                failed += 1
                errors.append({
                    "user_id": str(user.id),
                    "error": "User has not granted admin trading permission",
                })
                continue
            
            # Create assignment
            assignment = UserStrategyAssignment(
                user_id=user.id,
                strategy_def_id=data.strategy_def_id,
                config=data.config,
                assigned_by=admin.id,
            )
            db.add(assignment)
            await db.flush()  # Flush to catch integrity errors per user
            successful += 1
        except IntegrityError:
            await db.rollback()
            failed += 1
            errors.append({
                "user_id": str(user.id),
                "error": "User already has this strategy assigned",
            })
        except Exception as e:
            await db.rollback()
            failed += 1
            errors.append({
                "user_id": str(user.id),
                "error": str(e),
            })
    
    # Commit all successful assignments
    if successful > 0:
        await db.commit()
    
    # Check for users not found
    found_user_ids = {user.id for user, _ in users_data}
    for user_id in data.user_ids:
        if user_id not in found_user_ids:
            failed += 1
            errors.append({
                "user_id": str(user_id),
                "error": "User not found",
            })
    
    return BulkAssignmentResponse(
        total_requested=len(data.user_ids),
        successful=successful,
        failed=failed,
        errors=errors,
    )


@router.get("/assignments", response_model=list[UserStrategyAssignmentDetailResponse])
async def list_assignments(
    user_id: UUID | None = Query(None, description="Filter by user"),
    strategy_def_id: int | None = Query(None, description="Filter by strategy"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    List all strategy assignments with filters.
    
    Returns assignments with strategy name and description for display.
    """
    query = (
        select(
            UserStrategyAssignment,
            StrategyDefinition.name.label("strategy_name"),
            StrategyDefinition.description.label("strategy_description"),
        )
        .join(StrategyDefinition, UserStrategyAssignment.strategy_def_id == StrategyDefinition.id)
        .order_by(UserStrategyAssignment.assigned_at.desc())
    )
    
    if user_id:
        query = query.where(UserStrategyAssignment.user_id == user_id)
    
    if strategy_def_id:
        query = query.where(UserStrategyAssignment.strategy_def_id == strategy_def_id)
    
    if is_active is not None:
        query = query.where(UserStrategyAssignment.is_active == is_active)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
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


@router.get("/assignments/{assignment_id}", response_model=UserStrategyAssignmentDetailResponse)
async def get_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Get details of a specific assignment.
    """
    result = await db.execute(
        select(
            UserStrategyAssignment,
            StrategyDefinition.name.label("strategy_name"),
            StrategyDefinition.description.label("strategy_description"),
        )
        .join(StrategyDefinition, UserStrategyAssignment.strategy_def_id == StrategyDefinition.id)
        .where(UserStrategyAssignment.id == assignment_id)
    )
    row = result.one_or_none()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment {assignment_id} not found",
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


@router.put("/assignments/{assignment_id}", response_model=UserStrategyAssignmentResponse)
async def update_assignment(
    assignment_id: int,
    data: UserStrategyAssignmentUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Update an assignment's configuration or active status.
    
    Note: Use the start/stop endpoints to control strategy execution.
    This endpoint is for updating configuration.
    """
    result = await db.execute(
        select(UserStrategyAssignment).where(UserStrategyAssignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment {assignment_id} not found",
        )
    
    # Update fields if provided
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(assignment, field, value)
    
    await db.commit()
    await db.refresh(assignment)
    return assignment


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Remove a strategy assignment.
    
    If the strategy is currently running, it should be stopped first.
    """
    result = await db.execute(
        select(UserStrategyAssignment).where(UserStrategyAssignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment {assignment_id} not found",
        )
    
    if assignment.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete active assignment. Stop the strategy first.",
        )
    
    await db.delete(assignment)
    await db.commit()


# ============================================================================
# Strategy Control (Start/Stop)
# ============================================================================

@router.post("/assignments/{assignment_id}/start", response_model=StrategyControlResponse)
async def start_strategy(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Start a user's assigned strategy.
    
    Sets is_active=True and records started_at timestamp.
    """
    result = await db.execute(
        select(UserStrategyAssignment, StrategyDefinition)
        .join(StrategyDefinition, UserStrategyAssignment.strategy_def_id == StrategyDefinition.id)
        .where(UserStrategyAssignment.id == assignment_id)
    )
    row = result.one_or_none()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment {assignment_id} not found",
        )
    
    assignment, strategy_def = row
    
    if assignment.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy is already running",
        )
    
    assignment.is_active = True
    assignment.started_at = datetime.utcnow()
    assignment.stopped_at = None
    
    await db.commit()
    
    return StrategyControlResponse(
        assignment_id=assignment.id,
        user_id=assignment.user_id,
        strategy_name=strategy_def.name,
        is_active=True,
        message=f"Strategy '{strategy_def.name}' started for user",
    )


@router.post("/assignments/{assignment_id}/stop", response_model=StrategyControlResponse)
async def stop_strategy(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Stop a user's assigned strategy.
    
    Sets is_active=False and records stopped_at timestamp.
    """
    result = await db.execute(
        select(UserStrategyAssignment, StrategyDefinition)
        .join(StrategyDefinition, UserStrategyAssignment.strategy_def_id == StrategyDefinition.id)
        .where(UserStrategyAssignment.id == assignment_id)
    )
    row = result.one_or_none()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment {assignment_id} not found",
        )
    
    assignment, strategy_def = row
    
    if not assignment.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy is not running",
        )
    
    assignment.is_active = False
    assignment.stopped_at = datetime.utcnow()
    
    await db.commit()
    
    return StrategyControlResponse(
        assignment_id=assignment.id,
        user_id=assignment.user_id,
        strategy_name=strategy_def.name,
        is_active=False,
        message=f"Strategy '{strategy_def.name}' stopped for user",
    )


# ============================================================================
# Statistics and Monitoring
# ============================================================================

@router.get("/stats", response_model=list[StrategyUsageStats])
async def get_strategy_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Get usage statistics for all strategies.
    
    Shows total assignments, active, and inactive counts per strategy.
    """
    query = (
        select(
            StrategyDefinition.id.label("strategy_id"),
            StrategyDefinition.name.label("strategy_name"),
            func.count(UserStrategyAssignment.id).label("total_assignments"),
            func.sum(func.cast(UserStrategyAssignment.is_active, type_=int)).label("active_assignments"),
        )
        .outerjoin(UserStrategyAssignment, StrategyDefinition.id == UserStrategyAssignment.strategy_def_id)
        .group_by(StrategyDefinition.id, StrategyDefinition.name)
        .order_by(StrategyDefinition.name)
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    stats = []
    for strategy_id, strategy_name, total, active in rows:
        total = total or 0
        active = active or 0
        stats.append(
            StrategyUsageStats(
                strategy_id=strategy_id,
                strategy_name=strategy_name,
                total_assignments=total,
                active_assignments=active,
                inactive_assignments=total - active,
            )
        )
    
    return stats


@router.get("/users/overview", response_model=list[UserStrategyOverview])
async def get_user_strategy_overview(
    has_permission: bool | None = Query(None, description="Filter by permission status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Get overview of strategy assignments per user.
    
    Shows which users have permissions and how many strategies are assigned.
    """
    query = (
        select(
            User.id.label("user_id"),
            User.email.label("user_email"),
            User.full_name.label("user_full_name"),
            UserStrategyPermission.allow_admin_trading.label("has_permission"),
            func.count(UserStrategyAssignment.id).label("total_assignments"),
            func.sum(func.cast(UserStrategyAssignment.is_active, type_=int)).label("active_assignments"),
        )
        .outerjoin(UserStrategyPermission, User.id == UserStrategyPermission.user_id)
        .outerjoin(UserStrategyAssignment, User.id == UserStrategyAssignment.user_id)
        .group_by(
            User.id,
            User.email,
            User.full_name,
            UserStrategyPermission.allow_admin_trading,
        )
        .order_by(User.email)
    )
    
    if has_permission is not None:
        if has_permission:
            query = query.where(UserStrategyPermission.allow_admin_trading == True)
        else:
            query = query.where(
                (UserStrategyPermission.allow_admin_trading == False) |
                (UserStrategyPermission.allow_admin_trading.is_(None))
            )
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    rows = result.all()
    
    overview = []
    for user_id, email, full_name, has_perm, total, active in rows:
        total = total or 0
        active = active or 0
        overview.append(
            UserStrategyOverview(
                user_id=user_id,
                user_email=email,
                user_full_name=full_name,
                has_permission=has_perm or False,
                total_assignments=total,
                active_assignments=active,
            )
        )
    
    return overview


# ============================================================================
# User Permission Management (Admin View/Update)
# ============================================================================

@router.get("/users/{user_id}/permissions", response_model=UserStrategyPermissionResponse | None)
async def get_user_permission(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Get a user's strategy permission settings.
    
    Returns None if user hasn't set up permissions yet.
    """
    result = await db.execute(
        select(UserStrategyPermission).where(UserStrategyPermission.user_id == user_id)
    )
    permission = result.scalar_one_or_none()
    
    return permission


@router.put("/users/{user_id}/permissions", response_model=UserStrategyPermissionResponse)
async def update_user_permission(
    user_id: UUID,
    data: UserStrategyPermissionUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Update a user's strategy permission settings (admin override).
    
    This allows admin to adjust risk limits even after user has granted permission.
    Use with caution - normally users should control their own limits.
    """
    # Check if user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    
    # Get or create permission
    perm_result = await db.execute(
        select(UserStrategyPermission).where(UserStrategyPermission.user_id == user_id)
    )
    permission = perm_result.scalar_one_or_none()
    
    if not permission:
        permission = UserStrategyPermission(user_id=user_id)
        db.add(permission)
    
    # Update fields
    permission.allow_admin_trading = data.allow_admin_trading
    permission.max_daily_loss = data.max_daily_loss
    permission.max_position_size = data.max_position_size
    
    await db.commit()
    await db.refresh(permission)
    
    return permission
