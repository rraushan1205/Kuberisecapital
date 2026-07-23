from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DbSession
from app.core.config import get_settings
from app.models.domain import Strategy

router = APIRouter(prefix="/api/v1/client", tags=["client"])


class ProfileData(BaseModel):
    name: str
    email: str
    subscriptionStatus: str
    connectedBroker: str | None


class DashboardSnapshot(BaseModel):
    profile: ProfileData


class MarketplaceStrategy(BaseModel):
    id: str
    name: str
    status: str | None
    scriptFileName: str | None


@router.get("/dashboard", response_model=DashboardSnapshot)
def get_dashboard_snapshot(user: CurrentUser) -> DashboardSnapshot:
    """
    Get dashboard overview data for the authenticated user.
    Returns profile information and account status.
    """
    return DashboardSnapshot(
        profile=ProfileData(
            name=user.full_name or "User",
            email=user.email,
            subscriptionStatus=user.subscription_status.value,
            connectedBroker=None,  # TODO: Fetch from broker_connections
        )
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
