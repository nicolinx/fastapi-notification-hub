"""Import every model here so `Base.metadata` sees all tables (Alembic needs this)."""

from src.models.base import Base
from src.models.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
)
from src.models.user import User

__all__ = [
    "Base",
    "Notification",
    "NotificationChannel",
    "NotificationStatus",
    "User",
]
