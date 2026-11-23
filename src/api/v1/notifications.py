from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import enforce_rate_limit, get_current_api_key
from src.core.database import get_db
from src.core.redis import get_redis
from src.schemas.notification import NotificationCreate, NotificationResponse
from src.services import idempotency_service, notification_service

router = APIRouter(
    prefix="/api/v1/notifications",
    tags=["notifications"],
    dependencies=[Depends(get_current_api_key)],
)

DbSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis)]


@router.post(
    "/send",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=NotificationResponse,
    dependencies=[Depends(enforce_rate_limit)],
)
async def send_notification(
    payload: NotificationCreate,
    db: DbSession,
    redis: RedisClient,
    response: Response,
    x_idempotency_key: Annotated[
        str | None, Header(min_length=1, max_length=255)
    ] = None,
) -> NotificationResponse:
    """Accept a notification, queue it for delivery, and return immediately."""

    async def create() -> NotificationResponse:
        notification = await notification_service.create_notification(db, payload)
        return NotificationResponse.model_validate(notification)

    if x_idempotency_key is None:
        return await create()

    result, replayed = await idempotency_service.run_once(
        redis, x_idempotency_key, payload, create
    )

    if replayed:
        response.headers["Idempotent-Replayed"] = "true"
    return result


@router.get("/{task_id}", response_model=NotificationResponse)
async def get_notification(task_id: str, db: DbSession) -> NotificationResponse:
    """Check the delivery status of notification"""
    notification = await notification_service.get_by_task_id(db, task_id)
    return NotificationResponse.model_validate(notification)
