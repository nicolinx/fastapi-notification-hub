from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.notification import NotificationCreate, NotificationResponse
from src.services import notification_service

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/send",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=NotificationResponse,
)
async def send_notification(
    payload: NotificationCreate, db: DbSession
) -> NotificationResponse:
    """Accept a notification, queue it for delivery, and return immediately."""
    notification = await notification_service.create_notification(db, payload)
    return NotificationResponse.model_validate(notification)


@router.get("/{task_id}", response_model=NotificationResponse)
async def get_notification(task_id: str, db: DbSession) -> NotificationResponse:
    """Check the delivery status of notification"""
    notification = await notification_service.get_by_task_id(db, task_id)
    return NotificationResponse.model_validate(notification)
