from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DbSession
from app.core.config import get_settings
from app.models.domain import (
    BrokerApiKey,
    BrokerConnection,
    BrokerStatus,
    Strategy,
    SubscriptionPlan,
    SubscriptionRequest,
    SubscriptionRequestStatus,
    SubscriptionStatus,
)
from app.schemas.client import EnhancedProfileOutput
from app.schemas.subscription import (
    SubscriptionPlanOutput,
    SubscriptionRequestInput,
    SubscriptionRequestOutput,
)

router = APIRouter(prefix="/api/v1/client", tags=["client"])


class ProfileData(BaseModel):
    name: str | None
    subscriptionStatus: str | None


class StrategyData(BaseModel):
    status: str | None
    selectedName: str | None
    scriptFileName: str | None


class PnlData(BaseModel):
    daily: str | None
    overall: str | None


class PositionsData(BaseModel):
    open: int | None
    closed: int | None


class SubscriptionData(BaseModel):
    status: str | None


class PreferencesData(BaseModel):
    lotSize: str | None
    riskSettings: str | None


class BrokerData(BaseModel):
    provider: str | None
    status: str | None


class DashboardSnapshot(BaseModel):
    profile: ProfileData | None
    strategy: StrategyData | None
    pnl: PnlData | None
    positions: PositionsData | None
    subscription: SubscriptionData | None
    preferences: PreferencesData | None
    broker: BrokerData | None = None


class MarketplaceStrategy(BaseModel):
    id: str
    name: str
    status: str | None
    scriptFileName: str | None


@router.get("/dashboard", response_model=DashboardSnapshot)
def get_dashboard_snapshot(user: CurrentUser, db: DbSession) -> DashboardSnapshot:
    """
    Get dashboard overview data for the authenticated user.
    Returns profile information, subscription plan, account status, and broker connection.
    """
    # Format subscription status with plan details
    subscription_status = None
    subscription_info = None
    if user.subscription_status == SubscriptionStatus.ACTIVE and user.current_plan_id:
        plan = db.get(SubscriptionPlan, user.current_plan_id)
        if plan:
            # Format as "PRO · Active" or similar
            tier_name = plan.tier.value.title()
            subscription_status = f"{tier_name} · Active"
            # For subscription section, could add renewal date when implemented
            subscription_info = f"{tier_name} · Active"
    elif user.subscription_status == SubscriptionStatus.INACTIVE:
        subscription_status = "Inactive"
        subscription_info = "Inactive"
    
    # Get lot size info from current plan
    lot_size_info = None
    if user.current_plan_id:
        plan = db.get(SubscriptionPlan, user.current_plan_id)
        if plan:
            lot_size_info = f"{plan.nifty_lots} lots · NIFTY"
    
    # Get broker connection info
    connection = db.scalar(
        select(BrokerConnection).where(
            BrokerConnection.user_id == user.id,
            BrokerConnection.status == BrokerStatus.CONNECTED,
        )
    )

    broker_data = None
    if connection is not None:
        broker_data = BrokerData(
            provider=connection.provider,
            status=connection.status.value,
        )
    
    return DashboardSnapshot(
        profile=ProfileData(
            name=user.full_name,
            subscriptionStatus=subscription_status,
        ),
        strategy=StrategyData(
            status=None,  # TODO: Implement strategy assignment per user
            selectedName=None,
            scriptFileName=None,
        ),
        pnl=PnlData(
            daily=None,  # TODO: Implement P&L tracking
            overall=None,
        ),
        positions=PositionsData(
            open=None,  # TODO: Implement position tracking
            closed=None,
        ),
        subscription=SubscriptionData(
            status=subscription_info,
        ),
        preferences=PreferencesData(
            lotSize=lot_size_info,
            riskSettings=None,  # TODO: Implement user preferences/risk settings
        ),
        broker=broker_data,
    )


@router.get("/marketplace/strategies", response_model=list[MarketplaceStrategy])
def get_marketplace_strategies(_: CurrentUser, db: DbSession) -> list[MarketplaceStrategy]:
    """
    Get all available strategies uploaded by admin.
    All approved users can see all uploaded strategies.
    """
    strategies = db.scalars(select(Strategy).order_by(Strategy.created_at.desc())).all()
    return [
        MarketplaceStrategy(
            id=str(strategy.id),
            name=strategy.name,
            status=strategy.status.value,
            scriptFileName=strategy.script_filename,
        )
        for strategy in strategies
    ]


@router.get("/strategies/{strategy_id}/download")
def download_strategy_file(strategy_id: UUID, _: CurrentUser, db: DbSession) -> FileResponse:
    """
    Download a strategy Python file.
    Users can read/download strategy files but cannot edit them.
    """
    strategy = db.get(Strategy, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found.")
    
    storage_path = get_settings().strategy_storage_path
    file_path = storage_path / strategy.script_storage_key
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy file not found on disk.",
        )
    
    return FileResponse(
        path=file_path,
        filename=strategy.script_filename,
        media_type="text/x-python",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Subscription Plans & Requests
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/subscription-plans", response_model=list[SubscriptionPlanOutput])
def get_subscription_plans(_: CurrentUser, db: DbSession) -> list[SubscriptionPlanOutput]:
    """Get all available subscription plans"""
    plans = db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.is_active == True)).all()
    # Schema has from_attributes=True, so return models directly
    return list(plans)


@router.post("/subscription-requests", response_model=SubscriptionRequestOutput)
def create_subscription_request(
    data: SubscriptionRequestInput, user: CurrentUser, db: DbSession
) -> SubscriptionRequestOutput:
    """
    Create a new subscription request for the authenticated user.
    Only users with INACTIVE subscription can request a subscription.
    """
    # Check if user already has an active subscription
    if user.subscription_status == SubscriptionStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has an active subscription",
        )

    # Check if plan exists
    plan = db.get(SubscriptionPlan, data.plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subscription plan not found"
        )

    # Check for existing pending request
    existing_request = db.scalar(
        select(SubscriptionRequest).where(
            SubscriptionRequest.user_id == user.id,
            SubscriptionRequest.status == SubscriptionRequestStatus.PENDING,
        )
    )
    if existing_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a pending subscription request",
        )

    # Create new subscription request
    new_request = SubscriptionRequest(
        user_id=user.id,
        plan_id=data.plan_id,
        status=SubscriptionRequestStatus.PENDING,
        requested_at=datetime.now(UTC),
    )

    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    # Schema has from_attributes=True, so return model directly
    return new_request


@router.get("/subscription-requests", response_model=list[SubscriptionRequestOutput])
def get_user_subscription_requests(user: CurrentUser, db: DbSession) -> list[SubscriptionRequestOutput]:
    """Get all subscription requests for the authenticated user"""
    requests = db.scalars(
        select(SubscriptionRequest)
        .where(SubscriptionRequest.user_id == user.id)
        .order_by(SubscriptionRequest.requested_at.desc())
    ).all()

    # Schema has from_attributes=True, so return models directly
    return list(requests)


@router.delete("/subscription-requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_subscription_request(
    request_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    """Cancel a pending subscription request belonging to the authenticated user."""

    request = db.scalar(
        select(SubscriptionRequest).where(
            SubscriptionRequest.id == request_id,
            SubscriptionRequest.user_id == user.id,
        )
    )

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription request not found",
        )

    if request.status != SubscriptionRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending subscription requests can be cancelled",
        )

    db.delete(request)
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Enhanced User Profile
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/profile/enhanced", response_model=EnhancedProfileOutput)
def get_enhanced_profile(user: CurrentUser, db: DbSession) -> EnhancedProfileOutput:
    """
    Get enhanced user profile with broker authentication summary.
    
    Returns comprehensive profile information including:
    - Basic user details (email, name, status)
    - Connected OAuth brokers
    - Stored API keys (count and providers)
    - Last broker used
    - Login method preference
    
    Args:
        user: Authenticated user from JWT token
        db: Database session
    
    Returns:
        EnhancedProfileOutput: Enhanced profile with broker summary
    
    Example:
        GET /api/v1/client/profile/enhanced
        -> Returns: {
            "user_id": "uuid",
            "email": "user@example.com",
            "full_name": "John Doe",
            "account_status": "APPROVED",
            "subscription_status": "ACTIVE",
            "connected_brokers": ["fyers"],
            "stored_api_keys": ["zerodha"],
            "last_broker_used": "fyers",
            "login_method": "OAUTH",
            "created_at": "2026-01-15T10:30:00Z",
            "last_login_at": "2026-08-03T08:00:00Z"
        }
    """
    # Get connected OAuth brokers
    stmt = select(BrokerConnection).where(
        BrokerConnection.user_id == user.id,
        BrokerConnection.status == BrokerStatus.CONNECTED,
    )
    connections = db.execute(stmt).scalars().all()
    connected_brokers = [conn.provider for conn in connections]
    
    # Get stored API keys
    stmt = select(BrokerApiKey).where(BrokerApiKey.user_id == user.id)
    api_keys = db.execute(stmt).scalars().all()
    stored_api_keys = [key.provider for key in api_keys]
    
    return EnhancedProfileOutput(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        account_status=user.account_status.value,
        subscription_status=user.subscription_status.value,
        connected_brokers=connected_brokers,
        stored_api_keys=stored_api_keys,
        last_broker_used=user.last_broker_used,
        login_method=user.login_method.value if user.login_method else None,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )
