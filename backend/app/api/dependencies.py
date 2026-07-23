from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.domain import AccountStatus, User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


def require_super_admin(
    db: DbSession,
    bearer: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    admin_session: Annotated[str | None, Cookie(alias="stratum_admin_session")] = None,
) -> User:
    token = bearer.credentials if bearer is not None else admin_session
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin authentication is required.")
    try:
        payload = decode_access_token(token)
        subject = UUID(str(payload["sub"]))
    except (InvalidTokenError, KeyError, ValueError, TypeError) as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin session.") from error

    user = db.get(User, subject)
    if user is None or user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super Admin access is required.")
    return user


SuperAdmin = Annotated[User, Depends(require_super_admin)]


def require_current_user(
    db: DbSession,
    bearer: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[str | None, Cookie(alias="stratum_session")] = None,
) -> User:
    """
    Require authenticated user (regular user, not admin).
    
    Validates JWT token from Authorization header or session cookie and returns the authenticated user.
    Used for client-facing endpoints that require user authentication.
    
    Args:
        db: Database session
        bearer: Bearer token from Authorization header
        session: Session token from cookie
    
    Returns:
        User: The authenticated user
    
    Raises:
        HTTPException: 401 if token is missing or invalid
        HTTPException: 403 if user account is not approved
    """
    token = bearer.credentials if bearer is not None else session
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
        )

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

    # Check if user account is approved
    if user.account_status != AccountStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending approval or has been rejected.",
        )

    return user


CurrentUser = Annotated[User, Depends(require_current_user)]
