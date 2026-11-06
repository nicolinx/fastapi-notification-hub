from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import get_settings

# One engine for the whole app. It manages a pool of connections and does not
# connect until the first query.
engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)

# A factory that creates sessions. expire_on_commit=False keeps objects usable
# after commit (otherwise reading an attribute would trigger a hidden query, which
# fails in async code).
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency: gives each request its own session, closed afterwards."""
    async with SessionLocal() as session:
        yield session
