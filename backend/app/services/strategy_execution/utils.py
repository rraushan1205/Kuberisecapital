"""
Utility functions for strategy execution.
Market hours, state management, etc.
"""
from datetime import datetime
from uuid import UUID
import pytz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import StrategyState


def is_market_hours() -> bool:
    """
    Check if Indian markets are open.
    NSE/BSE: Mon-Fri, 9:15 AM - 3:30 PM IST
    """
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    # Weekend check
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    
    # Market hours: 9:15 AM - 3:30 PM
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    return market_open <= now <= market_close


async def load_strategy_state(db: AsyncSession, user_id: UUID, strategy_id: int) -> StrategyState | None:
    """Load strategy state from database"""
    result = await db.execute(
        select(StrategyState)
        .where(StrategyState.user_id == user_id)
        .where(StrategyState.strategy_id == strategy_id)
    )
    return result.scalar_one_or_none()


async def get_or_create_strategy_state(db: AsyncSession, user_id: UUID, strategy_id: int, broker: str) -> StrategyState:
    """Get existing state or create new one"""
    state = await load_strategy_state(db, user_id, strategy_id)
    
    if not state:
        state = StrategyState(
            user_id=user_id,
            strategy_id=strategy_id,
            broker=broker,
            status="idle"
        )
        db.add(state)
        await db.flush()
    
    return state


async def update_last_signal(db: AsyncSession, state: StrategyState, signal: dict):
    """Update last signal information"""
    state.last_signal_candle = datetime.utcnow()
    state.last_signal_type = signal['type']
    state.updated_at = datetime.utcnow()


async def update_state_with_position(
    db: AsyncSession,
    user_id: UUID,
    strategy_id: int,
    symbol: str,
    side: str,
    qty: int,
    entry_price: float,
    entry_order_id: str,
    tp_order_id: str | None,
    sl_order_id: str | None,
    target_price: float,
    stoploss_price: float
):
    """Update state when position is opened"""
    state = await load_strategy_state(db, user_id, strategy_id)
    
    if state:
        state.has_open_position = True
        state.position_symbol = symbol
        state.position_side = side
        state.position_qty = qty
        state.position_entry_price = entry_price
        state.position_entry_time = datetime.utcnow()
        state.entry_order_id = entry_order_id
        state.tp_order_id = tp_order_id
        state.sl_order_id = sl_order_id
        state.target_price = target_price
        state.stoploss_price = stoploss_price
        state.updated_at = datetime.utcnow()


async def close_position_in_db(db: AsyncSession, state: StrategyState, exit_reason: str, exit_price: float):
    """Clear position from state when closed"""
    
    # Calculate PnL
    pnl = None
    if state.position_entry_price and state.position_qty:
        pnl = (exit_price - state.position_entry_price) * state.position_qty
    
    # Clear position fields
    state.has_open_position = False
    state.position_symbol = None
    state.position_side = None
    state.position_qty = None
    state.position_entry_price = None
    state.position_entry_time = None
    state.entry_order_id = None
    state.tp_order_id = None
    state.sl_order_id = None
    state.target_price = None
    state.stoploss_price = None
    state.updated_at = datetime.utcnow()
    
    # TODO: Log trade to execution_logs table with PnL
    # This would require importing ExecutionLog model and creating entry


async def mark_strategy_status(db: AsyncSession, user_id: UUID, strategy_id: int, status: str, error_message: str | None = None):
    """Update strategy status"""
    state = await load_strategy_state(db, user_id, strategy_id)
    
    if state:
        state.status = status
        state.error_message = error_message
        state.updated_at = datetime.utcnow()
