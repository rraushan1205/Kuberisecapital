import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(subject: str, role: str, session_id: UUID | None = None) -> str:
    settings = get_settings()
    minutes = settings.access_token_admin_minutes if role == "SUPER_ADMIN" else settings.access_token_user_minutes
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=minutes)
    payload = {"sub": subject, "role": role, "jti": str(uuid4()), "iat": now, "exp": expires_at}
    if session_id is not None:
        payload["sid"] = str(session_id)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, object]:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """Hash an opaque refresh token without storing a reusable credential."""
    settings = get_settings()
    return hmac.new(
        settings.jwt_secret_key.encode(),
        token.encode(),
        hashlib.sha256,
    ).hexdigest()
