"""Use cases: register an incoming package and identify an unknown recipient."""
import secrets
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    ConflictError,
    DuplicateTrackingIdError,
    InvalidTransitionError,
    NotFoundError,
    ValidationFailedError,
)
from app.core.time import utcnow
from app.domain.enums import (
    IncidentStatus,
    IncidentType,
    PackageCondition,
    PackageSize,
    PackageStatus,
    Role,
)
from app.infrastructure.models import Incident, Package, PackageStatusHistory, User
from app.repositories.unit_of_work import UnitOfWork
from app.services.audit import AuditService
from app.services.idempotency import IdempotencyGuard, fingerprint
from app.services.transitions import PackageTransitioner

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I confusion


def normalise_tracking_id(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = "".join(value.split()).upper()
    return cleaned or None


class PackageIntakeService:
    SCOPE = "package.register"

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow
        self._audit = AuditService(uow.audit)
        self._transitioner = PackageTransitioner(uow)
        self._idempotency = IdempotencyGuard(uow.idempotency)

    def _new_internal_code(self, now: datetime) -> str:
        for _ in range(10):
            suffix = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(5))
            code = f"PKG-{now:%y%m%d}-{suffix}"
            if not self._uow.packages.code_exists(code):
                return code
        raise ConflictError("Could not generate a unique package code; retry the request.")

    def _resolve_learner(self, institutional_id: str) -> User:
        user = self._uow.users.get_by_institutional_id(institutional_id)
        if user is None or user.role != Role.LEARNER or not user.is_active:
            raise ValidationFailedError(
                f"No active learner with ID '{institutional_id}'. Check the label, or register the "
                "package without a recipient so it enters the unidentified workflow.",
                code="LEARNER_NOT_FOUND",
            )
        return user

    def register(self, *, actor: User, courier_name: str, tracking_id: str | None,
                 recipient_institutional_id: str | None, recipient_hint: str | None,
                 size: PackageSize, condition: PackageCondition, condition_notes: str | None,
                 arrived_at: datetime | None, notes: str | None,
                 idempotency_key: str | None = None) -> tuple[Package, bool]:
        """Returns (package, replayed). `replayed` is True for an idempotent retry."""
        tracking = normalise_tracking_id(tracking_id)
        request_hash = fingerprint({
            "courier": courier_name, "tracking": tracking, "recipient": recipient_institutional_id,
            "hint": recipient_hint, "size": size, "condition": condition,
            "condition_notes": condition_notes, "arrived_at": arrived_at, "notes": notes,
        })
        if (existing_id := self._idempotency.find(actor.id, self.SCOPE, idempotency_key, request_hash)):
            return self._uow.packages.get(existing_id), True

        if tracking and (duplicate := self._uow.packages.get_by_tracking_id(tracking)):
            # Never silently drop a duplicate: record the rejected attempt, then refuse.
            self._audit.record(actor, "package.duplicate_rejected", "package", duplicate.id,
                               {"tracking_id": tracking, "courier": courier_name})
            self._uow.commit()
            raise DuplicateTrackingIdError(
                f"Tracking ID {tracking} is already registered as {duplicate.internal_code}.",
                details={"existing_package_id": duplicate.id, "existing_internal_code": duplicate.internal_code},
            )

        recipient = self._resolve_learner(recipient_institutional_id) if recipient_institutional_id else None
        now = utcnow()
        package = self._uow.packages.add(
            Package(
                internal_code=self._new_internal_code(now),
                courier_name=" ".join(courier_name.split()),
                tracking_id=tracking,
                recipient_id=recipient.id if recipient else None,
                recipient_hint=recipient_hint,
                size=size,
                condition=condition,
                condition_notes=condition_notes,
                status=PackageStatus.RECEIVED,
                arrived_at=arrived_at or now,
                received_by_id=actor.id,
                notes=notes,
            )
        )
        self._uow.packages.add_history(PackageStatusHistory(
            package_id=package.id, from_status=None, to_status=PackageStatus.RECEIVED,
            changed_by_id=actor.id, reason="Registered at Gate No. 2", created_at=now))
        self._audit.record(actor, "package.registered", "package", package.id, {
            "internal_code": package.internal_code, "tracking_id": tracking, "courier": package.courier_name,
            "recipient_id": package.recipient_id, "condition": condition.value})

        # Step 2 of the workflow: automatic validation outcome.
        if condition == PackageCondition.DAMAGED:
            self._transitioner.apply(package, PackageStatus.DAMAGED, actor, condition_notes)
            self._open_incident(package, actor, IncidentType.DAMAGE,
                                f"Arrived damaged: {condition_notes or 'no notes'}")
        elif recipient is None:
            self._transitioner.apply(package, PackageStatus.UNIDENTIFIED, actor, "No matching learner on label")
            self._open_incident(package, actor, IncidentType.UNIDENTIFIED_RECIPIENT,
                                f"Recipient could not be identified. Label: {recipient_hint or 'n/a'}")
        else:
            self._transitioner.apply(package, PackageStatus.VERIFIED, actor, "Recipient matched")

        self._idempotency.remember(actor.id, self.SCOPE, idempotency_key, request_hash, package.id)
        try:
            self._uow.commit()
        except IntegrityError:
            # A concurrent request inserted the same tracking ID or idempotency key first.
            self._uow.rollback()
            if (existing_id := self._idempotency.find(actor.id, self.SCOPE, idempotency_key, request_hash)):
                return self._uow.packages.get(existing_id), True
            if tracking and (duplicate := self._uow.packages.get_by_tracking_id(tracking)):
                raise DuplicateTrackingIdError(
                    f"Tracking ID {tracking} is already registered as {duplicate.internal_code}.",
                    details={"existing_package_id": duplicate.id},
                ) from None
            raise ConflictError("The package could not be saved because of a conflicting record.") from None
        return package, False

    def _open_incident(self, package: Package, actor: User, kind: IncidentType, description: str) -> None:
        incident = self._uow.incidents.add(Incident(
            package_id=package.id, type=kind, status=IncidentStatus.OPEN,
            description=description, reported_by_id=actor.id))
        self._audit.record(actor, "incident.opened", "incident", incident.id,
                           {"type": kind.value, "package_id": package.id, "automatic": True})

    def identify_recipient(self, *, package_id: int, learner_institutional_id: str, actor: User) -> Package:
        package = self._uow.packages.get_for_update(package_id)
        if package is None:
            raise NotFoundError("Package not found")
        if package.recipient_id is not None:
            raise InvalidTransitionError("This package already has a recipient.")
        if package.status not in {PackageStatus.UNIDENTIFIED, PackageStatus.DAMAGED,
                                  PackageStatus.UNDER_INVESTIGATION}:
            raise InvalidTransitionError(f"A recipient cannot be set while the package is {package.status.value}.")
        learner = self._resolve_learner(learner_institutional_id)
        package.recipient_id = learner.id
        self._uow.session.flush()
        self._uow.session.refresh(package)
        self._audit.record(actor, "package.recipient_identified", "package", package.id,
                           {"learner_id": learner.id})
        if package.status == PackageStatus.UNIDENTIFIED:
            target = PackageStatus.STORED if package.storage_location_id else PackageStatus.VERIFIED
            self._transitioner.apply(package, target, actor, f"Recipient identified as {learner.institutional_id}")
            now = utcnow()
            for incident in self._uow.incidents.open_for_package(package.id):
                if incident.type == IncidentType.UNIDENTIFIED_RECIPIENT:
                    incident.status = IncidentStatus.RESOLVED
                    incident.resolved_by_id = actor.id
                    incident.resolved_at = now
                    incident.resolution_note = f"Recipient identified as {learner.institutional_id}"
        self._uow.commit()
        return package
