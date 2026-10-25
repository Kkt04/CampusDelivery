from datetime import datetime, timedelta
from functools import lru_cache
import logging
from typing import Any

from pymongo.errors import DuplicateKeyError as IntegrityError

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError, ValidationFailedError
from app.core.rate_limit import SlidingWindowRateLimiter
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    generate_reset_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.core.time import utcnow
from app.domain.enums import Role
from app.infrastructure.models import PasswordResetToken, RefreshToken, User
from app.repositories.filters import Page
from app.repositories.unit_of_work import UnitOfWork
from app.services.audit import AuditService
from app.services.package_intake import PackageIntakeService

logger = logging.getLogger("campus.auth")


@lru_cache
def _dummy_hash() -> str:
    """Checked when the user does not exist, so response time does not reveal valid IDs."""
    return hash_password("not-a-real-password-0")


class AuthService:
    def __init__(self, uow: UnitOfWork, limiter: SlidingWindowRateLimiter, settings: Settings | None = None) -> None:
        self._uow = uow
        self._limiter = limiter
        self._settings = settings or get_settings()
        self._audit = AuditService(uow.audit)

    def login(self, identifier: str, password: str, client_ip: str) -> tuple[str, int, str, User]:
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
        access_token, expires_in = create_access_token(user.id, user.role.value)
        raw_refresh, token_hash = generate_refresh_token()
        now = utcnow()
        refresh_expires = now + timedelta(days=self._settings.refresh_token_expire_days)
        self._uow.refresh_tokens.add(RefreshToken(
            user_id=user.id, token_hash=token_hash, expires_at=refresh_expires, created_at=now
        ))
        self._audit.record(user, "auth.login_succeeded", "user", user.id, {"ip": client_ip})
        self._uow.commit()
        return access_token, expires_in, raw_refresh, user

    def signup(self, *, institutional_id: str, full_name: str, email: str, phone: str | None,
               password: str) -> tuple[str, int, str, User]:
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
        access_token, expires_in = create_access_token(user.id, user.role.value)
        raw_refresh, token_hash = generate_refresh_token()
        now = utcnow()
        refresh_expires = now + timedelta(days=self._settings.refresh_token_expire_days)
        self._uow.refresh_tokens.add(RefreshToken(
            user_id=user.id, token_hash=token_hash, expires_at=refresh_expires, created_at=now
        ))
        self._uow.commit()
        return access_token, expires_in, raw_refresh, user

    def refresh_session(self, raw_refresh_token: str) -> tuple[str, int, str, User]:
        token_hash = hash_token(raw_refresh_token)
        record = self._uow.refresh_tokens.get_by_hash(token_hash)
        now = utcnow()
        if not record or record.revoked_at is not None or record.expires_at < now:
            raise AuthenticationError("Invalid or expired session refresh token. Please sign in again.")

        # Rotate refresh token
        self._uow.refresh_tokens.revoke(record.id, now)
        user = self._uow.users.get(record.user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User account not found or deactivated.")

        access_token, expires_in = create_access_token(user.id, user.role.value)
        new_raw_refresh, new_token_hash = generate_refresh_token()
        new_expires = now + timedelta(days=self._settings.refresh_token_expire_days)
        self._uow.refresh_tokens.add(RefreshToken(
            user_id=user.id, token_hash=new_token_hash, expires_at=new_expires, created_at=now
        ))
        self._audit.record(user, "auth.token_refreshed", "user", user.id)
        self._uow.commit()
        return access_token, expires_in, new_raw_refresh, user

    def request_password_reset(self, identifier: str, client_ip: str) -> dict[str, Any]:
        """Initiates cryptographic single-use 15-min password reset with anti-enumeration."""
        key = f"reset:{identifier.strip().lower()}|{client_ip}"
        self._limiter.ensure_allowed(key)
        now = utcnow()
        user = self._uow.users.get_by_login(identifier)
        reset_token_plain = None
        if user and user.is_active:
            self._uow.password_resets.invalidate_for_user(user.id, now)
            reset_token_plain, token_hash = generate_reset_token()
            expires_at = now + timedelta(minutes=self._settings.password_reset_token_expire_minutes)
            self._uow.password_resets.add(PasswordResetToken(
                user_id=user.id, token_hash=token_hash, expires_at=expires_at, created_at=now
            ))
            self._audit.record(
                user, "auth.password_reset_requested", "user", user.id,
                {"ip": client_ip, "expires_at": expires_at.isoformat()}
            )
            logger.info("Password reset token issued for user %s (%s): %s", user.id, user.email, reset_token_plain)
        else:
            verify_password("dummy", _dummy_hash())

        self._uow.commit()
        result: dict[str, Any] = {
            "message": "If an active account exists for that ID or email, instructions have been sent."
        }
        if self._settings.environment != "production" and reset_token_plain:
            result["dev_token"] = reset_token_plain
        return result

    def reset_password_with_token(self, token: str, new_password: str) -> tuple[str, int, str, User]:
        require_password_strength(new_password)
        now = utcnow()
        token_hash = hash_token(token)
        record = self._uow.password_resets.get_by_hash(token_hash)
        if not record or record.used_at is not None or record.expires_at < now:
            raise AuthenticationError("The password reset token is invalid, expired, or already used.")

        user = self._uow.users.get(record.user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User account not found or deactivated.")

        if not self._uow.password_resets.mark_used(record.id, now):
            raise AuthenticationError("The password reset token has already been used.")

        user.password_hash = hash_password(new_password)
        self._uow.session.flush()

        self._uow.refresh_tokens.revoke_all_for_user(user.id, now)
        self._audit.record(user, "auth.password_reset_completed", "user", user.id)
        if user.role == Role.LEARNER:
            PackageIntakeService(self._uow).claim_packages_for_learner(user)

        access_token, expires_in = create_access_token(user.id, user.role.value)
        raw_refresh, new_token_hash = generate_refresh_token()
        refresh_expires = now + timedelta(days=self._settings.refresh_token_expire_days)
        self._uow.refresh_tokens.add(RefreshToken(
            user_id=user.id, token_hash=new_token_hash, expires_at=refresh_expires, created_at=now
        ))
        self._uow.commit()
        return access_token, expires_in, raw_refresh, user

    def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect.")
        require_password_strength(new_password)
        now = utcnow()
        user.password_hash = hash_password(new_password)
        self._uow.session.flush()
        self._uow.refresh_tokens.revoke_all_for_user(user.id, now)
        self._audit.record(user, "auth.password_changed", "user", user.id)
        self._uow.commit()


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
