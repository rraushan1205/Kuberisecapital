from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.api.dependencies import DbSession
from app.core.logging import log_auth_event
from app.core.security import create_access_token, verify_password
from app.middleware.rate_limit import get_limiter
from app.models.domain import AccountStatus, User, UserRole
from app.schemas.client import ClientLoginInput, ClientRefreshInput, ClientSessionOutput
from app.services.refresh_sessions import (
    create_refresh_session,
    revoke_refresh_session,
    rotate_refresh_session,
)

router = APIRouter(prefix="/api/v1/client/auth", tags=["Client Auth"])
limiter = get_limiter()


@router.post("/login", response_model=ClientSessionOutput)
@limiter.limit("5/minute")
def login_client(payload: ClientLoginInput, request: Request, db: DbSession) -> ClientSessionOutput:
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))

    if user is None or not verify_password(payload.password, user.password_hash):
        log_auth_event(
            event_type="client_login",
            success=False,
            email=payload.email,
            reason="Invalid credentials",
            ip_address=request.client.host if request.client else None
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    if user.role != UserRole.USER:
        log_auth_event(
            event_type="client_login",
            success=False,
            email=user.email,
            user_id=str(user.id),
            reason="Wrong login portal - admin account",
            ip_address=request.client.host if request.client else None
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Use the admin login for this account.")

    if user.account_status == AccountStatus.PENDING:
        log_auth_event(
            event_type="client_login",
            success=False,
            email=user.email,
            user_id=str(user.id),
            reason="Account pending approval",
            ip_address=request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending approval. Please wait for admin approval.",
        )

    if user.account_status == AccountStatus.REJECTED:
        log_auth_event(
            event_type="client_login",
            success=False,
            email=user.email,
            user_id=str(user.id),
            reason="Account rejected",
            ip_address=request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been rejected. Please contact support.",
        )

    user.last_login_at = datetime.now(UTC)
    refresh_session, raw_refresh_token = create_refresh_session(db, user)
    db.commit()
    access_token = create_access_token(str(user.id), user.role.value, refresh_session.id)

    log_auth_event(
        event_type="client_login",
        success=True,
        email=user.email,
        user_id=str(user.id),
        ip_address=request.client.host if request.client else None
    )

    return ClientSessionOutput(
        user_id=user.id,
        email=user.email,
        account_status=user.account_status.value.lower(),
        access_token=access_token,
        refresh_token=raw_refresh_token,
    )


@router.post("/refresh", response_model=ClientSessionOutput)
def refresh_client_session(payload: ClientRefreshInput, db: DbSession) -> ClientSessionOutput:
    user, refresh_session, raw_refresh_token = rotate_refresh_session(db, payload.refresh_token, UserRole.USER)
    access_token = create_access_token(str(user.id), user.role.value, refresh_session.id)
    return ClientSessionOutput(
        user_id=user.id,
        email=user.email,
        account_status=user.account_status.value.lower(),
        access_token=access_token,
        refresh_token=raw_refresh_token,
    )


@router.post("/logout")
def logout_client(payload: ClientRefreshInput, db: DbSession) -> dict[str, str]:
    revoke_refresh_session(db, payload.refresh_token)
    return {"message": "Logged out."}
