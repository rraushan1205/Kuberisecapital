"""
Shared types and enums for broker operations.

This module defines common types used across all broker implementations.
These types provide a consistent interface for broker operations regardless
of the underlying broker API differences.

Design rationale:
    - Follows existing enum pattern from app.models.domain (UserRole, BrokerStatus, etc.)
    - Uses str enums for JSON serialization compatibility
    - Provides type hints for broker method signatures
    - Enables static type checking with mypy
"""

import enum
from typing import TypedDict


class OrderType(str, enum.Enum):
    """
    Standard order types supported across brokers.
    
    Not all brokers support all order types. Broker implementations should
    raise BrokerValidationError if an unsupported order type is requested.
    """

    MARKET = "MARKET"  # Execute at current market price
    LIMIT = "LIMIT"  # Execute at specified price or better
    STOP_LOSS = "STOP_LOSS"  # Trigger when price reaches stop price
    STOP_LOSS_MARKET = "STOP_LOSS_MARKET"  # Market order triggered at stop price


class OrderSide(str, enum.Enum):
    """Order direction: buy or sell."""

    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, enum.Enum):
    """
    Standard order statuses.
    
    Broker-specific statuses should be mapped to these standard values
    to provide consistent behavior across different brokers.
    """

    PENDING = "PENDING"  # Order placed, awaiting execution
    OPEN = "OPEN"  # Order active in the market
    COMPLETE = "COMPLETE"  # Order fully executed
    CANCELLED = "CANCELLED"  # Order cancelled by user or system
    REJECTED = "REJECTED"  # Order rejected by broker or exchange
    EXPIRED = "EXPIRED"  # Order expired (for GTD orders)


class OrderValidity(str, enum.Enum):
    """Order validity/duration."""

    DAY = "DAY"  # Valid for the trading day
    IOC = "IOC"  # Immediate or cancel
    GTC = "GTC"  # Good till cancelled (if supported)


class PositionType(str, enum.Enum):
    """Position type classification."""

    INTRADAY = "INTRADAY"  # Intraday/MIS positions
    DELIVERY = "DELIVERY"  # Delivery/CNC positions
    CARRYFORWARD = "CARRYFORWARD"  # Overnight/NRML positions


class ExchangeSegment(str, enum.Enum):
    """
    Exchange segments for Indian markets.
    
    Different brokers may use different naming conventions. Implementations
    should map broker-specific segment names to these standard values.
    """

    NSE_EQ = "NSE_EQ"  # NSE Cash/Equity
    NSE_FO = "NSE_FO"  # NSE Futures & Options
    NSE_CD = "NSE_CD"  # NSE Currency Derivatives
    BSE_EQ = "BSE_EQ"  # BSE Cash/Equity
    BSE_FO = "BSE_FO"  # BSE Futures & Options
    MCX_FO = "MCX_FO"  # MCX Commodity Derivatives
    NFO = "NFO"  # NSE Futures & Options (alternate)
    CDS = "CDS"  # Currency Derivatives Segment


class ProductType(str, enum.Enum):
    """
    Product types for order placement.
    
    These determine margin requirements and position duration.
    """

    INTRADAY = "INTRADAY"  # Intraday/MIS (higher leverage)
    DELIVERY = "DELIVERY"  # Delivery/CNC (no leverage)
    CARRYFORWARD = "CARRYFORWARD"  # Overnight/NRML (moderate leverage)
    MARGIN = "MARGIN"  # Margin trading (if supported)


class Interval(str, enum.Enum):
    """
    Time intervals for historical data (candles/OHLCV).
    
    Supported intervals for historical chart data. Not all brokers
    support all intervals.
    """

    MINUTE_1 = "1m"
    MINUTE_3 = "3m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_2 = "2h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"


# Type definitions for structured data
# These use TypedDict for runtime type checking and IDE autocomplete


class BrokerProfile(TypedDict, total=False):
    """
    User profile information from broker.
    
    Fields marked as NotRequired (total=False) may not be available
    from all brokers.
    """

    user_id: str  # Broker's internal user ID
    user_name: str  # User's registered name
    email: str  # Email address
    mobile: str  # Mobile number
    pan: str  # PAN card number (India-specific)
    broker: str  # Broker name/code
    products: list[str]  # Enabled product types
    exchanges: list[str]  # Accessible exchanges
    order_types: list[str]  # Supported order types


class Funds(TypedDict, total=False):
    """Available funds in trading account."""

    available_cash: float  # Cash available for trading
    used_margin: float  # Margin currently in use
    available_margin: float  # Margin available for new positions
    collateral: float  # Collateral value (securities)
    total: float  # Total funds (cash + collateral)
    currency: str  # Currency code (e.g., "INR")


class Position(TypedDict, total=False):
    """Trading position information."""

    symbol: str  # Trading symbol
    exchange: str  # Exchange segment
    product: str  # Product type (INTRADAY, DELIVERY, etc.)
    quantity: int  # Net quantity (positive=long, negative=short)
    average_price: float  # Average buy/sell price
    last_price: float  # Current market price
    pnl: float  # Realized + unrealized P&L
    realized_pnl: float  # Realized profit/loss
    unrealized_pnl: float  # Unrealized profit/loss
    day_buy_quantity: int  # Quantity bought today
    day_sell_quantity: int  # Quantity sold today
    day_buy_price: float  # Average buy price today
    day_sell_price: float  # Average sell price today
    overnight_quantity: int  # Carried forward quantity


class Holding(TypedDict, total=False):
    """Long-term investment holding."""

    symbol: str  # Trading symbol
    exchange: str  # Exchange segment
    isin: str  # ISIN code
    quantity: int  # Total quantity
    average_price: float  # Average acquisition price
    last_price: float  # Current market price
    pnl: float  # Profit/loss
    pnl_percentage: float  # P&L as percentage
    collateral_type: str  # Collateral category (if applicable)
    collateral_quantity: int  # Quantity pledged as collateral


class Order(TypedDict, total=False):
    """Order information."""

    order_id: str  # Broker's order ID
    exchange_order_id: str  # Exchange order ID
    parent_order_id: str  # Parent order ID (for bracket/cover orders)
    symbol: str  # Trading symbol
    exchange: str  # Exchange segment
    order_type: str  # MARKET, LIMIT, etc.
    side: str  # BUY or SELL
    product: str  # Product type
    quantity: int  # Order quantity
    price: float  # Limit price (for limit orders)
    trigger_price: float  # Stop-loss trigger price
    filled_quantity: int  # Executed quantity
    pending_quantity: int  # Pending quantity
    cancelled_quantity: int  # Cancelled quantity
    average_price: float  # Average execution price
    status: str  # Order status
    validity: str  # Order validity (DAY, IOC, etc.)
    order_timestamp: str  # Order placed time
    exchange_timestamp: str  # Exchange timestamp
    status_message: str  # Status/rejection message
    tag: str  # Custom tag/label


class Quote(TypedDict, total=False):
    """Real-time market quote."""

    symbol: str  # Trading symbol
    exchange: str  # Exchange segment
    last_price: float  # Last traded price (LTP)
    last_quantity: int  # Last traded quantity
    last_trade_time: str  # Last trade timestamp
    open: float  # Opening price
    high: float  # Day high
    low: float  # Day low
    close: float  # Previous close
    volume: int  # Total volume traded
    bid_price: float  # Best bid price
    bid_quantity: int  # Best bid quantity
    ask_price: float  # Best ask price
    ask_quantity: int  # Best ask quantity
    oi: int  # Open interest (for F&O)
    oi_change: int  # Change in open interest


class Candle(TypedDict):
    """
    OHLCV candle data.
    
    All fields are required for candle data.
    """

    timestamp: str  # ISO timestamp
    open: float
    high: float
    low: float
    close: float
    volume: int


class OrderRequest(TypedDict, total=False):
    """
    Order placement request.
    
    This is the input structure for place_order() method.
    """

    symbol: str  # Required
    exchange: str  # Required
    side: str  # Required: BUY or SELL
    order_type: str  # Required: MARKET, LIMIT, etc.
    quantity: int  # Required
    product: str  # Required: INTRADAY, DELIVERY, etc.
    price: float  # Required for LIMIT orders
    trigger_price: float  # Required for SL orders
    validity: str  # Optional: DAY, IOC, GTC
    disclosed_quantity: int  # Optional: Iceberg order quantity
    tag: str  # Optional: Custom tag
