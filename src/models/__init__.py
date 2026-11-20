"""Import every model here so `Base.metadata` sees all tables (Alembic needs this)."""

from src.models.api_key import ApiKey
from src.models.base import Base
from src.models.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
)
from src.models.user import User

__all__ = [
    "ApiKey",
    "Base",
    "Notification",
    "NotificationChannel",
    "NotificationStatus",
    "User",
]
