"""Use case: generic lifecycle transitions (investigate, return, mark lost, ...).

Transitions that need extra input (assigning a shelf, issuing a code, handing
over) have dedicated services and are rejected here.
"""
from app.core.exceptions import InvalidTransitionError, NotFoundError, ValidationFailedError
from app.domain.enums import PackageStatus
from app.domain.state_machine import state_machine
from app.infrastructure.models import Package, User
from app.repositories.unit_of_work import UnitOfWork
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
