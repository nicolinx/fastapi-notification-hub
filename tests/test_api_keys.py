from unittest.mock import MagicMock

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from src.models import ApiKey, User
from src.services.api_key_service import hash_key

SEND_URL = "/api/v1/notifications/send"


def _payload(user_id: int) -> dict[str, object]:
    return {
        "user_id": user_id,
        "channel": "EMAIL",
        "title": "Halo",
        "body": "Tes pertama",
    }


async def test_send_without_api_key_returns_401(
    anon_client: AsyncClient, user: User, send_task_mock: MagicMock
) -> None:
    response = await anon_client.post(SEND_URL, json=_payload(user.id))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "missing_api_key"
    send_task_mock.assert_not_called()


async def test_send_with_unknown_api_key_returns_401(
    anon_client: AsyncClient, user: User, send_task_mock: MagicMock
) -> None:
    response = await anon_client.post(
        SEND_URL, json=_payload(user.id), headers={"X-API-Key": "nh_salah"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_api_key"
    send_task_mock.assert_not_called()


async def test_send_with_inactive_api_key_returns_403(
    anon_client: AsyncClient,
    user: User,
    send_task_mock: MagicMock,
    sync_session_factory: sessionmaker[Session],
) -> None:
    with sync_session_factory() as session:
        session.add(ApiKey(name="off", key_hash=hash_key("nh_mati"), is_active=False))
        session.commit()

    response = await anon_client.post(
        SEND_URL, json=_payload(user.id), headers={"X-API-Key": "nh_mati"}
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "api_key_inactive"
    send_task_mock.assert_not_called()


async def test_get_notification_requires_api_key(anon_client: AsyncClient) -> None:
    response = await anon_client.get("/api/v1/notifications/any-task-id")

    assert response.status_code == 401


async def test_api_key_is_stored_as_a_hash(
    api_key: str, sync_session_factory: sessionmaker[Session]
) -> None:
    with sync_session_factory() as session:
        row = session.scalars(select(ApiKey)).one()

    assert row.key_hash == hash_key(api_key)
    assert row.key_hash != api_key
