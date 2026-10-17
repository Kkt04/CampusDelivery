"""SQLAlchemy implementations of the repositories.

Concurrency-critical writes use *conditional* UPDATE statements and check the
affected row count, so two requests can never both "win" the same change.
"""
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, or_, select, update
from sqlalchemy.orm import Session, aliased

from app.domain.allocation import StorageCandidate
from app.domain.enums import AWAITING_COLLECTION_STATUSES, NotificationStatus, PackageStatus, Role
from app.domain.overdue import overdue_cutoff
from app.infrastructure.models import (
    AuditLog,
    IdempotencyKey,
    Incident,
    Notification,
    Package,
    PackageStatusHistory,
    PickupRecord,
    PickupToken,
    StorageLocation,
    User,
)
from app.repositories.filters import AuditFilters, IncidentFilters, Page, PackageFilters


def _paginate(session: Session, stmt: Select, page: int, page_size: int) -> Page:
    total = session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = list(session.scalars(stmt.limit(page_size).offset((page - 1) * page_size)).unique())
    return Page(items=items, total=total, page=page, page_size=page_size)


class SqlUserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def get_by_institutional_id(self, institutional_id: str) -> User | None:
        return self.session.scalar(
            select(User).where(func.upper(User.institutional_id) == institutional_id.strip().upper())
        )

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))

    def get_by_login(self, identifier: str) -> User | None:
        identifier = identifier.strip()
        if "@" in identifier:
            return self.get_by_email(identifier)
        return self.get_by_institutional_id(identifier)

    def add(self, user: User) -> User:
        self.session.add(user)
        self.session.flush()
        return user

    def search(self, q: str | None, role: Role | None, active_only: bool,
               page: int, page_size: int) -> Page[User]:
        stmt = select(User).order_by(User.role, User.full_name)
        if role:
            stmt = stmt.where(User.role == role)
        if active_only:
            stmt = stmt.where(User.is_active.is_(True))
        if q:
            like = f"%{q.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(User.full_name).like(like),
                    func.lower(User.institutional_id).like(like),
                    func.lower(User.email).like(like),
                    User.phone.like(f"%{q.strip()}%"),
                )
            )
        return _paginate(self.session, stmt, page, page_size)


class SqlPackageRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, package_id: int) -> Package | None:
        return self.session.get(Package, package_id)

    def get_for_update(self, package_id: int) -> Package | None:
        """Row lock (PostgreSQL) held until commit; concurrent writers wait."""
        stmt = select(Package).where(Package.id == package_id).with_for_update(of=Package)
        return self.session.scalars(stmt).unique().one_or_none()

    def get_by_code_for_update(self, internal_code: str) -> Package | None:
        stmt = (
            select(Package)
            .where(Package.internal_code == internal_code.strip().upper())
            .with_for_update(of=Package)
        )
        return self.session.scalars(stmt).unique().one_or_none()

    def get_by_tracking_id(self, tracking_id: str) -> Package | None:
        return self.session.scalar(select(Package).where(Package.tracking_id == tracking_id))

    def code_exists(self, internal_code: str) -> bool:
        return self.session.scalar(select(Package.id).where(Package.internal_code == internal_code)) is not None

    def add(self, package: Package) -> Package:
        self.session.add(package)
        self.session.flush()
        return package

    def compare_and_set_status(self, package_id: int, expected: PackageStatus, new: PackageStatus,
                               values: dict[str, Any]) -> bool:
        result = self.session.execute(
            update(Package)
            .where(Package.id == package_id, Package.status == expected)
            .values(status=new, version=Package.version + 1, **values)
            .execution_options(synchronize_session=False)
        )
        return result.rowcount == 1

    def add_history(self, entry: PackageStatusHistory) -> None:
        self.session.add(entry)

    def history(self, package_id: int) -> list[PackageStatusHistory]:
        stmt = (
            select(PackageStatusHistory)
            .where(PackageStatusHistory.package_id == package_id)
            .order_by(PackageStatusHistory.created_at, PackageStatusHistory.id)
        )
        return list(self.session.scalars(stmt))

    def search(self, filters: PackageFilters, page: int, page_size: int, now: datetime) -> Page[Package]:
        recipient = aliased(User)
        stmt = (
            select(Package)
            .outerjoin(recipient, Package.recipient_id == recipient.id)
            .order_by(Package.arrived_at.desc(), Package.id.desc())
        )
        if filters.q:
            raw = filters.q.strip()
            like = f"%{raw.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Package.internal_code).like(like),
                    func.lower(Package.tracking_id).like(like),
                    func.lower(Package.courier_name).like(like),
                    func.lower(Package.recipient_hint).like(like),
                    func.lower(recipient.full_name).like(like),
                    func.lower(recipient.institutional_id).like(like),
                )
            )
        if filters.statuses:
            stmt = stmt.where(Package.status.in_(filters.statuses))
        if filters.recipient_id is not None:
            stmt = stmt.where(Package.recipient_id == filters.recipient_id)
        if filters.condition:
            stmt = stmt.where(Package.condition == filters.condition)
        if filters.storage_location_id is not None:
            stmt = stmt.where(Package.storage_location_id == filters.storage_location_id)
        if filters.arrived_from:
            stmt = stmt.where(Package.arrived_at >= filters.arrived_from)
        if filters.arrived_to:
            stmt = stmt.where(Package.arrived_at < filters.arrived_to)
        if filters.overdue_only:
            stmt = stmt.where(
                Package.status.in_(AWAITING_COLLECTION_STATUSES),
                Package.arrived_at < overdue_cutoff(now, filters.overdue_deadline_days),
            )
        return _paginate(self.session, stmt, page, page_size)

    def count_by_status(self) -> dict[PackageStatus, int]:
        rows = self.session.execute(select(Package.status, func.count()).group_by(Package.status))
        return {status: count for status, count in rows}

    def count_overdue(self, now: datetime, deadline_days: int) -> int:
        return self.session.scalar(
            select(func.count()).select_from(Package).where(
                Package.status.in_(AWAITING_COLLECTION_STATUSES),
                Package.arrived_at < overdue_cutoff(now, deadline_days),
            )
        ) or 0

    def count_where(self, *criteria: Any) -> int:
        return self.session.scalar(select(func.count()).select_from(Package).where(*criteria)) or 0

    def arrival_times_between(self, start: datetime, end: datetime) -> list[datetime]:
        return list(self.session.scalars(
            select(Package.arrived_at).where(Package.arrived_at >= start, Package.arrived_at < end)
        ))


class SqlStorageRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, location_id: int) -> StorageLocation | None:
        return self.session.get(StorageLocation, location_id)

    def get_by_code(self, code: str) -> StorageLocation | None:
        return self.session.scalar(select(StorageLocation).where(StorageLocation.code == code.strip().upper()))

    def list_locations(self, active_only: bool = False) -> list[StorageLocation]:
        stmt = select(StorageLocation).order_by(StorageLocation.code)
        if active_only:
            stmt = stmt.where(StorageLocation.is_active.is_(True))
        return list(self.session.scalars(stmt))

    def add(self, location: StorageLocation) -> StorageLocation:
        self.session.add(location)
        self.session.flush()
        return location

    def candidates(self) -> Sequence[StorageCandidate]:
        rows = self.session.scalars(
            select(StorageLocation).where(
                StorageLocation.is_active.is_(True),
                StorageLocation.occupied_count < StorageLocation.capacity,
            )
        )
        return [
            StorageCandidate(
                id=r.id, code=r.code, capacity=r.capacity, occupied=r.occupied_count,
                max_package_size=r.max_package_size, is_active=r.is_active,
            )
            for r in rows
        ]

    def try_reserve(self, location_id: int) -> bool:
        """Atomically take one slot. Fails (returns False) if full or inactive."""
        result = self.session.execute(
            update(StorageLocation)
            .where(
                StorageLocation.id == location_id,
                StorageLocation.is_active.is_(True),
                StorageLocation.occupied_count < StorageLocation.capacity,
            )
            .values(occupied_count=StorageLocation.occupied_count + 1)
            .execution_options(synchronize_session=False)
        )
        return result.rowcount == 1

    def release(self, location_id: int) -> None:
        self.session.execute(
            update(StorageLocation)
            .where(StorageLocation.id == location_id, StorageLocation.occupied_count > 0)
            .values(occupied_count=StorageLocation.occupied_count - 1)
            .execution_options(synchronize_session=False)
        )

    def totals(self) -> tuple[int, int]:
        capacity, occupied = self.session.execute(
            select(func.coalesce(func.sum(StorageLocation.capacity), 0),
                   func.coalesce(func.sum(StorageLocation.occupied_count), 0))
            .where(StorageLocation.is_active.is_(True))
        ).one()
        return int(capacity), int(occupied)


class SqlPickupTokenRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, token: PickupToken) -> PickupToken:
        self.session.add(token)
        self.session.flush()
        return token

    def latest_for_package(self, package_id: int) -> PickupToken | None:
        return self.session.scalar(
            select(PickupToken).where(PickupToken.package_id == package_id).order_by(PickupToken.id.desc()).limit(1)
        )

    def revoke_active(self, package_id: int, now: datetime) -> int:
        result = self.session.execute(
            update(PickupToken)
            .where(PickupToken.package_id == package_id, PickupToken.used_at.is_(None),
                   PickupToken.revoked_at.is_(None))
            .values(revoked_at=now)
            .execution_options(synchronize_session=False)
        )
        return result.rowcount

    def mark_used(self, token_id: int, now: datetime) -> bool:
        result = self.session.execute(
            update(PickupToken)
            .where(PickupToken.id == token_id, PickupToken.used_at.is_(None), PickupToken.revoked_at.is_(None))
            .values(used_at=now)
            .execution_options(synchronize_session=False)
        )
        return result.rowcount == 1

    def increment_failed_attempts(self, token_id: int) -> None:
        self.session.execute(
            update(PickupToken)
            .where(PickupToken.id == token_id)
            .values(failed_attempts=PickupToken.failed_attempts + 1)
            .execution_options(synchronize_session=False)
        )


class SqlPickupRecordRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, record: PickupRecord) -> PickupRecord:
        self.session.add(record)
        self.session.flush()
        return record

    def get(self, record_id: int) -> PickupRecord | None:
        return self.session.get(PickupRecord, record_id)

    def list_records(self, learner_id: int | None, page: int, page_size: int) -> Page[PickupRecord]:
        stmt = select(PickupRecord).order_by(PickupRecord.collected_at.desc())
        if learner_id is not None:
            stmt = stmt.where(PickupRecord.learner_id == learner_id)
        return _paginate(self.session, stmt, page, page_size)

    def collection_times_between(self, start: datetime, end: datetime) -> list[datetime]:
        return list(self.session.scalars(
            select(PickupRecord.collected_at).where(PickupRecord.collected_at >= start,
                                                    PickupRecord.collected_at < end)
        ))


class SqlNotificationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, notification: Notification) -> Notification:
        self.session.add(notification)
        self.session.flush()
        return notification

    def get(self, notification_id: int) -> Notification | None:
        return self.session.get(Notification, notification_id)

    def list_in_app(self, user_id: int, page: int, page_size: int) -> Page[Notification]:
        from app.domain.enums import NotificationChannelType

        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id, Notification.channel == NotificationChannelType.IN_APP)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
        )
        return _paginate(self.session, stmt, page, page_size)

    def unread_count(self, user_id: int) -> int:
        from app.domain.enums import NotificationChannelType

        return self.session.scalar(
            select(func.count()).select_from(Notification).where(
                Notification.user_id == user_id,
                Notification.channel == NotificationChannelType.IN_APP,
                Notification.read_at.is_(None),
            )
        ) or 0

    def mark_all_read(self, user_id: int, now: datetime) -> int:
        result = self.session.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
            .values(read_at=now)
            .execution_options(synchronize_session=False)
        )
        return result.rowcount

    def retryable(self, max_attempts: int) -> list[Notification]:
        return list(self.session.scalars(
            select(Notification).where(
                Notification.delivery_status.in_([NotificationStatus.FAILED, NotificationStatus.PENDING]),
                Notification.attempts < max_attempts,
            ).order_by(Notification.id)
        ))

    def count_by_status(self, status: NotificationStatus) -> int:
        return self.session.scalar(
            select(func.count()).select_from(Notification).where(Notification.delivery_status == status)
        ) or 0


class SqlIncidentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, incident: Incident) -> Incident:
        self.session.add(incident)
        self.session.flush()
        return incident

    def get(self, incident_id: int) -> Incident | None:
        return self.session.get(Incident, incident_id)

    def open_for_package(self, package_id: int) -> list[Incident]:
        from app.domain.enums import IncidentStatus

        return list(self.session.scalars(
            select(Incident).where(Incident.package_id == package_id, Incident.status == IncidentStatus.OPEN)
        ))

    def search(self, filters: IncidentFilters, page: int, page_size: int) -> Page[Incident]:
        stmt = select(Incident).order_by(Incident.created_at.desc(), Incident.id.desc())
        if filters.status:
            stmt = stmt.where(Incident.status == filters.status)
        if filters.type:
            stmt = stmt.where(Incident.type == filters.type)
        if filters.package_id is not None:
            stmt = stmt.where(Incident.package_id == filters.package_id)
        if filters.reported_by_id is not None:
            stmt = stmt.where(Incident.reported_by_id == filters.reported_by_id)
        return _paginate(self.session, stmt, page, page_size)

    def count_open(self) -> int:
        from app.domain.enums import IncidentStatus

        return self.session.scalar(
            select(func.count()).select_from(Incident).where(Incident.status == IncidentStatus.OPEN)
        ) or 0


class SqlAuditRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entry: AuditLog) -> None:
        self.session.add(entry)

    def search(self, filters: AuditFilters, page: int, page_size: int) -> Page[AuditLog]:
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        if filters.action:
            stmt = stmt.where(AuditLog.action.like(f"{filters.action}%"))
        if filters.entity_type:
            stmt = stmt.where(AuditLog.entity_type == filters.entity_type)
        if filters.entity_id:
            stmt = stmt.where(AuditLog.entity_id == filters.entity_id)
        if filters.actor_id is not None:
            stmt = stmt.where(AuditLog.actor_id == filters.actor_id)
        if filters.date_from:
            stmt = stmt.where(AuditLog.created_at >= filters.date_from)
        if filters.date_to:
            stmt = stmt.where(AuditLog.created_at < filters.date_to)
        return _paginate(self.session, stmt, page, page_size)


class SqlIdempotencyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, user_id: int, scope: str, key: str) -> IdempotencyKey | None:
        return self.session.scalar(
            select(IdempotencyKey).where(
                IdempotencyKey.user_id == user_id, IdempotencyKey.scope == scope, IdempotencyKey.key == key
            )
        )

    def add(self, record: IdempotencyKey) -> None:
        self.session.add(record)
