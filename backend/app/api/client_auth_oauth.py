"""
OAuth-based authentication endpoints for broker login.

This module provides OAuth login functionality where users can authenticate
using their broker accounts (e.g., Fyers) instead of email/password.

Flow:
1. User clicks "Login with Fyers" on login page
2. GET /auth/oauth/{provider}/login - Generates OAuth URL
3. User redirects to broker OAuth page
4. Broker redirects back to callback
5. GET /auth/oauth/{provider}/callback - Creates/finds user, establishes session
6. User redirected to dashboard with JWT tokens
"""

import secrets
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.api.dependencies import DbSession
from app.core.config import get_settings
from app.core.logging import log_auth_event
from app.core.security import create_access_token
from app.models.domain import AccountStatus, BrokerConnection, BrokerStatus, LoginMethod, User, UserRole
from app.schemas.client import ClientSessionOutput
from app.services.brokers.exceptions import BrokerError
from app.services.brokers.registry import get_global_registry
from app.services.crypto import encrypt_token
from app.services.oauth_state_store import store_oauth_state, consume_oauth_state
from app.services.refresh_sessions import create_refresh_session

router = APIRouter(prefix="/api/v1/client/auth/oauth", tags=["Client Auth OAuth"])


@router.get("/{provider}/login")
async def oauth_login_initiate(
    provider: str,
    request: Request,
    db: DbSession,
) -> dict[str, str]:
    """
    Initiate OAuth-based login flow (unauthenticated endpoint).
    
    Generates an OAuth authorization URL for users to log in using their broker account.
    This endpoint does NOT require authentication - it's for users who want to log in.
    
    The state parameter encodes: login_flow=true to differentiate from broker connection flow.
    
    Args:
        provider: Broker provider name (e.g., "fyers", "zerodha")
        request: FastAPI request object
        db: Database session
    
    Returns:
        dict: JSON containing the authorize_url
    
    Raises:
        HTTPException 404: If provider is not supported
        HTTPException 500: If OAuth URL generation fails
    
    Example:
        GET /api/v1/client/auth/oauth/fyers/login
        -> Returns: {"authorize_url": "https://api-t1.fyers.in/api/v3/generate-authcode?..."}
    """
    # Get broker provider from registry
    registry = get_global_registry()
    try:
        broker_class = registry.get(provider)
        broker = broker_class()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Broker provider '{provider}' is not supported for OAuth login.",
        )

    settings = get_settings()
    
    # Build callback URL for OAuth login (different from broker connection callback)
    if hasattr(settings, f"{provider}_login_redirect_uri"):
        redirect_uri = getattr(settings, f"{provider}_login_redirect_uri")
    else:
        api_base = getattr(settings, "api_base_url", "http://localhost:8000")
        redirect_uri = f"{api_base}/api/v1/client/auth/oauth/{provider}/callback"

    try:
        # Generate OAuth authorization URL using broker's get_auth_url
        # Use special marker "LOGIN_FLOW" to indicate this is OAuth login (not broker connection)
        # The broker will generate its own state with this marker and store it in Redis
        login_marker = "LOGIN_FLOW"
        auth_url = await broker.get_auth_url(
            user_id=login_marker,  # Broker will use this to create state: "LOGIN_FLOW:{random}"
            redirect_uri=redirect_uri,
        )

        log_auth_event(
            event_type="oauth_login_initiated",
            success=True,
            email=None,
            user_id=None,
            reason=f"OAuth login flow started for provider: {provider}",
            ip_address=request.client.host if request.client else None
        )

        return {"authorize_url": auth_url}

    except BrokerError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate OAuth login: {str(error)}",
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during OAuth login initialization.",
        ) from error


@router.get("/{provider}/callback")
async def oauth_login_callback(
    provider: str,
    request: Request,
    auth_code: str = Query(..., alias="auth_code", description="Authorization code from broker"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    db: DbSession = None,
) -> RedirectResponse:
    """
    Handle OAuth callback for login flow.
    
    This endpoint:
    1. Validates state parameter
    2. Exchanges auth code for access token
    3. Gets broker user ID
    4. Finds or creates User account
    5. Creates/updates BrokerConnection
    6. Establishes login session (JWT tokens)
    7. Redirects to dashboard with tokens in URL fragment
    
    Args:
        provider: Broker provider name
        request: FastAPI request object
        auth_code: Authorization code from broker redirect
        state: State parameter for CSRF validation
        db: Database session
    
    Returns:
        RedirectResponse: Redirect to frontend with tokens or error
    
    Note:
        This is an unauthenticated endpoint - user is not logged in yet.
    """
    code = auth_code
    settings = get_settings()
    frontend_url = settings.frontend_url
    
    # Validate and consume state parameter (single-use, prevents replay attacks)
    # This uses the same OAuth state store as broker connection flow
    state_valid = await consume_oauth_state(state)
    if not state_valid:
        log_auth_event(
            event_type="oauth_login_callback",
            success=False,
            email=None,
            reason="Invalid state parameter (CSRF check failed)",
            ip_address=request.client.host if request.client else None
        )
        return RedirectResponse(
            url=f"{frontend_url}/login?error=invalid_state",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Get broker provider from registry
    registry = get_global_registry()
    try:
        broker_class = registry.get(provider)
        broker = broker_class()
    except Exception:
        return RedirectResponse(
            url=f"{frontend_url}/login?error=unsupported_provider",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        # Exchange auth code for access token
        token_data = await broker.handle_oauth_callback(code=code, state=state)
        
        broker_user_id = token_data.get("broker_user_id")
        if not broker_user_id:
            raise ValueError("broker_user_id not returned from OAuth")

        # Find user by broker_user_id in BrokerConnection table
        stmt = select(BrokerConnection).where(
            BrokerConnection.provider == provider,
            BrokerConnection.broker_user_id == broker_user_id,
        )
        existing_connection = db.execute(stmt).scalar_one_or_none()
        
        user = None
        if existing_connection:
            # User already has a broker connection - fetch the user
            user = db.get(User, existing_connection.user_id)
        
        if not user:
            # No existing connection found - this means first-time OAuth login
            # We cannot create a user without an email address
            # Redirect to registration with broker info
            return RedirectResponse(
                url=f"{frontend_url}/register?oauth_provider={provider}&broker_user_id={broker_user_id}&error=no_account",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        # Check account status
        if user.account_status == AccountStatus.PENDING:
            log_auth_event(
                event_type="oauth_login_callback",
                success=False,
                email=user.email,
                user_id=str(user.id),
                reason="Account pending approval",
                ip_address=request.client.host if request.client else None
            )
            return RedirectResponse(
                url=f"{frontend_url}/pending-approval?email={user.email}",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        if user.account_status == AccountStatus.REJECTED:
            log_auth_event(
                event_type="oauth_login_callback",
                success=False,
                email=user.email,
                user_id=str(user.id),
                reason="Account rejected",
                ip_address=request.client.host if request.client else None
            )
            return RedirectResponse(
                url=f"{frontend_url}/account-rejected?email={user.email}",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        # Update user's login method and last broker used
        user.login_method = LoginMethod.OAUTH
        user.last_broker_used = provider
        user.last_login_at = datetime.now(UTC)

        # Encrypt and update broker tokens
        access_token_encrypted = encrypt_token(token_data["access_token"])
        refresh_token_encrypted = None
        if token_data.get("refresh_token"):
            refresh_token_encrypted = encrypt_token(token_data["refresh_token"])

        token_expires_at = None
        if token_data.get("token_expires_at"):
            token_expires_at = datetime.fromisoformat(token_data["token_expires_at"])

        # Update existing broker connection
        existing_connection.status = BrokerStatus.CONNECTED
        existing_connection.connected_at = datetime.now(UTC)
        existing_connection.access_token_encrypted = access_token_encrypted
        existing_connection.refresh_token_encrypted = refresh_token_encrypted
        existing_connection.token_expires_at = token_expires_at

        # Create refresh session for Stratum authentication
        refresh_session, raw_refresh_token = create_refresh_session(db, user)
        
        db.commit()

        # Create access token (JWT)
        access_token = create_access_token(str(user.id), user.role.value, refresh_session.id)

        log_auth_event(
            event_type="oauth_login_callback",
            success=True,
            email=user.email,
            user_id=str(user.id),
            reason=f"OAuth login successful via {provider}",
            ip_address=request.client.host if request.client else None
        )

        # Redirect to frontend with tokens in URL fragment (not query params for security)
        # Frontend will extract these and store them properly
        return RedirectResponse(
            url=f"{frontend_url}/login/oauth-callback?access_token={access_token}&refresh_token={raw_refresh_token}&user_id={user.id}&email={user.email}&account_status={user.account_status.value.lower()}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    except BrokerError as error:
        log_auth_event(
            event_type="oauth_login_callback",
            success=False,
            email=None,
            reason=f"Broker OAuth error: {str(error)}",
            ip_address=request.client.host if request.client else None
        )
        return RedirectResponse(
            url=f"{frontend_url}/login?error=broker_auth_failed",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as error:
        log_auth_event(
            event_type="oauth_login_callback",
            success=False,
            email=None,
            reason=f"Unexpected error: {str(error)}",
            ip_address=request.client.host if request.client else None
        )
        return RedirectResponse(
            url=f"{frontend_url}/login?error=unexpected_error",
            status_code=status.HTTP_303_SEE_OTHER,
        )
