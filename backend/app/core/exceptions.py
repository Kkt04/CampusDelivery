"""Domain and application exceptions.

Services raise these meaningful exceptions; the API layer translates them into
safe JSON error responses (see app/main.py). No stack traces leave the server.
"""
from typing import Any


class AppError(Exception):
    status_code: int = 400
    code: str = "BAD_REQUEST"

    def __init__(self, message: str, *, code: str | None = None, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.details = details


class AuthenticationError(AppError):
    status_code = 401
    code = "AUTHENTICATION_FAILED"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "PERMISSION_DENIED"


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class ValidationFailedError(AppError):
    status_code = 422
    code = "VALIDATION_FAILED"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class InvalidTransitionError(ConflictError):
    code = "INVALID_STATUS_TRANSITION"


class DuplicateTrackingIdError(ConflictError):
    code = "DUPLICATE_TRACKING_ID"


class StorageFullError(ConflictError):
    code = "STORAGE_FULL"


class StorageUnavailableError(ConflictError):
    code = "STORAGE_UNAVAILABLE"


class AlreadyCollectedError(ConflictError):
    code = "ALREADY_COLLECTED"


class ConcurrentModificationError(ConflictError):
    code = "CONCURRENT_MODIFICATION"


class IdempotencyKeyReuseError(ConflictError):
    code = "IDEMPOTENCY_KEY_REUSED"


class PickupCodeError(AppError):
    """Invalid, expired, used, locked or mismatched pickup code."""

    status_code = 400
    code = "PICKUP_CODE_INVALID"


class RateLimitedError(AppError):
    status_code = 429
    code = "RATE_LIMITED"


class NotificationDeliveryError(Exception):
    """Raised by a notification channel when it could not hand a message over."""
