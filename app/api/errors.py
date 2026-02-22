"""Centralized API exception definitions and handlers."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base domain/application error."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundError(AppError):
    """Raised when required resource does not exist."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=404)


class ValidationError(AppError):
    """Raised when domain-level validation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=422)


class ConflictError(AppError):
    """Raised when operation conflicts with current state."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=409)


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    """Render typed application exceptions as JSON responses."""

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Catch-all exception handler for non-domain errors."""

    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


def register_exception_handlers(app: FastAPI) -> None:
    """Attach API exception handlers once during startup."""

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
