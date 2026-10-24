"""Use cases: authentication and user administration."""
from functools import lru_cache

from pymongo.errors import DuplicateKeyError as IntegrityError

from app.core.config import Settings
from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError, ValidationFailedError
from app.core.rate_limit import SlidingWindowRateLimiter
from app.core.security import create_access_token, hash_password, verify_password
from app.domain.enums import Role
from app.infrastructure.models import User
from app.repositories.filters import Page
from app.repositories.unit_of_work import UnitOfWork
from app.services.audit import AuditService
from app.services.package_intake import PackageIntakeService



@lru_cache
def _dummy_hash() -> str:
    """Checked when the user does not exist, so response time does not reveal valid IDs."""
    return hash_password("not-a-real-password-0")


class AuthService:
    def __init__(self, uow: UnitOfWork, limiter: SlidingWindowRateLimiter) -> None:
        self._uow = uow
        self._limiter = limiter
        self._audit = AuditService(uow.audit)

    def login(self, identifier: str, password: str, client_ip: str) -> tuple[str, int, User]:
        key = f"{identifier.strip().lower()}|{client_ip}"
        self._limiter.ensure_allowed(key)
        user = self._uow.users.get_by_login(identifier)
        valid = verify_password(password, user.password_hash if user else _dummy_hash())
        if not user or not valid or not user.is_active:
            self._limiter.record_failure(key)
            self._audit.record(user, "auth.login_failed", "user", user.id if user else None,
                               {"identifier": identifier.strip()[:64], "ip": client_ip})
            self._uow.commit()
            raise AuthenticationError("Incorrect ID/email or password, or the account is disabled.")
        self._limiter.reset(key)
        if user.role == Role.LEARNER:
            PackageIntakeService(self._uow).claim_packages_for_learner(user)
        token, expires_in = create_access_token(user.id, user.role.value)
        self._audit.record(user, "auth.login_succeeded", "user", user.id, {"ip": client_ip})
        self._uow.commit()
        return token, expires_in, user

    def signup(self, *, institutional_id: str, full_name: str, email: str, phone: str | None,
               password: str) -> tuple[str, int, User]:
        """Public self-registration. Always creates a LEARNER account and signs in."""
        if self._uow.users.get_by_institutional_id(institutional_id):
            raise ConflictError("An account with this institutional ID already exists.", code="USER_EXISTS")
        require_password_strength(password)
        if self._uow.users.get_by_email(email):
            raise ConflictError("An account with this email already exists.", code="USER_EXISTS")
        try:
            user = self._uow.users.add(User(
                institutional_id=institutional_id.strip().upper(), full_name=full_name.strip(),
                email=email.strip().lower(), phone=phone or None, role=Role.LEARNER,
                password_hash=hash_password(password), is_active=True))
        except IntegrityError:  # concurrent signup with the same ID or email
            raise ConflictError("An account with this institutional ID or email already exists.",
                                code="USER_EXISTS") from None
        self._audit.record(user, "auth.signup", "user", user.id, {"role": Role.LEARNER.value})
        PackageIntakeService(self._uow).claim_packages_for_learner(user)
        self._uow.commit()
        token, expires_in = create_access_token(user.id, user.role.value)
        return token, expires_in, user

    def reset_password(self, identifier: str, new_password: str) -> tuple[str, int, User]:
        user = self._uow.users.get_by_login(identifier)
        if not user or not user.is_active:
            raise NotFoundError("No active account matches this ID or email.")
        require_password_strength(new_password)
        user.password_hash = hash_password(new_password)
        self._uow.session.flush()
        self._audit.record(user, "auth.password_reset", "user", user.id, {"identifier": identifier.strip()})
        if user.role == Role.LEARNER:
            PackageIntakeService(self._uow).claim_packages_for_learner(user)
        self._uow.commit()
        token, expires_in = create_access_token(user.id, user.role.value)
        return token, expires_in, user


class UserService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow
        self._audit = AuditService(uow.audit)

    def create(self, *, actor: User, institutional_id: str, full_name: str, email: str, phone: str | None,
               role: Role, password: str) -> User:
        if self._uow.users.get_by_institutional_id(institutional_id):
            raise ConflictError("A user with this institutional ID already exists.", code="USER_EXISTS")
        require_password_strength(password)
        if self._uow.users.get_by_email(email):
            raise ConflictError("A user with this email already exists.", code="USER_EXISTS")
        user = self._uow.users.add(User(
            institutional_id=institutional_id.strip().upper(), full_name=full_name.strip(),
            email=email.strip().lower(), phone=phone, role=role,
            password_hash=hash_password(password), is_active=True))
        self._audit.record(actor, "user.created", "user", user.id, {"role": role.value})
        self._uow.commit()
        return user

    def update(self, *, actor: User, user_id: int, full_name: str | None = None, phone: str | None = None,
               is_active: bool | None = None, password: str | None = None) -> User:
        user = self._uow.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found")
        if user.id == actor.id and is_active is False:
            raise ValidationFailedError("You cannot deactivate your own account.")
        changed: list[str] = []
        if full_name is not None and full_name.strip() != user.full_name:
            user.full_name = full_name.strip()
            changed.append("full_name")
        if phone is not None and phone != user.phone:
            user.phone = phone or None
            changed.append("phone")
        if is_active is not None and is_active != user.is_active:
            user.is_active = is_active
            changed.append("is_active")
        if password:
            require_password_strength(password)
            user.password_hash = hash_password(password)
            changed.append("password")
        if changed:
            self._audit.record(actor, "user.updated", "user", user.id,
                               {"fields": changed, "is_active": user.is_active})
        self._uow.commit()
        return user

    def search(self, *, q: str | None, role: Role | None, active_only: bool, page: int,
               page_size: int) -> Page[User]:
        return self._uow.users.search(q, role, active_only, page, page_size)


def require_password_strength(password: str) -> None:
    if len(password) < 8 or password.isalpha() or password.isdigit():
        raise ValidationFailedError("Password must be at least 8 characters and mix letters with numbers or symbols.")
