from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.domain import AccountStatus, SubscriptionStatus, User, UserRole


def ensure_initial_super_admin(session: Session) -> User | None:
    existing_super_admin = session.scalar(select(User).where(User.role == UserRole.SUPER_ADMIN))
    if existing_super_admin is not None:
        return None

    settings = get_settings()
    account_with_admin_email = session.scalar(select(User).where(User.email == settings.admin_email))
    if account_with_admin_email is not None:
        raise RuntimeError("ADMIN_EMAIL already belongs to a non-Super-Admin account.")

    initial_admin = User(
        email=settings.admin_email,
        password_hash=hash_password(settings.admin_password),
        role=UserRole.SUPER_ADMIN,
        email_verified=True,
        account_status=AccountStatus.APPROVED,
        subscription_status=SubscriptionStatus.ACTIVE,
    )
    session.add(initial_admin)
    session.commit()
    session.refresh(initial_admin)

    # Do not print secrets to stdout. Log the creation event without exposing the password.
    from app.core.logging import get_logger

    logger = get_logger("admin_bootstrap")
    logger.info("initial_super_admin_created", email=settings.admin_email)

    return initial_admin
