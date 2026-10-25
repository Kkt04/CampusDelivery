from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest

from app.core.config import Settings
from app.core.exceptions import (
    AlreadyCollectedError,
    AmbiguousPackageError,
    NotFoundError,
    PickupCodeError,
    ValidationFailedError,
)
from app.domain.enums import PackageStatus, Role
from app.infrastructure.models import Package, PickupRecord, PickupToken, StorageLocation, User
from app.services.pickup import PickupService


NOW = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)


class MockPickupUoW:
    def __init__(self):
        self.packages_map: dict[int, Package] = {}
        self.tokens_map: dict[int, list[PickupToken]] = {}
        self.pickups_map: dict[int, PickupRecord] = {}
        self.audit_records: list[dict] = []
        self._seq = 1

        class MockPkgs:
            def find_by_identifier(_, identifier: str):
                clean = identifier.strip().upper()
                results = []
                for p in self.packages_map.values():
                    if p.internal_code == clean or (p.tracking_id and p.tracking_id.upper() == clean):
                        results.append(p)
                return results

            def get_by_code_for_update(_, code: str):
                clean = code.strip().upper()
                for p in self.packages_map.values():
                    if p.internal_code == clean:
                        return p
                return None

            def get_for_update(_, pkg_id: int):
                return self.packages_map.get(pkg_id)

            def compare_and_set_status(_, pkg_id: int, expected: PackageStatus, new: PackageStatus, values: dict):
                p = self.packages_map.get(pkg_id)
                if p and p.status == expected:
                    p.status = new
                    for k, v in values.items():
                        setattr(p, k, v)
                    return True
                return False

            def add_history(_, entry):
                pass

        class MockTokens:
            def latest_for_package(_, pkg_id: int):
                tlist = self.tokens_map.get(pkg_id, [])
                return tlist[-1] if tlist else None

            def mark_used(_, token_id: int, now: datetime):
                for tlist in self.tokens_map.values():
                    for t in tlist:
                        if t.id == token_id and t.used_at is None:
                            t.used_at = now
                            return True
                return False

        class MockPickups:
            def add(_, record: PickupRecord):
                record.id = self._seq
                self._seq += 1
                self.pickups_map[record.id] = record
                return record

            def get(_, record_id: int):
                return self.pickups_map.get(record_id)

        class MockStorage:
            def release(_, loc_id: int):
                pass

        class MockAudit:
            def add(_, entry):
                self.audit_records.append(entry)

        self.packages = MockPkgs()
        self.tokens = MockTokens()
        self.pickups = MockPickups()
        self.storage = MockStorage()
        self.audit = MockAudit()
        self.idempotency = MagicMock()
        self.idempotency.find.return_value = None
        self.session = MagicMock()

    def record_event(self, event):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass


def test_package_lookup_by_courier_tracking_id_and_code():
    uow = MockPickupUoW()
    settings = Settings()
    svc = PickupService(uow, settings)

    pkg = Package(id=1, internal_code="PKG-2026-0001", tracking_id="1Z9999999999",
                  status=PackageStatus.READY_FOR_PICKUP, recipient_id=10)
    uow.packages_map[1] = pkg

    # Lookup by internal code
    found_by_code = svc._locked_package("PKG-2026-0001")
    assert found_by_code.id == 1

    # Lookup by physical courier barcode
    found_by_tracking = svc._locked_package("1Z9999999999")
    assert found_by_tracking.id == 1

    # Non-existent raises NotFoundError
    with pytest.raises(NotFoundError):
        svc._locked_package("NON-EXISTENT-CODE")


def test_duplicate_tracking_id_disambiguation():
    uow = MockPickupUoW()
    settings = Settings()
    svc = PickupService(uow, settings)

    # 1 package was collected previously, 1 is newly arrived for pickup
    pkg_old = Package(id=1, internal_code="PKG-2026-0001", tracking_id="AWB123456",
                      status=PackageStatus.COLLECTED, recipient_id=10)
    pkg_new = Package(id=2, internal_code="PKG-2026-0099", tracking_id="AWB123456",
                      status=PackageStatus.READY_FOR_PICKUP, recipient_id=10)
    uow.packages_map[1] = pkg_old
    uow.packages_map[2] = pkg_new

    # Automatically resolves to the single active package awaiting pickup
    resolved = svc._locked_package("AWB123456")
    assert resolved.id == 2
    assert resolved.internal_code == "PKG-2026-0099"

    # If both are actively awaiting pickup, it raises AmbiguousPackageError with matching codes
    pkg_third = Package(id=3, internal_code="PKG-2026-0100", tracking_id="AWB123456",
                        status=PackageStatus.PICKUP_REQUESTED, recipient_id=11)
    uow.packages_map[3] = pkg_third

    with pytest.raises(AmbiguousPackageError) as err:
        svc._locked_package("AWB123456")
    assert "Multiple packages found" in err.value.message
    assert "PKG-2026-0099" in err.value.details["matching_codes"]
    assert "PKG-2026-0100" in err.value.details["matching_codes"]


def test_supervisor_manual_override_happy_path_and_audit():
    uow = MockPickupUoW()
    settings = Settings()
    svc = PickupService(uow, settings)

    recipient = User(id=10, institutional_id="STU4001", full_name="Diana Prince", email="diana@campus.edu",
                     role=Role.LEARNER, password_hash="dummy")
    guard = User(id=5, institutional_id="SEC1005", full_name="Guard Officer", email="guard@campus.edu",
                 role=Role.SECURITY, password_hash="dummy")

    loc = StorageLocation(id=2, code="RACK-B-04", capacity=10, occupied_count=3, max_package_size="MEDIUM")
    pkg = Package(id=10, internal_code="PKG-2026-0555", tracking_id="DELHI-9988",
                  status=PackageStatus.READY_FOR_PICKUP, recipient_id=recipient.id,
                  storage_location_id=loc.id)
    pkg.recipient = recipient
    pkg.storage_location = loc
    uow.packages_map[10] = pkg

    # Active token outstanding
    tok = PickupToken(id=77, package_id=10, learner_id=recipient.id, salt="s", code_hash="h",
                      expires_at=NOW, created_at=NOW)
    uow.tokens_map[10] = [tok]

    # Perform manual override
    record, replayed = svc.manual_override(
        package_code="DELHI-9988",
        learner_institutional_id="STU4001",
        reason="Student phone battery died. Verified student photo ID card physically at Gate No. 2 desk.",
        actor=guard,
    )

    assert not replayed
    assert record.package_id == 10
    assert record.learner_id == recipient.id
    assert record.is_override is True
    assert "Verified student photo ID" in record.override_reason
    assert pkg.status == PackageStatus.COLLECTED
    assert tok.used_at is not None  # Token revoked/marked used

    # Audit log entry created
    override_audits = [a for a in uow.audit_records if a.action == "pickup.override_completed"]
    assert len(override_audits) == 1
    audit = override_audits[0]
    assert audit.actor_id == guard.id
    assert audit.entity_id == "10"
    assert audit.details["learner_institutional_id"] == "STU4001"
    assert "battery died" in audit.details["reason"]


def test_supervisor_manual_override_validation():
    uow = MockPickupUoW()
    settings = Settings()
    svc = PickupService(uow, settings)

    recipient = User(id=10, institutional_id="STU4001", full_name="Diana", role=Role.LEARNER)
    guard = User(id=5, institutional_id="SEC1005", role=Role.SECURITY)
    pkg = Package(id=10, internal_code="PKG-2026-0555", status=PackageStatus.READY_FOR_PICKUP, recipient_id=recipient.id)
    pkg.recipient = recipient
    uow.packages_map[10] = pkg

    # 1. Reason too short (< 5 chars)
    with pytest.raises(ValidationFailedError):
        svc.manual_override(package_code="PKG-2026-0555", learner_institutional_id="STU4001",
                            reason="ok", actor=guard)

    # 2. Wrong student ID mismatch
    with pytest.raises(PickupCodeError) as err:
        svc.manual_override(package_code="PKG-2026-0555", learner_institutional_id="WRONG_ID",
                            reason="Student verified", actor=guard)
    assert err.value.code == "PICKUP_WRONG_RECIPIENT"

    # 3. Already collected package cannot be overridden
    pkg.status = PackageStatus.COLLECTED
    with pytest.raises(AlreadyCollectedError):
        svc.manual_override(package_code="PKG-2026-0555", learner_institutional_id="STU4001",
                            reason="Student verified", actor=guard)
