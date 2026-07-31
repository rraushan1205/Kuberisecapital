"""
Security headers middleware.

Adds security headers to all HTTP responses to protect against common attacks.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Headers added:
        - X-Content-Type-Options: Prevents MIME-sniffing
        - X-Frame-Options: Prevents clickjacking
        - X-XSS-Protection: Enables browser XSS filter
        - Strict-Transport-Security: Forces HTTPS (production only)
        - Content-Security-Policy: Restricts resource loading
        - Referrer-Policy: Controls referrer information
        - Permissions-Policy: Controls browser features
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        settings = get_settings()

        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Enable XSS filter in older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Force HTTPS in production (HSTS)
        if settings.environment == "production":
            # max-age=31536000 (1 year), includeSubDomains, preload
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # Content Security Policy
        # Restrict to same-origin for most resources
        csp_directives = [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline'",  # Allow inline styles for frontend
            "img-src 'self' data: https:",
            "font-src 'self'",
            "connect-src 'self'",
            "frame-ancestors 'none'",  # Equivalent to X-Frame-Options: DENY
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Control browser features (Permissions Policy)
        permissions_policy = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions_policy)

        return response
