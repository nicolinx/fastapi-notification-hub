import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for expected, client-facing errors.

    Subclass it for specific cases, e.g. `NotificationNotFoundError`.
    """

    status_code: int = 400
    code: str = "app_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class UserNotFoundError(NotFoundError):
    code = "user_not_found"


class NotificationNotFoundError(NotFoundError):
    code = "notification_not_found"


class IdempotencyKeyReusedError(AppError):
    status_code = 422
    code = "idempotency_key_reused"


class IdempotencyInProgressError(AppError):
    status_code = 409
    code = "idempotency_in_progress"


def _error_body(code: str, message: str) -> dict[str, dict[str, str]]:
    return {"error": {"code": code, "message": message}}


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.code, exc.message),
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Log the real error for us, but never leak internals to the client.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=_error_body("internal_error", "Internal server error"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_error_handler)
