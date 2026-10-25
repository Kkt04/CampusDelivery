from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
import pytest

from app.core.config import Settings
from app.core.exceptions import AuthenticationError, RateLimitedError, ValidationFailedError
from app.core.rate_limit import SlidingWindowRateLimiter, resolve_client_ip
from app.core.security import (
    generate_refresh_token,
    generate_reset_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.domain.enums import Role
from app.infrastructure.models import PasswordResetToken, RefreshToken, User
from app.services.users import AuthService, require_password_strength


def test_crypto_tokens_generation_and_hashing():
    raw1, hash1 = generate_reset_token()
    raw2, hash2 = generate_reset_token()
    assert len(raw1) >= 32
    assert raw1 != raw2
    assert hash1 != hash2
    assert hash_token(raw1) == hash1

    ref1, ref_hash1 = generate_refresh_token()
    assert len(ref1) >= 32
    assert hash_token(ref1) == ref_hash1


def test_resolve_client_ip_with_trusted_proxies():
    req = MagicMock()
    req.client.host = "10.0.0.1"
    req.headers = {"X-Forwarded-For": "203.0.113.195, 10.0.0.1"}

    # Untrusted proxy -> takes client.host
    assert resolve_client_ip(req, ["127.0.0.1"]) == "10.0.0.1"

    # Trusted proxy -> extracts client original IP
    assert resolve_client_ip(req, ["10.0.0.1"]) == "203.0.113.195"


def test_password_strength_enforcement():
    require_password_strength("ValidPass123!")
    with pytest.raises(ValidationFailedError):
        require_password_strength("short1!")
    with pytest.raises(ValidationFailedError):
        require_password_strength("onlylettersalltheway")
    with pytest.raises(ValidationFailedError):
        require_password_strength("1234567890")


class InMemoryRepo:
    def __init__(self):
        self.items = {}
        self._id_seq = 1

    def add(self, obj):
        obj.id = self._id_seq
        self._id_seq += 1
        self.items[obj.id] = obj
        return obj


class MockUnitOfWork:
    def __init__(self):
        self.users_map = {}
        self.reset_tokens = {}
        self.refresh_tokens_map = {}
        self.audit_records = []
        self._seq = 1

        class MockUsers:
            def __init__(outer):
                outer.self = outer
            def get_by_login(_, ident):
                clean = ident.strip().lower()
                for u in self.users_map.values():
                    if u.email.lower() == clean or u.institutional_id.lower() == clean:
                        return u
                return None
            def get(_, uid):
                return self.users_map.get(uid)

        class MockResets:
            def invalidate_for_user(_, uid, now):
                count = 0
                for t in self.reset_tokens.values():
                    if t.user_id == uid and t.used_at is None:
                        t.used_at = now
                        count += 1
                return count
            def add(_, token):
                token.id = self._seq
                self._seq += 1
                self.reset_tokens[token.token_hash] = token
                return token
            def get_by_hash(_, thash):
                return self.reset_tokens.get(thash)
            def mark_used(_, tid, now):
                for t in self.reset_tokens.values():
                    if t.id == tid and t.used_at is None:
                        t.used_at = now
                        return True
                return False

        class MockRefresh:
            def add(_, token):
                token.id = self._seq
                self._seq += 1
                self.refresh_tokens_map[token.token_hash] = token
                return token
            def get_by_hash(_, thash):
                return self.refresh_tokens_map.get(thash)
            def revoke(_, tid, now):
                for t in self.refresh_tokens_map.values():
                    if t.id == tid and t.revoked_at is None:
                        t.revoked_at = now
                        return True
                return False
            def revoke_all_for_user(_, uid, now):
                count = 0
                for t in self.refresh_tokens_map.values():
                    if t.user_id == uid and t.revoked_at is None:
                        t.revoked_at = now
                        count += 1
                return count

        class MockAudit:
            def add(_, entry):
                self.audit_records.append(entry)

        self.users = MockUsers()
        self.password_resets = MockResets()
        self.refresh_tokens = MockRefresh()
        self.audit = MockAudit()
        self.idempotency = MagicMock()
        self.packages = MagicMock()
        self.packages.claim_unidentified_for_recipient.return_value = []
        self.session = MagicMock()

    def commit(self):
        pass


def test_auth_service_forgot_password_anti_enumeration():
    uow = MockUnitOfWork()
    user = User(id=1, institutional_id="STU1001", full_name="Alice", email="alice@campus.edu",
                role=Role.LEARNER, password_hash=hash_password("OldPassword123!"), is_active=True)
    uow.users_map[1] = user

    limiter = SlidingWindowRateLimiter(max_failures=5, window_seconds=60)
    settings = Settings(environment="development")
    svc = AuthService(uow, limiter, settings)

    # 1. Existing user -> succeeds and dev_token is available in dev environment
    res1 = svc.request_password_reset("alice@campus.edu", "127.0.0.1")
    assert "instructions have been sent" in res1["message"]
    assert "dev_token" in res1
    token1 = res1["dev_token"]

    # 2. Non-existent user -> identical message (anti-enumeration)
    res2 = svc.request_password_reset("nonexistent@campus.edu", "127.0.0.1")
    assert "instructions have been sent" in res2["message"]
    assert "dev_token" not in res2

    # 3. Use reset token to set new password
    access_tok, exp, raw_refresh, u = svc.reset_password_with_token(token1, "BrandNewPassword2026!")
    assert u.id == user.id
    assert verify_password("BrandNewPassword2026!", user.password_hash)
    assert raw_refresh is not None

    # 4. Token cannot be reused (Single-Use protection)
    with pytest.raises(AuthenticationError) as err:
        svc.reset_password_with_token(token1, "AnotherPassword2026!")
    assert "already used" in err.value.message or "invalid" in err.value.message


def test_auth_service_refresh_token_rotation():
    uow = MockUnitOfWork()
    user = User(id=2, institutional_id="SEC2001", full_name="Guard Bob", email="guard@campus.edu",
                role=Role.SECURITY, password_hash=hash_password("GuardPass123!"), is_active=True)
    uow.users_map[2] = user

    limiter = SlidingWindowRateLimiter(max_failures=5, window_seconds=60)
    settings = Settings(environment="production")
    svc = AuthService(uow, limiter, settings)

    # Login produces access token and refresh token
    acc1, exp1, ref1, u = svc.login("guard@campus.edu", "GuardPass123!", "127.0.0.1")
    assert acc1 and ref1

    # Refresh session produces new rotated tokens
    acc2, exp2, ref2, u2 = svc.refresh_session(ref1)
    assert acc2 and ref2
    assert ref2 != ref1

    # Replay of old ref1 is immediately rejected
    with pytest.raises(AuthenticationError) as err:
        svc.refresh_session(ref1)
    assert "expired" in err.value.message or "Invalid" in err.value.message


def test_auth_service_change_password():
    uow = MockUnitOfWork()
    user = User(id=3, institutional_id="ADM3001", full_name="Admin Charlie", email="admin@campus.edu",
                role=Role.ADMIN, password_hash=hash_password("AdminInitialPass1!"), is_active=True)
    uow.users_map[3] = user

    limiter = SlidingWindowRateLimiter(max_failures=5, window_seconds=60)
    svc = AuthService(uow, limiter)

    # Wrong current password fails
    with pytest.raises(AuthenticationError):
        svc.change_password(user, "WrongPass000!", "NewPass12345!")

    # Correct current password succeeds
    svc.change_password(user, "AdminInitialPass1!", "NewPass12345!")
    assert verify_password("NewPass12345!", user.password_hash)
