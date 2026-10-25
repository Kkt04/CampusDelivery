"""Unit of Work: one persistence session per business use case.

* All repositories share one `Store`, so nothing is written until `commit()`
  flushes the changed fields.
* Domain events are buffered and published only after a successful commit, so
  a notification is never sent for a change that was not stored.

MongoDB note: standalone deployments have no multi-document transactions, so
`rollback()` only discards buffered events; the concurrency guarantees come
from the conditional updates and unique indexes in the repositories.
"""
from types import TracebackType

from app.domain.events import DomainEvent, EventBus
from app.infrastructure.store import Store
from app.repositories.mongo_repos import (
    MongoAuditRepository,
    MongoIdempotencyRepository,
    MongoIncidentRepository,
    MongoNotificationRepository,
    MongoPackageRepository,
    MongoPasswordResetTokenRepository,
    MongoPickupRecordRepository,
    MongoPickupTokenRepository,
    MongoRefreshTokenRepository,
    MongoStorageRepository,
    MongoUserRepository,
)


class UnitOfWork:
    def __init__(self, event_bus: EventBus, store: Store | None = None) -> None:
        self._event_bus = event_bus
        self._events: list[DomainEvent] = []
        self._store = store

    def __enter__(self) -> "UnitOfWork":
        self.session = self._store or Store()
        self.users = MongoUserRepository(self.session)
        self.packages = MongoPackageRepository(self.session)
        self.storage = MongoStorageRepository(self.session)
        self.tokens = MongoPickupTokenRepository(self.session)
        self.pickups = MongoPickupRecordRepository(self.session)
        self.notifications = MongoNotificationRepository(self.session)
        self.incidents = MongoIncidentRepository(self.session)
        self.audit = MongoAuditRepository(self.session)
        self.idempotency = MongoIdempotencyRepository(self.session)
        self.password_resets = MongoPasswordResetTokenRepository(self.session)
        self.refresh_tokens = MongoRefreshTokenRepository(self.session)
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None,
                 tb: TracebackType | None) -> None:
        if exc_type is not None:
            self.rollback()

    def record_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def commit(self) -> None:
        self.session.commit()
        events, self._events = self._events, []
        for event in events:
            self._event_bus.publish(event)

    def rollback(self) -> None:
        self._events.clear()
