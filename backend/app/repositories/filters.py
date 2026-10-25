"""Filter and pagination value objects used by repositories and services."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Generic, TypeVar

from app.domain.enums import IncidentStatus, IncidentType, PackageCondition, PackageStatus

T = TypeVar("T")


@dataclass
class Page(Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


@dataclass
class PackageFilters:
    q: str | None = None
    statuses: list[PackageStatus] = field(default_factory=list)
    recipient_id: int | None = None
    condition: PackageCondition | None = None
    overdue_only: bool = False
    overdue_deadline_days: int = 3
    arrived_from: datetime | None = None
    arrived_to: datetime | None = None
    storage_location_id: int | None = None


@dataclass
class IncidentFilters:
    status: IncidentStatus | None = None
    type: IncidentType | None = None
    package_id: int | None = None
    reported_by_id: int | None = None


@dataclass
class AuditFilters:
    action: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    actor_id: int | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
