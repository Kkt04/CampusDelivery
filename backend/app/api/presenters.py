"""Turn ORM objects into response schemas, applying per-role visibility rules."""
from datetime import datetime

from app.core.config import Settings
from app.domain.enums import STATUS_LABELS, PackageStatus, Role
from app.domain.overdue import is_overdue
from app.domain.state_machine import state_machine
from app.infrastructure.models import AuditLog, Incident, Package, PackageStatusHistory, PickupRecord, User
from app.schemas.common import UserBrief
from app.schemas.misc import AuditLogOut, IncidentOut
from app.schemas.packages import ActionOut, HistoryEntryOut, PackageOut, StorageBrief
from app.schemas.pickups import PickupRecordOut
from app.services.transitions import context_of

# Learners see the shelf only when it helps them collect the package.
_LEARNER_SEES_LOCATION = {PackageStatus.READY_FOR_PICKUP, PackageStatus.PICKUP_REQUESTED}


def brief(user: User | None) -> UserBrief | None:
    return UserBrief.model_validate(user) if user else None


def present_package(pkg: Package, viewer: User, now: datetime, settings: Settings) -> PackageOut:
    is_learner = viewer.role == Role.LEARNER
    show_location = pkg.storage_location and (not is_learner or pkg.status in _LEARNER_SEES_LOCATION)
    actions = [
        ActionOut(action=t.action, label=t.label, target_status=t.target, dedicated=t.requires_dedicated_endpoint)
        for t in state_machine.available(pkg.status, viewer.role, context_of(pkg))
    ]
    return PackageOut(
        id=pkg.id,
        internal_code=pkg.internal_code,
        courier_name=pkg.courier_name,
        tracking_id=pkg.tracking_id,
        recipient=brief(pkg.recipient),
        recipient_hint=None if is_learner else pkg.recipient_hint,
        size=pkg.size,
        condition=pkg.condition,
        condition_notes=pkg.condition_notes,
        status=pkg.status,
        status_label=STATUS_LABELS[pkg.status],
        storage_location=StorageBrief.model_validate(pkg.storage_location) if show_location else None,
        arrived_at=pkg.arrived_at,
        ready_at=pkg.ready_at,
        closed_at=pkg.closed_at,
        received_by=None if is_learner else brief(pkg.received_by),
        is_overdue=is_overdue(pkg.status, pkg.arrived_at, now, settings.collection_deadline_days),
        notes=None if is_learner else pkg.notes,
        available_actions=actions,
        updated_at=pkg.updated_at,
    )


def present_history(entry: PackageStatusHistory, viewer: User) -> HistoryEntryOut:
    return HistoryEntryOut(
        from_status=entry.from_status, to_status=entry.to_status, to_label=STATUS_LABELS[entry.to_status],
        reason=entry.reason if viewer.role != Role.LEARNER else None,
        changed_by=brief(entry.changed_by) if viewer.role != Role.LEARNER else None,
        created_at=entry.created_at,
    )


def present_pickup(record: PickupRecord, viewer: User) -> PickupRecordOut:
    return PickupRecordOut(
        id=record.id, package_id=record.package_id, internal_code=record.package.internal_code,
        courier_name=record.package.courier_name, learner_id=record.learner_id,
        handed_over_by=brief(record.handed_over_by) if viewer.role != Role.LEARNER else None,
        storage_location_code=record.storage_location_code, collected_at=record.collected_at,
    )


def present_incident(incident: Incident) -> IncidentOut:
    return IncidentOut(
        id=incident.id, package_id=incident.package_id,
        package_code=incident.package.internal_code if incident.package else None,
        type=incident.type, status=incident.status, description=incident.description,
        reported_by=brief(incident.reported_by), resolved_by=brief(incident.resolved_by),
        resolution_note=incident.resolution_note, created_at=incident.created_at,
        resolved_at=incident.resolved_at,
    )


def present_audit(entry: AuditLog) -> AuditLogOut:
    return AuditLogOut(id=entry.id, actor=brief(entry.actor), action=entry.action, entity_type=entry.entity_type,
                       entity_id=entry.entity_id, details=entry.details, created_at=entry.created_at)
