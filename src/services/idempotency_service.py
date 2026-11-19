import hashlib
from collections.abc import Awaitable, Callable
from typing import Literal

from pydantic import BaseModel
from redis.asyncio import Redis

from src.core.exceptions import (
    IdempotencyInProgressError,
    IdempotencyKeyReusedError,
)
from src.schemas.notification import NotificationCreate, NotificationResponse

# While a request is running, the key is held only briefly, so a crash cannot
# block the client for long.
PROCESSING_TTL_SECONDS = 60
# After success, the answer is kept for a day, so retries get the same response.
RESULT_TTL_SECONDS = 24 * 60 * 60


class IdempotencyRecord(BaseModel):
    """What we remember in Redis about one idempotency key."""

    state: Literal["processing", "done"]
    fingerprint: str
    response: NotificationResponse | None = None


def redis_key(key: str) -> str:
    return f"idem:{key}"


def fingerprint(payload: NotificationCreate) -> str:
    """A hash of the request body, to detect a reused key with different data."""
    return hashlib.sha256(payload.model_dump_json().encode()).hexdigest()


async def run_once(
    redis: Redis,
    key: str,
    payload: NotificationCreate,
    action: Callable[[], Awaitable[NotificationResponse]],
) -> tuple[NotificationResponse, bool]:
    """Run `action` at most once per key. Returns (response, was_replayed)."""
    name = redis_key(key)
    body_hash = fingerprint(payload)

    claim = IdempotencyRecord(state="processing", fingerprint=body_hash)
    claimed = await redis.set(
        name, claim.model_dump_json(), nx=True, ex=PROCESSING_TTL_SECONDS
    )

    if not claimed:
        raw = await redis.get(name)
        if raw is None:
            # The key expired between our two calls. Rare: ask the client to retry.
            raise IdempotencyInProgressError("Please retry the request")
        existing = IdempotencyRecord.model_validate_json(raw)
        if existing.fingerprint != body_hash:
            raise IdempotencyKeyReusedError(
                "This idempotency key was already used with a different request body"
            )
        if existing.state == "processing" or existing.response is None:
            raise IdempotencyInProgressError(
                "A request with this idempotency key is still being processed"
            )
        return existing.response, True

    try:
        response = await action()
    except Exception:
        # Do not remember failures: let the client try again.
        await redis.delete(name)
        raise

    done = IdempotencyRecord(state="done", fingerprint=body_hash, response=response)
    await redis.set(name, done.model_dump_json(), ex=RESULT_TTL_SECONDS)
    return response, False
