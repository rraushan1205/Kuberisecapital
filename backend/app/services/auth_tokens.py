"""Services for email verification and password reset tokens.

This module provides creation and verification helpers for one-time tokens used in
email verification and password reset flows. Tokens are stored hashed in the DB to
avoid persistent plaintext tokens.
"""
from datetime import UTC, datetime, timedelta
from typing import Tuple
import secrets

from sqlalchemy import select, update
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.security import hash_refresh_token
from app.models.domain import EmailVerificationToken, PasswordResetToken, User


def _utc_now() -> datetime:
    return datetime.now(UTC)


def create_email_verification_token(db: Session, user: User, ttl_seconds: int = 3600) -> Tuple[EmailVerificationToken, str]:
    now = _utc_now()
    raw = secrets.token_urlsafe(48)
    token_hash = hash_refresh_token(raw)
    expires_at = now + timedelta(seconds=ttl_seconds)

    token = EmailVerificationToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token, raw


def use_email_verification_token(db: Session, raw_token: str) -> User:
    now = _utc_now()
    token_hash = hash_refresh_token(raw_token)
    token = db.scalar(select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash))
    if token is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token.")
    if token.used:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification token has already been used.")
    if token.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification token has expired.")

    user = db.get(User, token.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found.")

    # mark token used and set user verified
    token.used = True
    token.used_at = now
    user.email_verified = True
    db.commit()
    db.refresh(user)
    return user


def create_password_reset_token(db: Session, user: User, ttl_seconds: int = 3600) -> Tuple[PasswordResetToken, str]:
    now = _utc_now()
    raw = secrets.token_urlsafe(48)
    token_hash = hash_refresh_token(raw)
    expires_at = now + timedelta(seconds=ttl_seconds)

    token = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token, raw


def use_password_reset_token(db: Session, raw_token: str) -> PasswordResetToken:
    now = _utc_now()
    token_hash = hash_refresh_token(raw_token)
    token = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    if token is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired password reset token.")
    if token.used:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password reset token has already been used.")
    if token.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password reset token has expired.")

    # mark used
    token.used = True
    token.used_at = now
    db.commit()
    db.refresh(token)
    return token
