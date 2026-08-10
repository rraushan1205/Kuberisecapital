"""
Alice Blue broker implementation.

This module implements the BrokerProvider interface for Alice Blue broker integration.
Currently implements ONLY the authentication flow (connect, callback, disconnect).

Other methods (orders, positions, quotes, etc.) raise BrokerOperationError as they
are not part of the initial authentication-only implementation phase.

Alice Blue OAuth Flow:
    1. get_auth_url() - Generate OAuth URL (note: state param may not persist in redirect)
    2. User authorizes on Alice Blue website
    3. Alice Blue redirects with authCode AND userId query params
    4. handle_oauth_callback() - Compute checksum and exchange for session token
    5. Tokens stored encrypted in database
    6. revoke_token() - Graceful no-op (no documented revoke endpoint)

Configuration Required (in .env):
    ALICEBLUE_APP_CODE - Your Alice Blue app code
    ALICEBLUE_API_SECRET - Your Alice Blue API secret
    ALICEBLUE_REDIRECT_URI - OAuth callback URL

Notes:
    - Alice Blue tokens are valid for 24 hours
    - No refresh token support (must re-authenticate after expiry)
    - userId is returned in callback (no separate profile call needed for broker_user_id)
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx

from app.core.config import get_settings
from app.services.brokers.base import BrokerProvider
from app.services.brokers.exceptions import (
    BrokerAuthenticationError,
    BrokerConnectionError,
    BrokerOperationError,
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


class AliceBlueBroker(BrokerProvider):
    """
    Alice Blue broker implementation.
    
    Implements OAuth-style authentication flow for Alice Blue API.
    
    Authentication Flow:
        1. get_auth_url() - Generate authorization URL with state parameter
        2. User authorizes on Alice Blue website
        3. Alice Blue redirects with authCode and userId params
        4. handle_oauth_callback() - Compute checksum, exchange for userSession token
        5. Tokens stored encrypted in database
        6. revoke_token() - No-op (no documented revocation endpoint)
    
    Key Differences from Fyers:
        - Alice Blue returns both authCode AND userId in callback (dual-param flow)
        - Checksum required for token exchange: SHA256(userId + authCode + apiSecret)
        - userSession is the access token (24-hour validity, no refresh)
        - userId from callback is the broker_user_id (no separate profile fetch needed)
    """

    # Alice Blue API endpoints
    LOGIN_REDIRECT_URL = "https://ant.aliceblueonline.com/"
    GET_USER_DETAILS_URL = "https://a3.aliceblueonline.com/open-api/od/v1/vendor/getUserDetails"
    GET_USER_DETAILS_URL_FALLBACK = "https://ant.aliceblueonline.com/rest/AliceBlueAPIService/sso/getUserDetails"
    API_BASE_URL = "https://ant.aliceblueonline.com/rest/AliceBlueAPIService/api/"

    @property
    def provider_name(self) -> str:
        """Return provider name for registry and database storage."""
        return "aliceblue"

    @property
    def display_name(self) -> str:
        """Return human-readable broker name for UI display."""
        return "Alice Blue"

    @property
    def supports_websocket(self) -> bool:
        """Alice Blue WebSocket streaming not implemented yet."""
        return False

    # ============================================================
    # Authentication & Authorization (IMPLEMENTED)
    # ============================================================

    async def get_auth_url(self, user_id: UUID, redirect_uri: str) -> str:
        """
        Generate Alice Blue OAuth authorization URL.
        
        Creates a URL that redirects the user to Alice Blue login page. After authorization,
        Alice Blue redirects back with authCode and userId query params.
        
        Args:
            user_id: UUID of the Stratum user initiating connection
            redirect_uri: URL where Alice Blue will redirect after authorization
        
        Returns:
            str: Authorization URL to redirect the user to
        
        Raises:
            BrokerValidationError: If configuration is missing
            BrokerConnectionError: If URL generation fails
        
        Note:
            Alice Blue's redirect URL is configured server-side in their dashboard.
            The state parameter is generated and stored for CSRF protection, but
            whether it survives the round trip depends on Alice Blue's implementation.
        """
        settings = get_settings()

        # Validate configuration
        if not settings.aliceblue_app_code:
            raise BrokerValidationError(
                "Alice Blue app code not configured",
                provider=self.provider_name,
                field="aliceblue_app_code",
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

            # Store state in Redis for verification
            from app.services.oauth_state_store import store_oauth_state
            await store_oauth_state(state)

            # Build authorization URL
            # Note: Alice Blue may not preserve the state param in redirect
            # If state is lost, we'll fall back to extracting user_id from frontend session
            auth_url = f"{self.LOGIN_REDIRECT_URL}?appcode={settings.aliceblue_app_code}&state={state}"

            return auth_url

        except Exception as error:
            raise BrokerConnectionError(
                f"Failed to generate Alice Blue auth URL: {str(error)}",
                provider=self.provider_name,
                user_id=str(user_id),
            ) from error

    async def handle_oauth_callback(
        self, code: str, state: str, user_id: str | None = None
    ) -> dict[str, str]:
        """
        Handle OAuth callback and exchange auth code for access token.
        
        Alice Blue's callback provides TWO parameters: authCode and userId.
        This method computes a checksum and exchanges them for a userSession token.
        
        Args:
            code: Combined "authCode|userId" string from callback route (see Note below)
            state: State parameter for CSRF validation (contains user_id)
            user_id: Optional explicit userId from callback (if route passes it separately)
        
        Returns:
            dict containing:
                - access_token: userSession token for API calls
                - token_expires_at: ISO timestamp of expiry (24 hours from now)
                - broker_user_id: Alice Blue's userId
        
        Raises:
            BrokerValidationError: If state, code, or userId is invalid
            BrokerAuthenticationError: If session exchange fails
            BrokerConnectionError: If Alice Blue API is unreachable
        
        Note:
            CRITICAL: Alice Blue returns BOTH authCode AND userId in callback.
            The client_brokers.py callback route MUST be updated to handle this.
            Either:
            1. Concatenate as "authCode|userId" into code param, OR
            2. Add provider-aware logic to capture userId separately
            
            This implementation expects format: code = "authCode|userId"
        """
        settings = get_settings()

        # Validate inputs
        if not code:
            raise BrokerValidationError(
                "Authorization code is missing",
                provider=self.provider_name,
                field="code",
            )

        if not state or ":" not in state:
            raise BrokerValidationError(
                "Invalid or missing state parameter",
                provider=self.provider_name,
                field="state",
            )

        # Extract user_id from state
        try:
            user_id_str = state.split(":")[0]
            extracted_user_id = UUID(user_id_str)
        except (IndexError, ValueError) as error:
            raise BrokerValidationError(
                "Invalid user ID in state parameter",
                provider=self.provider_name,
                field="state",
            ) from error

        # Parse authCode and userId from code parameter
        # Expected format: "authCode|userId" (concatenated by callback route)
        if "|" in code:
            auth_code, broker_user_id = code.split("|", 1)
        else:
            # Fallback: assume code is just authCode, userId must be provided separately
            auth_code = code
            broker_user_id = user_id

        if not broker_user_id:
            raise BrokerValidationError(
                "Alice Blue userId missing from callback. "
                "The callback route must forward both authCode and userId parameters.",
                provider=self.provider_name,
                user_id=str(extracted_user_id),
                field="userId",
            )

        if not settings.aliceblue_api_secret:
            raise BrokerValidationError(
                "Alice Blue API secret not configured",
                provider=self.provider_name,
                field="aliceblue_api_secret",
            )

        try:
            # Compute checksum: SHA256(userId + authCode + apiSecret)
            # Order is critical: userId first, then authCode, then apiSecret
            checksum_string = f"{broker_user_id}{auth_code}{settings.aliceblue_api_secret}"
            checksum = hashlib.sha256(checksum_string.encode()).hexdigest()

            # Prepare payload for session exchange
            payload = {
                "userId": broker_user_id,
                "authCode": auth_code,
                "checkSum": checksum,
            }

            # Exchange authCode for userSession token
            async with httpx.AsyncClient(timeout=30) as client:
                try:
                    # Try newer endpoint first
                    response = await client.post(
                        self.GET_USER_DETAILS_URL,
                        json=payload,
                    )
                    # If 404, fall back to older endpoint
                    if response.status_code == 404:
                        response = await client.post(
                            self.GET_USER_DETAILS_URL_FALLBACK,
                            json=payload,
                        )
                except httpx.HTTPError as http_error:
                    # Network error, try fallback endpoint
                    try:
                        response = await client.post(
                            self.GET_USER_DETAILS_URL_FALLBACK,
                            json=payload,
                        )
                    except httpx.HTTPError:
                        raise BrokerConnectionError(
                            f"Failed to connect to Alice Blue API: {str(http_error)}",
                            provider=self.provider_name,
                            user_id=str(extracted_user_id),
                        ) from http_error

            # Check response status
            if response.status_code != 200:
                raise BrokerAuthenticationError(
                    f"Alice Blue session exchange failed with HTTP {response.status_code}",
                    provider=self.provider_name,
                    user_id=str(extracted_user_id),
                    details={
                        "status_code": response.status_code,
                        "body": response.text[:500],
                    },
                )

            # Parse response
            data = response.json()

            # Check for error in response
            # Alice Blue error shape: {"stat": "Not_Ok", "emsg": "error message"}
            if data.get("stat") == "Not_Ok" or "userSession" not in data:
                error_msg = data.get("emsg", "unknown error")
                raise BrokerAuthenticationError(
                    f"Alice Blue session exchange failed: {error_msg}",
                    provider=self.provider_name,
                    user_id=str(extracted_user_id),
                    details={"response": data},
                )

            # Extract userSession (this is the access token)
            access_token = data["userSession"]

            # Alice Blue tokens are valid for 24 hours (same as Fyers)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

            return {
                "access_token": access_token,
                "token_expires_at": expires_at.isoformat(),
                "broker_user_id": broker_user_id,
            }

        except (BrokerAuthenticationError, BrokerValidationError):
            # Re-raise broker exceptions as-is
            raise
        except Exception as error:
            # Catch all other errors as connection errors
            raise BrokerConnectionError(
                f"Failed to exchange Alice Blue auth code: {str(error)}",
                provider=self.provider_name,
                user_id=str(extracted_user_id),
            ) from error

    async def refresh_access_token(
        self, user_id: UUID, refresh_token: str
    ) -> dict[str, str]:
        """
        Refresh access token (NOT SUPPORTED by Alice Blue).
        
        Alice Blue does not provide refresh tokens. When the access token expires (after 24 hours),
        users must re-authenticate through the OAuth flow.
        
        Args:
            user_id: UUID of the Stratum user
            refresh_token: Not used (Alice Blue doesn't support refresh tokens)
        
        Raises:
            BrokerTokenExpiredError: Always raised as refresh is not supported
        """
        raise BrokerTokenExpiredError(
            "Alice Blue does not support token refresh. Please reconnect your broker.",
            provider=self.provider_name,
            user_id=str(user_id),
        )

    async def revoke_token(self, user_id: UUID, access_token: str) -> None:
        """
        Revoke access token and disconnect broker.
        
        Alice Blue API does not provide a documented token revocation endpoint. The token will
        naturally expire after 24 hours. This method completes successfully without making
        an API call, allowing the database connection to be marked as disconnected.
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Access token to revoke (ignored as Alice Blue has no revocation endpoint)
        
        Note:
            This is a graceful no-op. The BrokerConnection status will be updated
            to DISCONNECTED in the database, and the encrypted token will be removed.
        """
        # Alice Blue doesn't have a revocation endpoint
        # Token will expire naturally after 24 hours
        # This is a graceful no-op - the connection will be marked as disconnected in DB
        pass

    # ============================================================
    # Account Information (STUBBED - Phase 2)
    # ============================================================

    async def get_profile(self, user_id: UUID, access_token: str) -> BrokerProfile:
        """
        Fetch user profile information from Alice Blue.
        
        TODO: Implementation requires confirmation of:
            1. Exact API endpoint path
            2. Authorization header format
            3. Response shape
        
        Args:
            user_id: UUID of the Stratum user
            access_token: Valid Alice Blue access token (userSession)
        
        Returns:
            BrokerProfile: User profile data
        
        Raises:
            BrokerOperationError: Not yet implemented
        """
        raise BrokerOperationError(
            "get_profile is not yet implemented for Alice Blue",
            provider=self.provider_name,
            user_id=str(user_id),
        )

    async def get_funds(self, user_id: UUID, access_token: str) -> Funds:
        """Fetch available funds (NOT IMPLEMENTED)."""
        raise BrokerOperationError(
            "get_funds is not yet implemented for Alice Blue",
            provider=self.provider_name,
            user_id=str(user_id),
        )

    # ============================================================
    # Portfolio & Positions (STUBBED - Phase 2)
    # ============================================================

    async def get_holdings(self, user_id: UUID, access_token: str) -> list[Holding]:
        """Fetch long-term holdings (NOT IMPLEMENTED)."""
        raise BrokerOperationError(
            "get_holdings is not yet implemented for Alice Blue",
            provider=self.provider_name,
            user_id=str(user_id),
        )

    async def get_positions(self, user_id: UUID, access_token: str) -> list[Position]:
        """Fetch open trading positions (NOT IMPLEMENTED)."""
        raise BrokerOperationError(
            "get_positions is not yet implemented for Alice Blue",
            provider=self.provider_name,
            user_id=str(user_id),
        )

    # ============================================================
    # Order Management (STUBBED - Phase 2)
    # ============================================================

    async def place_order(
        self, user_id: UUID, access_token: str, order: OrderRequest
    ) -> Order:
        """Place a new order (NOT IMPLEMENTED)."""
        raise BrokerOperationError(
            "place_order is not yet implemented for Alice Blue",
            provider=self.provider_name,
            user_id=str(user_id),
        )

    async def modify_order(
        self, user_id: UUID, access_token: str, order_id: str, modifications: dict
    ) -> Order:
        """Modify an existing pending order (NOT IMPLEMENTED)."""
        raise BrokerOperationError(
            "modify_order is not yet implemented for Alice Blue",
            provider=self.provider_name,
            user_id=str(user_id),
        )

    async def cancel_order(
        self, user_id: UUID, access_token: str, order_id: str
    ) -> Order:
        """Cancel a pending order (NOT IMPLEMENTED)."""
        raise BrokerOperationError(
            "cancel_order is not yet implemented for Alice Blue",
            provider=self.provider_name,
            user_id=str(user_id),
        )

    async def get_orders(
        self, user_id: UUID, access_token: str
    ) -> list[Order]:
        """Fetch all orders for the current trading day (NOT IMPLEMENTED)."""
        raise BrokerOperationError(
            "get_orders is not yet implemented for Alice Blue",
            provider=self.provider_name,
            user_id=str(user_id),
        )

    async def get_order_details(
        self, user_id: UUID, access_token: str, order_id: str
    ) -> Order:
        """Fetch details of a specific order (NOT IMPLEMENTED)."""
        raise BrokerOperationError(
            "get_order_details is not yet implemented for Alice Blue",
            provider=self.provider_name,
            user_id=str(user_id),
        )

    # ============================================================
    # Market Data (STUBBED - Phase 2)
    # ============================================================

    async def get_quotes(
        self, user_id: UUID, access_token: str, symbols: list[str]
    ) -> list[Quote]:
        """Fetch real-time quotes for given symbols (NOT IMPLEMENTED)."""
        raise BrokerOperationError(
            "get_quotes is not yet implemented for Alice Blue",
            provider=self.provider_name,
            user_id=str(user_id),
        )

    async def get_historical_data(
        self,
        user_id: UUID,
        access_token: str,
        symbol: str,
        interval: str,
        from_date: datetime,
        to_date: datetime,
    ) -> list[Candle]:
        """Fetch historical OHLCV candle data (NOT IMPLEMENTED)."""
        raise BrokerOperationError(
            "get_historical_data is not yet implemented for Alice Blue",
            provider=self.provider_name,
            user_id=str(user_id),
        )
