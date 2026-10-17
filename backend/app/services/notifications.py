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

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.time import utcnow
from app.domain.enums import NotificationStatus, PackageStatus
from app.domain.events import DomainEvent, PackageStatusChanged
from app.domain.interfaces import NotificationChannel, NotificationRecipient
from app.infrastructure.models import Notification, Package, User
from app.repositories.filters import Page
from app.repositories.sqlalchemy_repos import SqlNotificationRepository
from app.repositories.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)

Template = Callable[[PackageStatusChanged, Package], tuple[str, str] | None]


def _arrived(event: PackageStatusChanged, pkg: Package) -> tuple[str, str] | None:
    if event.from_status in {PackageStatus.RECEIVED, PackageStatus.UNIDENTIFIED}:
        return ("Package arrived",
                f"A {pkg.courier_name} package ({pkg.internal_code}) arrived at Gate No. 2. "
                "We will tell you when it is ready for pickup.")
    return None


# Which lifecycle events produce a learner message (extend here; workflow code is untouched).
TEMPLATES: dict[PackageStatus, Template] = {
    PackageStatus.VERIFIED: _arrived,
    PackageStatus.READY_FOR_PICKUP: lambda e, p: (
        "Ready for pickup",
        f"Your {p.courier_name} package {p.internal_code} is ready at Gate No. 2. "
        "Open the app to get your pickup code."),
    PackageStatus.COLLECTED: lambda e, p: (
        "Package collected", f"Package {p.internal_code} was handed over to you. Thank you."),
    PackageStatus.DAMAGED: lambda e, p: (
        "Package arrived damaged",
        f"Package {p.internal_code} arrived damaged and is held at Gate No. 2 while staff review it."),
    PackageStatus.RETURN_REQUESTED: lambda e, p: (
        "Package being returned", f"Package {p.internal_code} will be returned to {p.courier_name}."),
    PackageStatus.LOST: lambda e, p: (
        "Package reported lost", f"Package {p.internal_code} could not be located. Operations will contact you."),
}


class NotificationDispatcher:
    def __init__(self, session_factory: Callable[[], Session], channels: list[NotificationChannel],
                 templates: dict[PackageStatus, Template] | None = None) -> None:
        self._session_factory = session_factory
        self.channels = channels
        self._templates = templates or TEMPLATES

    def handle(self, event: DomainEvent) -> None:
        if not isinstance(event, PackageStatusChanged) or event.recipient_id is None:
            return
        template = self._templates.get(event.to_status)
        if template is None:
            return
        with self._session_factory() as session:
            package = session.get(Package, event.package_id)
            user = session.get(User, event.recipient_id)
            if package is None or user is None or (rendered := template(event, package)) is None:
                return
            title, message = rendered
            rows = [Notification(user_id=user.id, package_id=package.id, channel=ch.channel_type, title=title,
                                 message=message, delivery_status=NotificationStatus.PENDING)
                    for ch in self.channels]
            session.add_all(rows)
            session.commit()  # the record exists even if every channel fails below
            for channel, row in zip(self.channels, rows):
                self.attempt(channel, row, user)
            session.commit()

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

    def retry(self, session: Session, max_attempts: int) -> dict[str, int]:
        by_type = {ch.channel_type: ch for ch in self.channels}
        result = {"retried": 0, "sent": 0, "failed": 0, "skipped": 0}
        for row in SqlNotificationRepository(session).retryable(max_attempts):
            channel = by_type.get(row.channel)
            user = session.get(User, row.user_id)
            if channel is None or user is None:
                result["skipped"] += 1
                continue
            self.attempt(channel, row, user)
            result["retried"] += 1
            result["sent" if row.delivery_status == NotificationStatus.SENT else "failed"] += 1
        session.commit()
        return result


class NotificationService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

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
