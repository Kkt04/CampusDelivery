"""Use cases: report, list and resolve incidents."""
from app.core.exceptions import InvalidTransitionError, NotFoundError, PermissionDeniedError, ValidationFailedError
from app.core.time import utcnow
from app.domain.enums import IncidentStatus, IncidentType, PackageStatus, Role
from app.domain.state_machine import state_machine
from app.infrastructure.models import Incident, User
from app.repositories.filters import IncidentFilters, Page
from app.repositories.unit_of_work import UnitOfWork
from app.services.audit import AuditService
from app.services.transitions import PackageTransitioner


class IncidentService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow
        self._audit = AuditService(uow.audit)

    def report(self, *, actor: User, package_id: int | None, kind: IncidentType, description: str,
               escalate: bool = False) -> Incident:
        package = None
        if actor.role == Role.LEARNER:
            # Learners may only report issues about their own packages.
            kind, escalate = IncidentType.LEARNER_REPORTED_ISSUE, False
            if package_id is None:
                raise ValidationFailedError("Choose the package this issue is about.")
        if package_id is not None:
            package = self._uow.packages.get_for_update(package_id) if escalate else self._uow.packages.get(package_id)
            if package is None or (actor.role == Role.LEARNER and package.recipient_id != actor.id):
                raise NotFoundError("Package not found")
        incident = self._uow.incidents.add(Incident(
            package_id=package_id, type=kind, status=IncidentStatus.OPEN,
            description=description.strip(), reported_by_id=actor.id))
        self._audit.record(actor, "incident.opened", "incident", incident.id,
                           {"type": kind.value, "package_id": package_id})
        if escalate:
            if package is None:
                raise ValidationFailedError("Escalation needs a package.")
            if state_machine.find(package.status, PackageStatus.UNDER_INVESTIGATION) is None:
                raise InvalidTransitionError(f"A {package.status.value} package cannot be put under investigation.")
            PackageTransitioner(self._uow).apply(package, PackageStatus.UNDER_INVESTIGATION, actor,
                                                 f"Incident #{incident.id}: {description.strip()[:200]}")
        self._uow.commit()
        return incident

    def search(self, *, actor: User, filters: IncidentFilters, page: int, page_size: int) -> Page[Incident]:
        if actor.role == Role.LEARNER:
            filters.reported_by_id = actor.id
        return self._uow.incidents.search(filters, page, page_size)

    def resolve(self, *, actor: User, incident_id: int, resolution_note: str) -> Incident:
        if actor.role != Role.ADMIN:
            raise PermissionDeniedError("Only operations admins can resolve incidents.")
        incident = self._uow.incidents.get(incident_id)
        if incident is None:
            raise NotFoundError("Incident not found")
        if incident.status == IncidentStatus.RESOLVED:
            return incident  # already resolved: repeat calls are harmless
        incident.status = IncidentStatus.RESOLVED
        incident.resolved_by_id = actor.id
        incident.resolved_at = utcnow()
        incident.resolution_note = resolution_note.strip()
        self._audit.record(actor, "incident.resolved", "incident", incident.id, {"note": incident.resolution_note})
        self._uow.commit()
        self._uow.session.refresh(incident)
        return incident
