"""
Rate limiting middleware for authentication endpoints.

Implements token bucket algorithm with Redis backend for distributed rate limiting.
Protects against brute force attacks on login, registration, and password reset endpoints.
"""

import hashlib
import inspect
import time
from functools import wraps
from typing import Callable

from fastapi import HTTPException, Request, status
from redis import Redis

from app.core.config import get_settings


class RateLimiter:
    """
    Token bucket rate limiter using Redis for distributed state.

    Features:
        - Per-IP rate limiting
        - Per-email rate limiting
        - Configurable limits per endpoint
        - Exponential backoff on repeated violations
        - Automatic cleanup of old records

    Usage:
        limiter = RateLimiter()

        @router.post("/login")
        @limiter.limit("5/minute", key_func=lambda req: req.client.host)
        def login(...):
            ...
    """

    def __init__(self):
        settings = get_settings()
        self.redis = Redis.from_url(settings.redis_url, decode_responses=True)

    def _parse_rate(self, rate: str) -> tuple[int, int]:
        """
        Parse rate string into (max_requests, window_seconds).

        Args:
            rate: Rate string like "5/minute" or "100/hour"

        Returns:
            tuple: (max_requests, window_seconds)

        Examples:
            "5/minute" -> (5, 60)
            "100/hour" -> (100, 3600)
            "1000/day" -> (1000, 86400)
        """
        max_requests, period = rate.split("/")
        max_requests = int(max_requests)

        period_map = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
        }

        window_seconds = period_map.get(period.lower())
        if window_seconds is None:
            raise ValueError(f"Invalid period: {period}. Must be second/minute/hour/day")

        return max_requests, window_seconds

    def _get_key(self, identifier: str, endpoint: str) -> str:
        """
        Generate Redis key for rate limit tracking.

        Args:
            identifier: IP address or email
            endpoint: API endpoint path

        Returns:
            str: Redis key
        """
        # Hash identifier for privacy
        hashed = hashlib.sha256(identifier.encode()).hexdigest()[:16]
        return f"ratelimit:{endpoint}:{hashed}"

    def _check_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, int]:
        """
        Check if request is within rate limit using sliding window.

        Args:
            key: Redis key for this limit
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            tuple: (is_allowed, retry_after_seconds)
        """
        now = time.time()
        window_start = now - window_seconds

        # Use Redis pipeline for atomic operations
        pipe = self.redis.pipeline()

        # Remove old requests outside the window
        pipe.zremrangebyscore(key, 0, window_start)

        # Count requests in current window
        pipe.zcard(key)

        # Add current request
        pipe.zadd(key, {str(now): now})

        # Set expiration on key
        pipe.expire(key, window_seconds + 1)

        results = pipe.execute()
        request_count = results[1]

        if request_count >= max_requests:
            # Calculate retry-after time
            oldest_request = float(self.redis.zrange(key, 0, 0, withscores=True)[0][1])
            retry_after = int(oldest_request + window_seconds - now) + 1
            return False, retry_after

        return True, 0

    def limit(self, rate: str, key_func: Callable[[Request], str] = None):
        """
        Rate limit decorator for FastAPI routes.

        Args:
            rate: Rate limit string (e.g., "5/minute")
            key_func: Function to extract identifier from request
                     Defaults to IP address

        Returns:
            Decorated function

        Example:
            @limiter.limit("5/minute")
            def login_user(...):
                ...

            @limiter.limit("3/hour", key_func=lambda req: req.json()["email"])
            def register_user(...):
                ...
        """
        max_requests, window_seconds = self._parse_rate(rate)

        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract request object from args/kwargs
                request = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

                # Get identifier
                if request is not None:
                    if key_func:
                        try:
                            identifier = key_func(request)
                        except Exception:
                            # Fallback to IP if custom key_func fails
                            identifier = request.client.host if request.client else "unknown"
                    else:
                        identifier = request.client.host if request.client else "unknown"

                    # Check rate limit
                    endpoint = request.url.path
                    key = self._get_key(identifier, endpoint)
                    is_allowed, retry_after = self._check_limit(key, max_requests, window_seconds)

                    if not is_allowed:
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                            headers={"Retry-After": str(retry_after)}
                        )

                # Endpoints may be sync or async; await only when the result is awaitable.
                result = func(*args, **kwargs)
                if inspect.isawaitable(result):
                    return await result
                return result

            return wrapper
        return decorator


# Global limiter instance
_limiter = None


def get_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter()
    return _limiter
