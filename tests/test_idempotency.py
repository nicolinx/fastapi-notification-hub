from unittest.mock import MagicMock

from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from src.models import Notification, User
from src.schemas.notification import NotificationCreate
from src.services.idempotency_service import (
    IdempotencyRecord,
    fingerprint,
    redis_key,
)

SEND_URL = "/api/v1/notifications/send"
KEY = "order-123"
KEY_HEADER = {"X-Idempotency-Key": KEY}


def _payload(user_id: int) -> dict[str, object]:
    return {
        "user_id": user_id,
        "channel": "EMAIL",
        "title": "Halo",
        "body": "Tes pertama",
    }


def _count_notifications(factory: sessionmaker[Session]) -> int:
    with factory() as session:
        return session.scalar(select(func.count()).select_from(Notification)) or 0


async def test_same_key_and_body_replays_the_first_response(
    client: AsyncClient,
    user: User,
    send_task_mock: MagicMock,
    sync_session_factory: sessionmaker[Session],
) -> None:
    first = await client.post(SEND_URL, json=_payload(user.id), headers=KEY_HEADER)
    second = await client.post(SEND_URL, json=_payload(user.id), headers=KEY_HEADER)

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json() == first.json()
    assert "idempotent-replayed" not in first.headers
    assert second.headers["idempotent-replayed"] == "true"
    assert _count_notifications(sync_session_factory) == 1
    send_task_mock.assert_called_once()


async def test_same_key_with_different_body_returns_422(
    client: AsyncClient,
    user: User,
    send_task_mock: MagicMock,
    sync_session_factory: sessionmaker[Session],
) -> None:
    await client.post(SEND_URL, json=_payload(user.id), headers=KEY_HEADER)
    changed = {**_payload(user.id), "title": "Judul lain"}

    response = await client.post(SEND_URL, json=changed, headers=KEY_HEADER)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "idempotency_key_reused"
    assert _count_notifications(sync_session_factory) == 1
    send_task_mock.assert_called_once()


async def test_same_key_while_first_request_is_running_returns_409(
    client: AsyncClient,
    user: User,
    redis_client: Redis,
    send_task_mock: MagicMock,
) -> None:
    payload = _payload(user.id)
    running = IdempotencyRecord(
        state="processing",
        fingerprint=fingerprint(NotificationCreate.model_validate(payload)),
    )
    await redis_client.set(redis_key(KEY), running.model_dump_json(), ex=60)

    response = await client.post(SEND_URL, json=payload, headers=KEY_HEADER)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "idempotency_in_progress"
    send_task_mock.assert_not_called()


async def test_failed_request_does_not_keep_the_key(
    client: AsyncClient, redis_client: Redis
) -> None:
    response = await client.post(
        SEND_URL, json=_payload(user_id=999), headers=KEY_HEADER
    )

    assert response.status_code == 404
    assert await redis_client.exists(redis_key(KEY)) == 0
