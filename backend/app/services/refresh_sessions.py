from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import generate_refresh_token, hash_refresh_token
from app.models.domain import AccountStatus, RefreshToken, User, UserRole


def utc_now() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def session_lifetime_for(user: User) -> tuple[int, int | None]:
    settings = get_settings()
    if user.role == UserRole.SUPER_ADMIN:
        return settings.inactivity_timeout_admin_minutes, settings.absolute_max_session_admin_hours
    return settings.inactivity_timeout_user_minutes, settings.absolute_max_session_user_hours


def _next_expiration(now: datetime, inactivity_minutes: int, absolute_expires_at: datetime | None) -> datetime:
    inactivity_expiration = now + timedelta(minutes=inactivity_minutes)
    return min(inactivity_expiration, absolute_expires_at) if absolute_expires_at else inactivity_expiration


def create_refresh_session(db: Session, user: User) -> tuple[RefreshToken, str]:
    now = utc_now()
    inactivity_minutes, absolute_max_hours = session_lifetime_for(user)
    absolute_expires_at = now + timedelta(hours=absolute_max_hours) if absolute_max_hours else None
    raw_token = generate_refresh_token()
    refresh_session = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_token),
        expires_at=_next_expiration(now, inactivity_minutes, absolute_expires_at),
        absolute_expires_at=absolute_expires_at,
        last_activity_at=now,
        inactivity_timeout_minutes=inactivity_minutes,
        absolute_max_hours=absolute_max_hours,
    )
    db.add(refresh_session)
    db.flush()
    return refresh_session, raw_token


def rotate_refresh_session(db: Session, raw_token: str, required_role: UserRole) -> tuple[User, RefreshToken, str]:
    now = utc_now()
    refresh_session = db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(raw_token))
        .with_for_update()
    )
    if refresh_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session is invalid.")

    user = db.get(User, refresh_session.user_id)
    if user is None or user.role != required_role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session is invalid.")
    if required_role == UserRole.USER and user.account_status != AccountStatus.APPROVED:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_family_id == refresh_session.token_family_id, RefreshToken.revoked.is_(False))
            .values(revoked=True, revoked_at=now)
        )
        db.commit()
        if user.account_status == AccountStatus.PENDING:
            detail = "Your account is pending approval. Please wait for admin approval."
        else:
            detail = "Your account has been rejected. Please contact support."
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

    if refresh_session.revoked:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_family_id == refresh_session.token_family_id, RefreshToken.revoked.is_(False))
            .values(revoked=True, revoked_at=now)
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session reuse was detected. Please sign in again.")

    if as_utc(refresh_session.expires_at) <= now or (
        refresh_session.absolute_expires_at is not None and as_utc(refresh_session.absolute_expires_at) <= now
    ):
        refresh_session.revoked = True
        refresh_session.revoked_at = now
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session has expired. Please sign in again.")

    refresh_session.revoked = True
    refresh_session.revoked_at = now
    refresh_session.last_activity_at = now
    raw_next_token = generate_refresh_token()
    next_session = RefreshToken(
        user_id=user.id,
        token_family_id=refresh_session.token_family_id,
        token_hash=hash_refresh_token(raw_next_token),
        expires_at=_next_expiration(now, refresh_session.inactivity_timeout_minutes, refresh_session.absolute_expires_at),
        absolute_expires_at=refresh_session.absolute_expires_at,
        last_activity_at=now,
        inactivity_timeout_minutes=refresh_session.inactivity_timeout_minutes,
        absolute_max_hours=refresh_session.absolute_max_hours,
    )
    db.add(next_session)
    db.commit()
    db.refresh(next_session)
    return user, next_session, raw_next_token


def revoke_refresh_session(db: Session, raw_token: str | None) -> None:
    if not raw_token:
        return
    refresh_session = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token)))
    if refresh_session is None or refresh_session.revoked:
        return
    refresh_session.revoked = True
    refresh_session.revoked_at = utc_now()
    db.commit()


def invalidate_all_user_sessions(db: Session, user_id: UUID) -> int:
    """
    Invalidate all active sessions for a user.

    Call this when:
        - User changes password
        - User role changes
        - Account status changes (suspended/banned)
        - Security breach detected

    Args:
        db: Database session
        user_id: User UUID

    Returns:
        int: Number of sessions invalidated
    """
    now = utc_now()
    result = db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
        .values(revoked=True, revoked_at=now)
    )
    db.commit()
    return result.rowcount


def session_is_active(db: Session, session_id: UUID) -> bool:
    refresh_session = db.get(RefreshToken, session_id)
    if refresh_session is None or refresh_session.revoked:
        return False
    now = utc_now()
    return as_utc(refresh_session.expires_at) > now and (
        refresh_session.absolute_expires_at is None or as_utc(refresh_session.absolute_expires_at) > now
    )
