from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile, status
from sqlalchemy import func, select

from app.api.dependencies import DbSession, SuperAdmin
from app.core.config import get_settings
from app.core.logging import log_admin_action, log_auth_event
from app.core.security import create_access_token, verify_password
from app.middleware.rate_limit import get_limiter
from app.models.domain import (
    AccountStatus,
    Announcement,
    BrokerConnection,
    BrokerStatus,
    ExecutionAction,
    ExecutionLog,
    Strategy,
    StrategyStatus,
    SubscriptionPlan,
    SubscriptionRequest,
    SubscriptionRequestStatus,
    SubscriptionStatus,
    User,
    UserRole,
)
from app.schemas.admin import (
    AdminAuthOutput,
    AdminLoginInput,
    AdminRefreshInput,
    AdminSessionOutput,
    AnnouncementInput,
    AnnouncementOutput,
    BrokerAccountOutput,
    BrokerAccountsListResponse,
    DashboardStatsOutput,
    ExecutionLogOutput,
    StrategyOutput,
    UpdateUserSubscriptionInput,
    UserDetailOutput,
    UserOutput,
)
from app.schemas.subscription import (
    ApproveSubscriptionRequestInput,
    RejectSubscriptionRequestInput,
    SubscriptionPlanInput,
    SubscriptionPlanOutput,
    SubscriptionRequestWithDetailsOutput,
)
from app.services.trading_engine import dispatch_engine_command
from app.services.refresh_sessions import (
    create_refresh_session,
    revoke_refresh_session,
    rotate_refresh_session,
)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
limiter = get_limiter()


@router.post("/auth/login", response_model=AdminAuthOutput)
@limiter.limit("5/minute")
def login_admin(payload: AdminLoginInput, request: Request, db: DbSession) -> AdminAuthOutput:
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))

    if user is None or not verify_password(payload.password, user.password_hash):
        log_auth_event(
            event_type="admin_login",
            success=False,
            email=payload.email,
            reason="Invalid credentials",
            ip_address=request.client.host if request.client else None
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    if user.role != UserRole.SUPER_ADMIN:
        log_auth_event(
            event_type="admin_login",
            success=False,
            email=user.email,
            user_id=str(user.id),
            reason="Not a super admin",
            ip_address=request.client.host if request.client else None
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super Admin access is required.")

    user.last_login_at = datetime.now(UTC)
    refresh_session, raw_refresh_token = create_refresh_session(db, user)
    db.commit()
    access_token = create_access_token(str(user.id), user.role.value, refresh_session.id)

    log_auth_event(
        event_type="admin_login",
        success=True,
        email=user.email,
        user_id=str(user.id),
        ip_address=request.client.host if request.client else None
    )

    return AdminAuthOutput(
        user_id=user.id,
        email=user.email,
        role=user.role,
        access_token=access_token,
        refresh_token=raw_refresh_token,
    )


@router.post("/auth/refresh", response_model=AdminAuthOutput)
def refresh_admin_session(payload: AdminRefreshInput, db: DbSession) -> AdminAuthOutput:
    user, refresh_session, raw_refresh_token = rotate_refresh_session(db, payload.refresh_token, UserRole.SUPER_ADMIN)
    access_token = create_access_token(str(user.id), user.role.value, refresh_session.id)
    return AdminAuthOutput(
        user_id=user.id,
        email=user.email,
        role=user.role,
        access_token=access_token,
        refresh_token=raw_refresh_token,
    )


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_admin(payload: AdminRefreshInput, db: DbSession) -> Response:
    revoke_refresh_session(db, payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/auth/session", response_model=AdminSessionOutput)
def get_admin_session(admin: SuperAdmin) -> AdminSessionOutput:
    return AdminSessionOutput(user_id=admin.id, email=admin.email, role=admin.role)


@router.get("/dashboard", response_model=DashboardStatsOutput)
def get_dashboard_stats(_: SuperAdmin, db: DbSession) -> DashboardStatsOutput:
    """
    Get admin dashboard statistics.
    Returns counts for key metrics across the platform.
    """
    total_users = db.scalar(select(func.count()).select_from(User).where(User.role == UserRole.USER)) or 0
    pending_registrations = db.scalar(
        select(func.count())
        .select_from(User)
        .where(User.account_status == AccountStatus.PENDING, User.role == UserRole.USER)
    ) or 0
    active_subscriptions = db.scalar(
        select(func.count())
        .select_from(User)
        .where(User.subscription_status == SubscriptionStatus.ACTIVE, User.role == UserRole.USER)
    ) or 0
    active_strategies = db.scalar(
        select(func.count())
        .select_from(Strategy)
        .where(Strategy.status == StrategyStatus.RUNNING)
    ) or 0
    total_execution_logs = db.scalar(select(func.count()).select_from(ExecutionLog)) or 0
    
    return DashboardStatsOutput(
        total_users=total_users,
        pending_registrations=pending_registrations,
        active_subscriptions=active_subscriptions,
        active_strategies=active_strategies,
        total_execution_logs=total_execution_logs,
    )


@router.get("/users", response_model=list[UserOutput])
def list_users(_: SuperAdmin, db: DbSession) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())))


@router.get("/users/{user_id}", response_model=UserDetailOutput)
def get_user_detail(user_id: UUID, _: SuperAdmin, db: DbSession) -> UserDetailOutput:
    """
    Get detailed information about a specific user including subscription details.
    """
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    
    # Get current plan details
    current_plan = None
    if user.current_plan_id:
        current_plan = db.get(SubscriptionPlan, user.current_plan_id)
    
    # Get pending subscription request
    pending_request_statement = select(SubscriptionRequest, SubscriptionPlan).join(
        SubscriptionPlan, SubscriptionRequest.plan_id == SubscriptionPlan.id
    ).where(
        SubscriptionRequest.user_id == user_id,
        SubscriptionRequest.status == SubscriptionRequestStatus.PENDING
    ).order_by(SubscriptionRequest.requested_at.desc())
    
    pending_request_result = db.execute(pending_request_statement).first()
    pending_request_id = None
    pending_request_plan_tier = None
    if pending_request_result:
        request, plan = pending_request_result
        pending_request_id = request.id
        pending_request_plan_tier = plan.tier.value
    
    return UserDetailOutput(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        email_verified=user.email_verified,
        account_status=user.account_status,
        subscription_status=user.subscription_status,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        current_plan_id=user.current_plan_id,
        current_plan_tier=current_plan.tier.value if current_plan else None,
        current_plan_capital=current_plan.capital if current_plan else None,
        current_plan_nifty_lots=current_plan.nifty_lots if current_plan else None,
        current_plan_sensex_lots=current_plan.sensex_lots if current_plan else None,
        current_plan_bank_nifty_lots=current_plan.bank_nifty_lots if current_plan else None,
        pending_request_id=pending_request_id,
        pending_request_plan_tier=pending_request_plan_tier,
    )


@router.put("/users/{user_id}/subscription", response_model=UserDetailOutput)
def update_user_subscription(
    user_id: UUID,
    payload: UpdateUserSubscriptionInput,
    admin: SuperAdmin,
    db: DbSession
) -> UserDetailOutput:
    """
    Update a user's subscription plan directly.
    Super admin can change or assign subscription plans without request approval flow.
    """
    user = db.get(User, user_id)
    if user is None or user.role != UserRole.USER:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    
    plan = db.get(SubscriptionPlan, payload.plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription plan not found.")
    
    if not plan.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign an inactive subscription plan."
        )
    
    # Update user's subscription
    old_plan_id = user.current_plan_id
    user.current_plan_id = plan.id
    user.subscription_status = SubscriptionStatus.ACTIVE
    
    # Create a log entry in subscription requests for audit trail
    request = SubscriptionRequest(
        user_id=user_id,
        plan_id=plan.id,
        status=SubscriptionRequestStatus.APPROVED,
        requested_at=datetime.now(UTC),
        reviewed_at=datetime.now(UTC),
        reviewed_by_id=admin.id,
        notes=f"Direct subscription update by admin. {payload.notes or ''}".strip()
    )
    db.add(request)
    
    db.commit()
    db.refresh(user)
    
    # Return updated user detail
    return get_user_detail(user_id, admin, db)


@router.get("/pending-registrations", response_model=list[UserOutput])
def list_pending_registrations(_: SuperAdmin, db: DbSession) -> list[User]:
    statement = select(User).where(User.account_status == AccountStatus.PENDING).order_by(User.created_at.asc())
    return list(db.scalars(statement))


@router.post("/users/{user_id}/approve", response_model=UserOutput)
def approve_user_account(user_id: UUID, admin: SuperAdmin, db: DbSession) -> User:
    """
    Approve a pending user registration.
    Sets account_status to APPROVED and allows the user to login.
    """
    user = db.get(User, user_id)
    if user is None or user.role != UserRole.USER:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account was not found.")

    if user.account_status == AccountStatus.APPROVED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User account is already approved.")

    user.account_status = AccountStatus.APPROVED
    db.commit()
    db.refresh(user)

    log_admin_action(
        action="approve_user",
        admin_id=str(admin.id),
        target_id=str(user.id),
        target_type="user",
        details={"email": user.email}
    )

    return user


@router.post("/users/{user_id}/reject", response_model=UserOutput)
def reject_user_account(user_id: UUID, _: SuperAdmin, db: DbSession) -> User:
    """
    Reject a pending user registration.
    Sets account_status to REJECTED and prevents the user from logging in.
    """
    user = db.get(User, user_id)
    if user is None or user.role != UserRole.USER:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account was not found.")
    
    if user.account_status == AccountStatus.REJECTED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User account is already rejected.")
    
    user.account_status = AccountStatus.REJECTED
    db.commit()
    db.refresh(user)
    return user


@router.post("/subscriptions/{user_id}/approve", response_model=UserOutput)
def approve_subscription(user_id: UUID, _: SuperAdmin, db: DbSession) -> User:
    user = db.get(User, user_id)
    if user is None or user.role != UserRole.USER:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account was not found.")
    if not user.email_verified:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email verification is required before approval.")

    user.account_status = AccountStatus.APPROVED
    user.subscription_status = SubscriptionStatus.ACTIVE
    db.commit()
    db.refresh(user)
    return user


@router.get("/strategies", response_model=list[StrategyOutput])
def list_strategies(_: SuperAdmin, db: DbSession) -> list[Strategy]:
    return list(db.scalars(select(Strategy).order_by(Strategy.created_at.desc())))


@router.post("/strategies", response_model=StrategyOutput, status_code=status.HTTP_201_CREATED)
async def upload_strategy(
    _: SuperAdmin,
    db: DbSession,
    name: str = Form(min_length=1, max_length=160),
    script: UploadFile = File(),
) -> Strategy:
    if not script.filename or Path(script.filename).suffix.lower() != ".py":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Only Python strategy files are accepted.")
    existing_count = db.scalar(select(func.count()).select_from(Strategy)) or 0
    if existing_count >= 3:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The platform supports a maximum of three strategies.")
    existing_name = db.scalar(select(Strategy).where(Strategy.name == name.strip()))
    if existing_name is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A strategy with this name already exists.")

    contents = await script.read()
    if not contents:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="The strategy file is empty.")
    if len(contents) > 1_048_576:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Strategy files are limited to 1 MB.")

    # Validate Python syntax
    import ast
    try:
        ast.parse(contents.decode('utf-8'))
    except SyntaxError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid Python syntax: {str(e)}"
        )

    # Scan for dangerous code patterns
    content_str = contents.decode('utf-8')
    dangerous_patterns = [
        ("import os", "Operating system access"),
        ("import subprocess", "Subprocess execution"),
        ("eval(", "Code evaluation"),
        ("exec(", "Code execution"),
        ("__import__", "Dynamic imports"),
        ("open(", "File operations"),
        ("compile(", "Code compilation"),
    ]

    for pattern, description in dangerous_patterns:
        if pattern in content_str:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Forbidden code pattern detected: {description} ({pattern})"
            )

    storage_path = get_settings().strategy_storage_path
    storage_path.mkdir(parents=True, exist_ok=True)
    storage_key = f"{uuid4()}.py"
    destination = storage_path / storage_key
    destination.write_bytes(contents)

    strategy = Strategy(
        name=name.strip(),
        script_filename=Path(script.filename).name,
        script_storage_key=storage_key,
        uploaded_by_id=_.id,
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return strategy


async def update_strategy_execution(strategy_id: UUID, command: str, action: ExecutionAction, admin: User, db: DbSession) -> Strategy:
    strategy = db.get(Strategy, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy was not found.")
    await dispatch_engine_command(command, {"strategy_id": str(strategy.id)})
    strategy.status = StrategyStatus.RUNNING if action == ExecutionAction.STRATEGY_STARTED else StrategyStatus.STOPPED
    db.add(ExecutionLog(action=action, message=f"Strategy {strategy.name} {command} command accepted by the trading engine.", strategy_id=strategy.id, initiated_by_id=admin.id))
    db.commit()
    db.refresh(strategy)
    return strategy


@router.post("/strategies/{strategy_id}/start", response_model=StrategyOutput)
async def start_strategy(strategy_id: UUID, admin: SuperAdmin, db: DbSession) -> Strategy:
    return await update_strategy_execution(strategy_id, "start", ExecutionAction.STRATEGY_STARTED, admin, db)


@router.post("/strategies/{strategy_id}/stop", response_model=StrategyOutput)
async def stop_strategy(strategy_id: UUID, admin: SuperAdmin, db: DbSession) -> Strategy:
    return await update_strategy_execution(strategy_id, "stop", ExecutionAction.STRATEGY_STOPPED, admin, db)


@router.post("/force-square-off", status_code=status.HTTP_204_NO_CONTENT)
async def force_square_off(admin: SuperAdmin, db: DbSession) -> Response:
    await dispatch_engine_command("force-square-off", {})
    db.add(ExecutionLog(action=ExecutionAction.FORCE_SQUARE_OFF, message="Force square off command accepted by the trading engine.", initiated_by_id=admin.id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/logs", response_model=list[ExecutionLogOutput])
def list_execution_logs(_: SuperAdmin, db: DbSession) -> list[ExecutionLog]:
    return list(db.scalars(select(ExecutionLog).order_by(ExecutionLog.created_at.desc()).limit(200)))


@router.get("/announcements", response_model=list[AnnouncementOutput])
def list_announcements(_: SuperAdmin, db: DbSession) -> list[Announcement]:
    return list(db.scalars(select(Announcement).order_by(Announcement.created_at.desc())))


@router.post("/announcements", response_model=AnnouncementOutput, status_code=status.HTTP_201_CREATED)
def create_announcement(payload: AnnouncementInput, admin: SuperAdmin, db: DbSession) -> Announcement:
    announcement = Announcement(title=payload.title.strip(), message=payload.message.strip(), created_by_id=admin.id)
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement


@router.get("/subscription-requests", response_model=list[SubscriptionRequestWithDetailsOutput])
def list_subscription_requests(_: SuperAdmin, db: DbSession) -> list[SubscriptionRequestWithDetailsOutput]:
    """
    Get all subscription requests with user and plan details.
    Returns pending requests first, then recent approved/rejected.
    """
    statement = (
        select(SubscriptionRequest, User, SubscriptionPlan)
        .join(User, SubscriptionRequest.user_id == User.id)
        .join(SubscriptionPlan, SubscriptionRequest.plan_id == SubscriptionPlan.id)
        .order_by(
            # Pending first
            (SubscriptionRequest.status == SubscriptionRequestStatus.PENDING).desc(),
            # Then by most recent
            SubscriptionRequest.requested_at.desc()
        )
    )
    
    results = []
    for request, user, plan in db.execute(statement).all():
        # Get current plan info
        current_plan = None
        if user.current_plan_id:
            current_plan = db.get(SubscriptionPlan, user.current_plan_id)
        
        results.append(
            SubscriptionRequestWithDetailsOutput(
                id=request.id,
                user_id=user.id,
                user_email=user.email,
                user_full_name=user.full_name,
                plan_tier=plan.tier,
                plan_capital=plan.capital,
                current_plan_tier=current_plan.tier if current_plan else None,
                status=request.status,
                requested_at=request.requested_at,
                reviewed_at=request.reviewed_at,
                reviewed_by_id=request.reviewed_by_id,
                notes=request.notes,
            )
        )
    
    return results


@router.post("/subscription-requests/{request_id}/approve")
def approve_subscription_request(
    request_id: UUID,
    payload: ApproveSubscriptionRequestInput,
    admin: SuperAdmin,
    db: DbSession
) -> SubscriptionRequestWithDetailsOutput:
    """
    Approve a subscription request.
    Updates user's current plan and activates their subscription.
    """
    request = db.get(SubscriptionRequest, request_id)
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription request not found.")
    
    if request.status != SubscriptionRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request is already {request.status.value.lower()}."
        )
    
    # Get user and plan
    user = db.get(User, request.user_id)
    plan = db.get(SubscriptionPlan, request.plan_id)
    
    if user is None or plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User or plan not found.")
    
    # Update the request
    request.status = SubscriptionRequestStatus.APPROVED
    request.reviewed_at = datetime.now(UTC)
    request.reviewed_by_id = admin.id
    request.notes = payload.notes
    
    # Update user's subscription
    user.current_plan_id = plan.id
    user.subscription_status = SubscriptionStatus.ACTIVE
    
    db.commit()
    db.refresh(request)
    
    # Return detailed output
    current_plan = db.get(SubscriptionPlan, user.current_plan_id)
    return SubscriptionRequestWithDetailsOutput(
        id=request.id,
        user_id=user.id,
        user_email=user.email,
        user_full_name=user.full_name,
        plan_tier=plan.tier,
        plan_capital=plan.capital,
        current_plan_tier=current_plan.tier if current_plan else None,
        status=request.status,
        requested_at=request.requested_at,
        reviewed_at=request.reviewed_at,
        reviewed_by_id=request.reviewed_by_id,
        notes=request.notes,
    )


@router.get("/brokers/accounts", response_model=BrokerAccountsListResponse)
def list_broker_accounts(
    _: SuperAdmin,
    db: DbSession,
    skip: int = 0,
    limit: int = 20,
    provider: str | None = None,
    broker_status: str | None = None,
    user_id: UUID | None = None,
) -> BrokerAccountsListResponse:
    """
    List all broker accounts across the system with pagination and filtering.
    
    Super admins can view all broker connections with optional filters for
    provider, status, and user_id. Returns paginated results with connection
    details but excludes sensitive token data.
    
    Args:
        skip: Pagination offset (default: 0, must be >= 0)
        limit: Results per page (default: 20, max: 100)
        provider: Optional filter by broker provider (e.g., "fyers", "zerodha")
        status: Optional filter by connection status (e.g., "connected", "disconnected")
        user_id: Optional filter by user ID (UUID string)
    
    Returns:
        BrokerAccountsListResponse: Paginated list with total count
    
    Raises:
        HTTPException 400: If limit > 100 or skip < 0 or invalid filter values
        HTTPException 403: If not super admin (handled by dependency)
    """
    # Validate pagination parameters
    if skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="skip must be greater than or equal to 0."
        )
    
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit must be between 1 and 100."
        )
    
    # Build base query
    query = select(BrokerConnection)
    count_query = select(func.count()).select_from(BrokerConnection)
    
    # Apply filters
    if user_id is not None:
        query = query.where(BrokerConnection.user_id == user_id)
        count_query = count_query.where(BrokerConnection.user_id == user_id)
    
    if provider is not None:
        provider_stripped = provider.strip()
        if not provider_stripped:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="provider filter cannot be empty."
            )
        query = query.where(BrokerConnection.provider == provider_stripped)
        count_query = count_query.where(BrokerConnection.provider == provider_stripped)
    
    if broker_status is not None:
        status_stripped = broker_status.strip()
        if not status_stripped:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="status filter cannot be empty."
            )
        # Convert status string to enum (case-insensitive)
        try:
            status_enum = BrokerStatus[status_stripped.upper()]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status value. Must be one of: {', '.join([s.value.lower() for s in BrokerStatus])}."
            )
        query = query.where(BrokerConnection.status == status_enum)
        count_query = count_query.where(BrokerConnection.status == status_enum)
    
    # Get total count with filters applied
    total = db.scalar(count_query) or 0
    
    # Apply ordering and pagination
    query = query.order_by(BrokerConnection.connected_at.desc())
    query = query.offset(skip).limit(limit)
    
    # Execute query
    connections = db.scalars(query).all()
    
    # Convert to response schema with lowercase status
    items = [
        BrokerAccountOutput(
            id=conn.id,
            user_id=conn.user_id,
            provider=conn.provider,
            status=conn.status.value.lower(),
            connected_at=conn.connected_at,
            token_expires_at=conn.token_expires_at,
            broker_user_id=conn.broker_user_id,
        )
        for conn in connections
    ]
    
    return BrokerAccountsListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=items,
    )


@router.get("/subscription-plans", response_model=list[SubscriptionPlanOutput])
def list_subscription_plans(_: SuperAdmin, db: DbSession) -> list[SubscriptionPlan]:
    """
    Get all subscription plans.
    Returns all plans ordered by capital (ascending).
    """
    statement = select(SubscriptionPlan).order_by(SubscriptionPlan.capital.asc())
    return list(db.scalars(statement))


@router.post("/subscription-plans", response_model=SubscriptionPlanOutput, status_code=status.HTTP_201_CREATED)
def create_subscription_plan(
    payload: SubscriptionPlanInput,
    _: SuperAdmin,
    db: DbSession
) -> SubscriptionPlan:
    """
    Create a new subscription plan.
    Tier must be unique.
    """
    # Check if tier already exists
    existing = db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.tier == payload.tier))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A subscription plan with tier {payload.tier.value} already exists."
        )
    
    plan = SubscriptionPlan(
        tier=payload.tier,
        capital=payload.capital,
        nifty_lots=payload.nifty_lots,
        sensex_lots=payload.sensex_lots,
        bank_nifty_lots=payload.bank_nifty_lots,
        is_active=payload.is_active
    )
    
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.put("/subscription-plans/{plan_id}", response_model=SubscriptionPlanOutput)
def update_subscription_plan(
    plan_id: UUID,
    payload: SubscriptionPlanInput,
    _: SuperAdmin,
    db: DbSession
) -> SubscriptionPlan:
    """
    Update an existing subscription plan.
    All fields can be modified.
    """
    plan = db.get(SubscriptionPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription plan not found.")
    
    # Check if changing tier to one that already exists
    if plan.tier != payload.tier:
        existing = db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.tier == payload.tier))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A subscription plan with tier {payload.tier.value} already exists."
            )
    
    # Update all fields
    plan.tier = payload.tier
    plan.capital = payload.capital
    plan.nifty_lots = payload.nifty_lots
    plan.sensex_lots = payload.sensex_lots
    plan.bank_nifty_lots = payload.bank_nifty_lots
    plan.is_active = payload.is_active
    
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/subscription-plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription_plan(
    plan_id: UUID,
    _: SuperAdmin,
    db: DbSession
) -> Response:
    """
    Delete a subscription plan.
    Cannot delete plans that are currently assigned to users.
    """
    plan = db.get(SubscriptionPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription plan not found.")
    
    # Check if any users have this plan
    user_count = db.scalar(
        select(func.count()).select_from(User).where(User.current_plan_id == plan_id)
    ) or 0
    
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete plan. {user_count} user(s) are currently subscribed to this plan."
        )
    
    # Check if any pending subscription requests reference this plan
    request_count = db.scalar(
        select(func.count())
        .select_from(SubscriptionRequest)
        .where(
            SubscriptionRequest.plan_id == plan_id,
            SubscriptionRequest.status == SubscriptionRequestStatus.PENDING
        )
    ) or 0
    
    if request_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete plan. {request_count} pending subscription request(s) reference this plan."
        )
    
    db.delete(plan)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/subscription-requests/{request_id}/reject")
def reject_subscription_request(
    request_id: UUID,
    payload: RejectSubscriptionRequestInput,
    admin: SuperAdmin,
    db: DbSession
) -> SubscriptionRequestWithDetailsOutput:
    """
    Reject a subscription request.
    User's current plan remains unchanged.
    """
    request = db.get(SubscriptionRequest, request_id)
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription request not found.")
    
    if request.status != SubscriptionRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request is already {request.status.value.lower()}."
        )
    
    # Get user and plan
    user = db.get(User, request.user_id)
    plan = db.get(SubscriptionPlan, request.plan_id)
    
    if user is None or plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User or plan not found.")
    
    # Update the request
    request.status = SubscriptionRequestStatus.REJECTED
    request.reviewed_at = datetime.now(UTC)
    request.reviewed_by_id = admin.id
    request.notes = payload.notes
    
    db.commit()
    db.refresh(request)
    
    # Return detailed output
    current_plan = None
    if user.current_plan_id:
        current_plan = db.get(SubscriptionPlan, user.current_plan_id)
    
    return SubscriptionRequestWithDetailsOutput(
        id=request.id,
        user_id=user.id,
        user_email=user.email,
        user_full_name=user.full_name,
        plan_tier=plan.tier,
        plan_capital=plan.capital,
        current_plan_tier=current_plan.tier if current_plan else None,
        status=request.status,
        requested_at=request.requested_at,
        reviewed_at=request.reviewed_at,
        reviewed_by_id=request.reviewed_by_id,
        notes=request.notes,
    )
