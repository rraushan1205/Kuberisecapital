"""
Shared constants for broker operations.

This module defines constants used across broker implementations to ensure
consistency and avoid magic numbers/strings throughout the codebase.

Design rationale:
    - Centralized configuration for timeout values, limits, etc.
    - Follows Python constant naming convention (UPPER_SNAKE_CASE)
    - Values based on common broker API limitations and best practices
"""

# API Timeout Configuration
# Most broker APIs should respond within these timeframes
DEFAULT_API_TIMEOUT_SECONDS = 30  # Standard API request timeout
QUOTE_API_TIMEOUT_SECONDS = 10  # Faster timeout for real-time quotes
HISTORICAL_DATA_TIMEOUT_SECONDS = 60  # Longer timeout for bulk historical data
WEBSOCKET_CONNECT_TIMEOUT_SECONDS = 15  # WebSocket connection timeout
WEBSOCKET_PING_INTERVAL_SECONDS = 30  # WebSocket ping interval to keep alive

# Rate Limiting
# These are conservative defaults. Individual brokers may have stricter limits.
DEFAULT_RATE_LIMIT_PER_SECOND = 10  # Maximum requests per second
DEFAULT_RATE_LIMIT_PER_MINUTE = 600  # Maximum requests per minute
RATE_LIMIT_RETRY_ATTEMPTS = 3  # Number of retry attempts on rate limit
RATE_LIMIT_BACKOFF_SECONDS = 5  # Initial backoff duration

# Token Management
TOKEN_EXPIRY_BUFFER_SECONDS = 300  # Refresh token 5 minutes before expiry
TOKEN_REFRESH_RETRY_ATTEMPTS = 3  # Retry attempts for token refresh
DEFAULT_TOKEN_VALIDITY_HOURS = 24  # Default token validity (broker-specific)

# Order Limits
MAX_ORDER_QUANTITY = 100000  # Maximum single order quantity (conservative)
MIN_ORDER_QUANTITY = 1  # Minimum order quantity
MAX_DISCLOSED_QUANTITY_PERCENT = 10  # Max disclosed quantity as % of total

# Retry Configuration
# For transient errors like network issues
MAX_RETRY_ATTEMPTS = 3  # Maximum number of retry attempts
INITIAL_RETRY_DELAY_SECONDS = 1  # Initial delay before first retry
MAX_RETRY_DELAY_SECONDS = 30  # Maximum delay between retries
RETRY_BACKOFF_MULTIPLIER = 2  # Exponential backoff multiplier

# Historical Data Limits
# Maximum number of candles to fetch in a single request
MAX_HISTORICAL_CANDLES = 5000
MAX_HISTORICAL_DAYS = 365  # Maximum lookback period

# Symbol/Instrument Limits
MAX_SYMBOLS_PER_QUOTE_REQUEST = 500  # Max symbols in a single quote request
MAX_SYMBOLS_PER_WEBSOCKET_SUBSCRIPTION = 1000  # Max WebSocket subscriptions

# Cache Configuration
# TTL values for caching broker data
PROFILE_CACHE_TTL_SECONDS = 3600  # Cache user profile for 1 hour
FUNDS_CACHE_TTL_SECONDS = 60  # Cache funds for 1 minute
HOLDINGS_CACHE_TTL_SECONDS = 300  # Cache holdings for 5 minutes
INSTRUMENTS_CACHE_TTL_SECONDS = 86400  # Cache instrument list for 24 hours

# WebSocket Configuration
WEBSOCKET_MAX_RECONNECT_ATTEMPTS = 5  # Max reconnection attempts
WEBSOCKET_RECONNECT_DELAY_SECONDS = 5  # Delay between reconnect attempts
WEBSOCKET_MESSAGE_QUEUE_SIZE = 1000  # Max messages in queue before dropping

# Supported Brokers
# Registry of known broker providers
# This list is used for validation and documentation purposes
SUPPORTED_BROKERS = [
    "zerodha",
    "fyers",
    "groww",
    "dhan",
    "angelone",
    "upstox",
    "5paisa",
    "aliceblue",
    "iifl",
    "kotak",
]

# Broker API Version Compatibility
# Some brokers may have multiple API versions
API_VERSION_DEFAULT = "v1"  # Default API version if not specified

# Error Messages
# Standardized error messages for common scenarios
ERROR_BROKER_NOT_FOUND = "Broker provider '{provider}' is not registered"
ERROR_BROKER_NOT_CONFIGURED = "Broker '{provider}' is not properly configured"
ERROR_TOKEN_MISSING = "No authentication token found for user {user_id}"
ERROR_TOKEN_EXPIRED = "Authentication token has expired"
ERROR_TOKEN_INVALID = "Authentication token is invalid or malformed"
ERROR_RATE_LIMIT_EXCEEDED = "Rate limit exceeded for broker '{provider}'"
ERROR_MARKET_CLOSED = "Market is currently closed"
ERROR_INSUFFICIENT_FUNDS = "Insufficient funds for the operation"
ERROR_INVALID_SYMBOL = "Invalid or unsupported trading symbol"
ERROR_INVALID_QUANTITY = "Invalid order quantity"
ERROR_INVALID_PRICE = "Invalid price value"
ERROR_ORDER_REJECTED = "Order was rejected by the broker"
ERROR_CONNECTION_FAILED = "Failed to connect to broker API"
ERROR_TIMEOUT = "Broker API request timed out"
ERROR_UNSUPPORTED_OPERATION = "Operation not supported by this broker"

# Logging Configuration
# Standard log prefixes for broker operations
LOG_PREFIX_AUTH = "[BROKER_AUTH]"
LOG_PREFIX_ORDER = "[BROKER_ORDER]"
LOG_PREFIX_POSITION = "[BROKER_POSITION]"
LOG_PREFIX_QUOTE = "[BROKER_QUOTE]"
LOG_PREFIX_WEBSOCKET = "[BROKER_WS]"
LOG_PREFIX_ERROR = "[BROKER_ERROR]"

# Currency Codes
# Primary currency for Indian brokers
DEFAULT_CURRENCY = "INR"

# Market Hours (India Standard Time)
# These are approximate and may vary by exchange/holiday
# Broker implementations should verify with exchange API
MARKET_OPEN_HOUR = 9  # 9:15 AM IST
MARKET_OPEN_MINUTE = 15
MARKET_CLOSE_HOUR = 15  # 3:30 PM IST
MARKET_CLOSE_MINUTE = 30

# Feature Flags
# Used to check broker capability support
FEATURE_BRACKET_ORDERS = "bracket_orders"
FEATURE_COVER_ORDERS = "cover_orders"
FEATURE_GTD_ORDERS = "gtd_orders"
FEATURE_AMO_ORDERS = "amo_orders"  # After Market Orders
FEATURE_WEBSOCKET_STREAMING = "websocket_streaming"
FEATURE_HISTORICAL_DATA = "historical_data"
FEATURE_OPTION_CHAIN = "option_chain"
FEATURE_MARGIN_CALCULATOR = "margin_calculator"
