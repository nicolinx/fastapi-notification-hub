from collections.abc import AsyncIterator, Iterator
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from src.core.config import get_settings
from src.core.database import get_db
from src.main import app
from src.models import Base, User
from src.workers.celery_app import celery_app

# Tests always run against this database, never the dev one.
TEST_DB_NAME = "notification_hub_test"


@pytest.fixture(scope="session")
def sync_engine() -> Iterator[Engine]:
    """Create the test database and tables once per test run."""
    base_url = make_url(get_settings().sync_database_url)
    test_url = base_url.set(database=TEST_DB_NAME)

    # CREATE DATABASE cannot run inside a transaction, hence AUTOCOMMIT.
    admin_engine = create_engine(base_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": TEST_DB_NAME},
        ).scalar()
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin_engine.dispose()

    engine = create_engine(test_url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def clean_db(sync_engine: Engine) -> Iterator[None]:
    """Empty every table after each test, so tests do not affect each other."""
    yield
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    with sync_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def sync_session_factory(sync_engine: Engine, clean_db: None) -> sessionmaker[Session]:
    return sessionmaker(sync_engine, expire_on_commit=False)


@pytest.fixture
def user(sync_session_factory: sessionmaker[Session]) -> User:
    """A user row, because notifications have a foreign key to users."""
    with sync_session_factory() as session:
        new_user = User(email="test@example.com", name="Test User")
        session.add(new_user)
        session.commit()
        return new_user


@pytest.fixture
def send_task_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replace celery_app.send_task so no test ever talks to Redis."""
    mock = MagicMock()
    monkeypatch.setattr(celery_app, "send_task", mock)
    return mock


@pytest.fixture
async def client(
    sync_engine: Engine, clean_db: None, send_task_mock: MagicMock
) -> AsyncIterator[AsyncClient]:
    """An HTTP client wired to the app and the test database."""
    async_url = make_url(get_settings().database_url).set(database=TEST_DB_NAME)
    engine = create_async_engine(async_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    await engine.dispose()
