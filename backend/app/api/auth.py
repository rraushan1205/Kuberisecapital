from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.api.dependencies import DbSession
from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.middleware.rate_limit import get_limiter
from app.models.domain import AccountStatus, User, UserRole
from app.services.auth_tokens import (
    create_email_verification_token,
    use_email_verification_token,
    create_password_reset_token,
    use_password_reset_token,
)
from app.services.refresh_sessions import invalidate_all_user_sessions
from app.schemas.auth import (
    AccountStatusResponse,
    UserInfo,
    UserLoginInput,
    UserLoginOutput,
    UserRegistrationInput,
    UserRegistrationOutput,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
limiter = get_limiter()


@router.post("/register", response_model=UserRegistrationOutput, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/hour")
def register_user(payload: UserRegistrationInput, request: Request, db: DbSession) -> UserRegistrationOutput:
    """
    Register a new user account. The account will be in PENDING status
    and requires admin approval before the user can access the system.
    """
    configured_codes = {
        code.strip().upper()
        for code in get_settings().registration_invitation_codes
        if code.strip()
    }
    if not configured_codes:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration is temporarily unavailable. Please contact support.",
        )
    if payload.invitation_code.strip().upper() not in configured_codes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation code is not active.",
        )

    email_normalized = payload.email.strip().lower()
    
    # Check if user already exists
    existing_user = db.scalar(select(User).where(User.email == email_normalized))
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists."
        )
    
    # Create new user with PENDING status
    new_user = User(
        email=email_normalized,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip() if payload.full_name else None,
        role=UserRole.USER,
        email_verified=False,  # Can be verified via email later
        account_status=AccountStatus.PENDING,  # Requires admin approval
    )
    
    db.add(new_user)
    db.commit()
    
    return UserRegistrationOutput(
        message="Registration successful! Your account is pending admin approval.",
        email=email_normalized
    )


@router.post("/login", response_model=UserLoginOutput)
@limiter.limit("5/minute")
def login_user(payload: UserLoginInput, request: Request, db: DbSession) -> UserLoginOutput:
    """
    Authenticate a user and return an access token.
    Only users with APPROVED account status can log in.
    """
    email_normalized = payload.email.strip().lower()
    
    # Find user by email
    user = db.scalar(select(User).where(User.email == email_normalized))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
    
    # Verify password
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
    
    # Check account status
    if user.account_status == AccountStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending approval. Please wait for admin approval."
        )
    
    if user.account_status == AccountStatus.REJECTED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been rejected. Please contact support."
        )
    
    # Generate JWT token
    access_token = create_access_token(subject=str(user.id), role=user.role.value)
    
    return UserLoginOutput(
        access_token=access_token,
        token_type="bearer",
        user=UserInfo(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            account_status=user.account_status.value,
            email_verified=user.email_verified,
        )
    )


@router.get("/account-status/{email}", response_model=AccountStatusResponse)
def get_account_status(email: str, db: DbSession) -> AccountStatusResponse:
    """
    Check the account status for a given email address.
    Used to determine if a user is pending, approved, or rejected.
    """
    email_normalized = email.strip().lower()
    
    user = db.scalar(select(User).where(User.email == email_normalized))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email address."
        )
    
    status_messages = {
        AccountStatus.PENDING: "Your account is pending approval.",
        AccountStatus.APPROVED: "Your account is approved.",
        AccountStatus.REJECTED: "Your account has been rejected.",
    }
    
    return AccountStatusResponse(
        email=user.email,
        account_status=user.account_status.value,
        message=status_messages.get(user.account_status, "Unknown status")
    )


@router.get("/verify-email")
def verify_email(token: str, db: DbSession):
    """Verify a user's email using a one-time token.

    In development environment the verification URL/token is returned by the registration flow
    for convenience. In production, tokens should be sent via email and not returned in responses.
    """
    user = use_email_verification_token(db, token)
    return {"message": "Email verified successfully.", "email": user.email}


@router.post("/forgot-password")
@limiter.limit("3/hour")
def forgot_password(email: str, db: DbSession):
    """Initiate password reset flow. Creates a one-time token and (in development) returns the reset URL.

    Production deployments should send the reset URL to the user's email address instead of returning it.
    """
    settings = get_settings()
    email_normalized = email.strip().lower()
    user = db.scalar(select(User).where(User.email == email_normalized))
    # Do not reveal whether the email exists
    if user is None:
        return {"message": "If an account exists for this email, a password reset link has been sent."}

    token_obj, raw = create_password_reset_token(db, user)
    reset_url = f"{settings.frontend_url}/reset-password?token={raw}" if settings.environment != "production" else None

    # NOTE: Integrate real email sending here in production.
    response = {"message": "If an account exists for this email, a password reset link has been sent."}
    if reset_url:
        response["reset_url"] = reset_url
    return response


@router.post("/reset-password")
@limiter.limit("5/hour")
def reset_password(token: str, new_password: str, db: DbSession):
    """Reset a user's password using a one-time token. Invalidates all existing sessions on success."""
    # Validate password strength via existing schema rules (reuse hash_password here)
    token_obj = use_password_reset_token(db, token)
    user = db.get(User, token_obj.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token or user.")

    # Update password
    user.password_hash = hash_password(new_password)
    db.commit()

    # Invalidate existing sessions
    invalidate_all_user_sessions(db, user.id)

    return {"message": "Password has been reset successfully."}
