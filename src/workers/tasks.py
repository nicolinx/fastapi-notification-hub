import logging
import time

from src.models.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
)
from src.workers.celery_app import DISPATCH_TASK_NAME, celery_app
from src.workers.db import get_sync_session

logger = logging.getLogger(__name__)


def _send_email(notification: Notification) -> None:
    """Mock SMTP delivery. Phase 1 does not talk to a real mail server."""
    logger.info("[mock SMTP] to user %s: %s", notification.user_id, notification.title)
    time.sleep(1)


def _send_push(notification: Notification) -> None:
    """Mock FCM delivery. Phase 1 does not talk to Firebase."""
    logger.info("[mock FCM] to user %s: %s", notification.user_id, notification.title)
    time.sleep(1)


@celery_app.task(name=DISPATCH_TASK_NAME)  # type: ignore[untyped-decorator]
def dispatch_notification(notification_id: int) -> str:
    with get_sync_session() as session:
        notification = session.get(Notification, notification_id)
        if notification is None:
            logger.warning("Notification %s not found, skipping", notification_id)
            return "not_found"

        if notification.status == NotificationStatus.DELIVERED:
            logger.info("Notification %s already delivered, skipping", notification_id)
            return "already_delivered"

        if notification.channel == NotificationChannel.EMAIL:
            _send_email(notification)
        else:
            _send_push(notification)

        notification.status = NotificationStatus.DELIVERED
        session.commit()

    return "delivered"
