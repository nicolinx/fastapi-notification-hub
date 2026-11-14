import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from sqlalchemy.orm import Session, sessionmaker

from src.models import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    User,
)
from src.workers.tasks import dispatch_notification


@pytest.fixture(autouse=True)
def worker_uses_test_db(
    monkeypatch: pytest.MonkeyPatch,
    sync_session_factory: sessionmaker[Session],
) -> None:
    """Point the task at the test database and skip the mock 1-second delay."""

    @contextmanager
    def test_session() -> Iterator[Session]:
        with sync_session_factory() as session:
            yield session

    monkeypatch.setattr("src.workers.tasks.get_sync_session", test_session)
    monkeypatch.setattr("src.workers.tasks.time.sleep", lambda _seconds: None)


def _create_notification(
    factory: sessionmaker[Session],
    user: User,
    channel: NotificationChannel = NotificationChannel.EMAIL,
    status: NotificationStatus = NotificationStatus.PENDING,
) -> int:
    with factory() as session:
        notification = Notification(
            user_id=user.id,
            channel=channel,
            title="Halo",
            body="Tes",
            task_id=str(uuid.uuid4()),
            status=status,
        )
        session.add(notification)
        session.commit()
        return notification.id


def _status_of(factory: sessionmaker[Session], notification_id: int) -> object:
    with factory() as session:
        row = session.get(Notification, notification_id)
        assert row is not None
        return row.status


def test_dispatch_marks_email_notification_delivered(
    sync_session_factory: sessionmaker[Session], user: User
) -> None:
    notification_id = _create_notification(sync_session_factory, user)

    result = dispatch_notification(notification_id)

    assert result == "delivered"
    assert _status_of(sync_session_factory, notification_id) == (
        NotificationStatus.DELIVERED
    )


def test_dispatch_marks_push_notification_delivered(
    sync_session_factory: sessionmaker[Session], user: User
) -> None:
    notification_id = _create_notification(
        sync_session_factory, user, channel=NotificationChannel.PUSH
    )

    result = dispatch_notification(notification_id)

    assert result == "delivered"
    assert _status_of(sync_session_factory, notification_id) == (
        NotificationStatus.DELIVERED
    )


def test_dispatch_skips_already_delivered_notification(
    sync_session_factory: sessionmaker[Session], user: User
) -> None:
    notification_id = _create_notification(
        sync_session_factory, user, status=NotificationStatus.DELIVERED
    )

    result = dispatch_notification(notification_id)

    assert result == "already_delivered"


def test_dispatch_handles_missing_notification(
    sync_session_factory: sessionmaker[Session],
) -> None:
    result = dispatch_notification(999_999)

    assert result == "not_found"
