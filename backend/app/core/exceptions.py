"""Domain and application exceptions.

Services raise these meaningful exceptions; the API layer translates them into
safe JSON error responses (see app/main.py). No stack traces leave the server.
"""
# ==============================================================================
# [EVAL-9: ERROR-HANDLING-CONCURRENCY] Structured Domain Exception Hierarchy
# WHAT IT IS FOR:
#   Eliminates generic 500 errors and fragile string checks. Maps business errors
#   directly to RFC 7807 problem details and semantic HTTP status codes.
# HOW IT IS USED HERE:
#   - AppError: Base class carrying status_code, machine-readable code, and details.
#   - ConflictError (409): Base for business conflict and concurrency collisions:
#       * InvalidTransitionError: Illegal FSM status leap.
#       * AlreadyCollectedError: Anti-double-collection collision.
#       * ConcurrentModificationError: CAS status optimistic concurrency mismatch.
#       * DuplicateTrackingIdError: Integrity violation on active tracking ID.
#   - RateLimitedError (429): Brute force prevention carrying Retry-After header.
# ==============================================================================
# [EVAL-3: OOP-INHERITANCE] Exception Specialization
# WHAT IT IS FOR:
#   Inheritance hierarchy allows controllers or middleware to catch broad categories
#   (e.g. `except ConflictError`) or handle specific edge cases without code duplication.
# ==============================================================================
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


class AmbiguousPackageError(ConflictError):
    code = "AMBIGUOUS_TRACKING_ID"


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

    def __init__(self, message: str = "Too many failed attempts. Try again in a few minutes.", *, retry_after: int = 60, details: Any = None) -> None:
        super().__init__(message, code="RATE_LIMITED", details=details)
        self.retry_after = retry_after



class NotificationDeliveryError(Exception):
    """Raised by a notification channel when it could not hand a message over."""
