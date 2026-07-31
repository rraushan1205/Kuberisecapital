from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DbSession
from app.core.config import get_settings
from app.models.domain import Strategy, SubscriptionPlan, SubscriptionRequest, SubscriptionRequestStatus, SubscriptionStatus
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


class DashboardSnapshot(BaseModel):
    profile: ProfileData | None
    strategy: StrategyData | None
    pnl: PnlData | None
    positions: PositionsData | None
    subscription: SubscriptionData | None
    preferences: PreferencesData | None


class MarketplaceStrategy(BaseModel):
    id: str
    name: str
    status: str | None
    scriptFileName: str | None


@router.get("/dashboard", response_model=DashboardSnapshot)
def get_dashboard_snapshot(user: CurrentUser, db: DbSession) -> DashboardSnapshot:
    """
    Get dashboard overview data for the authenticated user.
    Returns profile information, subscription plan, and account status.
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy file not found in storage.")
    
    return FileResponse(
        path=file_path,
        filename=strategy.script_filename,
        media_type="text/x-python",
        headers={
            "Content-Disposition": f'attachment; filename="{strategy.script_filename}"',
            "Cache-Control": "no-cache",
        }
    )


@router.get("/strategies/{strategy_id}/view")
def view_strategy_file(strategy_id: UUID, _: CurrentUser, db: DbSession) -> dict[str, str]:
    """
    View strategy file contents (read-only).
    Returns the file content as text for viewing in the browser.
    """
    strategy = db.get(Strategy, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found.")
    
    storage_path = get_settings().strategy_storage_path
    file_path = storage_path / strategy.script_storage_key
    
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy file not found in storage.")
    
    try:
        content = file_path.read_text(encoding="utf-8")
        return {
            "filename": strategy.script_filename,
            "content": content,
            "readonly": True,
            "message": "This file is admin-managed and read-only"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not read strategy file."
        )


@router.get("/subscription/current-plan", response_model=SubscriptionPlanOutput | None)
def get_current_subscription_plan(user: CurrentUser, db: DbSession) -> SubscriptionPlan | None:
    """
    Get the user's current active subscription plan.
    Returns None if user has no active plan.
    """
    if user.current_plan_id:
        plan = db.get(SubscriptionPlan, user.current_plan_id)
        return plan
    return None


@router.get("/subscription/plans", response_model=list[SubscriptionPlanOutput])
def get_subscription_plans(_: CurrentUser, db: DbSession) -> list[SubscriptionPlan]:
    """
    Get all available subscription plans.
    Returns all active subscription plans with their details.
    """
    plans = db.scalars(
        select(SubscriptionPlan)
        .where(SubscriptionPlan.is_active == True)
        .order_by(SubscriptionPlan.capital.asc())
    ).all()
    return list(plans)


@router.get("/subscription/my-requests", response_model=list[SubscriptionRequestOutput])
def get_my_subscription_requests(user: CurrentUser, db: DbSession) -> list[SubscriptionRequest]:
    """
    Get all subscription requests made by the current user.
    Returns the user's subscription request history ordered by most recent first.
    """
    requests = db.scalars(
        select(SubscriptionRequest)
        .where(SubscriptionRequest.user_id == user.id)
        .order_by(SubscriptionRequest.requested_at.desc())
    ).all()
    return list(requests)


@router.post("/subscription/request", response_model=SubscriptionRequestOutput, status_code=status.HTTP_201_CREATED)
def request_subscription_plan(payload: SubscriptionRequestInput, user: CurrentUser, db: DbSession) -> SubscriptionRequest:
    """
    Request a subscription plan.
    Users can request any plan at any time. Current plan remains active until admin approves.
    """
    # Check if plan exists and is active
    plan = db.get(SubscriptionPlan, payload.plan_id)
    if plan is None or not plan.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription plan not found or inactive.")
    
    # Check if user already has a pending request for this plan
    existing_pending = db.scalar(
        select(SubscriptionRequest)
        .where(
            SubscriptionRequest.user_id == user.id,
            SubscriptionRequest.plan_id == payload.plan_id,
            SubscriptionRequest.status == SubscriptionRequestStatus.PENDING
        )
    )
    if existing_pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a pending request for this plan."
        )
    
    # Check if this is already the user's current plan
    if user.current_plan_id == payload.plan_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This is already your current active plan."
        )
    
    # Create the subscription request
    request = SubscriptionRequest(
        user_id=user.id,
        plan_id=payload.plan_id,
        status=SubscriptionRequestStatus.PENDING
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


@router.delete("/subscription/request/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_subscription_request(request_id: UUID, user: CurrentUser, db: DbSession) -> None:
    """
    Cancel a pending subscription request.
    Users can only cancel their own pending requests.
    """
    request = db.get(SubscriptionRequest, request_id)
    
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription request not found.")
    
    # Check if the request belongs to the current user
    if request.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only cancel your own requests.")
    
    # Check if the request is still pending
    if request.status != SubscriptionRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel a request that has already been {request.status.value.lower()}."
        )
    
    # Delete the request
    db.delete(request)
    db.commit()
