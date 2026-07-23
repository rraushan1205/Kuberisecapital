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
            auth_url = fyers.generate_authcode()

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

            # Extract broker user ID from access token (Fyers format: APP_ID:USER_ID:TOKEN)
            # Example: "ABC123-100:XY12345:eyJh..."
            broker_user_id = None
            if ":" in access_token:
                parts = access_token.split(":")
                if len(parts) >= 2:
                    broker_user_id = parts[1]

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
    # Account Information (NOT IMPLEMENTED - Phase 2)
    # ============================================================

    async def get_profile(self, user_id: UUID, access_token: str) -> BrokerProfile:
        """Not implemented in authentication-only phase."""
        raise NotImplementedError("get_profile will be implemented in Phase 2")

    async def get_funds(self, user_id: UUID, access_token: str) -> Funds:
        """Not implemented in authentication-only phase."""
        raise NotImplementedError("get_funds will be implemented in Phase 2")

    # ============================================================
    # Portfolio & Positions (NOT IMPLEMENTED - Phase 2)
    # ============================================================

    async def get_holdings(self, user_id: UUID, access_token: str) -> list[Holding]:
        """Not implemented in authentication-only phase."""
        raise NotImplementedError("get_holdings will be implemented in Phase 2")

    async def get_positions(self, user_id: UUID, access_token: str) -> list[Position]:
        """Not implemented in authentication-only phase."""
        raise NotImplementedError("get_positions will be implemented in Phase 2")

    # ============================================================
    # Order Management (NOT IMPLEMENTED - Phase 2)
    # ============================================================

    async def place_order(
        self, user_id: UUID, access_token: str, order: OrderRequest
    ) -> Order:
        """Not implemented in authentication-only phase."""
        raise NotImplementedError("place_order will be implemented in Phase 2")

    async def modify_order(
        self, user_id: UUID, access_token: str, order_id: str, modifications: dict
    ) -> Order:
        """Not implemented in authentication-only phase."""
        raise NotImplementedError("modify_order will be implemented in Phase 2")

    async def cancel_order(
        self, user_id: UUID, access_token: str, order_id: str
    ) -> Order:
        """Not implemented in authentication-only phase."""
        raise NotImplementedError("cancel_order will be implemented in Phase 2")

    async def get_orders(
        self, user_id: UUID, access_token: str
    ) -> list[Order]:
        """Not implemented in authentication-only phase."""
        raise NotImplementedError("get_orders will be implemented in Phase 2")

    async def get_order_details(
        self, user_id: UUID, access_token: str, order_id: str
    ) -> Order:
        """Not implemented in authentication-only phase."""
        raise NotImplementedError("get_order_details will be implemented in Phase 2")

    # ============================================================
    # Market Data (NOT IMPLEMENTED - Phase 2)
    # ============================================================

    async def get_quotes(
        self, user_id: UUID, access_token: str, symbols: list[str]
    ) -> list[Quote]:
        """Not implemented in authentication-only phase."""
        raise NotImplementedError("get_quotes will be implemented in Phase 2")

    async def get_historical_data(
        self,
        user_id: UUID,
        access_token: str,
        symbol: str,
        interval: str,
        from_date: datetime,
        to_date: datetime,
    ) -> list[Candle]:
        """Not implemented in authentication-only phase."""
        raise NotImplementedError("get_historical_data will be implemented in Phase 2")
