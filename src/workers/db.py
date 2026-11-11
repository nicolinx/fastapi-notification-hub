# Sync engine: Celery tasks are plain (blocking) function, not async def.
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import get_settings

engine = create_engine(get_settings().sync_database_url, pool_pre_ping=True)

SyncSessionLocal = sessionmaker(engine, expire_on_commit=False)


@contextmanager
def get_sync_session() -> Iterator[Session]:
    """Give a task its own session, closed when the `with` block ends."""
    with SyncSessionLocal() as session:
        yield session
