from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.models.notification import NotificationChannel, NotificationStatus


class NotificationCreate(BaseModel):
    """Request body for POST /send."""

    user_id: int = Field(gt=0)
    channel: NotificationChannel
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)


class NotificationResponse(BaseModel):
    """Response for POST /send and GET /{task_id}."""

    # Allow building this from an ORM object, not just a dict.
    model_config = ConfigDict(from_attributes=True)

    task_id: str | None
    status: NotificationStatus
    channel: NotificationChannel
    title: str
    created_at: datetime
    updated_at: datetime
