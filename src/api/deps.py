from typing import Annotated

from fastapi import Depends, Header, Response
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.core.database import get_db
from src.core.exceptions import (
    InactiveApiKeyError,
    InvalidApiKeyError,
    MissingApiKeyError,
    RateLimitExceededError,
)
from src.core.redis import get_redis
from src.models.api_key import ApiKey
from src.services import api_key_service, rate_limit_service


async def get_current_api_key(
    db: Annotated[AsyncSession, Depends(get_db)],
    x_api_key: Annotated[str | None, Header()] = None,
) -> ApiKey:
    """FastAPI dependency: the API key of the caller, or a 401/403 error."""
    if x_api_key is None:
        raise MissingApiKeyError("Missing X-API-Key header")

    api_key = await api_key_service.find_by_raw_key(db, x_api_key)
    if api_key is None:
        raise InvalidApiKeyError("Invalid API key")
    if not api_key.is_active:
        raise InactiveApiKeyError("This API key is inactive")

    return api_key


async def enforce_rate_limit(
    api_key: Annotated[ApiKey, Depends(get_current_api_key)],
    redis: Annotated[Redis, Depends(get_redis)],
    settings: Annotated[Settings, Depends(get_settings)],
    response: Response,
) -> None:
    """FastAPI dependency: count this request, or raise 429 when over the limit."""
    result = await rate_limit_service.check_rate_limit(
        redis,
        api_key.id,
        settings.rate_limit_requests,
        settings.rate_limit_window_seconds,
    )

    headers = {
        "X-RateLimit-Limit": str(result.limit),
        "X-RateLimit-Remaining": str(result.remaining),
    }

    if not result.allowed:
        headers["Retry-After"] = str(result.retry_after_seconds)
        raise RateLimitExceededError("Too many requests. Try again later.", headers)

    response.headers.update(headers)
