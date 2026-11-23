import math
import uuid
from dataclasses import dataclass

from redis.asyncio import Redis

SLIDING_WINDOW_SCRIPT = """
local t = redis.call('TIME')
local now = t[1] * 1000 + math.floor(t[2] / 1000)
local window = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])

-- 1. drop entries older than the window
redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, now - window)
-- 2. count what is left
local count = redis.call('ZCARD', KEYS[1])

-- 3. over the limit: reject, and tell the caller how long to wait
if count >= limit then
  local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
  return {0, count, tonumber(oldest[2]) + window - now}
end

-- 4. under the limit: record this request
redis.call('ZADD', KEYS[1], now, ARGV[3])
redis.call('PEXPIRE', KEYS[1], window)
return {1, count + 1, 0}
"""


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


def rate_limit_key(api_key_id: int) -> str:
    return f"rl:{api_key_id}"


async def check_rate_limit(
    redis: Redis, api_key_id: int, limit: int, windows_seconds: int
) -> RateLimitResult:
    """Count one request for this key. Says whether it is within the limit."""
    allowed, count, retry_after_ms = await redis.eval(
        SLIDING_WINDOW_SCRIPT,
        1,
        rate_limit_key(api_key_id),
        windows_seconds * 1000,
        limit,
        uuid.uuid4().hex,
    )

    retry_after = max(1, math.ceil(retry_after_ms / 1000)) if not allowed else 0
    return RateLimitResult(
        allowed=bool(allowed),
        limit=limit,
        remaining=max(limit - count, 0),
        retry_after_seconds=retry_after,
    )
