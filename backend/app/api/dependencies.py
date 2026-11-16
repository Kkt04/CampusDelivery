"""FastAPI dependencies: unit of work, current user and permission checks.

Authorization is enforced here on the server for every protected route;
the frontend only hides buttons for convenience.
"""
# ==============================================================================
# [EVAL-5: PATTERN-DECORATOR] Dependency Decorator Pattern (require(permission))
# WHAT IT IS FOR:
#   Parameterized factory returning a FastAPI dependency function that checks
#   fine-grained permissions before route execution.
# HOW IT IS USED HERE:
#   `require(Permission.PACKAGE_REGISTER)` decorates the intake route. It resolves
#   the current user, tests permission against the domain matrix, and aborts with
#   PermissionDeniedError (HTTP 403) before the controller logic executes.
# ==============================================================================
# [EVAL-1: REQUIREMENTS] Server-Side RBAC Enforcement
# WHAT IT IS FOR:
#   Enforces non-functional security requirement: client-side UI gating is purely
#   cosmetic; the server cryptographically validates JWTs and checks roles on every request.
# ==============================================================================
# [EVAL-7: API-LAYER-SEPARATION] Inversion of Control via Dependency Injection
# WHAT IT IS FOR:
#   FastAPI's Depends(get_uow) injects a scoped UnitOfWork context manager into
#   controllers, ensuring transactional boundaries are cleanly separated from HTTP logic.
# ==============================================================================
from collections.abc import Callable, Iterator

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.container import container
from app.core.config import Settings
from app.core.exceptions import AuthenticationError, PermissionDeniedError, ValidationFailedError
from app.core.security import decode_access_token
from app.domain.permissions import Permission, has_permission
from app.infrastructure.models import User
from app.repositories.unit_of_work import UnitOfWork

_bearer = HTTPBearer(auto_error=False)


def get_uow() -> Iterator[UnitOfWork]:
    with container.uow() as uow:
        yield uow


def get_settings_dep() -> Settings:
    return container.settings


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
                     uow: UnitOfWork = Depends(get_uow)) -> User:
    if credentials is None:
        raise AuthenticationError("Sign in to continue.", code="NOT_AUTHENTICATED")
    user = uow.users.get(decode_access_token(credentials.credentials))
    if user is None or not user.is_active:
        raise AuthenticationError("This account is no longer active.")
    return user


def require(permission: Permission) -> Callable[..., User]:
    def checker(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user.role, permission):
            raise PermissionDeniedError("You do not have permission to do this.")
        return user

    return checker


def idempotency_key(key: str | None = Header(default=None, alias="Idempotency-Key")) -> str | None:
    if key is not None and not (8 <= len(key) <= 80):
        raise ValidationFailedError("Idempotency-Key must be 8-80 characters.")
    return key
