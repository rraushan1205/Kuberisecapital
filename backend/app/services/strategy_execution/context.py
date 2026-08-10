"""
Strategy Execution Context
Manages per-user execution state, broker tokens, and signal queue.
"""
import logging
from dataclasses import dataclass
from uuid import UUID
from datetime import datetime, timedelta
import asyncio
from typing import Callable, Any

from sqlalchemy.ext.asyncio import AsyncSession
from app.services.brokers.manager import BrokerManager
from app.services.crypto import decrypt_token
from app.models.domain import BrokerConnection

logger = logging.getLogger(__name__)


@dataclass
class StrategyConfig:
    """Configuration for a user's strategy execution"""
    strategy_id: int
    user_id: UUID
    broker: str
    symbols: dict  # {"index": "NSE:NIFTY50-INDEX", "option_ce": "...", "option_pe": "..."}
    params: dict   # {"qty": 200, "target_points": 50, "sl_points": 25}


class StrategyExecutionContext:
    """
    Per-user execution context.
    Handles token caching, signal queue, and shared state.
    """
    
    def __init__(
        self,
        config: StrategyConfig,
        db_session_maker: Callable,
        broker_manager: BrokerManager
    ):
        self.config = config
        self.db_session_maker = db_session_maker
        self.broker_manager = broker_manager
        
        # Token cache (refreshed every 30 min)
        self._token_cache: str | None = None
        self._token_fetched_at: datetime | None = None
        
        # Signal communication between engines
        self._signal_queue: asyncio.Queue = asyncio.Queue()
        
        # Shutdown flag
        self._shutdown = asyncio.Event()
    
    async def get_broker_token(self, force_refresh: bool = False) -> str:
        """
        Get cached broker access token, or fetch from DB if stale.
        Tokens are cached for 30 minutes to reduce DB queries.
        Proactively refreshes if within 5 minutes of expiry.
        
        Args:
            force_refresh: Force token refresh from DB, bypassing cache
        
        Returns:
            Decrypted broker access token
        
        Raises:
            ValueError: If no broker connection found or token fetch fails
        """
        now = datetime.utcnow()
        
        # Check if proactive refresh is needed (within 5 minutes of cache expiry)
        if (not force_refresh and self._token_cache and self._token_fetched_at):
            time_since_fetch = now - self._token_fetched_at
            
            # Token still fresh (more than 5 min before expiry)
            if time_since_fetch < timedelta(minutes=25):
                return self._token_cache
            
            # Token approaching expiry (less than 5 min remaining)
            # Proactively refresh to avoid mid-operation expiry
            logger.info(
                f"Token approaching expiry (age: {time_since_fetch.total_seconds()/60:.1f}m), "
                f"proactively refreshing (user: {self.config.user_id})"
            )
        
        # Fetch from database
        try:
            async with self.db_session_maker() as db:
                from sqlalchemy import select
                
                result = await db.execute(
                    select(BrokerConnection)
                    .where(BrokerConnection.user_id == self.config.user_id)
                    .where(BrokerConnection.provider == self.config.broker)
                )
                broker_conn = result.scalar_one_or_none()
                
                if not broker_conn or not broker_conn.access_token_encrypted:
                    error_msg = f"No broker connection found for user {self.config.user_id}, broker {self.config.broker}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                # Check if broker token has expired
                if broker_conn.token_expires_at and broker_conn.token_expires_at < now:
                    logger.warning(
                        f"Broker token expired at {broker_conn.token_expires_at} "
                        f"(user: {self.config.user_id})"
                    )
                    # TODO: Trigger token refresh flow if implemented
                    # For now, attempt to use it anyway - broker will reject if truly expired
                
                # Decrypt token
                decrypted_token = decrypt_token(broker_conn.access_token_encrypted)
                
                # Update cache
                self._token_cache = decrypted_token
                self._token_fetched_at = now
                
                logger.debug(f"Token refreshed from DB (user: {self.config.user_id})")
                
                return decrypted_token
        
        except Exception as e:
            logger.error(
                f"Failed to fetch broker token for user {self.config.user_id}: {e}",
                exc_info=True
            )
            # Invalidate cache on error
            self._token_cache = None
            self._token_fetched_at = None
            raise
    
    def invalidate_token_cache(self):
        """Force token refresh on next request"""
        self._token_cache = None
        self._token_fetched_at = None
    
    async def put_signal(self, signal: dict):
        """Signal engine puts signals here"""
        await self._signal_queue.put(signal)
    
    async def get_signal(self, timeout: float = 2.0) -> dict | None:
        """Execution engine retrieves signals"""
        try:
            return await asyncio.wait_for(self._signal_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
    
    def request_shutdown(self):
        """Request graceful shutdown of both engines"""
        self._shutdown.set()
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown is requested"""
        return self._shutdown.is_set()
