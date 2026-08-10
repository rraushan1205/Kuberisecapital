"""
Execution Engine
Handles order placement, TP/SL management, and position monitoring.
"""
import asyncio
import logging
from datetime import datetime
from decimal import Decimal

from .context import StrategyExecutionContext
from .utils import load_strategy_state, update_state_with_position, close_position_in_db
from ..strategy_adapter import StrategyAdapter

logger = logging.getLogger(__name__)

# Retry configuration constants
MAX_ENTRY_ATTEMPTS = 2       # 1 initial + 1 retry (entry orders: low retry to avoid duplicates)
MAX_ORDER_ATTEMPTS = 3       # 1 initial + 2 retries (TP/SL orders)
MAX_CANCEL_ATTEMPTS = 3      # 1 initial + 2 retries (cancel operations)
MAX_CANCEL_TICKS = 10        # cross-tick cancel attempts before giving up (Bug 4)
MONITOR_INTERVAL_SECONDS = 5
RECONCILE_INTERVAL_SECONDS = 30
SHUTDOWN_WAIT_SECONDS = 30


async def cancel_order_with_retry(
    adapter: StrategyAdapter,
    user_id,
    token: str,
    order_id: str,
    max_attempts: int = MAX_CANCEL_ATTEMPTS,
    label: str = ""
) -> tuple[bool, str | None]:
    """
    Cancel an order with retry logic and exponential backoff.
    
    Args:
        adapter: Strategy adapter instance
        user_id: User ID
        token: Broker access token
        order_id: Order ID to cancel
        max_attempts: Maximum number of attempts (1 initial + retries)
        label: Description label for logging (e.g., "TP", "SL")
    
    Returns:
        tuple: (success: bool, error_message: str | None)
    """
    for attempt in range(max_attempts):
        try:
            await adapter.cancel_order(user_id, token, order_id)
            logger.info(
                f"Successfully cancelled {label} order {order_id} on attempt {attempt + 1} "
                f"(user: {user_id})"
            )
            return True, None
        except Exception as e:
            logger.warning(
                f"Failed to cancel {label} order {order_id} on attempt {attempt + 1}/{max_attempts}: {e} "
                f"(user: {user_id})"
            )
            
            if attempt < max_attempts - 1:
                # Exponential backoff: 1s, 2s, 4s
                backoff_seconds = 2 ** attempt
                await asyncio.sleep(backoff_seconds)
            else:
                # Final attempt failed
                error_msg = f"Failed to cancel {label} order {order_id} after {max_attempts} attempts: {e}"
                logger.error(f"{error_msg} (user: {user_id})", exc_info=True)
                return False, error_msg
    
    return False, f"Unexpected exit from cancel_order_with_retry for {label} order {order_id}"


async def place_order_with_retry(
    adapter: StrategyAdapter,
    order_func,
    order_label: str,
    max_attempts: int = MAX_ORDER_ATTEMPTS,
    **order_kwargs
):
    """
    Place an order with retry logic and exponential backoff.
    
    Args:
        adapter: Strategy adapter instance
        order_func: The order placement function to call (e.g., adapter.place_limit_order)
        order_label: Description label for logging (e.g., "TP", "SL", "Entry")
        max_attempts: Maximum number of attempts (1 initial + retries). 
                      max_attempts=2 means 1 initial attempt + 1 retry.
        **order_kwargs: Arguments to pass to order_func (must include user_id for logging)
    
    Returns:
        Order object if successful
    
    Raises:
        Exception: If all retry attempts fail
    """
    log_user_id = order_kwargs.get('user_id', 'unknown')
    last_exception = None
    
    for attempt in range(max_attempts):
        try:
            order = await order_func(**order_kwargs)
            logger.info(
                f"Successfully placed {order_label} order {order.order_id} on attempt {attempt + 1} "
                f"(user: {log_user_id})"
            )
            return order
        except Exception as e:
            last_exception = e
            logger.warning(
                f"Failed to place {order_label} order on attempt {attempt + 1}/{max_attempts}: {e} "
                f"(user: {log_user_id})"
            )
            
            if attempt < max_attempts - 1:
                # Exponential backoff: 1s, 2s, 4s
                backoff_seconds = 2 ** attempt
                await asyncio.sleep(backoff_seconds)
    
    # All retries exhausted
    error_msg = f"Failed to place {order_label} order after {max_attempts} attempts: {last_exception}"
    logger.error(f"{error_msg} (user: {log_user_id})", exc_info=True)
    raise Exception(error_msg) from last_exception


async def execution_engine_loop(context: StrategyExecutionContext):
    """
    Main execution loop.
    Listens for signals and monitors open positions.
    """
    logger.info(f"ExecutionEngine started for user {context.config.user_id}, strategy {context.config.strategy_id}")
    
    # Get broker provider
    broker_provider = context.broker_manager.get_provider(context.config.broker)
    adapter = StrategyAdapter(broker_provider)
    
    # Configurable monitor interval (default 5 seconds for position monitoring)
    monitor_interval = context.config.params.get('monitor_interval_seconds', MONITOR_INTERVAL_SECONDS)
    
    # State cache for reducing DB queries
    context.cached_state = None
    last_reconciliation = datetime.utcnow()
    reconciliation_interval_seconds = RECONCILE_INTERVAL_SECONDS
    
    while not context.is_shutdown_requested():
        try:
            # Check for new signals (with timeout)
            signal = await context.get_signal(timeout=monitor_interval)
            
            if signal:
                # Signal received - invalidate cache and handle it
                context.cached_state = None
                await handle_signal(signal, context, adapter)
            
            # Reconcile state from DB every 30 seconds to catch any drift
            now = datetime.utcnow()
            if (now - last_reconciliation).total_seconds() >= reconciliation_interval_seconds:
                context.cached_state = None
                last_reconciliation = now
            
            # Monitor existing positions
            await monitor_positions(context, adapter)
        
        except asyncio.CancelledError:
            logger.info(f"ExecutionEngine cancelled (user: {context.config.user_id})")
            # Graceful shutdown handling
            await shutdown_gracefully(context, adapter)
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error in ExecutionEngine (user: {context.config.user_id}): {e}", exc_info=True)
            await asyncio.sleep(monitor_interval)
    
    logger.info(f"ExecutionEngine stopped for user {context.config.user_id}")


async def shutdown_gracefully(context: StrategyExecutionContext, adapter: StrategyAdapter):
    """
    Handle graceful shutdown of execution engine.
    
    Args:
        context: Strategy execution context
        adapter: Strategy adapter instance
    """
    user_id = context.config.user_id
    strategy_id = context.config.strategy_id
    
    logger.info(f"Graceful shutdown initiated (user: {user_id}, strategy: {strategy_id})")
    
    try:
        # Check if there's an open position
        async with context.db_session_maker() as db:
            state = await load_strategy_state(db, user_id, strategy_id)
            
            if state and state.has_open_position:
                logger.warning(
                    f"Shutdown requested with open position: {state.position_symbol} "
                    f"qty={state.position_qty} entry={state.position_entry_price} "
                    f"(user: {user_id}, strategy: {strategy_id}) - Manual review required"
                )
                
                # Mark for manual review
                state.error_message = (
                    f"Server shutdown with open position at {datetime.utcnow().isoformat()}. "
                    f"Position: {state.position_symbol}, Qty: {state.position_qty}, "
                    f"Entry: {state.position_entry_price}, TP: {state.tp_order_id}, SL: {state.sl_order_id}"
                )
                state.updated_at = datetime.utcnow()
                await db.commit()
            
            logger.info(f"Graceful shutdown complete (user: {user_id}, strategy: {strategy_id})")
    
    except Exception as e:
        logger.error(f"Error during graceful shutdown (user: {user_id}, strategy: {strategy_id}): {e}", exc_info=True)


async def handle_signal(signal: dict, context: StrategyExecutionContext, adapter: StrategyAdapter):
    """
    Process a trading signal - place entry order with TP/SL.
    """
    logger.info(f"Handling signal for user {context.config.user_id}: {signal}")
    
    try:
        token = await context.get_broker_token()
        
        signal_type = signal['type']
        
        if signal_type == 'BUY':
            await handle_entry_signal(signal, context, adapter, token)
        
        elif signal_type == 'SELL':
            await handle_exit_signal(signal, context, adapter, token)
        
        else:
            logger.warning(f"Unknown signal type: {signal_type}")
    
    except Exception as e:
        logger.error(f"Error handling signal (user: {context.config.user_id}): {e}", exc_info=True)


async def handle_entry_signal(signal: dict, context: StrategyExecutionContext, adapter: StrategyAdapter, token: str):
    """Place entry order with TP and SL"""
    
    symbol = signal['symbol']
    qty = context.config.params['qty']
    target_points = context.config.params['target_points']
    sl_points = context.config.params['sl_points']
    
    logger.info(f"Placing entry order: {symbol} x {qty} (user: {context.config.user_id})")
    
    # Place market order with retry (1 retry to avoid duplicate fills)
    try:
        entry_order = await place_order_with_retry(
            adapter=adapter,
            order_func=adapter.place_market_order,
            order_label="Entry",
            max_attempts=MAX_ENTRY_ATTEMPTS,
            user_id=context.config.user_id,
            access_token=token,
            symbol=symbol,
            quantity=qty,
            side="BUY"
        )
        logger.info(f"Entry order placed: {entry_order.order_id} (user: {context.config.user_id})")
    except Exception as e:
        logger.error(f"Failed to place entry order (user: {context.config.user_id}): {e}")
        return
    
    # Wait for order to fill (max 5 seconds)
    await asyncio.sleep(1)
    
    try:
        is_filled, avg_price = await adapter.is_order_filled(
            user_id=context.config.user_id,
            access_token=token,
            order_id=entry_order.order_id
        )
    except Exception as e:
        logger.error(f"Failed to check order status (user: {context.config.user_id}): {e}")
        return
    
    if not is_filled:
        logger.warning(f"Entry order not filled yet: {entry_order.order_id} (user: {context.config.user_id})")
        return
    
    logger.info(f"Entry order filled at {avg_price} (user: {context.config.user_id})")
    
    # Calculate TP and SL prices
    tp_price = avg_price + target_points
    sl_price = avg_price - sl_points
    
    # Place TP order (limit order) with retry
    tp_order = None
    tp_failed = False
    try:
        tp_order = await place_order_with_retry(
            adapter=adapter,
            order_func=adapter.place_limit_order,
            order_label="TP",
            max_attempts=MAX_ORDER_ATTEMPTS,
            user_id=context.config.user_id,
            access_token=token,
            symbol=symbol,
            quantity=qty,
            side="SELL",
            price=tp_price
        )
        logger.info(f"TP order placed: {tp_order.order_id} @ {tp_price} (user: {context.config.user_id})")
    except Exception as e:
        logger.error(f"Failed to place TP order after retries (user: {context.config.user_id}): {e}", exc_info=True)
        tp_failed = True
    
    # Place SL order (stop-loss market) with retry
    sl_order = None
    sl_failed = False
    try:
        sl_order = await place_order_with_retry(
            adapter=adapter,
            order_func=adapter.place_stoploss_order,
            order_label="SL",
            max_attempts=MAX_ORDER_ATTEMPTS,
            user_id=context.config.user_id,
            access_token=token,
            symbol=symbol,
            quantity=qty,
            side="SELL",
            trigger_price=sl_price
        )
        logger.info(f"SL order placed: {sl_order.order_id} @ {sl_price} (user: {context.config.user_id})")
    except Exception as e:
        logger.error(f"Failed to place SL order after retries (user: {context.config.user_id}): {e}", exc_info=True)
        sl_failed = True
    
    # CRITICAL: If either TP or SL placement failed, close position immediately
    if tp_failed or sl_failed:
        logger.critical(
            f"EMERGENCY: Entry filled but {'TP' if tp_failed else 'SL'} placement failed. "
            f"Placing emergency exit order for {symbol} x {qty} (user: {context.config.user_id})"
        )
        
        try:
            # Place market exit order immediately
            exit_order = await adapter.place_market_order(
                user_id=context.config.user_id,
                access_token=token,
                symbol=symbol,
                quantity=qty,
                side="SELL"
            )
            logger.critical(
                f"Emergency exit order placed: {exit_order.order_id} (user: {context.config.user_id})"
            )
            
            # Mark for manual review in DB
            async with context.db_session_maker() as db:
                state = await load_strategy_state(db, context.config.user_id, context.config.strategy_id)
                if state:
                    state.error_message = (
                        f"Entry filled at {avg_price} but {'TP' if tp_failed else 'SL'} placement failed. "
                        f"Emergency exit placed: {exit_order.order_id}. Manual review required."
                    )
                    state.status = "error"
                    state.updated_at = datetime.utcnow()
                    await db.commit()
            
            return
        
        except Exception as exit_error:
            logger.critical(
                f"EMERGENCY EXIT FAILED: Could not place exit order after TP/SL failure. "
                f"Symbol: {symbol}, Qty: {qty}, Entry: {avg_price} (user: {context.config.user_id}). "
                f"Error: {exit_error}",
                exc_info=True
            )
            
            # Mark as critical error in DB
            async with context.db_session_maker() as db:
                state = await load_strategy_state(db, context.config.user_id, context.config.strategy_id)
                if state:
                    state.error_message = (
                        f"CRITICAL: Entry filled at {avg_price} but TP/SL placement failed AND "
                        f"emergency exit failed. Position open unprotected. IMMEDIATE MANUAL INTERVENTION REQUIRED."
                    )
                    state.status = "error"
                    state.updated_at = datetime.utcnow()
                    await db.commit()
            
            return
    
    # Update strategy state in database
    async with context.db_session_maker() as db:
        await update_state_with_position(
            db=db,
            user_id=context.config.user_id,
            strategy_id=context.config.strategy_id,
            symbol=symbol,
            side="BUY",
            qty=qty,
            entry_price=avg_price,
            entry_order_id=entry_order.order_id,
            tp_order_id=tp_order.order_id if tp_order else None,
            sl_order_id=sl_order.order_id if sl_order else None,
            target_price=tp_price,
            stoploss_price=sl_price
        )
        await db.commit()
    
    # Invalidate cache after position opened
    context.cached_state = None
    
    logger.info(f"Position opened and tracked (user: {context.config.user_id})")


async def handle_exit_signal(signal: dict, context: StrategyExecutionContext, adapter: StrategyAdapter, token: str):
    """Close open position on exit signal"""
    
    logger.info(f"Exit signal received (user: {context.config.user_id})")
    
    # READ: Load current state in a short session
    async with context.db_session_maker() as db:
        state = await load_strategy_state(db, context.config.user_id, context.config.strategy_id)
        
        if not state or not state.has_open_position:
            logger.warning(f"No open position to close (user: {context.config.user_id})")
            return
        
        # Capture what we need; session closes here
        tp_order_id = state.tp_order_id
        sl_order_id = state.sl_order_id
        position_symbol = state.position_symbol
        position_qty = state.position_qty
    
    # BROKER OPERATIONS: No DB session held during these calls
    tp_cancel_failed = False
    sl_cancel_failed = False
    
    if tp_order_id:
        success, error_msg = await cancel_order_with_retry(
            adapter, context.config.user_id, token, tp_order_id,
            max_attempts=MAX_CANCEL_ATTEMPTS, label="TP"
        )
        if not success:
            tp_cancel_failed = True
            logger.error(
                f"Failed to cancel TP order {tp_order_id} during exit: {error_msg} "
                f"(user: {context.config.user_id})"
            )
    
    if sl_order_id:
        success, error_msg = await cancel_order_with_retry(
            adapter, context.config.user_id, token, sl_order_id,
            max_attempts=MAX_CANCEL_ATTEMPTS, label="SL"
        )
        if not success:
            sl_cancel_failed = True
            logger.error(
                f"Failed to cancel SL order {sl_order_id} during exit: {error_msg} "
                f"(user: {context.config.user_id})"
            )
    
    # Place market order to exit
    try:
        exit_order = await adapter.place_market_order(
            user_id=context.config.user_id,
            access_token=token,
            symbol=position_symbol,
            quantity=position_qty,
            side="SELL"
        )
        logger.info(f"Exit order placed: {exit_order.order_id} (user: {context.config.user_id})")
        
        # Wait and check fill
        await asyncio.sleep(1)
        is_filled, exit_price = await adapter.is_order_filled(
            context.config.user_id, token, exit_order.order_id
        )
        
        if not is_filled:
            logger.warning(
                f"Exit order not filled yet: {exit_order.order_id} (user: {context.config.user_id})"
            )
            return
        
        # WRITE: Short session for DB update only
        async with context.db_session_maker() as db:
            state = await load_strategy_state(db, context.config.user_id, context.config.strategy_id)  # Reload for write
            
            if tp_cancel_failed or sl_cancel_failed:
                state.error_message = (
                    f"Exit filled at {exit_price} but cancel failed for "
                    f"{'TP' if tp_cancel_failed else ''}"
                    f"{' and ' if tp_cancel_failed and sl_cancel_failed else ''}"
                    f"{'SL' if sl_cancel_failed else ''}. "
                    f"Manual review required to verify no orphan orders."
                )
                logger.error(f"Position closed with cancel failures: {state.error_message}")
            
            await close_position_in_db(db, state, "MANUAL_EXIT", exit_price)
            await db.commit()
        
        # Invalidate cache
        context.cached_state = None
        
        logger.info(f"Position closed at {exit_price} (user: {context.config.user_id})")
    
    except Exception as e:
        logger.error(f"Failed to place exit order (user: {context.config.user_id}): {e}", exc_info=True)


async def monitor_positions(context: StrategyExecutionContext, adapter: StrategyAdapter):
    """
    Monitor open positions for TP/SL hits.
    Uses cached state to reduce DB queries.
    """
    try:
        # Fast path: cached state says no position — skip DB entirely
        if context.cached_state is not None and not context.cached_state.has_open_position:
            return
        
        # One session for the entire function
        async with context.db_session_maker() as db:
            state = await load_strategy_state(db, context.config.user_id, context.config.strategy_id)
            context.cached_state = state
            
            if not state or not state.has_open_position:
                return
            
            token = await context.get_broker_token()
            
            # Check TP order
            if state.tp_order_id:
                try:
                    is_filled, fill_price = await adapter.is_order_filled(
                        context.config.user_id, token, state.tp_order_id
                    )
                    
                    if is_filled:
                        logger.info(f"TARGET HIT at {fill_price} (user: {context.config.user_id})")
                        
                        # Cancel SL order with retry
                        if state.sl_order_id:
                            success, error_msg = await cancel_order_with_retry(
                                adapter, context.config.user_id, token, state.sl_order_id,
                                max_attempts=MAX_CANCEL_ATTEMPTS, label="SL"
                            )
                            
                            if not success:
                                # SL cancel failed - increment counter and check threshold
                                if state.cancel_attempt_count is None:
                                    state.cancel_attempt_count = 0
                                state.cancel_attempt_count += 1
                                
                                if state.cancel_attempt_count >= MAX_CANCEL_TICKS:
                                    # Maximum attempts reached - stop retrying
                                    logger.critical(
                                        f"Maximum cancel attempts reached ({MAX_CANCEL_TICKS}) for SL order {state.sl_order_id}. "
                                        f"TP filled at {fill_price}. User: {context.config.user_id}, Strategy: {context.config.strategy_id}. "
                                        f"Position: {state.position_symbol} x {state.position_qty} @ {state.position_entry_price}. "
                                        f"HUMAN INTERVENTION REQUIRED."
                                    )
                                    state.status = "error"
                                    state.error_message = (
                                        f"TP filled at {fill_price} but SL order {state.sl_order_id} could not be cancelled "
                                        f"after {MAX_CANCEL_TICKS} attempts. Position economically closed. "
                                        f"Manual verification required for orphan SL order."
                                    )
                                    state.has_open_position = False
                                    await db.commit()
                                    context.cached_state = None
                                    return
                                else:
                                    # Still below threshold - mark for retry on next tick
                                    logger.error(
                                        f"CRITICAL: TP filled but SL cancel failed (attempt {state.cancel_attempt_count}/{MAX_CANCEL_TICKS}): {error_msg}. "
                                        f"SL order {state.sl_order_id} may still be live. "
                                        f"Will retry on next tick. (user: {context.config.user_id})"
                                    )
                                    state.error_message = (
                                        f"TP filled at {fill_price} but SL cancel failed after {MAX_CANCEL_ATTEMPTS} retries. "
                                        f"SL order {state.sl_order_id} may still be live on broker. "
                                        f"Retry attempt {state.cancel_attempt_count}/{MAX_CANCEL_TICKS}. "
                                        f"ERROR: {error_msg}"
                                    )
                                    # Do NOT close position in DB until cancel succeeds
                                    await db.commit()
                                    context.cached_state = None
                                    return
                        
                        # SL cancelled successfully - reset counter and close position
                        state.cancel_attempt_count = 0
                        await close_position_in_db(db, state, "TARGET", fill_price)
                        await db.commit()
                        context.cached_state = None
                        return
                
                except Exception as e:
                    logger.error(f"Error checking TP order (user: {context.config.user_id}): {e}", exc_info=True)
            
            # Check SL order
            if state.sl_order_id:
                try:
                    is_filled, fill_price = await adapter.is_order_filled(
                        context.config.user_id, token, state.sl_order_id
                    )
                    
                    if is_filled:
                        logger.info(f"STOPLOSS HIT at {fill_price} (user: {context.config.user_id})")
                        
                        # Cancel TP order with retry
                        if state.tp_order_id:
                            success, error_msg = await cancel_order_with_retry(
                                adapter, context.config.user_id, token, state.tp_order_id,
                                max_attempts=MAX_CANCEL_ATTEMPTS, label="TP"
                            )
                            
                            if not success:
                                # TP cancel failed - increment counter and check threshold
                                if state.cancel_attempt_count is None:
                                    state.cancel_attempt_count = 0
                                state.cancel_attempt_count += 1
                                
                                if state.cancel_attempt_count >= MAX_CANCEL_TICKS:
                                    # Maximum attempts reached - stop retrying
                                    logger.critical(
                                        f"Maximum cancel attempts reached ({MAX_CANCEL_TICKS}) for TP order {state.tp_order_id}. "
                                        f"SL filled at {fill_price}. User: {context.config.user_id}, Strategy: {context.config.strategy_id}. "
                                        f"Position: {state.position_symbol} x {state.position_qty} @ {state.position_entry_price}. "
                                        f"HUMAN INTERVENTION REQUIRED."
                                    )
                                    state.status = "error"
                                    state.error_message = (
                                        f"SL filled at {fill_price} but TP order {state.tp_order_id} could not be cancelled "
                                        f"after {MAX_CANCEL_TICKS} attempts. Position economically closed. "
                                        f"Manual verification required for orphan TP order."
                                    )
                                    state.has_open_position = False
                                    await db.commit()
                                    context.cached_state = None
                                    return
                                else:
                                    # Still below threshold - mark for retry on next tick
                                    logger.error(
                                        f"CRITICAL: SL filled but TP cancel failed (attempt {state.cancel_attempt_count}/{MAX_CANCEL_TICKS}): {error_msg}. "
                                        f"TP order {state.tp_order_id} may still be live. "
                                        f"Will retry on next tick. (user: {context.config.user_id})"
                                    )
                                    state.error_message = (
                                        f"SL filled at {fill_price} but TP cancel failed after {MAX_CANCEL_ATTEMPTS} retries. "
                                        f"TP order {state.tp_order_id} may still be live on broker. "
                                        f"Retry attempt {state.cancel_attempt_count}/{MAX_CANCEL_TICKS}. "
                                        f"ERROR: {error_msg}"
                                    )
                                    # Do NOT close position in DB until cancel succeeds
                                    await db.commit()
                                    context.cached_state = None
                                    return
                        
                        # TP cancelled successfully - reset counter and close position
                        state.cancel_attempt_count = 0
                        await close_position_in_db(db, state, "STOPLOSS", fill_price)
                        await db.commit()
                        context.cached_state = None
                        return
                
                except Exception as e:
                    logger.error(f"Error checking SL order (user: {context.config.user_id}): {e}", exc_info=True)
    
    except Exception as e:
        logger.error(f"Error in position monitoring (user: {context.config.user_id}): {e}", exc_info=True)
