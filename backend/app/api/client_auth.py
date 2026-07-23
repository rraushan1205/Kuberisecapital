from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.api.dependencies import DbSession
from app.core.config import get_settings
from app.core.security import create_access_token, verify_password
from app.models.domain import User, UserRole
from app.schemas.client import ClientLoginInput, ClientSessionOutput

router = APIRouter(prefix="/api/v1/client/auth", tags=["Client Auth"])


@router.post("/login", response_model=ClientSessionOutput)
def login_client(payload: ClientLoginInput, response: Response, db: DbSession) -> ClientSessionOutput:
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    if user.role != UserRole.USER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Use the admin login for this account.")

    user.last_login_at = datetime.now(UTC)
    db.commit()

    token = create_access_token(str(user.id), user.role.value)
    response.set_cookie(
        key="stratum_session",
        value=token,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="lax",
        max_age=get_settings().jwt_expires_minutes * 60,
        path="/",
    )
    return ClientSessionOutput(user_id=user.id, email=user.email, account_status=user.account_status.value.lower())


@router.post("/logout")
def logout_client(response: Response) -> dict[str, str]:
    response.delete_cookie("stratum_session", path="/")
    return {"message": "Logged out."}
