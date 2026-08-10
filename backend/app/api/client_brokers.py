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
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DbSession
from app.core.config import get_settings
from app.models.domain import BrokerApiKey, BrokerConnection, BrokerStatus
from app.schemas.client import BrokerApiKeyInput, BrokerApiKeyOutput
from app.services.brokers.exceptions import BrokerError
from app.services.brokers.registry import get_global_registry
from app.services.crypto import decrypt_token, encrypt_token

router = APIRouter(prefix="/api/v1/client/brokers", tags=["Client Brokers"])


@router.get("/{provider}/connect")
async def connect_broker(
    provider: str,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, str]:
    """
    Initiate broker OAuth connection flow.
    
    Generates an OAuth authorization URL and returns it as JSON. The frontend
    then navigates the browser to this URL to begin the OAuth flow.
    
    Args:
        provider: Broker provider name (e.g., "fyers", "zerodha")
        user: Authenticated user from JWT token
        db: Database session
    
    Returns:
        dict: JSON containing the authorize_url
    
    Raises:
        HTTPException 404: If provider is not supported
        HTTPException 500: If OAuth URL generation fails
    
    Example:
        GET /api/v1/client/brokers/fyers/connect
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

        return {"authorize_url": auth_url}

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
    auth_code: str = Query(None, alias="auth_code", description="Authorization code from broker (Fyers uses this)"),
    code: str = Query(None, description="Alternative code param (fallback)"),
    authCode: str = Query(None, description="Alice Blue authCode parameter"),
    userId: str = Query(None, description="Alice Blue userId parameter"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    db: DbSession = None,
) -> RedirectResponse:
    """
    Handle OAuth callback from broker.
    
    Exchanges the authorization code for an access token and stores it encrypted
    in the database. Creates or updates the BrokerConnection record.
    
    Provider-Specific Callback Params:
        - Fyers: auth_code (or code)
        - Alice Blue: authCode + userId (both required)
    
    Args:
        provider: Broker provider name
        auth_code: Authorization code from Fyers
        code: Alternative code param (fallback)
        authCode: Alice Blue's authCode parameter
        userId: Alice Blue's userId parameter
        state: State parameter containing user_id (for CSRF validation)
        db: Database session
    
    Returns:
        RedirectResponse: Redirects to frontend with success or error params
    
    Raises:
        HTTPException 404: If provider is not supported
        HTTPException 400: If code or state is invalid
        HTTPException 500: If token exchange or storage fails
    
    Example:
        GET /api/v1/client/brokers/fyers/callback?auth_code=ABC123&state=uuid:random
        GET /api/v1/client/brokers/aliceblue/callback?authCode=XYZ&userId=AB123&state=uuid:random
    
    Note:
        This endpoint does NOT require authentication via JWT. Instead, it extracts
        the user_id from the state parameter. This is necessary because the broker
        redirects the user here, and we cannot include custom headers in that redirect.
    """
    # Handle provider-specific parameter mapping
    if provider == "aliceblue":
        # Alice Blue sends authCode and userId as separate params
        if not authCode or not userId:
            return RedirectResponse(
                url=f"{get_settings().frontend_url}/dashboard/broker?error=missing_params&provider={provider}",
                status_code=status.HTTP_303_SEE_OTHER,
            )
        # Combine them with pipe separator for Alice Blue's handle_oauth_callback
        code_param = f"{authCode}|{userId}"
    else:
        # Fyers and other brokers use auth_code or code param
        code_param = auth_code or code
        if not code_param:
            return RedirectResponse(
                url=f"{get_settings().frontend_url}/dashboard/broker?error=missing_code&provider={provider}",
                status_code=status.HTTP_303_SEE_OTHER,
            )
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
        token_data = await broker.handle_oauth_callback(code=code_param, state=state)

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


# ─────────────────────────────────────────────────────────────────────────────
# API Key Management
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/api-keys", response_model=BrokerApiKeyOutput, status_code=status.HTTP_201_CREATED)
async def store_broker_api_key(
    data: BrokerApiKeyInput,
    user: CurrentUser,
    db: DbSession,
) -> BrokerApiKeyOutput:
    """
    Store encrypted broker API credentials.
    
    Encrypts and stores API key and secret for a broker provider.
    Uses upsert behavior - updates if key exists for provider, creates if not.
    
    Args:
        data: API key input (provider, api_key, api_secret)
        user: Authenticated user from JWT token
        db: Database session
    
    Returns:
        BrokerApiKeyOutput: Created/updated API key with masked credentials
    
    Raises:
        HTTPException 400: If validation fails
        HTTPException 500: If storage fails
    
    Security:
        - API key and secret are encrypted before storage using Fernet
        - Original values are never stored in plaintext
        - Response contains only masked key (last 4 characters)
    """
    try:
        # Encrypt credentials before storage
        api_key_encrypted = encrypt_token(data.api_key)
        api_secret_encrypted = encrypt_token(data.api_secret)
        
        # Check if API key already exists for this provider
        stmt = select(BrokerApiKey).where(
            BrokerApiKey.user_id == user.id,
            BrokerApiKey.provider == data.provider,
        )
        existing_key = db.execute(stmt).scalar_one_or_none()
        
        if existing_key:
            # Update existing key (upsert behavior)
            existing_key.api_key_encrypted = api_key_encrypted
            existing_key.api_secret_encrypted = api_secret_encrypted
            existing_key.updated_at = datetime.now(UTC)
            db.commit()
            db.refresh(existing_key)
            
            # Return masked response
            return BrokerApiKeyOutput(
                id=existing_key.id,
                provider=existing_key.provider,
                api_key_masked=f"****{data.api_key[-4:]}" if len(data.api_key) >= 4 else "****",
                created_at=existing_key.created_at,
                updated_at=existing_key.updated_at,
            )
        else:
            # Create new API key
            new_key = BrokerApiKey(
                user_id=user.id,
                provider=data.provider,
                api_key_encrypted=api_key_encrypted,
                api_secret_encrypted=api_secret_encrypted,
            )
            db.add(new_key)
            db.commit()
            db.refresh(new_key)
            
            # Return masked response
            return BrokerApiKeyOutput(
                id=new_key.id,
                provider=new_key.provider,
                api_key_masked=f"****{data.api_key[-4:]}" if len(data.api_key) >= 4 else "****",
                created_at=new_key.created_at,
                updated_at=new_key.updated_at,
            )
            
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store API key: {str(error)}",
        ) from error


@router.get("/api-keys", response_model=list[BrokerApiKeyOutput])
async def list_broker_api_keys(
    user: CurrentUser,
    db: DbSession,
) -> list[BrokerApiKeyOutput]:
    """
    List all stored broker API keys for the authenticated user.
    
    Returns a list of all API keys with masked credentials.
    Never returns actual API keys or secrets.
    
    Args:
        user: Authenticated user from JWT token
        db: Database session
    
    Returns:
        list[BrokerApiKeyOutput]: List of API keys with masked credentials
    
    Example:
        GET /api/v1/client/brokers/api-keys
        -> Returns: [
            {
                "id": "uuid",
                "provider": "fyers",
                "api_key_masked": "****XY12",
                "created_at": "2026-08-03T12:00:00Z",
                "updated_at": "2026-08-03T12:00:00Z"
            }
        ]
    """
    stmt = select(BrokerApiKey).where(BrokerApiKey.user_id == user.id)
    api_keys = db.execute(stmt).scalars().all()
    
    result = []
    for key in api_keys:
        # Decrypt only to get last 4 chars for masking
        try:
            decrypted_key = decrypt_token(key.api_key_encrypted)
            masked = f"****{decrypted_key[-4:]}" if len(decrypted_key) >= 4 else "****"
        except Exception:
            masked = "****"
        
        result.append(
            BrokerApiKeyOutput(
                id=key.id,
                provider=key.provider,
                api_key_masked=masked,
                created_at=key.created_at,
                updated_at=key.updated_at,
            )
        )
    
    return result


@router.delete("/api-keys/{provider}", status_code=status.HTTP_200_OK)
async def delete_broker_api_key(
    provider: str,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, str]:
    """
    Delete stored broker API key.
    
    Removes the encrypted API key and secret for the specified provider.
    
    Args:
        provider: Broker provider name
        user: Authenticated user from JWT token
        db: Database session
    
    Returns:
        dict: Success message
    
    Raises:
        HTTPException 404: If API key not found for provider
        HTTPException 500: If deletion fails
    
    Example:
        DELETE /api/v1/client/brokers/api-keys/fyers
        -> Returns: {"message": "API key deleted successfully", "provider": "fyers"}
    """
    stmt = select(BrokerApiKey).where(
        BrokerApiKey.user_id == user.id,
        BrokerApiKey.provider == provider,
    )
    api_key = db.execute(stmt).scalar_one_or_none()
    
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No API key found for provider '{provider}'.",
        )
    
    try:
        db.delete(api_key)
        db.commit()
        
        return {
            "message": "API key deleted successfully",
            "provider": provider,
        }
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete API key: {str(error)}",
        ) from error
