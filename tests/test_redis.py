from redis.asyncio import Redis


async def test_redis_fixture_roundtrip(redis_client: Redis) -> None:
    await redis_client.set("idem:smoke", "1", ex=60)

    assert await redis_client.get("idem:smoke") == "1"


async def test_redis_fixture_starts_empty(redis_client: Redis) -> None:
    assert await redis_client.dbsize() == 0
