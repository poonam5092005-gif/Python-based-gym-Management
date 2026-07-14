"""Custom exception hierarchy used across services and translated to HTTP
responses by the FastAPI exception handlers in `app.py`.
"""

from __future__ import annotations


class GymSystemError(Exception):
    """Base class for all domain-level errors."""

    status_code: int = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(GymSystemError):
    status_code = 404


class ConflictError(GymSystemError):
    status_code = 409


class ValidationError(GymSystemError):
    status_code = 422


class AuthError(GymSystemError):
    status_code = 401


class ForbiddenError(GymSystemError):
    status_code = 403
