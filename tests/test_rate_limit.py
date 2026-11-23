import asyncio
from unittest.mock import MagicMock

from httpx import AsyncClient
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import get_settings
from src.main import app
from src.models import ApiKey, User
from src.services.api_key_service import generate_key, hash_key

SEND_URL = "/api/v1/notifications/send"


def _payload(user_id: int) -> dict[str, object]:
    return {
        "user_id": user_id,
        "channel": "EMAIL",
        "title": "Halo",
        "body": "Tes pertama",
    }


def _set_limit(requests: int, window_seconds: int) -> None:
    """Use a small limit in this test. The `client` fixture clears overrides after."""
    settings = get_settings().model_copy(
        update={
            "rate_limit_requests": requests,
            "rate_limit_window_seconds": window_seconds,
        }
    )
    app.dependency_overrides[get_settings] = lambda: settings


async def test_request_over_the_limit_returns_429(
    client: AsyncClient, user: User, send_task_mock: MagicMock
) -> None:
    _set_limit(3, 60)

    for _ in range(3):
        ok = await client.post(SEND_URL, json=_payload(user.id))
        assert ok.status_code == 202

    blocked = await client.post(SEND_URL, json=_payload(user.id))

    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limit_exceeded"
    # httpx stores header names in lowercase.
    assert int(blocked.headers["retry-after"]) >= 1
    assert blocked.headers["x-ratelimit-remaining"] == "0"
    # A rejected request must not enqueue a job.
    assert send_task_mock.call_count == 3


async def test_successful_response_has_rate_limit_headers(
    client: AsyncClient, user: User
) -> None:
    _set_limit(3, 60)

    response = await client.post(SEND_URL, json=_payload(user.id))

    assert response.status_code == 202
    assert response.headers["x-ratelimit-limit"] == "3"
    assert response.headers["x-ratelimit-remaining"] == "2"


async def test_requests_are_allowed_again_after_the_window(
    client: AsyncClient, user: User
) -> None:
    _set_limit(1, 1)

    assert (await client.post(SEND_URL, json=_payload(user.id))).status_code == 202
    assert (await client.post(SEND_URL, json=_payload(user.id))).status_code == 429

    # The window is 1 second. Wait slightly longer so the first entry expires.
    await asyncio.sleep(1.1)

    assert (await client.post(SEND_URL, json=_payload(user.id))).status_code == 202


async def test_each_api_key_has_its_own_counter(
    client: AsyncClient,
    user: User,
    sync_session_factory: sessionmaker[Session],
) -> None:
    _set_limit(1, 60)
    other_key = generate_key()
    with sync_session_factory() as session:
        session.add(ApiKey(name="other", key_hash=hash_key(other_key)))
        session.commit()

    # Key A (the `client` fixture's key) uses up its quota.
    assert (await client.post(SEND_URL, json=_payload(user.id))).status_code == 202
    assert (await client.post(SEND_URL, json=_payload(user.id))).status_code == 429

    # Key B overrides the default header for this request. Its quota is untouched.
    other = await client.post(
        SEND_URL, json=_payload(user.id), headers={"X-API-Key": other_key}
    )
    assert other.status_code == 202


async def test_only_send_is_rate_limited(client: AsyncClient, user: User) -> None:
    _set_limit(1, 60)
    await client.post(SEND_URL, json=_payload(user.id))
    assert (await client.post(SEND_URL, json=_payload(user.id))).status_code == 429

    # GET is not limited: 404 (unknown id), not 429.
    response = await client.get("/api/v1/notifications/any-task-id")

    assert response.status_code == 404
