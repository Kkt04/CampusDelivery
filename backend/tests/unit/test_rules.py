from datetime import datetime, timedelta, timezone

import pytest

from app.core.exceptions import PickupCodeError
from app.core.rate_limit import SlidingWindowRateLimiter
from app.core.exceptions import RateLimitedError
from app.core.security import generate_pickup_code, hash_pickup_code, pickup_code_matches
from app.domain.enums import PackageStatus as S, Role
from app.domain.events import EventBus, PackageStatusChanged
from app.domain.overdue import is_overdue
from app.domain.permissions import Permission, can_view_package, has_permission
from app.domain.pickup_rules import TokenState, ensure_token_usable
from app.services.package_intake import normalise_tracking_id

NOW = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)


def token(**kw):
    base = dict(learner_id=7, expires_at=NOW + timedelta(minutes=10), used_at=None, revoked_at=None,
                failed_attempts=0)
    base.update(kw)
    return TokenState(**base)


# ---- pickup tokens ---------------------------------------------------------
def test_valid_token_passes():
    ensure_token_usable(token(), now=NOW, max_attempts=5, expected_learner_id=7)


@pytest.mark.parametrize("state,code", [
    (None, "PICKUP_CODE_NOT_ISSUED"),
    (token(used_at=NOW), "PICKUP_CODE_USED"),
    (token(revoked_at=NOW), "PICKUP_CODE_REVOKED"),
    (token(failed_attempts=5), "PICKUP_CODE_LOCKED"),
    (token(expires_at=NOW), "PICKUP_CODE_EXPIRED"),
    (token(learner_id=8), "PICKUP_WRONG_RECIPIENT"),
])
def test_unusable_tokens_are_rejected_with_specific_codes(state, code):
    with pytest.raises(PickupCodeError) as err:
        ensure_token_usable(state, now=NOW, max_attempts=5, expected_learner_id=7)
    assert err.value.code == code


def test_pickup_code_is_six_digits_and_only_hash_matches():
    code = generate_pickup_code()
    assert len(code) == 6 and code.isdigit()
    digest = hash_pickup_code(code, "salt")
    assert digest != code
    assert pickup_code_matches(code, "salt", digest)
    assert not pickup_code_matches(code, "other-salt", digest)


# ---- permissions -----------------------------------------------------------
def test_learner_can_only_view_own_packages():
    assert can_view_package(Role.LEARNER, viewer_id=1, recipient_id=1)
    assert not can_view_package(Role.LEARNER, viewer_id=1, recipient_id=2)
    assert not can_view_package(Role.LEARNER, viewer_id=1, recipient_id=None)
    assert can_view_package(Role.SECURITY, viewer_id=1, recipient_id=2)


def test_role_permission_boundaries():
    assert not has_permission(Role.SECURITY, Permission.USER_MANAGE)
    assert not has_permission(Role.SECURITY, Permission.AUDIT_VIEW)
    assert not has_permission(Role.LEARNER, Permission.PACKAGE_REGISTER)
    assert not has_permission(Role.ADMIN, Permission.PICKUP_HANDOVER)
    assert has_permission(Role.ADMIN, Permission.AUDIT_VIEW)


# ---- overdue -----------------------------------------------------------------
def test_overdue_is_derived_from_arrival_and_status():
    old = NOW - timedelta(days=6)
    assert is_overdue(S.READY_FOR_PICKUP, old, NOW, deadline_days=5)
    assert is_overdue(S.STORED, old, NOW, deadline_days=5)
    assert not is_overdue(S.READY_FOR_PICKUP, NOW - timedelta(days=4), NOW, deadline_days=5)
    assert not is_overdue(S.COLLECTED, old, NOW, deadline_days=5)
    assert not is_overdue(S.UNDER_INVESTIGATION, old, NOW, deadline_days=5)

    # 3-day deadline rule
    assert is_overdue(S.READY_FOR_PICKUP, NOW - timedelta(days=4), NOW, deadline_days=3)
    assert not is_overdue(S.READY_FOR_PICKUP, NOW - timedelta(days=2), NOW, deadline_days=3)
    assert not is_overdue(S.COLLECTED, NOW - timedelta(days=4), NOW, deadline_days=3)


# ---- duplicates --------------------------------------------------------------
def test_tracking_ids_are_normalised_before_duplicate_check():
    assert normalise_tracking_id(" bd 77-81 ") == "BD77-81"
    assert normalise_tracking_id("   ") is None
    assert normalise_tracking_id(None) is None


# ---- infrastructure helpers -----------------------------------------------------
def test_event_bus_isolates_failing_subscribers():
    bus, seen = EventBus(), []
    bus.subscribe(PackageStatusChanged, lambda e: (_ for _ in ()).throw(RuntimeError("boom")))
    bus.subscribe(PackageStatusChanged, seen.append)
    bus.publish(PackageStatusChanged(package_id=1, internal_code="X", recipient_id=1, from_status=None,
                                     to_status=S.RECEIVED))
    assert len(seen) == 1


def test_rate_limiter_blocks_after_max_failures():
    limiter = SlidingWindowRateLimiter(max_failures=2, window_seconds=60)
    limiter.record_failure("k")
    limiter.ensure_allowed("k")
    limiter.record_failure("k")
    with pytest.raises(RateLimitedError):
        limiter.ensure_allowed("k")
    limiter.reset("k")
    limiter.ensure_allowed("k")
