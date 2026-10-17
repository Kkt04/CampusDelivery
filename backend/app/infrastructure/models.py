"""Document models (persistence layer).

These are plain, mutable dataclasses — the MongoDB equivalent of the previous
SQLAlchemy models. Repositories translate them to and from BSON documents and
hydrate the related-object attributes (`package.recipient`, `record.package`, …)
that the presenters expect.

* No hard deletes: history, pickup records and audit logs stay intact.
* `storage_locations.occupied_count` is a guarded denormalisation reserved with
  one atomic conditional update; invariant:
  occupied_count == number of packages whose storage_location_id points here.
* Pickup codes are stored only as salted HMAC hashes.
"""
from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import Any, ClassVar

from app.core.time import ensure_utc, utcnow
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


@dataclass
class Document:
    COLLECTION: ClassVar[str] = ""
    RELATIONS: ClassVar[tuple[str, ...]] = ()
    ENUMS: ClassVar[dict[str, Any]] = {}
    DATES: ClassVar[tuple[str, ...]] = ()

    id: int | None = None

    def to_doc(self) -> dict[str, Any]:
        doc: dict[str, Any] = {}
        for f in fields(self):
            if f.name == "id" or f.name in self.RELATIONS:
                continue
            value = getattr(self, f.name)
            if isinstance(value, str):
                doc[f.name] = value
            elif hasattr(value, "value"):  # StrEnum
                doc[f.name] = value.value
            else:
                doc[f.name] = value
        if self.id is not None:
            doc["_id"] = self.id
        return doc

    @classmethod
    def from_doc(cls, doc: dict[str, Any]) -> "Document":
        data: dict[str, Any] = {"id": doc.get("_id")}
        for f in fields(cls):
            if f.name == "id" or f.name in cls.RELATIONS:
                continue
            if f.name not in doc:
                continue
            value = doc[f.name]
            if f.name in cls.ENUMS and value is not None:
                value = cls.ENUMS[f.name](value)
            elif f.name in cls.DATES and value is not None:
                value = ensure_utc(value)
            data[f.name] = value
        return cls(**data)

    def apply_doc(self, doc: dict[str, Any]) -> None:
        for key, value in self.from_doc(doc).__dict__.items():
            if key in self.RELATIONS:
                continue
            setattr(self, key, value)


@dataclass
class User(Document):
    COLLECTION: ClassVar[str] = "users"
    ENUMS: ClassVar[dict[str, Any]] = {"role": Role}
    DATES: ClassVar[tuple[str, ...]] = ("created_at", "updated_at")

    institutional_id: str = ""
    full_name: str = ""
    email: str = ""
    phone: str | None = None
    role: Role = Role.LEARNER
    password_hash: str = ""
    is_active: bool = True
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class StorageLocation(Document):
    COLLECTION: ClassVar[str] = "storage_locations"
    ENUMS: ClassVar[dict[str, Any]] = {"max_package_size": PackageSize}
    DATES: ClassVar[tuple[str, ...]] = ("created_at", "updated_at")

    code: str = ""
    description: str | None = None
    capacity: int = 0
    occupied_count: int = 0
    max_package_size: PackageSize = PackageSize.SMALL
    is_active: bool = True
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class Package(Document):
    COLLECTION: ClassVar[str] = "packages"
    RELATIONS: ClassVar[tuple[str, ...]] = ("recipient", "received_by", "storage_location")
    ENUMS: ClassVar[dict[str, Any]] = {
        "size": PackageSize,
        "condition": PackageCondition,
        "status": PackageStatus,
    }
    DATES: ClassVar[tuple[str, ...]] = (
        "arrived_at", "ready_at", "closed_at", "created_at", "updated_at"
    )

    internal_code: str = ""
    courier_name: str = ""
    tracking_id: str | None = None
    recipient_id: int | None = None
    recipient_hint: str | None = None
    size: PackageSize = PackageSize.SMALL
    condition: PackageCondition = PackageCondition.GOOD
    condition_notes: str | None = None
    status: PackageStatus = PackageStatus.RECEIVED
    storage_location_id: int | None = None
    arrived_at: datetime = field(default_factory=utcnow)
    received_by_id: int = 0
    ready_at: datetime | None = None
    closed_at: datetime | None = None
    notes: str | None = None
    version: int = 1
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    recipient: User | None = None
    received_by: User | None = None
    storage_location: StorageLocation | None = None


@dataclass
class PackageStatusHistory(Document):
    COLLECTION: ClassVar[str] = "package_status_history"
    RELATIONS: ClassVar[tuple[str, ...]] = ("changed_by",)
    ENUMS: ClassVar[dict[str, Any]] = {"from_status": PackageStatus, "to_status": PackageStatus}
    DATES: ClassVar[tuple[str, ...]] = ("created_at",)

    package_id: int = 0
    from_status: PackageStatus | None = None
    to_status: PackageStatus = PackageStatus.RECEIVED
    changed_by_id: int = 0
    reason: str | None = None
    created_at: datetime = field(default_factory=utcnow)

    changed_by: User | None = None


@dataclass
class PickupToken(Document):
    COLLECTION: ClassVar[str] = "pickup_tokens"
    DATES: ClassVar[tuple[str, ...]] = ("expires_at", "used_at", "revoked_at", "created_at")

    package_id: int = 0
    learner_id: int = 0
    code_hash: str = ""
    salt: str = ""
    expires_at: datetime = field(default_factory=utcnow)
    used_at: datetime | None = None
    revoked_at: datetime | None = None
    failed_attempts: int = 0
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class PickupRecord(Document):
    """Proof of handover. The unique index on package_id is the last line of
    defence against double collection."""

    COLLECTION: ClassVar[str] = "pickup_records"
    RELATIONS: ClassVar[tuple[str, ...]] = ("package", "handed_over_by")
    DATES: ClassVar[tuple[str, ...]] = ("collected_at",)

    package_id: int = 0
    learner_id: int = 0
    handed_over_by_id: int = 0
    token_id: int = 0
    storage_location_code: str | None = None
    collected_at: datetime = field(default_factory=utcnow)

    package: Package | None = None
    handed_over_by: User | None = None


@dataclass
class Notification(Document):
    COLLECTION: ClassVar[str] = "notifications"
    ENUMS: ClassVar[dict[str, Any]] = {
        "channel": NotificationChannelType,
        "delivery_status": NotificationStatus,
    }
    DATES: ClassVar[tuple[str, ...]] = ("created_at", "sent_at", "read_at")

    user_id: int = 0
    package_id: int | None = None
    channel: NotificationChannelType = NotificationChannelType.IN_APP
    title: str = ""
    message: str = ""
    delivery_status: NotificationStatus = NotificationStatus.PENDING
    attempts: int = 0
    last_error: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    sent_at: datetime | None = None
    read_at: datetime | None = None


@dataclass
class Incident(Document):
    COLLECTION: ClassVar[str] = "incidents"
    RELATIONS: ClassVar[tuple[str, ...]] = ("package", "reported_by", "resolved_by")
    ENUMS: ClassVar[dict[str, Any]] = {"type": IncidentType, "status": IncidentStatus}
    DATES: ClassVar[tuple[str, ...]] = ("created_at", "resolved_at")

    package_id: int | None = None
    type: IncidentType = IncidentType.OPERATIONAL
    status: IncidentStatus = IncidentStatus.OPEN
    description: str = ""
    reported_by_id: int = 0
    resolved_by_id: int | None = None
    resolution_note: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    resolved_at: datetime | None = None

    package: Package | None = None
    reported_by: User | None = None
    resolved_by: User | None = None


@dataclass
class AuditLog(Document):
    COLLECTION: ClassVar[str] = "audit_logs"
    RELATIONS: ClassVar[tuple[str, ...]] = ("actor",)
    DATES: ClassVar[tuple[str, ...]] = ("created_at",)

    actor_id: int | None = None
    action: str = ""
    entity_type: str = ""
    entity_id: str | None = None
    details: dict | None = None
    created_at: datetime = field(default_factory=utcnow)

    actor: User | None = None


@dataclass
class IdempotencyKey(Document):
    COLLECTION: ClassVar[str] = "idempotency_keys"
    DATES: ClassVar[tuple[str, ...]] = ("created_at",)

    user_id: int = 0
    scope: str = ""
    key: str = ""
    request_hash: str = ""
    resource_id: int = 0
    created_at: datetime = field(default_factory=utcnow)
