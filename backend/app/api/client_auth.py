import base64
import io
from datetime import UTC, datetime

import jwt
import pyotp
import qrcode
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.logging import log_auth_event
from app.core.security import create_access_token, verify_password
from app.middleware.rate_limit import get_limiter
from app.models.domain import AccountStatus, User, UserRole
from app.schemas.client import (
    ClientLoginInput,
    ClientRefreshInput,
    ClientSessionOutput,
    Enable2FAInput,
    Verify2FAInput,
)
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

    if user.totp_enabled and user.totp_secret:
        # User has 2FA enabled, issue temporary 2FA challenge token
        settings = get_settings()
        temp_payload = {
            "sub": str(user.id),
            "type": "2fa_challenge",
            "exp": datetime.now(UTC).timestamp() + 300  # 5 mins
        }
        temp_2fa_token = jwt.encode(temp_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        return ClientSessionOutput(
            requires_2fa=True,
            temp_2fa_token=temp_2fa_token
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

@router.post("/verify-2fa", response_model=ClientSessionOutput)
def verify_2fa_login(payload: Verify2FAInput, request: Request, db: DbSession) -> ClientSessionOutput:
    settings = get_settings()
    try:
        decoded = jwt.decode(payload.temp_2fa_token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if decoded.get("type") != "2fa_challenge":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token type.")
        user_id = decoded.get("sub")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Expired or invalid 2FA session token.")

    user = db.get(User, user_id)
    if not user or not user.totp_secret or not user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA not configured for this user.")

    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(payload.totp_code.strip()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google Authenticator code.")

    user.last_login_at = datetime.now(UTC)
    refresh_session, raw_refresh_token = create_refresh_session(db, user)
    db.commit()
    access_token = create_access_token(str(user.id), user.role.value, refresh_session.id)

    return ClientSessionOutput(
        user_id=user.id,
        email=user.email,
        account_status=user.account_status.value.lower(),
        access_token=access_token,
        refresh_token=raw_refresh_token,
    )

@router.get("/2fa/setup")
def setup_2fa(user: CurrentUser, db: DbSession):
    if not user.totp_secret:
        user.totp_secret = pyotp.random_base32()
        db.commit()

    totp_uri = pyotp.totp.TOTP(user.totp_secret).provisioning_uri(
        name=user.email,
        issuer_name="Kuberise Capital"
    )

    qr = qrcode.make(totp_uri)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    qr_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    return {
        "secret": user.totp_secret,
        "qr_code": f"data:image/png;base64,{qr_base64}",
        "enabled": user.totp_enabled
    }

@router.post("/2fa/enable")
def enable_2fa(payload: Enable2FAInput, user: CurrentUser, db: DbSession):
    if not user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA setup not initiated.")

    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(payload.totp_code.strip()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code.")

    user.totp_enabled = True
    db.commit()
    return {"message": "Google Authenticator 2FA enabled successfully.", "enabled": True}

@router.post("/2fa/disable")
def disable_2fa(payload: Enable2FAInput, user: CurrentUser, db: DbSession):
    if not user.totp_enabled or not user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA is not enabled.")

    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(payload.totp_code.strip()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code.")

    user.totp_enabled = False
    user.totp_secret = None
    db.commit()
    return {"message": "Google Authenticator 2FA disabled successfully.", "enabled": False}


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
