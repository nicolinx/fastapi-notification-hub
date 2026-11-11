import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotificationNotFoundError, UserNotFoundError
from src.models.notification import Notification
from src.models.user import User
from src.schemas.notification import NotificationCreate
from src.workers.celery_app import DISPATCH_TASK_NAME, celery_app


async def create_notification(
    db: AsyncSession, payload: NotificationCreate
) -> Notification:
    user = await db.get(User, payload.user_id)
    if user is None:
        raise UserNotFoundError(f"User {payload.user_id} not found")

    task_id = str(uuid.uuid4())
    notification = Notification(
        user_id=payload.user_id,
        channel=payload.channel,
        title=payload.title,
        body=payload.body,
        task_id=task_id,
    )
    db.add(notification)
    # Commit BEFORE enqueueing, so the worker can always find the row
    await db.commit()

    # send_task is blocking (talks to Redis), so run it off the event loop.
    await asyncio.to_thread(
        celery_app.send_task,
        DISPATCH_TASK_NAME,
        args=[notification.id],
        task_id=task_id,
    )
    return notification


async def get_by_task_id(db: AsyncSession, task_id: str) -> Notification:
    result = await db.execute(
        select(Notification).where(Notification.task_id == task_id)
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        raise NotificationNotFoundError(f"Notification {task_id} not found")
    return notification
