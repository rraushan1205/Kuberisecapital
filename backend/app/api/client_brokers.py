"""
Client broker API endpoints.

This module provides broker connection management endpoints for authenticated users.
Implements OAuth2 authentication flow for broker integration.

Endpoints:
    POST /api/v1/client/brokers/{provider}/connect - Initiate OAuth flow
    GET /api/v1/client/brokers/{provider}/callback - Handle OAuth callback
    DELETE /api/v1/client/brokers/{provider}/disconnect - Disconnect broker
    GET /api/v1/client/brokers/status - Get broker connection status

Security:
    - All endpoints require valid user authentication (JWT token)
    - State parameter prevents CSRF attacks
    - Tokens are encrypted before database storage
    - Users can only manage their own broker connections
"""

from datetime import UTC, datetime
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DbSession
from app.core.config import get_settings
from app.models.domain import BrokerConnection, BrokerStatus
from app.services.brokers.exceptions import BrokerError
from app.services.brokers.registry import get_global_registry
from app.services.crypto import encrypt_token

router = APIRouter(prefix="/api/v1/client/brokers", tags=["Client Brokers"])


@router.get("/{provider}/connect", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def connect_broker(
    provider: str,
    user: CurrentUser,
    db: DbSession,
) -> JSONResponse:
    """
    Initiate broker OAuth connection flow.
    
    Generates an OAuth authorization URL and redirects the user to the broker's
    login page. After authorization, the broker redirects back to the callback endpoint.
    
    Args:
        provider: Broker provider name (e.g., "fyers", "zerodha")
        user: Authenticated user from JWT token
        db: Database session
    
    Returns:
        RedirectResponse: Redirects to broker OAuth authorization page
    
    Raises:
        HTTPException 404: If provider is not supported
        HTTPException 500: If OAuth URL generation fails
    
    Example:
        GET /api/v1/client/brokers/fyers/connect
        -> Redirects to: https://api-t1.fyers.in/api/v3/generate-authcode?...
    """
    # Get broker provider from registry
    registry = get_global_registry()
    try:
        broker_class = registry.get(provider)
        broker = broker_class()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Broker provider '{provider}' is not supported.",
        )

    settings = get_settings()
    
    # Build callback URL
    # Use configured redirect URI or construct from API base URL
    if hasattr(settings, f"{provider}_redirect_uri"):
        redirect_uri = getattr(settings, f"{provider}_redirect_uri")
    else:
        api_base = getattr(settings, "api_base_url", "http://localhost:8000")
        redirect_uri = f"{api_base}/api/v1/client/brokers/{provider}/callback"

    try:
        # Generate OAuth authorization URL
        auth_url = await broker.get_auth_url(
            user_id=user.id,
            redirect_uri=redirect_uri,
        )

        return JSONResponse(
    status_code=status.HTTP_200_OK,
    content={
        "redirect_url": auth_url
    },
)

    except BrokerError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate broker connection: {str(error)}",
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while connecting to broker.",
        ) from error


@router.get("/{provider}/callback")
async def broker_oauth_callback(
    provider: str,
    auth_code: str = Query(..., alias="auth_code", description="Authorization code from broker"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    db: DbSession = None,
) -> RedirectResponse:
    """
    Handle OAuth callback from broker.
    
    Exchanges the authorization code for an access token and stores it encrypted
    in the database. Creates or updates the BrokerConnection record.
    
    Args:
        provider: Broker provider name
        code: Authorization code from broker redirect
        state: State parameter containing user_id (for CSRF validation)
        db: Database session
    
    Returns:
        dict: Success message and connection status
    
    Raises:
        HTTPException 404: If provider is not supported
        HTTPException 400: If code or state is invalid
        HTTPException 500: If token exchange or storage fails
    
    Example:
        GET /api/v1/client/brokers/fyers/callback?code=ABC123&state=uuid:random
        -> Returns: {"message": "Broker connected successfully", "provider": "fyers"}
    
    Note:
        This endpoint does NOT require authentication via JWT. Instead, it extracts
        the user_id from the state parameter. This is necessary because the broker
        redirects the user here, and we cannot include custom headers in that redirect.
    """
    code = auth_code
    settings = get_settings()
    frontend_broker_url = f"{settings.frontend_url}/dashboard/broker"

    # Get broker provider from registry
    registry = get_global_registry()
    try:
        broker_class = registry.get(provider)
        broker = broker_class()
    except Exception:
        return RedirectResponse(
            url=f"{frontend_broker_url}?error=unsupported_provider&provider={provider}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        # Exchange auth code for access token
        token_data = await broker.handle_oauth_callback(code=code, state=state)

        # Extract user_id from state parameter
        # State format: "user_id:random_string"
        user_id_str = state.split(":")[0]
        from uuid import UUID
        user_id = UUID(user_id_str)

        # Encrypt access token before storing
        access_token_encrypted = encrypt_token(token_data["access_token"])
        
        # Encrypt refresh token if present
        refresh_token_encrypted = None
        if token_data.get("refresh_token"):
            refresh_token_encrypted = encrypt_token(token_data["refresh_token"])

        # Parse token expiry
        token_expires_at = None
        if token_data.get("token_expires_at"):
            token_expires_at = datetime.fromisoformat(token_data["token_expires_at"])

        # Check if connection already exists
        stmt = select(BrokerConnection).where(
            BrokerConnection.user_id == user_id,
            BrokerConnection.provider == provider,
        )
        existing_connection = db.execute(stmt).scalar_one_or_none()

        if existing_connection:
            # Update existing connection
            existing_connection.status = BrokerStatus.CONNECTED
            existing_connection.connected_at = datetime.now(UTC)
            existing_connection.access_token_encrypted = access_token_encrypted
            existing_connection.refresh_token_encrypted = refresh_token_encrypted
            existing_connection.token_expires_at = token_expires_at
            existing_connection.broker_user_id = token_data.get("broker_user_id")
        else:
            # Create new connection
            new_connection = BrokerConnection(
                user_id=user_id,
                provider=provider,
                status=BrokerStatus.CONNECTED,
                connected_at=datetime.now(UTC),
                access_token_encrypted=access_token_encrypted,
                refresh_token_encrypted=refresh_token_encrypted,
                token_expires_at=token_expires_at,
                broker_user_id=token_data.get("broker_user_id"),
            )
            db.add(new_connection)

        db.commit()

        return RedirectResponse(
            url=f"{frontend_broker_url}?connected=true&provider={provider}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    except BrokerError:
        return RedirectResponse(
            url=f"{frontend_broker_url}?error=broker_auth_failed&provider={provider}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception:
        db.rollback()
        return RedirectResponse(
            url=f"{frontend_broker_url}?error=unexpected&provider={provider}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


@router.delete("/{provider}/disconnect")
async def disconnect_broker(
    provider: str,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, str]:
    """
    Disconnect broker and revoke access token.
    
    Revokes the access token with the broker (if supported) and updates the
    database connection status to DISCONNECTED. Removes encrypted tokens.
    
    Args:
        provider: Broker provider name
        user: Authenticated user from JWT token
        db: Database session
    
    Returns:
        dict: Success message
    
    Raises:
        HTTPException 404: If provider is not supported or connection not found
        HTTPException 500: If revocation fails
    
    Example:
        DELETE /api/v1/client/brokers/fyers/disconnect
        -> Returns: {"message": "Broker disconnected successfully"}
    """
    # Get broker provider from registry
    registry = get_global_registry()
    try:
        broker_class = registry.get(provider)
        broker = broker_class()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Broker provider '{provider}' is not supported.",
        )

    # Find existing connection
    stmt = select(BrokerConnection).where(
        BrokerConnection.user_id == user.id,
        BrokerConnection.provider == provider,
    )
    connection = db.execute(stmt).scalar_one_or_none()

    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active connection found for broker '{provider}'.",
        )

    try:
        # Decrypt access token for revocation
        from app.services.crypto import decrypt_token
        
        access_token = None
        if connection.access_token_encrypted:
            access_token = decrypt_token(connection.access_token_encrypted)

        # Revoke token with broker (if supported)
        if access_token:
            await broker.revoke_token(user_id=user.id, access_token=access_token)

        # Update connection status
        connection.status = BrokerStatus.DISCONNECTED
        connection.access_token_encrypted = None
        connection.refresh_token_encrypted = None
        connection.token_expires_at = None
        connection.connected_at = None

        db.commit()

        return {
            "message": "Broker disconnected successfully",
            "provider": provider,
        }

    except BrokerError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect broker: {str(error)}",
        ) from error
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while disconnecting broker.",
        ) from error


@router.get("/status")
async def get_broker_status(
    user: CurrentUser,
    db: DbSession,
) -> dict[str, list[dict]]:
    """
    Get broker connection status for authenticated user.
    
    Returns a list of all broker connections for the user, including
    connection status, provider info, and expiry timestamps.
    
    Args:
        user: Authenticated user from JWT token
        db: Database session
    
    Returns:
        dict: List of broker connections with status
    
    Example:
        GET /api/v1/client/brokers/status
        -> Returns: {
            "connections": [
                {
                    "provider": "fyers",
                    "status": "connected",
                    "connected_at": "2026-07-22T12:00:00Z",
                    "token_expires_at": "2026-07-23T12:00:00Z",
                    "broker_user_id": "XY12345"
                }
            ]
        }
    """
    # Query all connections for user
    stmt = select(BrokerConnection).where(BrokerConnection.user_id == user.id)
    connections = db.execute(stmt).scalars().all()

    # Format response
    connections_data = []
    for conn in connections:
        connections_data.append({
            "provider": conn.provider,
            "status": conn.status.value,
            "connected_at": conn.connected_at.isoformat() if conn.connected_at else None,
            "token_expires_at": conn.token_expires_at.isoformat() if conn.token_expires_at else None,
            "broker_user_id": conn.broker_user_id,
        })

    return {"connections": connections_data}
