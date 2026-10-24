"""Use case: generic lifecycle transitions (investigate, return, mark lost, ...).

Transitions that need extra input (assigning a shelf, issuing a code, handing
over) have dedicated services and are rejected here.
"""
from app.core.exceptions import InvalidTransitionError, NotFoundError, ValidationFailedError
from app.core.time import utcnow
from app.domain.enums import PackageCondition, PackageSize, PackageStatus, Role
from app.domain.state_machine import state_machine
from app.infrastructure.models import Package, PackageStatusHistory, User
from app.repositories.unit_of_work import UnitOfWork
from app.services.audit import AuditService
from app.services.transitions import PackageTransitioner

REASON_REQUIRED = {PackageStatus.UNDER_INVESTIGATION, PackageStatus.RETURN_REQUESTED, PackageStatus.LOST,
                   PackageStatus.DAMAGED}


class PackageLifecycleService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow
        self._transitioner = PackageTransitioner(uow)

    def transition(self, *, package_id: int, target: PackageStatus, actor: User, reason: str | None) -> Package:
        package = self._uow.packages.get_for_update(package_id)
        if package is None:
            raise NotFoundError("Package not found")
        transition = state_machine.find(package.status, target)
        if transition and transition.requires_dedicated_endpoint:
            raise InvalidTransitionError(f"'{transition.label}' has its own screen and endpoint.",
                                         code="USE_DEDICATED_ENDPOINT")
        if target in REASON_REQUIRED and not (reason and reason.strip()):
            raise ValidationFailedError("A reason is required for this change.", code="REASON_REQUIRED")
        self._transitioner.apply(package, target, actor, reason)
        self._uow.commit()
        return package

    def request_return(self, *, package_id: int, actor: User, reason: str) -> Package:
        """A learner asks for their own package to go back to the courier."""
        package = self._uow.packages.get_for_update(package_id)
        # Learners may only act on their own packages; pretend others do not exist.
        if package is None or (actor.role == Role.LEARNER and package.recipient_id != actor.id):
            raise NotFoundError("Package not found")
        if not (reason and reason.strip()):
            raise ValidationFailedError("A reason is required for this change.", code="REASON_REQUIRED")
        self._transitioner.apply(package, PackageStatus.RETURN_REQUESTED, actor, reason.strip())
        self._uow.commit()
        return package

    def initiate_learner_return(self, *, actor: User, package_id: int | None = None,
                                courier_name: str | None = None, tracking_id: str | None = None,
                                reason: str, size: PackageSize = PackageSize.SMALL,
                                notes: str | None = None) -> Package:
        if not (reason and reason.strip()):
            raise ValidationFailedError("A reason is required for this return.", code="REASON_REQUIRED")

        if package_id is not None:
            return self.request_return(package_id=package_id, actor=actor, reason=reason)

        if not courier_name or not courier_name.strip():
            raise ValidationFailedError("Courier name is required for a new return parcel.", code="COURIER_REQUIRED")

        import secrets
        code_alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        now = utcnow()
        for _ in range(10):
            suffix = "".join(secrets.choice(code_alphabet) for _ in range(5))
            code = f"RET-{now:%y%m%d}-{suffix}"
            if not self._uow.packages.code_exists(code):
                break
        else:
            code = f"RET-{now:%y%m%d}-99999"

        package = self._uow.packages.add(Package(
            internal_code=code,
            courier_name=courier_name.strip(),
            tracking_id=tracking_id.strip() if tracking_id else None,
            recipient_id=actor.id,
            recipient_hint=actor.full_name,
            size=size,
            condition=PackageCondition.GOOD,
            status=PackageStatus.RETURN_REQUESTED,
            arrived_at=now,
            received_by_id=actor.id,
            notes=notes.strip() if notes else None,
        ))
        self._uow.packages.add_history(PackageStatusHistory(
            package_id=package.id,
            from_status=None,
            to_status=PackageStatus.RETURN_REQUESTED,
            changed_by_id=actor.id,
            reason=f"Return initiated by learner: {reason.strip()}",
            created_at=now,
        ))
        AuditService(self._uow.audit).record(
            actor, "package.return_initiated", "package", package.id,
            {"internal_code": package.internal_code, "reason": reason.strip()}
        )
        self._uow.commit()
        return package
