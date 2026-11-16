"""Use case: assign (or move) a package to a storage location.

Capacity safety: each reservation is an atomic find_one_and_update
matching occupied_count < capacity and incrementing occupied_count by 1.
Two staff members racing for the last slot can never both succeed.
"""
# ==============================================================================
# [EVAL-1: REQUIREMENTS] FR-2: Storage Allocation & Shelf Management
# WHAT IT IS FOR:
#   Assigns packages to optimal shelves based on size and capacity constraints.
# ==============================================================================
# [EVAL-4: SOLID-SRP] Single Responsibility Principle
# WHAT IT IS FOR:
#   StorageAllocationService is solely responsible for storage assignment and movement.
#   It delegates the selection algorithm to the injected StorageAllocationStrategy.
# ==============================================================================
# [EVAL-6: SEQUENCE-FLOW] Storage Allocation Sequence Flow
# WHAT IT IS FOR:
#   1. Fetch package and verify it is in STORABLE_STATUSES.
#   2. If shelf specified explicitly -> validate location and capacity.
#   3. If shelf not specified -> consult StorageAllocationStrategy (Strategy pattern).
#   4. Atomically reserve slot via try_reserve() (atomic CAS preventing over-capacity).
#   5. If moving from old shelf -> release(previous_id) slot on previous shelf.
#   6. Transition package status to STORED (or READY_FOR_PICKUP if requested).
#   7. Commit changes and audit the transaction.
# ==============================================================================
from app.core.exceptions import (
    InvalidTransitionError,
    NotFoundError,
    StorageFullError,
    StorageUnavailableError,
    ValidationFailedError,
)
from app.domain.enums import STORABLE_STATUSES, PackageStatus
from app.domain.interfaces import StorageAllocationStrategy
from app.infrastructure.models import Package, StorageLocation, User
from app.repositories.unit_of_work import UnitOfWork
from app.services.audit import AuditService
from app.services.transitions import PackageTransitioner


class StorageAllocationService:
    def __init__(self, uow: UnitOfWork, strategy: StorageAllocationStrategy) -> None:
        self._uow = uow
        self._strategy = strategy
        self._audit = AuditService(uow.audit)
        self._transitioner = PackageTransitioner(uow)

    def assign(self, *, package_id: int, actor: User, location_id: int | None,
               mark_ready: bool = False) -> Package:
        package = self._uow.packages.get_for_update(package_id)
        if package is None:
            raise NotFoundError("Package not found")
        if package.status not in STORABLE_STATUSES:
            raise InvalidTransitionError(f"Storage cannot be assigned while the package is {package.status.value}.")

        previous_id = package.storage_location_id
        if location_id is not None and location_id == previous_id:
            chosen = package.storage_location  # same shelf again: safe no-op (idempotent)
        else:
            chosen = self._reserve(package, location_id)
            if previous_id is not None:
                self._uow.storage.release(previous_id)
            package.storage_location_id = chosen.id
            package.storage_location = chosen
            self._uow.session.flush()
            self._uow.session.refresh(package)
            self._audit.record(actor, "package.storage_assigned", "package", package.id, {
                "from_location_id": previous_id, "to_location": chosen.code,
                "strategy": None if location_id else self._strategy.name})

        if package.status == PackageStatus.VERIFIED:
            self._transitioner.apply(package, PackageStatus.STORED, actor, f"Stored at {chosen.code}")
        if mark_ready and package.status == PackageStatus.STORED:
            self._transitioner.apply(package, PackageStatus.READY_FOR_PICKUP, actor, "Ready for pickup")
        self._uow.commit()
        return package

    def _reserve(self, package: Package, location_id: int | None) -> StorageLocation:
        if location_id is not None:
            location = self._uow.storage.get(location_id)
            if location is None:
                raise NotFoundError("Storage location not found")
            if not location.is_active:
                raise StorageUnavailableError(f"{location.code} is currently unavailable.")
            if package.size.rank > location.max_package_size.rank:
                raise ValidationFailedError(
                    f"{location.code} only holds {location.max_package_size.value.lower()} packages or smaller.",
                    code="STORAGE_SIZE_MISMATCH")
            if not self._uow.storage.try_reserve(location.id):
                raise StorageFullError(f"{location.code} is full.")
            return location

        for candidate in self._strategy.rank(self._uow.storage.candidates(), package.size):
            if self._uow.storage.try_reserve(candidate.id):  # may lose a race: try the next one
                return self._uow.storage.get(candidate.id)
        raise StorageFullError(f"No active storage location has room for a {package.size.value.lower()} package.")
