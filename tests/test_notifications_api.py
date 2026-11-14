from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from src.models import Notification, NotificationStatus, User
from src.workers.celery_app import DISPATCH_TASK_NAME

SEND_URL = "/api/v1/notifications/send"


def _payload(user_id: int) -> dict[str, object]:
    return {
        "user_id": user_id,
        "channel": "EMAIL",
        "title": "Halo",
        "body": "Tes pertama",
    }


async def test_send_returns_202_and_enqueues_job(
    client: AsyncClient,
    user: User,
    send_task_mock: MagicMock,
    sync_session_factory: sessionmaker[Session],
) -> None:
    response = await client.post(SEND_URL, json=_payload(user.id))

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["channel"] == "EMAIL"
    assert body["task_id"]

    # The row exists in the database as PENDING...
    with sync_session_factory() as session:
        row = session.scalars(select(Notification)).one()
    assert row.status == NotificationStatus.PENDING
    assert row.task_id == body["task_id"]

    # ...and exactly one job was handed to Celery, carrying the row id.
    send_task_mock.assert_called_once_with(
        DISPATCH_TASK_NAME, args=[row.id], task_id=row.task_id
    )


@pytest.mark.parametrize(
    "override",
    [
        {"channel": "SMS"},
        {"title": ""},
        {"body": ""},
        {"user_id": 0},
    ],
)
async def test_send_rejects_invalid_payload(
    client: AsyncClient,
    user: User,
    send_task_mock: MagicMock,
    override: dict[str, object],
) -> None:
    payload = {**_payload(user.id), **override}

    response = await client.post(SEND_URL, json=payload)

    assert response.status_code == 422
    send_task_mock.assert_not_called()


async def test_send_rejects_missing_field(
    client: AsyncClient, user: User, send_task_mock: MagicMock
) -> None:
    payload = _payload(user.id)
    del payload["title"]

    response = await client.post(SEND_URL, json=payload)

    assert response.status_code == 422
    send_task_mock.assert_not_called()


async def test_send_unknown_user_returns_404(
    client: AsyncClient, send_task_mock: MagicMock
) -> None:
    response = await client.post(SEND_URL, json=_payload(user_id=999))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "user_not_found"
    send_task_mock.assert_not_called()


async def test_get_notification_returns_status(client: AsyncClient, user: User) -> None:
    created = await client.post(SEND_URL, json=_payload(user.id))
    task_id = created.json()["task_id"]

    response = await client.get(f"/api/v1/notifications/{task_id}")

    assert response.status_code == 200
    assert response.json()["task_id"] == task_id
    assert response.json()["status"] == "PENDING"


async def test_get_unknown_task_id_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/notifications/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "notification_not_found"
