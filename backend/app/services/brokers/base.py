"""
Abstract base class for all broker implementations.

This module defines the contract that every broker provider must implement.
It uses Python's ABC (Abstract Base Class) to enforce this contract at
runtime, ensuring all brokers provide the required functionality.

Design rationale:
    - Strategy pattern: Each broker is a strategy for trading operations
    - Interface segregation: Only essential methods are required
    - Open/closed principle: Easy to add new brokers without modifying existing code
    - Dependency inversion: Routes depend on abstractions, not concrete implementations

All broker implementations must:
    1. Inherit from BrokerProvider
    2. Implement all @abstractmethod methods
    3. Raise appropriate broker exceptions (from exceptions.py)
    4. Return data in standard formats (from types.py)
    5. Handle errors gracefully with proper logging
"""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.services.brokers.types import (
    BrokerProfile,
    Candle,
    Funds,
    Holding,
    Order,
    OrderRequest,
    Position,
    Quote,
)


class BrokerProvider(ABC):
    """
    Abstract base class for broker integrations.
    
    This class defines the interface that all broker implementations must follow.
    Each method represents a core capability that brokers must provide to support
    the Stratum platform's trading features.
    
    Implementations must handle:
        - Authentication and token management
        - Error handling and retries
        - Rate limiting
        - Data format conversions (broker-specific → standard format)
        - Logging all operations
    
    Usage:
        class ZerodhaBroker(BrokerProvider):
            async def get_auth_url(self, user_id, redirect_uri):
                # Zerodha-specific implementation
                ...
        
        broker = ZerodhaBroker()
        url = await broker.get_auth_url(user_id, callback_url)
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Return the broker provider name (e.g., "zerodha", "fyers").
        
        This should be a lowercase, URL-safe string used for:
            - Registry lookups
            - Database storage in BrokerConnection.provider
            - API routes (/brokers/{provider}/...)
        
        Returns:
            str: The provider name
        """
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """
        Return the human-readable broker name (e.g., "Zerodha Kite", "Fyers").
        
        Used for UI display purposes.
        
        Returns:
            str: Display name for the broker
        """
        pass

    @property
    @abstractmethod
    def supports_websocket(self) -> bool:
        """
        Indicate whether this broker supports WebSocket streaming.
        
        Returns:
            bool: True if WebSocket streaming is supported
        """
        pass

    # ============================================================
    # Authentication & Authorization
    # ============================================================

    @abstractmethod
    async def get_auth_url(self, user_id: UUID, redirect_uri: str) -> str:
        """
        Generate OAuth authorization URL for user login.
        
        This method initiates the OAuth flow by generating a URL that the user
        should visit to authorize the application. The URL should include:
            - Client ID/API key
            - Redirect URI (callback endpoint)
            - State parameter (for CSRF protection, should include user_id)
            - Required scopes
        
        Args:
            user_id: UUID of the Stratum user connecting their broker
            redirect_uri: Callback URL where broker will redirect after auth
        
        Returns:
            str: Authorization URL to redirect the user to
        
        Raises:
            BrokerConnectionError: If unable to generate URL
            BrokerValidationError: If parameters are invalid
        
        Example:
            url = await broker.get_auth_url(
                user_id=UUID("..."),
                redirect_uri="https://stratum.com/api/v1/client/brokers/zerodha/callback"
            )
            # Returns: "https://kite.zerodha.com/connect/login?api_key=...&state=..."
        """
        pass

    @abstractmethod
    async def handle_oauth_callback(
        self, code: str, state: str
    ) -> dict[str, str]:
        """
        Handle OAuth callback and exchange authorization code for tokens.
        
        After the user authorizes the app, the broker redirects back with an
        authorization code. This method exchanges that code for access/refresh tokens.
        
        Implementation must:
            1. Validate the state parameter (CSRF check)
            2. Exchange code for access_token and refresh_token
            3. Return tokens in encrypted form (if sensitive)
            4. Extract broker_user_id if available
        
        Args:
            code: Authorization code from broker
            state: State parameter for CSRF validation (contains user_id)
        
        Returns:
            dict containing:
                - access_token: Token for API calls
                - refresh_token: Token for refreshing access (if applicable)
                - token_expires_at: ISO timestamp of expiry
                - broker_user_id: Broker's internal user ID
        
        Raises:
            BrokerAuthenticationError: If code exchange fails
            BrokerValidationError: If state validation fails
            BrokerConnectionError: If broker API is unreachable
        
        Example:
            tokens = await broker.handle_oauth_callback(
                code="abc123",
                state="user_id=..."
            )
            # Returns: {
            #     "access_token": "encrypted_token",
            #     "refresh_token": "encrypted_refresh",
            #     "token_expires_at": "2026-07-23T12:00:00Z",
            #     "broker_user_id": "XYZ123"
            # }
        """
        pass

    @abstractmethod
    async def refresh_access_token(
        self, user_id: UUID, refresh_token: str
    ) -> dict[str, str]:
        """
        Refresh an expired access token using refresh token.
        
        Most broker tokens expire after 24 hours. This method obtains a new
        access token without requiring user interaction.
        
        Args:
            user_id: UUID of the Stratum user
            refresh_token: Current refresh token (decrypted)
        
        Returns:
            dict containing:
                - access_token: New access token
                - refresh_token: New refresh token (if rotated)
                - token_expires_at: ISO timestamp of new expiry
        
        Raises:
            BrokerTokenExpiredError: If refresh token has expired
            BrokerTokenInvalidError: If refresh token is invalid
            BrokerAuthenticationError: If refresh fails
        
        Example:
            new_tokens = await broker.refresh_access_token(
                user_id=UUID("..."),
                refresh_token="current_refresh_token"
            )
        """
        pass

    @abstractmethod
    async def revoke_token(self, user_id: UUID, access_token: str) -> None:
        """
        Revoke access token and disconnect broker.
        
        Called when user explicitly disconnects their broker or when
        revoking access for security reasons.
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Access token to revoke (decrypted)
        
        Raises:
            BrokerAuthenticationError: If token is already invalid
            BrokerConnectionError: If broker API is unreachable
        
        Note:
            Some brokers may not support token revocation. In such cases,
            implementations should simply return without error and let the
            token expire naturally.
        """
        pass

    # ============================================================
    # Account Information
    # ============================================================

    @abstractmethod
    async def get_profile(self, user_id: UUID, access_token: str) -> BrokerProfile:
        """
        Fetch user profile information from broker.
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid access token (decrypted)
        
        Returns:
            BrokerProfile: User profile data (see types.py)
        
        Raises:
            BrokerTokenExpiredError: If token has expired
            BrokerAuthenticationError: If authentication fails
            BrokerConnectionError: If broker API is unreachable
        """
        pass

    @abstractmethod
    async def get_funds(self, user_id: UUID, access_token: str) -> Funds:
        """
        Fetch available funds and margin information.
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid access token (decrypted)
        
        Returns:
            Funds: Available funds and margin (see types.py)
        
        Raises:
            BrokerTokenExpiredError: If token has expired
            BrokerAuthenticationError: If authentication fails
            BrokerConnectionError: If broker API is unreachable
        """
        pass

    # ============================================================
    # Portfolio & Positions
    # ============================================================

    @abstractmethod
    async def get_holdings(self, user_id: UUID, access_token: str) -> list[Holding]:
        """
        Fetch long-term holdings (delivery positions).
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid access token (decrypted)
        
        Returns:
            list[Holding]: List of holdings (see types.py)
        
        Raises:
            BrokerTokenExpiredError: If token has expired
            BrokerAuthenticationError: If authentication fails
            BrokerConnectionError: If broker API is unreachable
        """
        pass

    @abstractmethod
    async def get_positions(self, user_id: UUID, access_token: str) -> list[Position]:
        """
        Fetch open trading positions (intraday and overnight).
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid access token (decrypted)
        
        Returns:
            list[Position]: List of positions (see types.py)
        
        Raises:
            BrokerTokenExpiredError: If token has expired
            BrokerAuthenticationError: If authentication fails
            BrokerConnectionError: If broker API is unreachable
        """
        pass

    # ============================================================
    # Order Management
    # ============================================================

    @abstractmethod
    async def place_order(
        self, user_id: UUID, access_token: str, order: OrderRequest
    ) -> Order:
        """
        Place a new order.
        
        Implementations must:
            1. Validate order parameters
            2. Convert to broker-specific format
            3. Place order via broker API
            4. Convert response to standard Order format
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid access token (decrypted)
            order: Order details (see types.OrderRequest)
        
        Returns:
            Order: Placed order details (see types.py)
        
        Raises:
            BrokerTokenExpiredError: If token has expired
            BrokerAuthenticationError: If authentication fails
            BrokerValidationError: If order parameters are invalid
            BrokerInsufficientFundsError: If insufficient funds
            BrokerOrderRejectedError: If broker rejects the order
            BrokerMarketClosedError: If market is closed
            BrokerConnectionError: If broker API is unreachable
        """
        pass

    @abstractmethod
    async def modify_order(
        self, user_id: UUID, access_token: str, order_id: str, modifications: dict
    ) -> Order:
        """
        Modify an existing pending order.
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid access token (decrypted)
            order_id: Broker's order ID
            modifications: Fields to modify (quantity, price, trigger_price, etc.)
        
        Returns:
            Order: Modified order details
        
        Raises:
            BrokerTokenExpiredError: If token has expired
            BrokerValidationError: If modifications are invalid
            BrokerOperationError: If order cannot be modified (already executed/cancelled)
        """
        pass

    @abstractmethod
    async def cancel_order(
        self, user_id: UUID, access_token: str, order_id: str
    ) -> Order:
        """
        Cancel a pending order.
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid access token (decrypted)
            order_id: Broker's order ID
        
        Returns:
            Order: Cancelled order details
        
        Raises:
            BrokerTokenExpiredError: If token has expired
            BrokerOperationError: If order cannot be cancelled (already executed)
        """
        pass

    @abstractmethod
    async def get_orders(
        self, user_id: UUID, access_token: str
    ) -> list[Order]:
        """
        Fetch all orders for the current trading day.
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid access token (decrypted)
        
        Returns:
            list[Order]: List of orders
        
        Raises:
            BrokerTokenExpiredError: If token has expired
            BrokerAuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    async def get_order_details(
        self, user_id: UUID, access_token: str, order_id: str
    ) -> Order:
        """
        Fetch details of a specific order.
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid access token (decrypted)
            order_id: Broker's order ID
        
        Returns:
            Order: Order details
        
        Raises:
            BrokerTokenExpiredError: If token has expired
            BrokerValidationError: If order_id is invalid
        """
        pass

    # ============================================================
    # Market Data
    # ============================================================

    @abstractmethod
    async def get_quotes(
        self, user_id: UUID, access_token: str, symbols: list[str]
    ) -> list[Quote]:
        """
        Fetch real-time quotes for given symbols.
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid access token (decrypted)
            symbols: List of trading symbols (e.g., ["NSE:INFY", "NSE:TCS"])
        
        Returns:
            list[Quote]: Real-time quotes (see types.py)
        
        Raises:
            BrokerTokenExpiredError: If token has expired
            BrokerValidationError: If symbols are invalid
            BrokerRateLimitError: If rate limit is exceeded
        
        Note:
            Implementations should respect MAX_SYMBOLS_PER_QUOTE_REQUEST
            from constants.py and batch requests if necessary.
        """
        pass

    @abstractmethod
    async def get_historical_data(
        self,
        user_id: UUID,
        access_token: str,
        symbol: str,
        interval: str,
        from_date: datetime,
        to_date: datetime,
    ) -> list[Candle]:
        """
        Fetch historical OHLCV candle data.
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid access token (decrypted)
            symbol: Trading symbol (e.g., "NSE:INFY")
            interval: Candle interval (see types.Interval)
            from_date: Start date
            to_date: End date
        
        Returns:
            list[Candle]: Historical candles (see types.py)
        
        Raises:
            BrokerTokenExpiredError: If token has expired
            BrokerValidationError: If parameters are invalid
            BrokerRateLimitError: If rate limit is exceeded
        
        Note:
            Implementations should respect MAX_HISTORICAL_CANDLES and
            MAX_HISTORICAL_DAYS from constants.py.
        """
        pass

    # ============================================================
    # WebSocket Streaming (Optional)
    # ============================================================

    async def subscribe_to_ticks(
        self, user_id: UUID, access_token: str, symbols: list[str]
    ) -> None:
        """
        Subscribe to real-time tick data via WebSocket.
        
        This method is optional. Brokers that don't support WebSocket
        streaming should raise BrokerOperationError with message
        "WebSocket streaming not supported".
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid access token (decrypted)
            symbols: List of symbols to subscribe to
        
        Raises:
            BrokerOperationError: If WebSocket not supported
            BrokerConnectionError: If WebSocket connection fails
        """
        raise NotImplementedError(
            f"{self.provider_name} does not support WebSocket streaming"
        )

    async def unsubscribe_from_ticks(
        self, user_id: UUID, access_token: str, symbols: list[str]
    ) -> None:
        """
        Unsubscribe from real-time tick data.
        
        This method is optional and pairs with subscribe_to_ticks.
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid access token (decrypted)
            symbols: List of symbols to unsubscribe from
        
        Raises:
            BrokerOperationError: If WebSocket not supported
        """
        raise NotImplementedError(
            f"{self.provider_name} does not support WebSocket streaming"
        )

    # ============================================================
    # Utility Methods
    # ============================================================

    def get_supported_features(self) -> list[str]:
        """
        Return list of optional features supported by this broker.
        
        Returns:
            list[str]: Feature flags (see constants.py FEATURE_* constants)
        
        Example:
            features = broker.get_supported_features()
            # Returns: ["websocket_streaming", "historical_data", "bracket_orders"]
        """
        return []

    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if a symbol format is correct for this broker.
        
        Args:
            symbol: Trading symbol to validate
        
        Returns:
            bool: True if symbol is valid
        
        Example:
            broker.validate_symbol("NSE:INFY")  # Returns True
            broker.validate_symbol("INVALID")    # Returns False
        """
        return True  # Default: accept all symbols
