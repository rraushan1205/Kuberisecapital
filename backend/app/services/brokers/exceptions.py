"""
Broker-specific exceptions for the Stratum platform.

This module defines a hierarchy of exceptions that broker implementations
can raise to communicate specific error conditions. These exceptions follow
Python's exception hierarchy best practices and provide structured error
information that can be caught and handled appropriately by route handlers.

Exception Hierarchy:
    BrokerError (base)
    ├── BrokerNotFoundError
    ├── BrokerAuthenticationError
    │   ├── BrokerTokenExpiredError
    │   └── BrokerTokenInvalidError
    ├── BrokerConnectionError
    │   ├── BrokerTimeoutError
    │   └── BrokerUnavailableError
    ├── BrokerRateLimitError
    ├── BrokerValidationError
    └── BrokerOperationError
        ├── BrokerInsufficientFundsError
        ├── BrokerOrderRejectedError
        └── BrokerMarketClosedError

Design rationale:
    - Follows existing pattern in trading_engine.py which raises HTTPException
    - Allows route handlers to catch and convert to appropriate HTTP responses
    - Provides structured error information (provider, user_id, details)
    - Enables centralized error logging and monitoring
"""

from typing import Any


class BrokerError(Exception):
    """
    Base exception for all broker-related errors.
    
    All broker implementations should raise subclasses of this exception
    to ensure consistent error handling across the platform.
    
    Attributes:
        provider: The broker provider name (e.g., "zerodha", "fyers")
        user_id: The UUID of the user affected by the error (optional)
        details: Additional error context as a dictionary
        message: Human-readable error message
    """

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        user_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.provider = provider
        self.user_id = user_id
        self.details = details or {}
        super().__init__(message)

    def __str__(self) -> str:
        parts = [self.message]
        if self.provider:
            parts.append(f"provider={self.provider}")
        if self.user_id:
            parts.append(f"user_id={self.user_id}")
        return f"{self.__class__.__name__}: {', '.join(parts)}"


class BrokerNotFoundError(BrokerError):
    """
    Raised when attempting to access an unregistered broker provider.
    
    This exception indicates that the requested broker provider name
    does not exist in the broker registry. Route handlers should return
    404 Not Found when catching this exception.
    
    Example:
        manager.get_broker("unknown_broker")  # Raises BrokerNotFoundError
    """

    pass


class BrokerAuthenticationError(BrokerError):
    """
    Base exception for authentication-related errors.
    
    Raised when broker authentication fails. This could be due to:
    - Invalid credentials
    - Expired tokens
    - Missing authorization
    - Revoked access
    
    Route handlers should return 401 Unauthorized when catching this exception.
    """

    pass


class BrokerTokenExpiredError(BrokerAuthenticationError):
    """
    Raised when the broker access token has expired.
    
    This signals that a token refresh is required. Background jobs should
    catch this exception and attempt to refresh the token automatically.
    
    Attributes:
        expired_at: ISO timestamp when the token expired (if available)
    """

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        user_id: str | None = None,
        expired_at: str | None = None,
    ) -> None:
        details = {"expired_at": expired_at} if expired_at else {}
        super().__init__(message, provider, user_id, details)


class BrokerTokenInvalidError(BrokerAuthenticationError):
    """
    Raised when the broker access token is invalid or malformed.
    
    This indicates that the stored token cannot be used and the user
    must re-authenticate. Unlike expired tokens, invalid tokens cannot
    be refreshed.
    """

    pass


class BrokerConnectionError(BrokerError):
    """
    Base exception for network-related errors.
    
    Raised when communication with the broker API fails. This could be due to:
    - Network timeout
    - DNS resolution failure
    - Connection refused
    - SSL/TLS errors
    
    Route handlers should return 502 Bad Gateway when catching this exception.
    """

    pass


class BrokerTimeoutError(BrokerConnectionError):
    """
    Raised when a broker API request times out.
    
    Indicates that the broker did not respond within the configured timeout
    period. Implementations should use reasonable timeout values (10-30s) to
    prevent indefinite blocking.
    
    Attributes:
        timeout_seconds: The timeout value that was exceeded
    """

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        user_id: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        details = {"timeout_seconds": timeout_seconds} if timeout_seconds else {}
        super().__init__(message, provider, user_id, details)


class BrokerUnavailableError(BrokerConnectionError):
    """
    Raised when the broker service is temporarily unavailable.
    
    This could indicate:
    - Broker server maintenance
    - Service outage
    - Rate limit exceeded at network level
    
    Applications should implement retry logic with exponential backoff
    when catching this exception.
    """

    pass


class BrokerRateLimitError(BrokerError):
    """
    Raised when broker API rate limits are exceeded.
    
    Most brokers enforce rate limits (e.g., 10 requests/second). When the
    limit is exceeded, this exception should be raised. Applications should
    implement request queuing or backoff strategies.
    
    Attributes:
        retry_after_seconds: How long to wait before retrying (if provided by broker)
        limit: The rate limit threshold
        window: The time window for the rate limit (e.g., "1s", "1m")
    
    Route handlers should return 429 Too Many Requests when catching this exception.
    """

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        user_id: str | None = None,
        retry_after_seconds: int | None = None,
        limit: int | None = None,
        window: str | None = None,
    ) -> None:
        details: dict[str, Any] = {}
        if retry_after_seconds:
            details["retry_after_seconds"] = retry_after_seconds
        if limit:
            details["limit"] = limit
        if window:
            details["window"] = window
        super().__init__(message, provider, user_id, details)


class BrokerValidationError(BrokerError):
    """
    Raised when broker API request validation fails.
    
    This indicates that the request parameters are invalid or malformed
    according to the broker's API requirements. Examples:
    - Invalid symbol
    - Invalid quantity (negative, non-integer)
    - Invalid order type
    - Missing required fields
    
    Route handlers should return 400 Bad Request when catching this exception.
    
    Attributes:
        field: The field that failed validation (if applicable)
        validation_errors: Dict of field names to error messages
    """

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        user_id: str | None = None,
        field: str | None = None,
        validation_errors: dict[str, str] | None = None,
    ) -> None:
        details: dict[str, Any] = {}
        if field:
            details["field"] = field
        if validation_errors:
            details["validation_errors"] = validation_errors
        super().__init__(message, provider, user_id, details)


class BrokerOperationError(BrokerError):
    """
    Base exception for broker operation failures.
    
    Raised when a broker operation fails due to business logic constraints
    rather than technical issues. Examples:
    - Insufficient funds
    - Order rejected
    - Market closed
    - Symbol not tradeable
    """

    pass


class BrokerInsufficientFundsError(BrokerOperationError):
    """
    Raised when account has insufficient funds for the requested operation.
    
    Attributes:
        required: Amount required for the operation
        available: Amount currently available
        currency: Currency code (e.g., "INR", "USD")
    """

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        user_id: str | None = None,
        required: float | None = None,
        available: float | None = None,
        currency: str | None = None,
    ) -> None:
        details: dict[str, Any] = {}
        if required is not None:
            details["required"] = required
        if available is not None:
            details["available"] = available
        if currency:
            details["currency"] = currency
        super().__init__(message, provider, user_id, details)


class BrokerOrderRejectedError(BrokerOperationError):
    """
    Raised when broker rejects an order.
    
    This could be due to:
    - Risk management rules
    - Position limits exceeded
    - Invalid order parameters
    - Regulatory restrictions
    
    Attributes:
        reason: Broker-provided rejection reason
        order_id: Order ID if assigned before rejection
    """

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        user_id: str | None = None,
        reason: str | None = None,
        order_id: str | None = None,
    ) -> None:
        details: dict[str, Any] = {}
        if reason:
            details["reason"] = reason
        if order_id:
            details["order_id"] = order_id
        super().__init__(message, provider, user_id, details)


class BrokerMarketClosedError(BrokerOperationError):
    """
    Raised when attempting market operations during non-trading hours.
    
    Attributes:
        market_open_time: When the market opens (ISO timestamp or time string)
        market_close_time: When the market closes (ISO timestamp or time string)
    """

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        user_id: str | None = None,
        market_open_time: str | None = None,
        market_close_time: str | None = None,
    ) -> None:
        details: dict[str, Any] = {}
        if market_open_time:
            details["market_open_time"] = market_open_time
        if market_close_time:
            details["market_close_time"] = market_close_time
        super().__init__(message, provider, user_id, details)
