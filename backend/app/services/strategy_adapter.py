"""
Strategy Adapter Layer
Provides strategy-friendly wrappers around BrokerProvider.
Converts between pandas DataFrames and broker API objects.
"""
import logging
from typing import List, Tuple
from uuid import UUID
from datetime import datetime, timedelta
import pandas as pd
import pytz

from app.services.brokers.base import BrokerProvider
from app.services.brokers.types import Candle, Quote, Order, OrderRequest

logger = logging.getLogger(__name__)


class StrategyAdapter:
    """
    Adapter between strategy code and BrokerProvider.
    Handles format conversions and provides convenience methods.
    """
    
    def __init__(self, broker: BrokerProvider):
        self.broker = broker
    
    async def get_candles_as_dataframe(
        self,
        user_id: UUID,
        access_token: str,
        symbol: str,
        interval: str,  # "1m", "5m", "15m", "1h", "1d"
        lookback_days: int = 5
    ) -> pd.DataFrame:
        """
        Fetch historical candles and return as pandas DataFrame.
        
        Returns DataFrame with columns: open, high, low, close, volume, oi
        Index is DatetimeIndex in IST timezone.
        """
        ist = pytz.timezone('Asia/Kolkata')
        to_date = datetime.now(ist)
        from_date = to_date - timedelta(days=lookback_days)
        
        candles: List[Candle] = await self.broker.get_historical_data(
            user_id=user_id,
            access_token=access_token,
            symbol=symbol,
            interval=interval,
            from_date=from_date,
            to_date=to_date
        )
        
        if not candles:
            return pd.DataFrame()
        
        df = pd.DataFrame([{
            'open': c.open,
            'high': c.high,
            'low': c.low,
            'close': c.close,
            'volume': c.volume,
            'oi': getattr(c, 'oi', None)  # Optional for options - None if not available
        } for c in candles])
        
        df.index = pd.DatetimeIndex([c.timestamp for c in candles])
        return df.sort_index()
    
    async def get_ltp(
        self,
        user_id: UUID,
        access_token: str,
        symbol: str
    ) -> float:
        """
        Get last traded price for a single symbol.
        Convenience wrapper around get_quotes().
        """
        quotes: List[Quote] = await self.broker.get_quotes(
            user_id=user_id,
            access_token=access_token,
            symbols=[symbol]
        )
        
        if not quotes:
            raise ValueError(f"No quote data for symbol: {symbol}")
        
        return quotes[0].last_price
    
    async def place_market_order(
        self,
        user_id: UUID,
        access_token: str,
        symbol: str,
        quantity: int,
        side: str,  # "BUY" or "SELL"
        product: str = "INTRADAY"
    ) -> Order:
        """
        Place a market order. Returns Order with order_id.
        """
        order_request = OrderRequest(
            symbol=symbol,
            quantity=quantity,
            side=side,
            order_type="MARKET",
            product=product,
            validity="DAY"
        )
        
        return await self.broker.place_order(
            user_id=user_id,
            access_token=access_token,
            order=order_request
        )
    
    async def place_limit_order(
        self,
        user_id: UUID,
        access_token: str,
        symbol: str,
        quantity: int,
        side: str,
        price: float,
        product: str = "INTRADAY"
    ) -> Order:
        """Place a limit order at specified price."""
        order_request = OrderRequest(
            symbol=symbol,
            quantity=quantity,
            side=side,
            order_type="LIMIT",
            price=price,
            product=product,
            validity="DAY"
        )
        
        return await self.broker.place_order(
            user_id=user_id,
            access_token=access_token,
            order=order_request
        )
    
    async def place_stoploss_order(
        self,
        user_id: UUID,
        access_token: str,
        symbol: str,
        quantity: int,
        side: str,
        trigger_price: float,
        product: str = "INTRADAY"
    ) -> Order:
        """Place a stop-loss market order."""
        order_request = OrderRequest(
            symbol=symbol,
            quantity=quantity,
            side=side,
            order_type="STOP_LOSS_MARKET",
            trigger_price=trigger_price,
            product=product,
            validity="DAY"
        )
        
        return await self.broker.place_order(
            user_id=user_id,
            access_token=access_token,
            order=order_request
        )
    
    async def cancel_order(
        self,
        user_id: UUID,
        access_token: str,
        order_id: str
    ) -> bool:
        """Cancel an open order."""
        return await self.broker.cancel_order(
            user_id=user_id,
            access_token=access_token,
            order_id=order_id
        )
    
    async def is_order_filled(
        self,
        user_id: UUID,
        access_token: str,
        order_id: str
    ) -> Tuple[bool, float]:
        """
        Check if order is filled.
        Returns (is_filled: bool, average_price: float)
        
        Note: Broker implementations should normalize order status to canonical values
        (COMPLETE, PENDING, CANCELLED, REJECTED). Partial fills are treated as not filled.
        """
        order = await self.broker.get_order_details(
            user_id=user_id,
            access_token=access_token,
            order_id=order_id
        )
        
        # Canonical filled status (normalized by broker implementations)
        is_filled = order.status == "COMPLETE"
        
        # Warn on partial fills - these need explicit handling
        if order.status == "PARTIAL" or (
            hasattr(order, 'filled_quantity') and 
            hasattr(order, 'quantity') and
            0 < order.get('filled_quantity', 0) < order.get('quantity', 0)
        ):
            logger.warning(
                f"Order {order_id} partially filled: "
                f"{order.get('filled_quantity', 0)}/{order.get('quantity', 0)} "
                f"(user: {user_id})"
            )
        
        avg_price = order.get('average_price', 0.0) or 0.0
        
        return is_filled, avg_price
    
    async def get_positions(
        self,
        user_id: UUID,
        access_token: str
    ) -> List:
        """Get all open positions."""
        return await self.broker.get_positions(
            user_id=user_id,
            access_token=access_token
        )
