"""
Fyers broker implementation.

This module implements the BrokerProvider interface for Fyers broker integration.
Currently implements ONLY the authentication flow (connect, callback, disconnect).

Other methods (orders, positions, quotes, etc.) raise NotImplementedError as they
are not part of the initial authentication-only implementation phase.
"""

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fyers_apiv3 import fyersModel

from app.core.config import get_settings
from app.services.brokers.base import BrokerProvider
from app.services.brokers.exceptions import (
    BrokerAuthenticationError,
    BrokerConnectionError,
    BrokerTokenExpiredError,
    BrokerTokenInvalidError,
    BrokerValidationError,
)
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


class FyersBroker(BrokerProvider):
    """
    Fyers broker implementation.
    
    Implements OAuth2 authentication flow for Fyers API v3.
    
    Authentication Flow:
        1. get_auth_url() - Generate OAuth URL with state parameter
        2. User authorizes on Fyers website
        3. handle_oauth_callback() - Exchange auth code for access token
        4. Tokens stored encrypted in database
        5. revoke_token() - Disconnect broker
    
    Configuration Required (in .env):
        FYERS_APP_ID - Your Fyers app ID (e.g., "ABC123-100")
        FYERS_SECRET_ID - Your Fyers secret key
        FYERS_REDIRECT_URI - OAuth callback URL (e.g., "http://localhost:8000/api/v1/client/brokers/fyers/callback")
    
    Notes:
        - Fyers tokens are valid for 24 hours
        - Fyers uses app_id (not API key) for authentication
        - State parameter is used for CSRF protection
        - Only authentication methods are implemented in this phase
    """

    @property
    def provider_name(self) -> str:
        """Return provider name for registry and database storage."""
        return "fyers"

    @property
    def display_name(self) -> str:
        """Return human-readable broker name for UI display."""
        return "Fyers"

    @property
    def supports_websocket(self) -> bool:
        """Fyers supports WebSocket streaming (not implemented yet)."""
        return False  # Will be True in future when WebSocket is implemented

    # ============================================================
    # Fyers API Constants - Order Type and Product Type Mappings
    # ============================================================
    
    # Fyers expects numeric codes for order types (from API v3 docs)
    ORDER_TYPE_MAP = {
        "LIMIT": 1,           # Limit order
        "MARKET": 2,          # Market order
        "STOP_LOSS": 3,       # Stop Loss Limit order
        "STOP_LOSS_MARKET": 4 # Stop Loss Market order
    }
    
    # Fyers product type mapping (Stratum normalized → Fyers-specific)
    PRODUCT_TYPE_MAP = {
        "INTRADAY": "INTRADAY",  # Intraday/MIS
        "DELIVERY": "CNC",       # Cash & Carry (Fyers uses CNC, not DELIVERY)
        "MARGIN": "MARGIN",      # Margin-based F&O
        "CO": "CO",              # Cover Order
        "BO": "BO",              # Bracket Order
    }

    # ============================================================
    # Authentication & Authorization (IMPLEMENTED)
    # ============================================================

    async def get_auth_url(self, user_id: UUID, redirect_uri: str) -> str:
        """
        Generate Fyers OAuth authorization URL.
        
        Creates a URL that redirects the user to Fyers login page. After authorization,
        Fyers redirects back to redirect_uri with an auth code.
        
        Args:
            user_id: UUID of the Stratum user initiating connection
            redirect_uri: URL where Fyers will redirect after authorization
        
        Returns:
            str: Authorization URL to redirect the user to
        
        Raises:
            BrokerValidationError: If configuration is missing
            BrokerConnectionError: If URL generation fails
        
        Example:
            url = await broker.get_auth_url(
                user_id=UUID("..."),
                redirect_uri="http://localhost:8000/api/v1/client/brokers/fyers/callback"
            )
            # Returns: "https://api-t1.fyers.in/api/v3/generate-authcode?client_id=...&state=..."
        """
        settings = get_settings()

        # Validate configuration
        if not hasattr(settings, "fyers_app_id") or not settings.fyers_app_id:
            raise BrokerValidationError(
                "Fyers app ID not configured",
                provider=self.provider_name,
                field="fyers_app_id",
            )

        if not redirect_uri:
            raise BrokerValidationError(
                "Redirect URI is required",
                provider=self.provider_name,
                field="redirect_uri",
            )

        try:
            # Generate secure random state parameter for CSRF protection
            # Include user_id in state so we can verify it in callback
            state = f"{user_id}:{secrets.token_urlsafe(32)}"

            # Create Fyers session
            fyers = fyersModel.SessionModel(
                client_id=settings.fyers_app_id,
                secret_key=getattr(settings, "fyers_secret_id", ""),
                redirect_uri=redirect_uri,
                response_type="code",
                grant_type="authorization_code",
                state=state,
            )

            # Generate auth URL (Fyers SDK includes the state we passed in above)
            print("=" * 80)
            print("APP ID:", settings.fyers_app_id)
            print("SECRET:", settings.fyers_secret_id[:6] + "..." if settings.fyers_secret_id else None)
            print("REDIRECT:", redirect_uri)
            print("STATE:", state)

            auth_url = fyers.generate_authcode()

            print("AUTH URL:", auth_url)
            print("=" * 80)
            # Record that this state was legitimately issued by this server, so the
            # callback can verify it later instead of just checking its format.
            from app.services.oauth_state_store import store_oauth_state
            await store_oauth_state(state)

            return auth_url

        except Exception as error:
            raise BrokerConnectionError(
                f"Failed to generate Fyers auth URL: {str(error)}",
                provider=self.provider_name,
                user_id=str(user_id),
            ) from error

    async def handle_oauth_callback(
        self, code: str, state: str
    ) -> dict[str, str]:
        """
        Handle OAuth callback and exchange auth code for access token.
        
        After user authorizes on Fyers, this method exchanges the authorization
        code for an access token.
        
        Args:
            code: Authorization code from Fyers redirect
            state: State parameter for CSRF validation (contains user_id)
        
        Returns:
            dict containing:
                - access_token: Access token for API calls
                - token_expires_at: ISO timestamp of expiry (24 hours from now)
                - broker_user_id: Fyers client ID
        
        Raises:
            BrokerValidationError: If state or code is invalid
            BrokerAuthenticationError: If token exchange fails
            BrokerConnectionError: If Fyers API is unreachable
        
        Example:
            tokens = await broker.handle_oauth_callback(
                code="auth_code_from_fyers",
                state="user_id:random_string"
            )
            # Returns: {
            #     "access_token": "eyJ...",
            #     "token_expires_at": "2026-07-23T12:00:00Z",
            #     "broker_user_id": "XY12345"
            # }
        """
        settings = get_settings()

        # Validate inputs
        if not code:
            raise BrokerValidationError(
                "Authorization code is missing",
                provider=self.provider_name,
                field="code",
            )

        if not state:
            raise BrokerValidationError(
                "State parameter is missing (possible CSRF attack)",
                provider=self.provider_name,
                field="state",
            )

        # Validate state format
        if ":" not in state:
            raise BrokerValidationError(
                "Invalid state parameter format",
                provider=self.provider_name,
                field="state",
            )

        # Extract user_id from state
        try:
            user_id_str = state.split(":")[0]
            user_id = UUID(user_id_str)
        except (IndexError, ValueError) as error:
            raise BrokerValidationError(
                "Invalid user ID in state parameter",
                provider=self.provider_name,
                field="state",
            ) from error

        try:
            # Create Fyers session for token exchange
            fyers = fyersModel.SessionModel(
                client_id=settings.fyers_app_id,
                secret_key=getattr(settings, "fyers_secret_id", ""),
                redirect_uri=getattr(settings, "fyers_redirect_uri", ""),
                response_type="code",
                grant_type="authorization_code",
            )

            # Set authorization code
            fyers.set_token(code)

            # Exchange code for access token
            response = fyers.generate_token()

            # Check if token generation was successful
            if not isinstance(response, dict):
                raise BrokerAuthenticationError(
                    "Unexpected response format from Fyers",
                    provider=self.provider_name,
                    user_id=str(user_id),
                )

            # Fyers API returns error in response
            if response.get("code") != 200:
                error_msg = response.get("message", "Token generation failed")
                raise BrokerAuthenticationError(
                    f"Fyers token generation failed: {error_msg}",
                    provider=self.provider_name,
                    user_id=str(user_id),
                    details={"fyers_code": response.get("code")},
                )

            access_token = response.get("access_token")
            if not access_token:
                raise BrokerAuthenticationError(
                    "Access token not found in Fyers response",
                    provider=self.provider_name,
                    user_id=str(user_id),
                )

            # Fyers access token is a JWT string, not colon-separated
            # The broker_user_id (fy_id) must be fetched separately via get_profile()
            # For now, we'll leave it as None and it can be populated later
            broker_user_id = None

            # Fyers tokens are valid for 24 hours
            expires_at = datetime.now(UTC) + timedelta(hours=24)

            return {
                "access_token": access_token,
                "token_expires_at": expires_at.isoformat(),
                "broker_user_id": broker_user_id or "unknown",
            }

        except BrokerAuthenticationError:
            # Re-raise broker exceptions as-is
            raise
        except BrokerValidationError:
            raise
        except Exception as error:
            # Catch all other errors as connection errors
            raise BrokerConnectionError(
                f"Failed to exchange auth code: {str(error)}",
                provider=self.provider_name,
                user_id=str(user_id),
            ) from error

    async def refresh_access_token(
        self, user_id: UUID, refresh_token: str
    ) -> dict[str, str]:
        """
        Refresh access token (NOT SUPPORTED by Fyers).
        
        Fyers does not provide refresh tokens. When the access token expires (after 24 hours),
        users must re-authenticate through the OAuth flow.
        
        Args:
            user_id: UUID of the Stratum user
            refresh_token: Not used (Fyers doesn't support refresh tokens)
        
        Raises:
            BrokerTokenExpiredError: Always raised as refresh is not supported
        """
        raise BrokerTokenExpiredError(
            "Fyers does not support token refresh. Please reconnect your broker.",
            provider=self.provider_name,
            user_id=str(user_id),
        )

    async def revoke_token(self, user_id: UUID, access_token: str) -> None:
        """
        Revoke access token and disconnect broker.
        
        Fyers API v3 does not provide a token revocation endpoint. The token will
        naturally expire after 24 hours. This method completes successfully without
        making an API call, allowing the database connection to be marked as disconnected.
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Access token to revoke (ignored as Fyers has no revocation endpoint)
        
        Note:
            This is a graceful no-op. The BrokerConnection status will be updated
            to DISCONNECTED in the database, and the encrypted token will be removed.
        """
        # Fyers doesn't have a revocation endpoint
        # Token will expire naturally after 24 hours
        # This is a graceful no-op - the connection will be marked as disconnected in DB
        pass

    # ============================================================
    # Account Information (IMPLEMENTED - Phase 2)
    # ============================================================

    async def get_profile(self, user_id: UUID, access_token: str) -> BrokerProfile:
        """
        Fetch user profile information from Fyers.
        
        Retrieves the authenticated user's profile including name, email, PAN,
        enabled products, and accessible exchanges.
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid Fyers access token (decrypted, in format "APP_ID:USER_ID:TOKEN")
        
        Returns:
            BrokerProfile: User profile data with fields:
                - user_id: Fyers client ID
                - user_name: User's registered name
                - email: Email address
                - pan: PAN card number
                - broker: Broker name (always "fyers")
                - products: List of enabled product types
                - exchanges: List of accessible exchanges
        
        Raises:
            BrokerTokenExpiredError: If access token has expired
            BrokerTokenInvalidError: If access token is invalid
            BrokerConnectionError: If Fyers API is unreachable
        
        Example:
            profile = await broker.get_profile(
                user_id=UUID("..."),
                access_token="ABC123-100:XY12345:eyJ..."
            )
            # Returns: {
            #     "user_id": "XY12345",
            #     "user_name": "John Doe",
            #     "email": "john@example.com",
            #     ...
            # }
        """
        settings = get_settings()
        
        try:
            # Extract app_id from access_token (format: "APP_ID:USER_ID:TOKEN")
            # Fyers SDK needs both client_id (app_id) and token (full access token)
            app_id = settings.fyers_app_id
            
            # Initialize Fyers SDK client for authenticated calls
            fyers = fyersModel.FyersModel(
                client_id=app_id,
                token=access_token,  # Full token in "APP_ID:USER_ID:TOKEN" format
                is_async=False,
            )
            
            # Call Fyers profile API
            response = fyers.get_profile()
            
            # Check response format
            if not isinstance(response, dict):
                raise BrokerConnectionError(
                    "Unexpected response format from Fyers get_profile",
                    provider=self.provider_name,
                    user_id=str(user_id),
                )
            
            # Check for error in response
            # Fyers API returns {"s": "error", "code": <error_code>, "message": "..."} on error
            # or {"s": "ok", "code": 200, "data": {...}} on success
            if response.get("s") == "error" or response.get("code") != 200:
                error_code = response.get("code")
                error_msg = response.get("message", "Profile fetch failed")
                
                # Handle token expiry/invalid errors
                # Fyers error codes: -1000 to -1005 for auth/token errors
                if error_code in [-1000, -1001, -1002, -1003, -1004, -1005]:
                    raise BrokerTokenExpiredError(
                        f"Fyers token expired or invalid: {error_msg}",
                        provider=self.provider_name,
                        user_id=str(user_id),
                    )
                
                # Other errors
                raise BrokerConnectionError(
                    f"Fyers profile fetch failed: {error_msg}",
                    provider=self.provider_name,
                    user_id=str(user_id),
                    details={"fyers_code": error_code},
                )
            
            # Extract profile data from response
            profile_data = response.get("data", {})
            
            # Map Fyers response to BrokerProfile format
            profile: BrokerProfile = {
                "user_id": profile_data.get("fy_id", ""),
                "user_name": profile_data.get("name", ""),
                "email": profile_data.get("email_id", ""),
                "mobile": profile_data.get("mobile_number", ""),
                "pan": profile_data.get("PAN", ""),
                "broker": "fyers",
                "products": [],  # Fyers doesn't provide product types in profile API
                "exchanges": profile_data.get("exchange", []),  # Accessible exchanges
                "order_types": [],  # Fyers doesn't provide this in profile
            }
            
            return profile
        
        except (BrokerTokenExpiredError, BrokerTokenInvalidError):
            # Re-raise broker exceptions as-is
            raise
        except Exception as error:
            # Catch all other errors as connection errors
            raise BrokerConnectionError(
                f"Failed to fetch Fyers profile: {str(error)}",
                provider=self.provider_name,
                user_id=str(user_id),
            ) from error

    async def get_funds(self, user_id: UUID, access_token: str) -> Funds:
        """
        Fetch available funds and margin information from Fyers.
        
        Retrieves fund limits including available cash, margin utilization,
        and collateral values.
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid Fyers access token (decrypted, in format "APP_ID:USER_ID:TOKEN")
        
        Returns:
            Funds: Available funds data with fields:
                - available_cash: Cash available for trading
                - used_margin: Margin currently in use
                - available_margin: Margin available for new positions
                - collateral: Collateral value
                - total: Total funds
                - currency: Currency code (always "INR" for Indian markets)
        
        Raises:
            BrokerTokenExpiredError: If access token has expired
            BrokerTokenInvalidError: If access token is invalid
            BrokerConnectionError: If Fyers API is unreachable
        
        Example:
            funds = await broker.get_funds(
                user_id=UUID("..."),
                access_token="ABC123-100:XY12345:eyJ..."
            )
            # Returns: {
            #     "available_cash": 50000.0,
            #     "used_margin": 10000.0,
            #     ...
            # }
        """
        settings = get_settings()
        
        try:
            # Initialize Fyers SDK client
            app_id = settings.fyers_app_id
            fyers = fyersModel.FyersModel(
                client_id=app_id,
                token=access_token,
                is_async=False,
            )
            
            # Call Fyers funds API
            response = fyers.funds()
            
            # Check response format
            if not isinstance(response, dict):
                raise BrokerConnectionError(
                    "Unexpected response format from Fyers funds",
                    provider=self.provider_name,
                    user_id=str(user_id),
                )
            
            # Check for error in response
            if response.get("s") == "error" or response.get("code") != 200:
                error_code = response.get("code")
                error_msg = response.get("message", "Funds fetch failed")
                
                # Handle token errors
                if error_code in [-1000, -1001, -1002, -1003, -1004, -1005]:
                    raise BrokerTokenExpiredError(
                        f"Fyers token expired or invalid: {error_msg}",
                        provider=self.provider_name,
                        user_id=str(user_id),
                    )
                
                raise BrokerConnectionError(
                    f"Fyers funds fetch failed: {error_msg}",
                    provider=self.provider_name,
                    user_id=str(user_id),
                    details={"fyers_code": error_code},
                )
            
            # Extract funds data from response
            # Fyers returns {"fund_limit": [{...}]} structure
            funds_data = response.get("fund_limit", [])
            if not funds_data or not isinstance(funds_data, list):
                raise BrokerConnectionError(
                    "Invalid funds data structure from Fyers",
                    provider=self.provider_name,
                    user_id=str(user_id),
                )
            
            # Get first fund limit entry (usually contains overall limits)
            fund_limit = funds_data[0] if funds_data else {}
            
            # Map Fyers response to Funds format
            # Fyers fields: equityAmount, commodityAmount, used_margin, etc.
            funds: Funds = {
                "available_cash": float(fund_limit.get("equityAmount", 0)),
                "used_margin": float(fund_limit.get("used_margin", 0)),
                "available_margin": float(fund_limit.get("margin_available", 0)),
                "collateral": float(fund_limit.get("collateral", 0)),
                "total": float(fund_limit.get("total_balance", 0)),
                "currency": "INR",
            }
            
            return funds
        
        except (BrokerTokenExpiredError, BrokerTokenInvalidError):
            raise
        except Exception as error:
            raise BrokerConnectionError(
                f"Failed to fetch Fyers funds: {str(error)}",
                provider=self.provider_name,
                user_id=str(user_id),
            ) from error

    # ============================================================
    # Portfolio & Positions (IMPLEMENTED - Phase 2)
    # ============================================================

    async def get_holdings(self, user_id: UUID, access_token: str) -> list[Holding]:
        """
        Fetch long-term holdings (delivery positions) from Fyers.
        
        Retrieves all delivery holdings with current valuation and P&L.
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid Fyers access token (decrypted, in format "APP_ID:USER_ID:TOKEN")
        
        Returns:
            list[Holding]: List of holdings, empty list if no holdings exist
        
        Raises:
            BrokerTokenExpiredError: If access token has expired
            BrokerConnectionError: If Fyers API is unreachable
        
        Example:
            holdings = await broker.get_holdings(
                user_id=UUID("..."),
                access_token="ABC123-100:XY12345:eyJ..."
            )
            # Returns: [
            #     {
            #         "symbol": "NSE:SBIN-EQ",
            #         "quantity": 100,
            #         "average_price": 550.0,
            #         ...
            #     }
            # ]
        """
        settings = get_settings()
        
        try:
            # Initialize Fyers SDK client
            app_id = settings.fyers_app_id
            fyers = fyersModel.FyersModel(
                client_id=app_id,
                token=access_token,
                is_async=False,
            )
            
            # Call Fyers holdings API
            response = fyers.holdings()
            
            # Check response format
            if not isinstance(response, dict):
                raise BrokerConnectionError(
                    "Unexpected response format from Fyers holdings",
                    provider=self.provider_name,
                    user_id=str(user_id),
                )
            
            # Check for error in response
            if response.get("s") == "error" or response.get("code") != 200:
                error_code = response.get("code")
                error_msg = response.get("message", "Holdings fetch failed")
                
                # Handle token errors
                if error_code in [-1000, -1001, -1002, -1003, -1004, -1005]:
                    raise BrokerTokenExpiredError(
                        f"Fyers token expired or invalid: {error_msg}",
                        provider=self.provider_name,
                        user_id=str(user_id),
                    )
                
                raise BrokerConnectionError(
                    f"Fyers holdings fetch failed: {error_msg}",
                    provider=self.provider_name,
                    user_id=str(user_id),
                    details={"fyers_code": error_code},
                )
            
            # Extract holdings data from response
            holdings_data = response.get("holdings", [])
            
            # Return empty list if no holdings
            if not holdings_data:
                return []
            
            # Map Fyers holdings to our Holding format
            holdings: list[Holding] = []
            for holding_item in holdings_data:
                holding: Holding = {
                    "symbol": holding_item.get("symbol", ""),
                    "exchange": holding_item.get("exchange", ""),
                    "isin": holding_item.get("isin", ""),
                    "quantity": int(holding_item.get("quantity", 0)),
                    "average_price": float(holding_item.get("costPrice", 0)),
                    "last_price": float(holding_item.get("ltp", 0)),
                    "pnl": float(holding_item.get("pl", 0)),
                    "pnl_percentage": float(holding_item.get("plPercent", 0)),
                    "collateral_type": holding_item.get("collateralType", ""),
                    "collateral_quantity": int(holding_item.get("collateralQty", 0)),
                }
                holdings.append(holding)
            
            return holdings
        
        except (BrokerTokenExpiredError, BrokerTokenInvalidError):
            raise
        except Exception as error:
            raise BrokerConnectionError(
                f"Failed to fetch Fyers holdings: {str(error)}",
                provider=self.provider_name,
                user_id=str(user_id),
            ) from error

    async def get_positions(self, user_id: UUID, access_token: str) -> list[Position]:
        """
        Fetch open trading positions (intraday and overnight) from Fyers.
        
        Retrieves all active positions with current P&L and market value.
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid Fyers access token (decrypted, in format "APP_ID:USER_ID:TOKEN")
        
        Returns:
            list[Position]: List of positions, empty list if no positions exist
        
        Raises:
            BrokerTokenExpiredError: If access token has expired
            BrokerConnectionError: If Fyers API is unreachable
        
        Example:
            positions = await broker.get_positions(
                user_id=UUID("..."),
                access_token="ABC123-100:XY12345:eyJ..."
            )
            # Returns: [
            #     {
            #         "symbol": "NSE:NIFTY25JANFUT",
            #         "quantity": 50,
            #         "product": "INTRADAY",
            #         "pnl": 1250.0,
            #         ...
            #     }
            # ]
        """
        settings = get_settings()
        
        try:
            # Initialize Fyers SDK client
            app_id = settings.fyers_app_id
            fyers = fyersModel.FyersModel(
                client_id=app_id,
                token=access_token,
                is_async=False,
            )
            
            # Call Fyers positions API
            response = fyers.positions()
            
            # Check response format
            if not isinstance(response, dict):
                raise BrokerConnectionError(
                    "Unexpected response format from Fyers positions",
                    provider=self.provider_name,
                    user_id=str(user_id),
                )
            
            # Check for error in response
            if response.get("s") == "error" or response.get("code") != 200:
                error_code = response.get("code")
                error_msg = response.get("message", "Positions fetch failed")
                
                # Handle token errors
                if error_code in [-1000, -1001, -1002, -1003, -1004, -1005]:
                    raise BrokerTokenExpiredError(
                        f"Fyers token expired or invalid: {error_msg}",
                        provider=self.provider_name,
                        user_id=str(user_id),
                    )
                
                raise BrokerConnectionError(
                    f"Fyers positions fetch failed: {error_msg}",
                    provider=self.provider_name,
                    user_id=str(user_id),
                    details={"fyers_code": error_code},
                )
            
            # Extract positions data from response
            # Fyers returns {"netPositions": [...], "overall": {...}}
            positions_data = response.get("netPositions", [])
            
            # Return empty list if no positions
            if not positions_data:
                return []
            
            # Map Fyers positions to our Position format
            positions: list[Position] = []
            for position_item in positions_data:
                # Calculate net quantity (positive for long, negative for short)
                buy_qty = int(position_item.get("buyQty", 0))
                sell_qty = int(position_item.get("sellQty", 0))
                net_qty = buy_qty - sell_qty
                
                position: Position = {
                    "symbol": position_item.get("symbol", ""),
                    "exchange": position_item.get("exchange", ""),
                    "product": position_item.get("productType", ""),
                    "quantity": net_qty,
                    "average_price": float(position_item.get("avgPrice", 0)),
                    "last_price": float(position_item.get("ltp", 0)),
                    "pnl": float(position_item.get("pl", 0)),
                    "realized_pnl": float(position_item.get("realized_profit", 0)),
                    "unrealized_pnl": float(position_item.get("unrealized_profit", 0)),
                    "day_buy_quantity": buy_qty,
                    "day_sell_quantity": sell_qty,
                    "day_buy_price": float(position_item.get("buyAvg", 0)),
                    "day_sell_price": float(position_item.get("sellAvg", 0)),
                    "overnight_quantity": int(position_item.get("cfQty", 0)),
                }
                positions.append(position)
            
            return positions
        
        except (BrokerTokenExpiredError, BrokerTokenInvalidError):
            raise
        except Exception as error:
            raise BrokerConnectionError(
                f"Failed to fetch Fyers positions: {str(error)}",
                provider=self.provider_name,
                user_id=str(user_id),
            ) from error

    # ============================================================
    # Order Management (IMPLEMENTED - Phase 2)
    # ============================================================

    async def get_orders(
        self, user_id: UUID, access_token: str
    ) -> list[Order]:
        """
        Fetch all orders for the current trading day from Fyers.
        
        Retrieves order history including pending, executed, and cancelled orders.
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid Fyers access token (decrypted, in format "APP_ID:USER_ID:TOKEN")
        
        Returns:
            list[Order]: List of orders, empty list if no orders exist
        
        Raises:
            BrokerTokenExpiredError: If access token has expired
            BrokerConnectionError: If Fyers API is unreachable
        
        Example:
            orders = await broker.get_orders(
                user_id=UUID("..."),
                access_token="ABC123-100:XY12345:eyJ..."
            )
        """
        settings = get_settings()
        
        try:
            # Initialize Fyers SDK client
            app_id = settings.fyers_app_id
            fyers = fyersModel.FyersModel(
                client_id=app_id,
                token=access_token,
                is_async=False,
            )
            
            # Call Fyers orderbook API
            response = fyers.orderbook()
            
            # Check response format
            if not isinstance(response, dict):
                raise BrokerConnectionError(
                    "Unexpected response format from Fyers orderbook",
                    provider=self.provider_name,
                    user_id=str(user_id),
                )
            
            # Check for error in response
            if response.get("s") == "error" or response.get("code") != 200:
                error_code = response.get("code")
                error_msg = response.get("message", "Orders fetch failed")
                
                # Handle token errors
                if error_code in [-1000, -1001, -1002, -1003, -1004, -1005]:
                    raise BrokerTokenExpiredError(
                        f"Fyers token expired or invalid: {error_msg}",
                        provider=self.provider_name,
                        user_id=str(user_id),
                    )
                
                raise BrokerConnectionError(
                    f"Fyers orders fetch failed: {error_msg}",
                    provider=self.provider_name,
                    user_id=str(user_id),
                    details={"fyers_code": error_code},
                )
            
            # Extract orders data from response
            orders_data = response.get("orderBook", [])
            
            # Return empty list if no orders
            if not orders_data:
                return []
            
            # Map Fyers orders to our Order format
            orders: list[Order] = []
            for order_item in orders_data:
                order: Order = {
                    "order_id": order_item.get("id", ""),
                    "exchange_order_id": order_item.get("exchOrdId", ""),
                    "parent_order_id": order_item.get("parentId", ""),
                    "symbol": order_item.get("symbol", ""),
                    "exchange": order_item.get("exchange", ""),
                    "order_type": order_item.get("type", "").upper(),
                    "side": "BUY" if order_item.get("side", 1) == 1 else "SELL",
                    "product": order_item.get("productType", ""),
                    "quantity": int(order_item.get("qty", 0)),
                    "price": float(order_item.get("limitPrice", 0)),
                    "trigger_price": float(order_item.get("stopPrice", 0)),
                    "filled_quantity": int(order_item.get("filledQty", 0)),
                    "pending_quantity": int(order_item.get("qty", 0)) - int(order_item.get("filledQty", 0)),
                    "cancelled_quantity": int(order_item.get("cancelledQty", 0)),
                    "average_price": float(order_item.get("tradedPrice", 0)),
                    "status": self._map_fyers_order_status(order_item.get("status", 0)),
                    "validity": order_item.get("validity", "DAY"),
                    "order_timestamp": order_item.get("orderDateTime", ""),
                    "exchange_timestamp": order_item.get("exchOrdId", ""),
                    "status_message": order_item.get("message", ""),
                    "tag": order_item.get("tag", ""),
                }
                orders.append(order)
            
            return orders
        
        except (BrokerTokenExpiredError, BrokerTokenInvalidError):
            raise
        except Exception as error:
            raise BrokerConnectionError(
                f"Failed to fetch Fyers orders: {str(error)}",
                provider=self.provider_name,
                user_id=str(user_id),
            ) from error

    async def get_order_details(
        self, user_id: UUID, access_token: str, order_id: str
    ) -> Order:
        """
        Fetch details of a specific order from Fyers.
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid Fyers access token (decrypted, in format "APP_ID:USER_ID:TOKEN")
            order_id: Fyers order ID
        
        Returns:
            Order: Order details
        
        Raises:
            BrokerTokenExpiredError: If access token has expired
            BrokerValidationError: If order_id is invalid or order not found
            BrokerConnectionError: If Fyers API is unreachable
        
        Example:
            order = await broker.get_order_details(
                user_id=UUID("..."),
                access_token="ABC123-100:XY12345:eyJ...",
                order_id="123456789"
            )
        """
        # Fyers doesn't have a dedicated get single order API
        # We fetch all orders and filter by order_id
        orders = await self.get_orders(user_id, access_token)
        
        for order in orders:
            if order.get("order_id") == order_id:
                return order
        
        # Order not found
        from app.services.brokers.exceptions import BrokerValidationError
        raise BrokerValidationError(
            f"Order with ID '{order_id}' not found",
            provider=self.provider_name,
            user_id=str(user_id),
            field="order_id",
        )

    async def place_order(
        self, user_id: UUID, access_token: str, order: OrderRequest
    ) -> Order:
        """
        Place a new order with Fyers.
        
        Validates all order parameters before making the API call, and logs
        the order attempt for audit purposes.
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid Fyers access token
            order: Order request with all required fields
        
        Returns:
            Order: Placed order details with broker order ID
        
        Raises:
            BrokerValidationError: If order parameters are invalid
            BrokerTokenExpiredError: If access token has expired
            BrokerConnectionError: If API call fails or order is rejected
        
        Example:
            order_request = {
                "symbol": "NSE:SBIN-EQ",
                "exchange": "NSE",
                "side": "BUY",
                "order_type": "LIMIT",
                "quantity": 1,
                "product": "INTRADAY",
                "price": 900.0,
                "validity": "DAY",
            }
            order = await broker.place_order(user_id, access_token, order_request)
        """
        import logging
        
        settings = get_settings()
        logger = logging.getLogger(__name__)
        
        # Validate required fields
        if not order.get("symbol"):
            raise BrokerValidationError(
                "symbol is required",
                provider=self.provider_name,
                user_id=str(user_id),
                field="symbol",
            )
        
        if not order.get("side") or order.get("side") not in ["BUY", "SELL"]:
            raise BrokerValidationError(
                "side must be 'BUY' or 'SELL'",
                provider=self.provider_name,
                user_id=str(user_id),
                field="side",
            )
        
        if not order.get("order_type"):
            raise BrokerValidationError(
                "order_type is required",
                provider=self.provider_name,
                user_id=str(user_id),
                field="order_type",
            )
        
        quantity = order.get("quantity", 0)
        if not isinstance(quantity, int) or quantity <= 0:
            raise BrokerValidationError(
                "quantity must be a positive integer",
                provider=self.provider_name,
                user_id=str(user_id),
                field="quantity",
            )
        
        if not order.get("product"):
            raise BrokerValidationError(
                "product is required (INTRADAY, DELIVERY, CARRYFORWARD)",
                provider=self.provider_name,
                user_id=str(user_id),
                field="product",
            )
        
        # Validate price for LIMIT orders
        if order.get("order_type") in ["LIMIT", "STOP_LOSS"]:
            price = order.get("price", 0)
            if not isinstance(price, (int, float)) or price <= 0:
                raise BrokerValidationError(
                    f"price must be a positive number for {order.get('order_type')} orders",
                    provider=self.provider_name,
                    user_id=str(user_id),
                    field="price",
                )
        
        # Validate trigger price for stop loss orders
        if order.get("order_type") in ["STOP_LOSS", "STOP_LOSS_MARKET"]:
            trigger_price = order.get("trigger_price", 0)
            if not isinstance(trigger_price, (int, float)) or trigger_price <= 0:
                raise BrokerValidationError(
                    f"trigger_price must be a positive number for {order.get('order_type')} orders",
                    provider=self.provider_name,
                    user_id=str(user_id),
                    field="trigger_price",
                )
        
        # Audit log BEFORE API call
        logger.info(
            f"FYERS ORDER PLACEMENT ATTEMPT: user_id={user_id}, provider=fyers, "
            f"symbol={order.get('symbol')}, side={order.get('side')}, "
            f"quantity={order.get('quantity')}, order_type={order.get('order_type')}, "
            f"product={order.get('product')}, price={order.get('price', 'N/A')}"
        )
        
        try:
            # Initialize Fyers SDK client
            app_id = settings.fyers_app_id
            fyers = fyersModel.FyersModel(
                client_id=app_id,
                token=access_token,
                is_async=False,
            )
            
            # Map order type to Fyers numeric code
            order_type_str = str(order.get("order_type", "LIMIT")).upper()
            fyers_type = self.ORDER_TYPE_MAP.get(order_type_str)
            
            if fyers_type is None:
                raise BrokerValidationError(
                    f"Invalid order_type '{order_type_str}'. Must be one of: {', '.join(self.ORDER_TYPE_MAP.keys())}",
                    provider=self.provider_name,
                    user_id=str(user_id),
                    field="order_type",
                )
            
            # Map product type to Fyers format
            product_str = str(order.get("product", "INTRADAY")).upper()
            fyers_product = self.PRODUCT_TYPE_MAP.get(product_str)
            
            if fyers_product is None:
                raise BrokerValidationError(
                    f"Invalid product type '{product_str}'. Must be one of: {', '.join(self.PRODUCT_TYPE_MAP.keys())}",
                    provider=self.provider_name,
                    user_id=str(user_id),
                    field="product",
                )
            
            # Map to Fyers order format
            fyers_order_data = {
                "symbol": order.get("symbol"),
                "qty": order.get("quantity"),
                "type": fyers_type,  # Integer: 1=LIMIT, 2=MARKET, 3=STOP_LOSS, 4=STOP_LOSS_MARKET
                "side": 1 if order.get("side") == "BUY" else -1,
                "productType": fyers_product,  # String: INTRADAY, CNC, MARGIN, CO, BO
                "limitPrice": order.get("price", 0),
                "stopPrice": order.get("trigger_price", 0),
                "validity": order.get("validity", "DAY").upper(),
                "disclosedQty": order.get("disclosed_quantity", 0),
                "offlineOrder": False,
            }
            
            # Call Fyers place order API
            response = fyers.place_order(data=fyers_order_data)
            
            # Check response format
            if not isinstance(response, dict):
                raise BrokerConnectionError(
                    "Unexpected response format from Fyers place_order",
                    provider=self.provider_name,
                    user_id=str(user_id),
                )
            
            # Check for error in response
            if response.get("s") == "error" or response.get("code") != 200:
                error_code = response.get("code")
                error_msg = response.get("message", "Order placement failed")
                
                # Handle token errors
                if error_code in [-1000, -1001, -1002, -1003, -1004, -1005]:
                    raise BrokerTokenExpiredError(
                        f"Fyers token expired or invalid: {error_msg}",
                        provider=self.provider_name,
                        user_id=str(user_id),
                    )
                
                # This is a rejection from Fyers (insufficient funds, invalid symbol, etc.)
                # Not a connection error
                raise BrokerConnectionError(
                    f"Fyers order rejected: {error_msg}",
                    provider=self.provider_name,
                    user_id=str(user_id),
                    details={"fyers_code": error_code, "rejection_reason": error_msg},
                )
            
            # Extract order ID from response
            order_id = response.get("id", "")
            
            if not order_id:
                raise BrokerConnectionError(
                    "Order placed but no order ID returned",
                    provider=self.provider_name,
                    user_id=str(user_id),
                )
            
            logger.info(f"FYERS ORDER PLACED SUCCESSFULLY: user_id={user_id}, order_id={order_id}")
            
            # Fetch the placed order details
            return await self.get_order_details(user_id, access_token, order_id)
        
        except (BrokerTokenExpiredError, BrokerValidationError):
            raise
        except Exception as error:
            raise BrokerConnectionError(
                f"Failed to place Fyers order: {str(error)}",
                provider=self.provider_name,
                user_id=str(user_id),
            ) from error

    async def modify_order(
        self, user_id: UUID, access_token: str, order_id: str, modifications: dict
    ) -> Order:
        """
        Modify an existing order with Fyers.
        
        Fetches the current order state first to validate it can be modified,
        then applies the requested modifications.
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid Fyers access token
            order_id: Broker order ID to modify
            modifications: Dict of fields to modify (quantity, price, trigger_price, etc.)
        
        Returns:
            Order: Modified order details
        
        Raises:
            BrokerValidationError: If order cannot be modified or modifications are invalid
            BrokerTokenExpiredError: If access token has expired
            BrokerConnectionError: If API call fails
        
        Example:
            modifications = {"price": 950.0}
            order = await broker.modify_order(user_id, access_token, order_id, modifications)
        """
        import logging
        
        settings = get_settings()
        logger = logging.getLogger(__name__)
        
        # Fetch current order to validate state
        current_order = await self.get_order_details(user_id, access_token, order_id)
        
        # Check if order is in a modifiable state
        # Only PENDING and OPEN orders can be modified
        if current_order.get("status") not in ["PENDING", "OPEN"]:
            raise BrokerValidationError(
                f"Order cannot be modified in {current_order.get('status')} state. Only PENDING or OPEN orders can be modified.",
                provider=self.provider_name,
                user_id=str(user_id),
                field="order_status",
            )
        
        # Validate modifications contain only allowed fields
        allowed_fields = {"quantity", "price", "trigger_price", "order_type"}
        invalid_fields = set(modifications.keys()) - allowed_fields
        if invalid_fields:
            raise BrokerValidationError(
                f"Invalid modification fields: {', '.join(invalid_fields)}. Allowed: {', '.join(allowed_fields)}",
                provider=self.provider_name,
                user_id=str(user_id),
                field="modifications",
            )
        
        # Validate new values
        if "quantity" in modifications:
            qty = modifications["quantity"]
            if not isinstance(qty, int) or qty <= 0:
                raise BrokerValidationError(
                    "quantity must be a positive integer",
                    provider=self.provider_name,
                    user_id=str(user_id),
                    field="quantity",
                )
        
        if "price" in modifications:
            price = modifications["price"]
            if not isinstance(price, (int, float)) or price <= 0:
                raise BrokerValidationError(
                    "price must be a positive number",
                    provider=self.provider_name,
                    user_id=str(user_id),
                    field="price",
                )
        
        if "trigger_price" in modifications:
            trigger = modifications["trigger_price"]
            if not isinstance(trigger, (int, float)) or trigger <= 0:
                raise BrokerValidationError(
                    "trigger_price must be a positive number",
                    provider=self.provider_name,
                    user_id=str(user_id),
                    field="trigger_price",
                )
        
        # Audit log
        logger.info(
            f"FYERS ORDER MODIFICATION ATTEMPT: user_id={user_id}, order_id={order_id}, "
            f"modifications={modifications}"
        )
        
        try:
            # Initialize Fyers SDK client
            app_id = settings.fyers_app_id
            fyers = fyersModel.FyersModel(
                client_id=app_id,
                token=access_token,
                is_async=False,
            )
            
            # Prepare modification data
            modify_data = {
                "id": order_id,
            }
            
            # Map modifications to Fyers format
            if "quantity" in modifications:
                modify_data["qty"] = modifications["quantity"]
            if "price" in modifications:
                modify_data["limitPrice"] = modifications["price"]
            if "trigger_price" in modifications:
                modify_data["stopPrice"] = modifications["trigger_price"]
            if "order_type" in modifications:
                # Map order type string to Fyers numeric code
                order_type_str = str(modifications["order_type"]).upper()
                fyers_type = self.ORDER_TYPE_MAP.get(order_type_str)
                if fyers_type is None:
                    raise BrokerValidationError(
                        f"Invalid order_type '{order_type_str}'. Must be one of: {', '.join(self.ORDER_TYPE_MAP.keys())}",
                        provider=self.provider_name,
                        user_id=str(user_id),
                        field="order_type",
                    )
                modify_data["type"] = fyers_type
            
            # Call Fyers modify order API
            response = fyers.modify_order(data=modify_data)
            
            # Check response format
            if not isinstance(response, dict):
                raise BrokerConnectionError(
                    "Unexpected response format from Fyers modify_order",
                    provider=self.provider_name,
                    user_id=str(user_id),
                )
            
            # Check for error in response
            if response.get("s") == "error" or response.get("code") != 200:
                error_code = response.get("code")
                error_msg = response.get("message", "Order modification failed")
                
                # Handle token errors
                if error_code in [-1000, -1001, -1002, -1003, -1004, -1005]:
                    raise BrokerTokenExpiredError(
                        f"Fyers token expired or invalid: {error_msg}",
                        provider=self.provider_name,
                        user_id=str(user_id),
                    )
                
                raise BrokerConnectionError(
                    f"Fyers order modification rejected: {error_msg}",
                    provider=self.provider_name,
                    user_id=str(user_id),
                    details={"fyers_code": error_code, "rejection_reason": error_msg},
                )
            
            logger.info(f"FYERS ORDER MODIFIED SUCCESSFULLY: user_id={user_id}, order_id={order_id}")
            
            # Fetch and return updated order details
            return await self.get_order_details(user_id, access_token, order_id)
        
        except (BrokerTokenExpiredError, BrokerValidationError):
            raise
        except Exception as error:
            raise BrokerConnectionError(
                f"Failed to modify Fyers order: {str(error)}",
                provider=self.provider_name,
                user_id=str(user_id),
            ) from error

    async def cancel_order(
        self, user_id: UUID, access_token: str, order_id: str
    ) -> Order:
        """
        Cancel an existing order with Fyers.
        
        Fetches the current order state first to validate it can be cancelled.
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid Fyers access token
            order_id: Broker order ID to cancel
        
        Returns:
            Order: Cancelled order details
        
        Raises:
            BrokerValidationError: If order cannot be cancelled
            BrokerTokenExpiredError: If access token has expired
            BrokerConnectionError: If API call fails
        
        Example:
            order = await broker.cancel_order(user_id, access_token, order_id)
        """
        import logging
        
        settings = get_settings()
        logger = logging.getLogger(__name__)
        
        # Fetch current order to validate state
        current_order = await self.get_order_details(user_id, access_token, order_id)
        
        # Check if order is in a cancellable state
        # Only PENDING and OPEN orders can be cancelled
        if current_order.get("status") not in ["PENDING", "OPEN"]:
            raise BrokerValidationError(
                f"Order cannot be cancelled in {current_order.get('status')} state. Only PENDING or OPEN orders can be cancelled.",
                provider=self.provider_name,
                user_id=str(user_id),
                field="order_status",
            )
        
        # Audit log
        logger.info(
            f"FYERS ORDER CANCELLATION ATTEMPT: user_id={user_id}, order_id={order_id}, "
            f"symbol={current_order.get('symbol')}"
        )
        
        try:
            # Initialize Fyers SDK client
            app_id = settings.fyers_app_id
            fyers = fyersModel.FyersModel(
                client_id=app_id,
                token=access_token,
                is_async=False,
            )
            
            # Call Fyers cancel order API
            response = fyers.cancel_order(data={"id": order_id})
            
            # Check response format
            if not isinstance(response, dict):
                raise BrokerConnectionError(
                    "Unexpected response format from Fyers cancel_order",
                    provider=self.provider_name,
                    user_id=str(user_id),
                )
            
            # Check for error in response
            if response.get("s") == "error" or response.get("code") != 200:
                error_code = response.get("code")
                error_msg = response.get("message", "Order cancellation failed")
                
                # Handle token errors
                if error_code in [-1000, -1001, -1002, -1003, -1004, -1005]:
                    raise BrokerTokenExpiredError(
                        f"Fyers token expired or invalid: {error_msg}",
                        provider=self.provider_name,
                        user_id=str(user_id),
                    )
                
                raise BrokerConnectionError(
                    f"Fyers order cancellation rejected: {error_msg}",
                    provider=self.provider_name,
                    user_id=str(user_id),
                    details={"fyers_code": error_code, "rejection_reason": error_msg},
                )
            
            logger.info(f"FYERS ORDER CANCELLED SUCCESSFULLY: user_id={user_id}, order_id={order_id}")
            
            # Fetch and return cancelled order details
            return await self.get_order_details(user_id, access_token, order_id)
        
        except (BrokerTokenExpiredError, BrokerValidationError):
            raise
        except Exception as error:
            raise BrokerConnectionError(
                f"Failed to cancel Fyers order: {str(error)}",
                provider=self.provider_name,
                user_id=str(user_id),
            ) from error

    # ============================================================
    # Market Data (IMPLEMENTED - Phase 2)
    # ============================================================

    async def get_quotes(
        self, user_id: UUID, access_token: str, symbols: list[str]
    ) -> list[Quote]:
        """
        Fetch real-time quotes for given symbols from Fyers.
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid Fyers access token (decrypted, in format "APP_ID:USER_ID:TOKEN")
            symbols: List of trading symbols in Fyers format (e.g., ["NSE:SBIN-EQ", "NSE:TCS-EQ"])
        
        Returns:
            list[Quote]: Real-time quotes for the requested symbols
        
        Raises:
            BrokerTokenExpiredError: If access token has expired
            BrokerValidationError: If symbols are invalid or empty
            BrokerConnectionError: If Fyers API is unreachable
        
        Example:
            quotes = await broker.get_quotes(
                user_id=UUID("..."),
                access_token="ABC123-100:XY12345:eyJ...",
                symbols=["NSE:SBIN-EQ", "NSE:TCS-EQ"]
            )
        """
        settings = get_settings()
        
        # Validate symbols
        if not symbols:
            raise BrokerValidationError(
                "Symbols list cannot be empty",
                provider=self.provider_name,
                user_id=str(user_id),
                field="symbols",
            )
        
        # Validate symbol format (Fyers format: EXCHANGE:SYMBOL-SEGMENT)
        for symbol in symbols:
            if ":" not in symbol:
                raise BrokerValidationError(
                    f"Invalid symbol format: '{symbol}'. Expected format: 'EXCHANGE:SYMBOL-SEGMENT' (e.g., 'NSE:SBIN-EQ')",
                    provider=self.provider_name,
                    user_id=str(user_id),
                    field="symbols",
                )
        
        try:
            # Initialize Fyers SDK client
            app_id = settings.fyers_app_id
            fyers = fyersModel.FyersModel(
                client_id=app_id,
                token=access_token,
                is_async=False,
            )
            
            # Call Fyers quotes API
            # Fyers expects {"symbols": "NSE:SBIN-EQ,NSE:TCS-EQ"}
            symbols_str = ",".join(symbols)
            response = fyers.quotes(data={"symbols": symbols_str})
            
            # Check response format
            if not isinstance(response, dict):
                raise BrokerConnectionError(
                    "Unexpected response format from Fyers quotes",
                    provider=self.provider_name,
                    user_id=str(user_id),
                )
            
            # Check for error in response
            if response.get("s") == "error" or response.get("code") != 200:
                error_code = response.get("code")
                error_msg = response.get("message", "Quotes fetch failed")
                
                # Handle token errors
                if error_code in [-1000, -1001, -1002, -1003, -1004, -1005]:
                    raise BrokerTokenExpiredError(
                        f"Fyers token expired or invalid: {error_msg}",
                        provider=self.provider_name,
                        user_id=str(user_id),
                    )
                
                raise BrokerConnectionError(
                    f"Fyers quotes fetch failed: {error_msg}",
                    provider=self.provider_name,
                    user_id=str(user_id),
                    details={"fyers_code": error_code},
                )
            
            # Extract quotes data from response
            quotes_data = response.get("d", [])
            
            # Map Fyers quotes to our Quote format
            quotes: list[Quote] = []
            for quote_item in quotes_data:
                # Extract market depth data
                v = quote_item.get("v", {})
                
                quote: Quote = {
                    "symbol": quote_item.get("n", ""),
                    "exchange": quote_item.get("n", "").split(":")[0] if ":" in quote_item.get("n", "") else "",
                    "last_price": float(v.get("lp", 0)),
                    "last_quantity": int(v.get("last_traded_qty", 0)),
                    "last_trade_time": v.get("last_traded_time", ""),
                    "open": float(v.get("open_price", 0)),
                    "high": float(v.get("high_price", 0)),
                    "low": float(v.get("low_price", 0)),
                    "close": float(v.get("prev_close_price", 0)),
                    "volume": int(v.get("volume", 0)),
                    "bid_price": float(v.get("bid_price", 0)),
                    "bid_quantity": int(v.get("bid_size", 0)),
                    "ask_price": float(v.get("ask_price", 0)),
                    "ask_quantity": int(v.get("ask_size", 0)),
                    "oi": int(v.get("oi", 0)),
                    "oi_change": int(v.get("oi_change", 0)),
                }
                quotes.append(quote)
            
            return quotes
        
        except (BrokerTokenExpiredError, BrokerValidationError):
            raise
        except Exception as error:
            raise BrokerConnectionError(
                f"Failed to fetch Fyers quotes: {str(error)}",
                provider=self.provider_name,
                user_id=str(user_id),
            ) from error

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
        Fetch historical OHLCV candle data from Fyers.
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid Fyers access token (decrypted, in format "APP_ID:USER_ID:TOKEN")
            symbol: Trading symbol in Fyers format (e.g., "NSE:SBIN-EQ")
            interval: Candle interval (e.g., "1", "5", "15", "60", "D" for daily)
            from_date: Start date for historical data
            to_date: End date for historical data
        
        Returns:
            list[Candle]: Historical OHLCV candles
        
        Raises:
            BrokerTokenExpiredError: If access token has expired
            BrokerValidationError: If parameters are invalid
            BrokerConnectionError: If Fyers API is unreachable
        
        Example:
            candles = await broker.get_historical_data(
                user_id=UUID("..."),
                access_token="ABC123-100:XY12345:eyJ...",
                symbol="NSE:SBIN-EQ",
                interval="15",
                from_date=datetime(2026, 1, 1),
                to_date=datetime(2026, 1, 31)
            )
        """
        settings = get_settings()
        
        # Validate inputs
        if not symbol or ":" not in symbol:
            raise BrokerValidationError(
                f"Invalid symbol format: '{symbol}'. Expected format: 'EXCHANGE:SYMBOL-SEGMENT'",
                provider=self.provider_name,
                user_id=str(user_id),
                field="symbol",
            )
        
        if from_date >= to_date:
            raise BrokerValidationError(
                "from_date must be earlier than to_date",
                provider=self.provider_name,
                user_id=str(user_id),
                field="from_date",
            )
        
        # Map interval to Fyers format
        # Fyers supports: 1, 2, 3, 5, 10, 15, 20, 30, 60, 120, 240, D, W, M
        interval_map = {
            "1m": "1",
            "3m": "3",
            "5m": "5",
            "15m": "15",
            "30m": "30",
            "1h": "60",
            "2h": "120",
            "4h": "240",
            "1d": "D",
            "1w": "W",
            "1M": "M",
        }
        
        fyers_interval = interval_map.get(interval, interval)
        
        try:
            # Initialize Fyers SDK client
            app_id = settings.fyers_app_id
            fyers = fyersModel.FyersModel(
                client_id=app_id,
                token=access_token,
                is_async=False,
            )
            
            # Convert dates to YYYY-MM-DD format (Fyers requires this format when date_format=1)
            # Note: Despite the parameter name "date_format", Fyers expects date strings, not timestamps
            from_date_str = from_date.strftime("%Y-%m-%d")
            to_date_str = to_date.strftime("%Y-%m-%d")
            
            # Call Fyers history API
            data = {
                "symbol": symbol,
                "resolution": fyers_interval,
                "date_format": "1",  # Date format (YYYY-MM-DD strings, not Unix timestamps)
                "range_from": from_date_str,
                "range_to": to_date_str,
                "cont_flag": "1",  # Continuous flag for futures
            }
            
            response = fyers.history(data=data)
            
            # Check response format
            if not isinstance(response, dict):
                raise BrokerConnectionError(
                    "Unexpected response format from Fyers history",
                    provider=self.provider_name,
                    user_id=str(user_id),
                )
            
            # Check for error in response
            if response.get("s") == "error" or response.get("code") != 200:
                error_code = response.get("code")
                error_msg = response.get("message", "Historical data fetch failed")
                
                # Handle token errors
                if error_code in [-1000, -1001, -1002, -1003, -1004, -1005]:
                    raise BrokerTokenExpiredError(
                        f"Fyers token expired or invalid: {error_msg}",
                        provider=self.provider_name,
                        user_id=str(user_id),
                    )
                
                raise BrokerConnectionError(
                    f"Fyers historical data fetch failed: {error_msg}",
                    provider=self.provider_name,
                    user_id=str(user_id),
                    details={"fyers_code": error_code},
                )
            
            # Extract candles data from response
            # Fyers returns {"candles": [[timestamp, open, high, low, close, volume], ...]}
            candles_data = response.get("candles", [])
            
            # Map Fyers candles to our Candle format
            candles: list[Candle] = []
            for candle_item in candles_data:
                if len(candle_item) >= 6:
                    # Convert Unix timestamp to ISO format
                    timestamp = datetime.fromtimestamp(candle_item[0], tz=UTC).isoformat()
                    
                    candle: Candle = {
                        "timestamp": timestamp,
                        "open": float(candle_item[1]),
                        "high": float(candle_item[2]),
                        "low": float(candle_item[3]),
                        "close": float(candle_item[4]),
                        "volume": int(candle_item[5]),
                    }
                    candles.append(candle)
            
            return candles
        
        except (BrokerTokenExpiredError, BrokerValidationError):
            raise
        except Exception as error:
            raise BrokerConnectionError(
                f"Failed to fetch Fyers historical data: {str(error)}",
                provider=self.provider_name,
                user_id=str(user_id),
            ) from error

    # ============================================================
    # Helper Methods
    # ============================================================

    def _map_fyers_order_status(self, fyers_status: int) -> str:
        """
        Map Fyers order status code to standard OrderStatus enum.
        
        Fyers status codes:
            1: Pending
            2: Placed
            3: Partially filled
            4: Filled
            5: Cancelled
            6: Rejected
            7: Expired
        
        Args:
            fyers_status: Fyers numeric status code
        
        Returns:
            str: Standard order status (PENDING, OPEN, COMPLETE, CANCELLED, REJECTED, EXPIRED)
        """
        status_map = {
            1: "PENDING",
            2: "OPEN",
            3: "OPEN",  # Partially filled is still open
            4: "COMPLETE",
            5: "CANCELLED",
            6: "REJECTED",
            7: "EXPIRED",
        }
        return status_map.get(fyers_status, "PENDING")
