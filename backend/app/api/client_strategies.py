"""
Client Strategy API Routes
Endpoints for users to start/stop/monitor their strategy executions.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser
from app.db.session import get_async_db
from app.models.domain import User, StrategyState
from app.schemas.client import StrategyStateResponse, StrategyControlRequest

router = APIRouter(prefix="/api/client/strategies", tags=["client-strategies"])


def get_strategy_scheduler():
    """Import here to avoid circular dependency"""
    from app.main import get_strategy_scheduler as _get_scheduler
    return _get_scheduler()


@router.post("/{strategy_id}/start", status_code=status.HTTP_200_OK)
async def start_strategy(
    strategy_id: int,
    request: StrategyControlRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Start a strategy execution for the current user.
    
    Requires:
    - User must have an active broker connection
    - Strategy must not already be running
    """
    scheduler = get_strategy_scheduler()
    
    # Check if strategy already running
    if scheduler.is_strategy_running(current_user.id, strategy_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy is already running"
        )
    
    # Verify user has broker connection
    if not current_user.broker_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active broker connection. Please connect your broker first."
        )
    
    broker = request.broker or current_user.broker
    
    if not broker:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Broker not specified"
        )
    
    try:
        await scheduler.start_strategy(current_user.id, strategy_id, broker)
        return {"message": "Strategy started successfully", "strategy_id": strategy_id}
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start strategy: {str(e)}"
        )


@router.post("/{strategy_id}/stop", status_code=status.HTTP_200_OK)
async def stop_strategy(
    strategy_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_async_db)
):
    """Stop a running strategy execution."""
    scheduler = get_strategy_scheduler()
    
    # Check if strategy is running
    if not scheduler.is_strategy_running(current_user.id, strategy_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy is not currently running"
        )
    
    try:
        await scheduler.stop_strategy(current_user.id, strategy_id)
        return {"message": "Strategy stopped successfully", "strategy_id": strategy_id}
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop strategy: {str(e)}"
        )


@router.get("/{strategy_id}/status", response_model=StrategyStateResponse)
async def get_strategy_status(
    strategy_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_async_db)
):
    """Get current status of a strategy."""
    scheduler = get_strategy_scheduler()
    
    # Load state from database
    result = await db.execute(
        select(StrategyState)
        .where(StrategyState.user_id == current_user.id)
        .where(StrategyState.strategy_id == strategy_id)
    )
    state = result.scalar_one_or_none()
    
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy state not found"
        )
    
    # Check if actively running in scheduler
    is_running = scheduler.is_strategy_running(current_user.id, strategy_id)
    
    return StrategyStateResponse(
        strategy_id=state.strategy_id,
        status=state.status,
        broker=state.broker,
        has_open_position=state.has_open_position,
        position_symbol=state.position_symbol,
        position_side=state.position_side,
        position_qty=state.position_qty,
        position_entry_price=state.position_entry_price,
        position_entry_time=state.position_entry_time,
        target_price=state.target_price,
        stoploss_price=state.stoploss_price,
        last_signal_candle=state.last_signal_candle,
        last_signal_type=state.last_signal_type,
        error_message=state.error_message,
        created_at=state.created_at,
        updated_at=state.updated_at,
        is_active=is_running
    )


@router.get("/", response_model=List[StrategyStateResponse])
async def list_user_strategies(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_async_db)
):
    """List all strategies for the current user."""
    scheduler = get_strategy_scheduler()
    
    result = await db.execute(
        select(StrategyState)
        .where(StrategyState.user_id == current_user.id)
        .order_by(StrategyState.updated_at.desc())
    )
    states = result.scalars().all()
    
    return [
        StrategyStateResponse(
            strategy_id=state.strategy_id,
            status=state.status,
            broker=state.broker,
            has_open_position=state.has_open_position,
            position_symbol=state.position_symbol,
            position_side=state.position_side,
            position_qty=state.position_qty,
            position_entry_price=state.position_entry_price,
            position_entry_time=state.position_entry_time,
            target_price=state.target_price,
            stoploss_price=state.stoploss_price,
            last_signal_candle=state.last_signal_candle,
            last_signal_type=state.last_signal_type,
            error_message=state.error_message,
            created_at=state.created_at,
            updated_at=state.updated_at,
            is_active=scheduler.is_strategy_running(current_user.id, state.strategy_id)
        )
        for state in states
    ]


@router.get("/health")
async def strategies_health():
    """Get health status of strategy execution system."""
    scheduler = get_strategy_scheduler()
    
    return {
        "status": "healthy",
        "active_strategies": scheduler.get_active_count(),
        "scheduler_running": True
    }
