"""Unit of Work: one database transaction per business use case.

* All repositories share one Session, so a use case commits or rolls back as a whole.
* Domain events are buffered and published only after a successful commit, so
  a notification is never sent for a change that was rolled back, and a
  failing notification can never undo a committed change.
"""
from collections.abc import Callable
from types import TracebackType

from sqlalchemy.orm import Session

from app.domain.events import DomainEvent, EventBus
from app.repositories.sqlalchemy_repos import (
    SqlAuditRepository,
    SqlIdempotencyRepository,
    SqlIncidentRepository,
    SqlNotificationRepository,
    SqlPackageRepository,
    SqlPickupRecordRepository,
    SqlPickupTokenRepository,
    SqlStorageRepository,
    SqlUserRepository,
)


class UnitOfWork:
    def __init__(self, session_factory: Callable[[], Session], event_bus: EventBus) -> None:
        self._session_factory = session_factory
        self._event_bus = event_bus
        self._events: list[DomainEvent] = []

    def __enter__(self) -> "UnitOfWork":
        self.session = self._session_factory()
        self.users = SqlUserRepository(self.session)
        self.packages = SqlPackageRepository(self.session)
        self.storage = SqlStorageRepository(self.session)
        self.tokens = SqlPickupTokenRepository(self.session)
        self.pickups = SqlPickupRecordRepository(self.session)
        self.notifications = SqlNotificationRepository(self.session)
        self.incidents = SqlIncidentRepository(self.session)
        self.audit = SqlAuditRepository(self.session)
        self.idempotency = SqlIdempotencyRepository(self.session)
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None,
                 tb: TracebackType | None) -> None:
        if exc_type is not None:
            self.rollback()
        self.session.close()

    def record_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def commit(self) -> None:
        self.session.commit()
        events, self._events = self._events, []
        for event in events:
            self._event_bus.publish(event)

    def rollback(self) -> None:
        self.session.rollback()
        self._events.clear()
