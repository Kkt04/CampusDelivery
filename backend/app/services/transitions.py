"""The single place where a package's status changes.

Steps for every transition:
1. Ask the state machine whether (current -> target) is allowed for this role.
2. Apply a conditional UPDATE `... WHERE id = ? AND status = <current>`.
   If another request changed the package first, 0 rows match and we abort.
3. Release storage capacity when the package leaves campus (terminal state).
4. Write status history + audit log, and queue a domain event for after commit.
"""
from typing import Any

from app.core.exceptions import ConcurrentModificationError
from app.core.time import utcnow
from app.domain.enums import TERMINAL_STATUSES, PackageStatus
from app.domain.events import PackageStatusChanged
from app.domain.state_machine import PackageContext, PackageStateMachine, Transition, state_machine
from app.infrastructure.models import Package, PackageStatusHistory, User
from app.repositories.unit_of_work import UnitOfWork
from app.services.audit import AuditService


def context_of(package: Package) -> PackageContext:
    return PackageContext(
        has_recipient=package.recipient_id is not None,
        has_storage=package.storage_location_id is not None,
    )


class PackageTransitioner:
    def __init__(self, uow: UnitOfWork, machine: PackageStateMachine = state_machine) -> None:
        self._uow = uow
        self._machine = machine
        self._audit = AuditService(uow.audit)

    def apply(self, package: Package, target: PackageStatus, actor: User, reason: str | None = None,
              extra_values: dict[str, Any] | None = None) -> Transition:
        transition = self._machine.check(package.status, target, actor.role, context_of(package))
        source = package.status
        now = utcnow()
        values: dict[str, Any] = {"updated_at": now, **(extra_values or {})}
        if target == PackageStatus.READY_FOR_PICKUP:
            values["ready_at"] = now
        released_location = None
        if target in TERMINAL_STATUSES:
            values["closed_at"] = now
            if package.storage_location_id is not None:
                released_location = package.storage_location.code if package.storage_location else None
                self._uow.storage.release(package.storage_location_id)
                values["storage_location_id"] = None
                package.storage_location = None

        self._uow.session.flush()
        if not self._uow.packages.compare_and_set_status(package.id, source, target, values):
            raise ConcurrentModificationError(
                "The package was changed by someone else. Reload and try again."
            )
        self._uow.session.refresh(package)

        self._uow.packages.add_history(
            PackageStatusHistory(package_id=package.id, from_status=source, to_status=target,
                                 changed_by_id=actor.id, reason=reason, created_at=now)
        )
        details: dict[str, Any] = {"from": source.value, "to": target.value, "action": transition.action}
        if reason:
            details["reason"] = reason
        if released_location:
            details["released_storage"] = released_location
        self._audit.record(actor, f"package.{transition.action}", "package", package.id, details)
        self._uow.record_event(
            PackageStatusChanged(package_id=package.id, internal_code=package.internal_code,
                                 recipient_id=package.recipient_id, from_status=source, to_status=target)
        )
        return transition
