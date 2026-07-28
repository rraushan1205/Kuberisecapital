"""
OAuth state parameter storage for CSRF protection.

Stores single-use, short-lived state tokens in Redis so that an OAuth callback
can be verified as corresponding to a request this server actually issued,
rather than just checking that the state value has a plausible format.
"""

import redis.asyncio as redis

from app.core.config import get_settings

_STATE_TTL_SECONDS = 600  # 10 minutes — enough time for a user to complete broker login
_KEY_PREFIX = "oauth_state:"

_redis_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis_client


async def store_oauth_state(state: str) -> None:
    """Record that this state value was legitimately issued by this server."""
    client = _get_client()
    await client.set(f"{_KEY_PREFIX}{state}", "1", ex=_STATE_TTL_SECONDS)


async def consume_oauth_state(state: str) -> bool:
    """
    Verify a state value was issued by this server, and invalidate it (single use).

    Returns True if the state was valid and has now been consumed. Returns False
    if it was missing, expired, or already used — all of which indicate the
    callback should be rejected.
    """
    client = _get_client()
    key = f"{_KEY_PREFIX}{state}"
    # GETDEL atomically retrieves and deletes in one operation, preventing a race
    # where the same state could be consumed twice by concurrent requests.
    value = await client.getdel(key)
    return value is not None
