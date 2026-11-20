from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.exceptions import (
    InactiveApiKeyError,
    InvalidApiKeyError,
    MissingApiKeyError,
)
from src.models.api_key import ApiKey
from src.services import api_key_service


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
