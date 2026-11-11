from celery import Celery

from src.core.config import get_settings

# The API and the worker only agree on this name; the API never import task code
DISPATCH_TASK_NAME = "notifications.dispatch"

_settings = get_settings()

celery_app = Celery(
    "notification_hub",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
    include=["src.workers.tasks"],
)
