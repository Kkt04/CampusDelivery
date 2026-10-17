"""SQLAlchemy ORM models (persistence layer).

Design notes
* No hard deletes for packages: history, pickup records and audit logs must
  stay intact, so foreign keys use ON DELETE RESTRICT.
* `storage_locations.occupied_count` is a deliberate, guarded denormalisation:
  it lets us reserve a slot with one atomic conditional UPDATE. Invariant:
  occupied_count == number of packages whose storage_location_id points here.
* Pickup codes are stored only as salted HMAC hashes.
"""
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.domain.enums import (
    IncidentStatus,
    IncidentType,
    NotificationChannelType,
    NotificationStatus,
    PackageCondition,
    PackageSize,
    PackageStatus,
    Role,
)
from app.infrastructure.database import Base, UTCDateTime


def _enum(enum_cls, length: int = 32) -> Enum:  # noqa: ANN001
    return Enum(enum_cls, native_enum=False, length=length, validate_strings=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, onupdate=utcnow, nullable=False
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institutional_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    role: Mapped[Role] = mapped_column(_enum(Role), index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class StorageLocation(TimestampMixin, Base):
    __tablename__ = "storage_locations"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="capacity_positive"),
        CheckConstraint("occupied_count >= 0", name="occupied_non_negative"),
        CheckConstraint("occupied_count <= capacity", name="occupied_within_capacity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    description: Mapped[str | None] = mapped_column(String(200))
    capacity: Mapped[int] = mapped_column(Integer)
    occupied_count: Mapped[int] = mapped_column(Integer, default=0)
    max_package_size: Mapped[PackageSize] = mapped_column(_enum(PackageSize, 10))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Package(TimestampMixin, Base):
    __tablename__ = "packages"
    __table_args__ = (Index("ix_packages_status_arrived_at", "status", "arrived_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    internal_code: Mapped[str] = mapped_column(String(24), unique=True)
    courier_name: Mapped[str] = mapped_column(String(80))
    # Uniqueness policy: a normalised tracking ID may be registered once. NULL allowed.
    tracking_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    recipient_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    recipient_hint: Mapped[str | None] = mapped_column(String(200))
    size: Mapped[PackageSize] = mapped_column(_enum(PackageSize, 10))
    condition: Mapped[PackageCondition] = mapped_column(_enum(PackageCondition, 16))
    condition_notes: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[PackageStatus] = mapped_column(_enum(PackageStatus), index=True)
    storage_location_id: Mapped[int | None] = mapped_column(
        ForeignKey("storage_locations.id", ondelete="RESTRICT"), index=True
    )
    arrived_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    received_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    ready_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())  # collected/returned/lost
    notes: Mapped[str | None] = mapped_column(String(500))
    version: Mapped[int] = mapped_column(Integer, default=1)

    recipient: Mapped[User | None] = relationship(foreign_keys=[recipient_id], lazy="joined")
    received_by: Mapped[User] = relationship(foreign_keys=[received_by_id], lazy="joined")
    storage_location: Mapped[StorageLocation | None] = relationship(lazy="joined")


class PackageStatusHistory(Base):
    __tablename__ = "package_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    package_id: Mapped[int] = mapped_column(ForeignKey("packages.id", ondelete="RESTRICT"), index=True)
    from_status: Mapped[PackageStatus | None] = mapped_column(_enum(PackageStatus))
    to_status: Mapped[PackageStatus] = mapped_column(_enum(PackageStatus))
    changed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    changed_by: Mapped[User] = relationship(lazy="joined")


class PickupToken(Base):
    __tablename__ = "pickup_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    package_id: Mapped[int] = mapped_column(ForeignKey("packages.id", ondelete="RESTRICT"), index=True)
    learner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    code_hash: Mapped[str] = mapped_column(String(64))
    salt: Mapped[str] = mapped_column(String(32))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class PickupRecord(Base):
    """Proof of handover. UNIQUE(package_id) is the last line of defence against
    double collection."""

    __tablename__ = "pickup_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    package_id: Mapped[int] = mapped_column(ForeignKey("packages.id", ondelete="RESTRICT"), unique=True)
    learner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    handed_over_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    token_id: Mapped[int] = mapped_column(ForeignKey("pickup_tokens.id", ondelete="RESTRICT"), unique=True)
    storage_location_code: Mapped[str | None] = mapped_column(String(20))
    collected_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, index=True)

    package: Mapped[Package] = relationship(lazy="joined")
    handed_over_by: Mapped[User] = relationship(foreign_keys=[handed_over_by_id], lazy="joined")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    package_id: Mapped[int | None] = mapped_column(ForeignKey("packages.id", ondelete="RESTRICT"))
    channel: Mapped[NotificationChannelType] = mapped_column(_enum(NotificationChannelType, 16))
    title: Mapped[str] = mapped_column(String(120))
    message: Mapped[str] = mapped_column(String(500))
    delivery_status: Mapped[NotificationStatus] = mapped_column(_enum(NotificationStatus, 16), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    read_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    package_id: Mapped[int | None] = mapped_column(
        ForeignKey("packages.id", ondelete="RESTRICT"), index=True
    )
    type: Mapped[IncidentType] = mapped_column(_enum(IncidentType))
    status: Mapped[IncidentStatus] = mapped_column(_enum(IncidentStatus, 16), index=True)
    description: Mapped[str] = mapped_column(Text)
    reported_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    resolved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    resolution_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    package: Mapped[Package | None] = relationship(lazy="joined")
    reported_by: Mapped[User] = relationship(foreign_keys=[reported_by_id], lazy="joined")
    resolved_by: Mapped[User | None] = relationship(foreign_keys=[resolved_by_id], lazy="joined")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_entity", "entity_type", "entity_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, index=True)

    actor: Mapped[User | None] = relationship(lazy="joined")


class IdempotencyKey(Base):
    """Remembers state-changing requests so network retries are replayed, not re-executed."""

    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("user_id", "scope", "key", name="uq_idempotency_user_scope_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    scope: Mapped[str] = mapped_column(String(40))
    key: Mapped[str] = mapped_column(String(80))
    request_hash: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
