from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import health
from src.api.v1 import notifications
from src.core.config import get_settings
from src.core.exceptions import register_exception_handlers


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(notifications.router)

    return app


app = create_app()
