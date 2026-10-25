"""Notifications: an event subscriber that turns lifecycle events into messages,
plus the read/retry use cases.

Failure handling: the notification rows are committed as PENDING first, then
each channel is tried. A failing channel marks only its own row FAILED with
the error; the package change that triggered it was committed earlier and is
never rolled back. FAILED/PENDING rows can be retried by an admin.
"""
import logging
from collections.abc import Callable
from datetime import datetime

from app.core.exceptions import NotFoundError
from app.core.time import utcnow
from app.domain.enums import NotificationStatus, PackageStatus
from app.domain.events import DomainEvent, PackageStatusChanged
from app.domain.interfaces import NotificationChannel, NotificationRecipient
from app.infrastructure.models import Notification, Package, User
from app.infrastructure.store import Store
from app.repositories.filters import Page
from app.repositories.mongo_repos import (
    MongoNotificationRepository,
    MongoPackageRepository,
    MongoUserRepository,
)
from app.repositories.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)

Template = Callable[..., tuple[str, str] | None]


def _arrived(event: PackageStatusChanged, pkg: Package, user: User | None = None) -> tuple[str, str] | None:
    if event.from_status in {PackageStatus.RECEIVED, PackageStatus.UNIDENTIFIED}:
        name = user.full_name.split()[0] if user and user.full_name else "there"
        return ("Package arrived",
                f"Hey {name} you have a parcel... 🙂, the parcel is waiting for you at Gate No. 2 ({pkg.courier_name}, {pkg.internal_code}). "
                "We will notify you the moment it is placed on a shelf.")
    return None


def _ready(event: PackageStatusChanged, pkg: Package, user: User | None = None) -> tuple[str, str]:
    name = user.full_name.split()[0] if user and user.full_name else "there"
    return (
        "Ready for pickup",
        f"Hey {name} you have a parcel... 🙂, the parcel is waiting for you at Gate No. 2 ({pkg.courier_name}, {pkg.internal_code}). "
        "Open your dashboard to get your one-time pickup code!"
    )


# Which lifecycle events produce a learner message (extend here; workflow code is untouched).
TEMPLATES: dict[PackageStatus, Template] = {
    PackageStatus.VERIFIED: _arrived,
    PackageStatus.READY_FOR_PICKUP: _ready,
    PackageStatus.COLLECTED: lambda e, p, u=None: (
        "Package collected", f"Package {p.internal_code} was handed over to you. Thank you."),
    PackageStatus.DAMAGED: lambda e, p, u=None: (
        "Package arrived damaged",
        f"Package {p.internal_code} arrived damaged and is held at Gate No. 2 while staff review it."),
    PackageStatus.RETURN_REQUESTED: lambda e, p, u=None: (
        "Package being returned", f"Package {p.internal_code} will be returned to {p.courier_name}."),
    PackageStatus.LOST: lambda e, p, u=None: (
        "Package reported lost", f"Package {p.internal_code} could not be located. Operations will contact you."),
}


class NotificationDispatcher:
    def __init__(self, channels: list[NotificationChannel],
                 templates: dict[PackageStatus, Template] | None = None) -> None:
        self.channels = channels
        self._templates = templates or TEMPLATES

    def handle(self, event: DomainEvent) -> None:
        if not isinstance(event, PackageStatusChanged) or event.recipient_id is None:
            return
        template = self._templates.get(event.to_status)
        if template is None:
            return
        store = Store()
        package = MongoPackageRepository(store).get(event.package_id)
        user = MongoUserRepository(store).get(event.recipient_id)
        if package is None or user is None:
            return
        try:
            rendered = template(event, package, user)
        except TypeError:
            rendered = template(event, package)
        if rendered is None:
            return
        title, message = rendered
        repo = MongoNotificationRepository(store)
        rows = [repo.add(Notification(user_id=user.id, package_id=package.id, channel=ch.channel_type,
                                      title=title, message=message,
                                      delivery_status=NotificationStatus.PENDING))
                for ch in self.channels]
        store.commit()  # the record exists even if every channel fails below
        for channel, row in zip(self.channels, rows):
            self.attempt(channel, row, user)
        store.commit()

    def attempt(self, channel: NotificationChannel, row: Notification, user: User) -> None:
        row.attempts += 1
        try:
            channel.send(NotificationRecipient(user.id, user.full_name, user.email), row.title, row.message)
        except Exception as exc:  # noqa: BLE001 - any channel failure is recorded, not raised
            row.delivery_status = NotificationStatus.FAILED
            row.last_error = f"{type(exc).__name__}: {exc}"[:300]
            logger.warning("Notification %s via %s failed: %s", row.id, channel.channel_type, exc)
        else:
            row.delivery_status = NotificationStatus.SENT
            row.sent_at = utcnow()
            row.last_error = None

    def retry(self, max_attempts: int) -> dict[str, int]:
        by_type = {ch.channel_type: ch for ch in self.channels}
        result = {"retried": 0, "sent": 0, "failed": 0, "skipped": 0}
        store = Store()
        users = MongoUserRepository(store)
        for row in MongoNotificationRepository(store).retryable(max_attempts):
            channel = by_type.get(row.channel)
            user = users.get(row.user_id)
            if channel is None or user is None:
                result["skipped"] += 1
                continue
            self.attempt(channel, row, user)
            result["retried"] += 1
            result["sent" if row.delivery_status == NotificationStatus.SENT else "failed"] += 1
        store.commit()
        return result


class NotificationService:
    def __init__(self, uow: UnitOfWork, channels: list[NotificationChannel] | None = None) -> None:
        self._uow = uow
        self._channels = channels or []

    def list_for(self, user: User, page: int, page_size: int) -> Page[Notification]:
        return self._uow.notifications.list_in_app(user.id, page, page_size)

    def unread_count(self, user: User) -> int:
        return self._uow.notifications.unread_count(user.id)

    def mark_read(self, user: User, notification_id: int, now: datetime | None = None) -> Notification:
        row = self._uow.notifications.get(notification_id)
        if row is None or row.user_id != user.id:
            raise NotFoundError("Notification not found")
        if row.read_at is None:
            row.read_at = now or utcnow()
            self._uow.commit()
        return row

    def mark_all_read(self, user: User) -> int:
        count = self._uow.notifications.mark_all_read(user.id, utcnow())
        self._uow.commit()
        return count

    def sweep_overdue(self, now: datetime | None = None, deadline_days: int | None = None) -> dict[str, int]:
        if now is None:
            now = utcnow()
        if deadline_days is None:
            from app.core.config import get_settings
            deadline_days = get_settings().collection_deadline_days

        overdue_packages = self._uow.packages.find_overdue_for_notification(now, deadline_days)
        notified = 0

        for pkg in overdue_packages:
            if not pkg.recipient_id:
                continue
            user = self._uow.users.get(pkg.recipient_id)
            if not user:
                continue

            shelf = pkg.storage_location.code if pkg.storage_location else "Gate No. 2 Storage"
            first_name = user.full_name.split()[0] if user.full_name else "there"
            title = "Overdue package reminder: Gate No. 2"
            message = (
                f"Hey {first_name}, your parcel {pkg.internal_code} ({pkg.courier_name}) has been waiting in rack {shelf} "
                f"at Gate No. 2 for over {deadline_days} days. Please collect it as soon as possible with your pickup code."
            )

            self._uow.notifications.add(
                Notification(
                    user_id=user.id,
                    package_id=pkg.id,
                    channel="in_app",
                    title=title,
                    message=message,
                    delivery_status=NotificationStatus.SENT,
                    sent_at=now,
                )
            )

            for ch in self._channels:
                if ch.channel_type != "in_app":
                    try:
                        ch.send(NotificationRecipient(user.id, user.full_name, user.email), title, message)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Overdue notification via %s failed: %s", ch.channel_type, exc)

            self._uow.packages.record_overdue_notification(pkg.id, now)
            notified += 1

        self._uow.commit()
        return {"checked": len(overdue_packages), "notified": notified}
