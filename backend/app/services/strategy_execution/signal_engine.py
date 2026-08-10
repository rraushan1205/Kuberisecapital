"""
Signal Engine
Polls market data every 15 seconds and generates entry/exit signals.
"""
import asyncio
import logging
from datetime import datetime
import pytz

from sqlalchemy import select

from .context import StrategyExecutionContext
from .utils import is_market_hours, load_strategy_state, update_last_signal
from ..strategy_adapter import StrategyAdapter
from ..strategies.reference_strategy import check_for_signal
from ..strategy_loader import (
    execute_strategy_signal_check,
    StrategyLoadError,
    SecurityViolation,
    StrategyExecutionError
)
from app.models.domain import UserStrategyAssignment

logger = logging.getLogger(__name__)


async def _get_admin_strategy_assignment(db, user_id, strategy_id):
    """
    Check if this is an admin-managed strategy assignment.
    
    Returns:
        UserStrategyAssignment if found and active, None otherwise
    """
    result = await db.execute(
        select(UserStrategyAssignment)
        .where(
            UserStrategyAssignment.user_id == user_id,
            UserStrategyAssignment.id == strategy_id,  # strategy_id in context is actually assignment.id
            UserStrategyAssignment.is_active == True
        )
    )
    return result.scalar_one_or_none()


async def signal_engine_loop(context: StrategyExecutionContext):
    """
    Main signal generation loop.
    Polls every 15 seconds during market hours.
    """
    logger.info(f"SignalEngine started for user {context.config.user_id}, strategy {context.config.strategy_id}")
    
    # Get broker provider
    broker_provider = context.broker_manager.get_provider(context.config.broker)
    adapter = StrategyAdapter(broker_provider)
    
    poll_interval = 15  # seconds
    
    while not context.is_shutdown_requested():
        try:
            # Check market hours (9:15 AM - 3:30 PM IST, Mon-Fri)
            if not is_market_hours():
                logger.debug(f"Market closed, sleeping 60s (user: {context.config.user_id})")
                await asyncio.sleep(60)
                continue
            
            # Get broker token
            try:
                token = await context.get_broker_token()
            except Exception as e:
                logger.error(f"Failed to get broker token (user: {context.config.user_id}): {e}")
                await asyncio.sleep(poll_interval)
                continue
            
            # Fetch market data
            try:
                index_df = await adapter.get_candles_as_dataframe(
                    user_id=context.config.user_id,
                    access_token=token,
                    symbol=context.config.symbols['index'],
                    interval="5m",
                    lookback_days=5
                )
            except Exception as e:
                logger.error(f"Failed to fetch candles (user: {context.config.user_id}): {e}")
                await asyncio.sleep(poll_interval)
                continue
            
            if index_df.empty:
                logger.warning(f"Empty candles data (user: {context.config.user_id})")
                await asyncio.sleep(poll_interval)
                continue
            
            # Load current strategy state and check if this is an admin-managed strategy
            async with context.db_session_maker() as db:
                state = await load_strategy_state(db, context.config.user_id, context.config.strategy_id)
                assignment = await _get_admin_strategy_assignment(db, context.config.user_id, context.config.strategy_id)
            
            # Check for trading signals
            try:
                if assignment:
                    # Admin-managed strategy: use dynamic loader
                    logger.debug(f"Using admin-managed strategy '{assignment.strategy_definition.name}' (user: {context.config.user_id})")
                    
                    try:
                        signal = await execute_strategy_signal_check(
                            strategy_def=assignment.strategy_definition,
                            index_df=index_df,
                            state=state,
                            config=context.config,
                            adapter=adapter,
                            token=token
                        )
                    except (StrategyLoadError, SecurityViolation) as e:
                        # Permanent error - deactivate assignment
                        logger.error(
                            f"Strategy load/security error for user {context.config.user_id}, "
                            f"strategy '{assignment.strategy_definition.name}': {e}"
                        )
                        async with context.db_session_maker() as db:
                            assignment.is_active = False
                            assignment.error_message = f"Strategy validation failed: {str(e)}"
                            db.add(assignment)
                            await db.commit()
                        logger.critical(
                            f"Deactivated assignment id={assignment.id} for user {context.config.user_id} "
                            f"due to strategy error"
                        )
                        # Stop this strategy execution
                        break
                    
                    except StrategyExecutionError as e:
                        # Transient error - log and continue
                        logger.error(
                            f"Strategy execution error for user {context.config.user_id}: {e}"
                        )
                        await asyncio.sleep(poll_interval)
                        continue
                else:
                    # User-owned strategy: use hardcoded reference strategy
                    logger.debug(f"Using user-owned strategy (user: {context.config.user_id})")
                    signal = await check_for_signal(index_df, state, context.config, adapter, token)
            
            except Exception as e:
                logger.error(f"Error in signal generation (user: {context.config.user_id}): {e}", exc_info=True)
                await asyncio.sleep(poll_interval)
                continue
            
            # If signal generated, send to execution engine
            if signal:
                logger.info(f"Signal generated (user: {context.config.user_id}): {signal}")
                await context.put_signal(signal)
                
                # Update last signal in DB
                async with context.db_session_maker() as db:
                    await update_last_signal(db, state, signal)
                    await db.commit()
            
            # Wait before next poll
            await asyncio.sleep(poll_interval)
        
        except asyncio.CancelledError:
            logger.info(f"SignalEngine cancelled (user: {context.config.user_id})")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error in SignalEngine (user: {context.config.user_id}): {e}", exc_info=True)
            await asyncio.sleep(poll_interval)
    
    logger.info(f"SignalEngine stopped for user {context.config.user_id}")
