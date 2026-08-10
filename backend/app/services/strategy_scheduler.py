"""
Strategy Scheduler
Manages lifecycle of all active strategy executions across multiple users.
"""
import asyncio
import logging
import os
from typing import Dict, Tuple, Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import StrategyState
from app.services.brokers.manager import BrokerManager
from app.services.strategy_execution import (
    StrategyConfig,
    StrategyExecutionContext,
    signal_engine_loop,
    execution_engine_loop
)
from app.services.strategy_execution.utils import get_or_create_strategy_state, mark_strategy_status

logger = logging.getLogger(__name__)

# Graceful shutdown timeout - configurable via environment variable
GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS = int(
    os.environ.get('STRATEGY_SHUTDOWN_TIMEOUT_SECONDS', '30')
)


class StrategyScheduler:
    """
    Singleton service managing all strategy executions.
    Runs as part of FastAPI lifespan, survives across requests.
    """
    
    def __init__(
        self,
        db_session_maker: Callable,
        broker_manager: BrokerManager
    ):
        self.db_session_maker = db_session_maker
        self.broker_manager = broker_manager
        
        # Track active strategy tasks: (user_id, strategy_id) -> asyncio.Task
        self.active_tasks: Dict[Tuple[UUID, int], asyncio.Task] = {}
        
        # Health monitor task
        self.health_monitor_task: asyncio.Task | None = None
        
        # Shutdown flag
        self._shutdown = False
    
    async def start(self):
        """
        Called on FastAPI startup.
        Loads all 'running' strategies from DB and starts them.
        """
        logger.info("StrategyScheduler starting...")
        
        try:
            # Load all strategies marked as 'running'
            async with self.db_session_maker() as db:
                result = await db.execute(
                    select(StrategyState).where(StrategyState.status == "running")
                )
                running_states = result.scalars().all()
            
            # Restart each running strategy
            for state in running_states:
                try:
                    await self._start_strategy_internal(state.user_id, state.strategy_id, state.broker)
                except Exception as e:
                    logger.error(f"Failed to restart strategy {state.strategy_id} for user {state.user_id}: {e}")
            
            # Start health monitor
            self.health_monitor_task = asyncio.create_task(self._health_monitor_loop())
            
            logger.info(f"StrategyScheduler started with {len(self.active_tasks)} active strategies")
        
        except Exception as e:
            logger.error(f"Error starting StrategyScheduler: {e}", exc_info=True)
    
    async def stop(self):
        """
        Called on FastAPI shutdown.
        Gracefully stops all running strategies.
        """
        logger.info("StrategyScheduler stopping...")
        self._shutdown = True
        
        # Cancel health monitor
        if self.health_monitor_task:
            self.health_monitor_task.cancel()
            try:
                await self.health_monitor_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all strategy tasks
        for (user_id, strategy_id), task in list(self.active_tasks.items()):
            logger.info(f"Cancelling strategy {strategy_id} for user {user_id}")
            task.cancel()
        
        # Wait for graceful shutdown with extended timeout
        if self.active_tasks:
            logger.info(
                f"Waiting up to {GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS}s for "
                f"{len(self.active_tasks)} strategies to shutdown gracefully..."
            )
            
            done, pending = await asyncio.wait(
                self.active_tasks.values(),
                timeout=float(GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS),
                return_when=asyncio.ALL_COMPLETED
            )
            
            if pending:
                # Log each pending strategy for manual review
                logger.error(
                    f"{len(pending)} strategies did not stop gracefully within "
                    f"{GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS}s. These require manual review:"
                )
                for (user_id, strategy_id), task in self.active_tasks.items():
                    if task in pending:
                        logger.error(
                            f"  - Strategy {strategy_id} for user {user_id} still running"
                        )
        
        logger.info("StrategyScheduler stopped")
    
    async def start_strategy(self, user_id: UUID, strategy_id: int, broker: str):
        """
        Start a strategy for a user.
        Called via API endpoint.
        """
        key = (user_id, strategy_id)
        
        if key in self.active_tasks:
            raise ValueError(f"Strategy {strategy_id} already running for user {user_id}")
        
        # Mark as running in DB
        async with self.db_session_maker() as db:
            state = await get_or_create_strategy_state(db, user_id, strategy_id, broker)
            await mark_strategy_status(db, user_id, strategy_id, "running")
            await db.commit()
        
        # Start execution
        await self._start_strategy_internal(user_id, strategy_id, broker)
        
        logger.info(f"Strategy {strategy_id} started for user {user_id}")
    
    async def stop_strategy(self, user_id: UUID, strategy_id: int):
        """
        Stop a running strategy.
        Called via API endpoint.
        """
        key = (user_id, strategy_id)
        
        if key not in self.active_tasks:
            raise ValueError(f"Strategy {strategy_id} not running for user {user_id}")
        
        # Cancel task
        task = self.active_tasks[key]
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        del self.active_tasks[key]
        
        # Mark as stopped in DB
        async with self.db_session_maker() as db:
            await mark_strategy_status(db, user_id, strategy_id, "stopped")
            await db.commit()
        
        logger.info(f"Strategy {strategy_id} stopped for user {user_id}")
    
    def get_active_count(self) -> int:
        """Get number of active strategies"""
        return len(self.active_tasks)
    
    def is_strategy_running(self, user_id: UUID, strategy_id: int) -> bool:
        """Check if strategy is currently running"""
        return (user_id, strategy_id) in self.active_tasks
    
    async def _start_strategy_internal(self, user_id: UUID, strategy_id: int, broker: str):
        """Internal method to start strategy execution"""
        
        # Create strategy config
        # TODO: Load these from database or config
        config = StrategyConfig(
            strategy_id=strategy_id,
            user_id=user_id,
            broker=broker,
            symbols={
                "index": "NSE:NIFTY50-INDEX",
                "option_ce": "NSE:NIFTY50-CE",  # Placeholder
                "option_pe": "NSE:NIFTY50-PE"   # Placeholder
            },
            params={
                "qty": 200,
                "target_points": 50,
                "sl_points": 25,
                "monitor_interval_seconds": 5  # Configurable position monitoring interval
            }
        )
        
        # Create execution context
        context = StrategyExecutionContext(
            config=config,
            db_session_maker=self.db_session_maker,
            broker_manager=self.broker_manager
        )
        
        # Start execution task
        key = (user_id, strategy_id)
        task = asyncio.create_task(self._run_strategy(context))
        
        # Add done callback for immediate crash detection
        task.add_done_callback(
            lambda t: asyncio.create_task(
                self._handle_task_completion(user_id, strategy_id, t)
            )
        )
        
        self.active_tasks[key] = task
    
    async def _run_strategy(self, context: StrategyExecutionContext):
        """
        Main execution wrapper for one strategy.
        Runs both signal and execution engines concurrently.
        """
        user_id = context.config.user_id
        strategy_id = context.config.strategy_id
        
        try:
            logger.info(f"Starting strategy execution: user={user_id}, strategy={strategy_id}")
            
            # Run both engines concurrently
            await asyncio.gather(
                signal_engine_loop(context),
                execution_engine_loop(context)
            )
        
        except asyncio.CancelledError:
            logger.info(f"Strategy cancelled: user={user_id}, strategy={strategy_id}")
            raise
        
        except Exception as e:
            logger.error(f"Strategy crashed: user={user_id}, strategy={strategy_id}, error={e}", exc_info=True)
            
            # Mark as error in DB
            try:
                async with context.db_session_maker() as db:
                    await mark_strategy_status(db, user_id, strategy_id, "error", str(e))
                    await db.commit()
            except Exception as db_error:
                logger.error(f"Failed to mark strategy error in DB: {db_error}")
    
    async def _handle_task_completion(self, user_id: UUID, strategy_id: int, task: asyncio.Task):
        """
        Handle immediate task completion/crash detection via callback.
        
        Args:
            user_id: User ID
            strategy_id: Strategy ID
            task: The completed task
        """
        key = (user_id, strategy_id)
        
        try:
            # Check if task raised an exception (not just cancellation)
            exception = None
            try:
                exception = task.exception()
            except asyncio.CancelledError:
                # Task was cancelled normally
                logger.info(f"Strategy task cancelled normally: user={user_id}, strategy={strategy_id}")
                
                # Remove from active tasks
                if key in self.active_tasks:
                    del self.active_tasks[key]
                
                # Mark as stopped in DB
                async with self.db_session_maker() as db:
                    await mark_strategy_status(db, user_id, strategy_id, "stopped")
                    await db.commit()
                
                return
            
            if exception:
                # Task crashed with an exception
                logger.error(
                    f"Strategy task crashed: user={user_id}, strategy={strategy_id}, "
                    f"exception={exception}",
                    exc_info=exception
                )
                
                # Remove from active tasks
                if key in self.active_tasks:
                    del self.active_tasks[key]
                
                # Mark as error in DB
                async with self.db_session_maker() as db:
                    await mark_strategy_status(db, user_id, strategy_id, "error", str(exception))
                    await db.commit()
                
                # TODO: Fire alert/notification if notification system exists
                
            else:
                # Task ended normally without exception
                logger.info(f"Strategy task ended normally: user={user_id}, strategy={strategy_id}")
                
                # Remove from active tasks
                if key in self.active_tasks:
                    del self.active_tasks[key]
                
                # Mark as stopped in DB
                async with self.db_session_maker() as db:
                    await mark_strategy_status(db, user_id, strategy_id, "stopped")
                    await db.commit()
        
        except Exception as e:
            logger.error(
                f"Error in task completion handler for user={user_id}, strategy={strategy_id}: {e}",
                exc_info=True
            )
    
    async def _health_monitor_loop(self):
        """
        Background task that monitors all strategy tasks.
        Runs every 10 seconds as a safety net for tasks that slip through callbacks.
        Reconciles active_tasks against DB state.
        """
        while not self._shutdown:
            try:
                await asyncio.sleep(10)  # Reduced from 60s to 10s
                
                # Check all tasks (safety net - most should be caught by callbacks)
                for key, task in list(self.active_tasks.items()):
                    user_id, strategy_id = key
                    
                    if task.done():
                        # Task completed but callback may have failed
                        logger.warning(
                            f"Health monitor caught completed task (callback may have failed): "
                            f"user={user_id}, strategy={strategy_id}"
                        )
                        
                        exception = None
                        try:
                            exception = task.exception()
                        except asyncio.CancelledError:
                            exception = None
                        
                        if exception:
                            logger.error(
                                f"Strategy task died (caught by health monitor): user={user_id}, "
                                f"strategy={strategy_id}, exception={exception}"
                            )
                        
                        # Remove from active tasks
                        del self.active_tasks[key]
                        
                        # Mark as stopped in DB
                        try:
                            async with self.db_session_maker() as db:
                                status = "error" if exception else "stopped"
                                error_msg = str(exception) if exception else None
                                await mark_strategy_status(db, user_id, strategy_id, status, error_msg)
                                await db.commit()
                        except Exception as e:
                            logger.error(f"Failed to update strategy status in DB: {e}")
                
                logger.debug(f"Health monitor: {len(self.active_tasks)} active strategies")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitor: {e}", exc_info=True)
        
        logger.info("Health monitor stopped")
