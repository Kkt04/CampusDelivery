"""FastAPI dependencies: unit of work, current user and permission checks.

Authorization is enforced here on the server for every protected route;
the frontend only hides buttons for convenience.
"""
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
