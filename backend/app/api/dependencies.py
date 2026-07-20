from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.domain import User, UserRole

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
