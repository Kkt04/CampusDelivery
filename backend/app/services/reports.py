"""Use cases: operations dashboard statistics and date-based reports.
Every number is computed from database rows at request time."""
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone

from app.core.config import Settings
from app.core.exceptions import ValidationFailedError
from app.domain.enums import NotificationStatus, PackageCondition, PackageStatus
from app.infrastructure.models import Package
from app.repositories.unit_of_work import UnitOfWork

MAX_REPORT_DAYS = 92


class ReportService:
    def __init__(self, uow: UnitOfWork, settings: Settings) -> None:
        self._uow = uow
        self._settings = settings

    def dashboard(self, now: datetime) -> dict:
        by_status = self._uow.packages.count_by_status()
        start_of_day = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
        capacity, occupied = self._uow.storage.totals()
        return {
            "by_status": {s.value: by_status.get(s, 0) for s in PackageStatus},
            "received": sum(by_status.values()),
            "in_custody": sum(c for s, c in by_status.items()
                              if s not in {PackageStatus.COLLECTED, PackageStatus.RETURNED, PackageStatus.LOST}),
            "overdue": self._uow.packages.count_overdue(now, self._settings.collection_deadline_days),
            "damaged_condition": self._uow.packages.count_where(Package.condition == PackageCondition.DAMAGED),
            "received_today": self._uow.packages.count_where(Package.arrived_at >= start_of_day),
            "collected_today": len(self._uow.pickups.collection_times_between(start_of_day, now + timedelta(seconds=1))),
            "open_incidents": self._uow.incidents.count_open(),
            "failed_notifications": self._uow.notifications.count_by_status(NotificationStatus.FAILED),
            "storage_capacity": capacity,
            "storage_occupied": occupied,
            "collection_deadline_days": self._settings.collection_deadline_days,
        }

    def daily(self, date_from: date, date_to: date) -> list[dict]:
        if date_to < date_from:
            raise ValidationFailedError("date_to must be on or after date_from")
        if (date_to - date_from).days + 1 > MAX_REPORT_DAYS:
            raise ValidationFailedError(f"Reports are limited to {MAX_REPORT_DAYS} days")
        start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        received = Counter(t.date() for t in self._uow.packages.arrival_times_between(start, end))
        collected = Counter(t.date() for t in self._uow.pickups.collection_times_between(start, end))
        days = (date_to - date_from).days + 1
        return [
            {"date": d.isoformat(), "received": received.get(d, 0), "collected": collected.get(d, 0)}
            for d in (date_from + timedelta(days=i) for i in range(days))
        ]
