from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.domain import AccountStatus, User, UserRole
from app.services.refresh_sessions import session_is_active

bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


def require_super_admin(
    db: DbSession,
    bearer: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if bearer is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin authentication is required.")
    token = bearer.credentials
    try:
        payload = decode_access_token(token)
        subject = UUID(str(payload["sub"]))
        session_id = UUID(str(payload["sid"]))
    except (InvalidTokenError, KeyError, ValueError, TypeError) as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin session.") from error

    user = db.get(User, subject)
    if user is None or user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super Admin access is required.")
    if not session_is_active(db, session_id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin session has expired or was revoked.")
    return user


SuperAdmin = Annotated[User, Depends(require_super_admin)]


def require_current_user(
    db: DbSession,
    bearer: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """
    Require authenticated user (regular user, not admin).

    Validates JWT token from the Authorization header and returns the authenticated user.
    Used for client-facing endpoints that require user authentication.

    Args:
        db: Database session
        bearer: Bearer token from Authorization header

    Returns:
        User: The authenticated user

    Raises:
        HTTPException: 401 if token is missing or invalid
        HTTPException: 403 if user account is not approved
    """
    if bearer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
        )
    token = bearer.credentials

    try:
        payload = decode_access_token(token)
        subject = UUID(str(payload["sub"]))
    except (InvalidTokenError, KeyError, ValueError, TypeError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        ) from error

    user = db.get(User, subject)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    session_identifier = payload.get("sid")
    if session_identifier is not None:
        try:
            is_active = session_is_active(db, UUID(str(session_identifier)))
        except (ValueError, TypeError) as error:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication session.") from error
        if not is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication session has expired or was revoked.")

    # Check if user account is approved
    if user.account_status != AccountStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending approval or has been rejected.",
        )

    return user


CurrentUser = Annotated[User, Depends(require_current_user)]
