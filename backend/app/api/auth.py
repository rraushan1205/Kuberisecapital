from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.dependencies import DbSession
from app.core.security import create_access_token, hash_password, verify_password
from app.models.domain import AccountStatus, User, UserRole
from app.schemas.auth import (
    AccountStatusResponse,
    UserInfo,
    UserLoginInput,
    UserLoginOutput,
    UserRegistrationInput,
    UserRegistrationOutput,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=UserRegistrationOutput, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserRegistrationInput, db: DbSession) -> UserRegistrationOutput:
    """
    Register a new user account. The account will be in PENDING status
    and requires admin approval before the user can access the system.
    """
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
def login_user(payload: UserLoginInput, db: DbSession) -> UserLoginOutput:
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
