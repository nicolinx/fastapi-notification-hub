from redis.asyncio import Redis

from src.core.config import get_settings

# One client for the whole app. It keeps a pool of connections and does not connect
# until the first command. decode_responses=True returns str, not bytes.
redis_client = Redis.from_url(get_settings().redis_url, decode_response=True)


async def get_redis() -> Redis:
    """FastAPI dependency: the shared Redis Client."""
    return redis_client
