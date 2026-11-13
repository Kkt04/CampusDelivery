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


class PackageFilterBuilder:
    """Builder pattern for fluent construction of complex package queries."""

    def __init__(self) -> None:
        self._filters = PackageFilters()

    def search(self, query: str | None) -> "PackageFilterBuilder":
        if query:
            self._filters.q = query.strip()
        return self

    def with_statuses(self, statuses: list[PackageStatus] | None) -> "PackageFilterBuilder":
        if statuses:
            self._filters.statuses = list(statuses)
        return self

    def for_recipient(self, recipient_id: int | None) -> "PackageFilterBuilder":
        self._filters.recipient_id = recipient_id
        return self

    def with_condition(self, condition: PackageCondition | None) -> "PackageFilterBuilder":
        self._filters.condition = condition
        return self

    def overdue(self, overdue_only: bool = True, deadline_days: int = 3) -> "PackageFilterBuilder":
        self._filters.overdue_only = overdue_only
        self._filters.overdue_deadline_days = deadline_days
        return self

    def arrival_between(self, start: datetime | None, end: datetime | None) -> "PackageFilterBuilder":
        self._filters.arrived_from = start
        self._filters.arrived_to = end
        return self

    def for_location(self, storage_location_id: int | None) -> "PackageFilterBuilder":
        self._filters.storage_location_id = storage_location_id
        return self

    def build(self) -> PackageFilters:
        return self._filters


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
