from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings


async def dispatch_engine_command(command: str, payload: dict[str, Any]) -> None:
    settings = get_settings()
    if not settings.trading_engine_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The trading engine is not configured.",
        )

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{settings.trading_engine_url}/commands/{command}", json=payload)
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The trading engine did not accept the command.",
        ) from error
