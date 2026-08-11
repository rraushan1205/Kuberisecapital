"""
CSRF protection middleware for state-changing operations.

Implements Double Submit Cookie pattern with HMAC validation.
Protects admin endpoints from cross-site request forgery attacks.
"""

import hashlib
import hmac
import secrets
from typing import Optional

from fastapi import HTTPException, Request, Response, status

from app.core.config import get_settings


def generate_csrf_token() -> str:
    """
    Generate a cryptographically secure CSRF token.

    Returns:
        str: 32-byte URL-safe token
    """
    return secrets.token_urlsafe(32)


def create_csrf_cookie(response: Response, token: str) -> None:
    """
    Set CSRF token in HTTP-only cookie.

    Args:
        response: FastAPI response object
        token: CSRF token to set
    """
    settings = get_settings()
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=3600,  # 1 hour
        path="/",
    )


def verify_csrf_token(request: Request) -> bool:
    """
    Verify CSRF token from request header matches cookie.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        request: FastAPI request object

    Returns:
        bool: True if valid, False otherwise
    """
    # Get token from header
    header_token = request.headers.get("X-CSRF-Token")
    if not header_token:
        return False

    # Get token from cookie
    cookie_token = request.cookies.get("csrf_token")
    if not cookie_token:
        return False

    # Constant-time comparison
    return hmac.compare_digest(header_token, cookie_token)


async def csrf_protect_middleware(request: Request, call_next):
    """
    CSRF protection middleware for state-changing requests.

    Validates CSRF tokens on POST/PUT/DELETE/PATCH requests.
    Skips validation for:
        - Safe methods (GET, HEAD, OPTIONS)
        - Authentication endpoints (login/register)
        - API endpoints with Bearer auth

    Args:
        request: Incoming request
        call_next: Next middleware/route handler

    Returns:
        Response from next handler or 403 Forbidden
    """
    # Skip CSRF check for safe methods
    if request.method in ["GET", "HEAD", "OPTIONS"]:
        return await call_next(request)

    # Skip CSRF check for authentication endpoints
    # (they have their own rate limiting and don't use cookies yet)
    skip_paths = [
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
        "/api/v1/auth/verify-email",
        "/api/v1/client/auth/login",
        "/api/v1/admin/auth/login",
        "/api/v1/client/auth/refresh",
        "/api/v1/admin/auth/refresh",
    ]

    if request.url.path in skip_paths:
        return await call_next(request)

    # Skip CSRF check if using Bearer token authentication
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return await call_next(request)

    # Verify CSRF token for state-changing operations
    if not verify_csrf_token(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed. Missing or invalid CSRF token.",
        )

    return await call_next(request)


def require_csrf_token(func):
    """
    Decorator to require CSRF token validation on specific endpoints.

    Use this for critical state-changing operations that need extra protection.

    Example:
        @router.post("/strategies/{id}/start")
        @require_csrf_token
        def start_strategy(...):
            ...
    """
    async def wrapper(*args, **kwargs):
        # Extract request from args
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break

        if request and not verify_csrf_token(request):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF validation failed. Missing or invalid CSRF token.",
            )

        return await func(*args, **kwargs) if callable(func) else func(*args, **kwargs)

    return wrapper
