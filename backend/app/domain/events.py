"""Domain events and a minimal in-process event bus (Observer pattern).

Services record events; the Unit of Work publishes them only AFTER the
database transaction commits. Each subscriber runs in isolation: if one
fails (e.g. email is down), the error is logged and the already-committed
package update is unaffected.
"""
import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from app.core.time import utcnow
from app.domain.enums import PackageStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DomainEvent:
    occurred_at: datetime = field(default_factory=utcnow, kw_only=True)


@dataclass(frozen=True)
class PackageStatusChanged(DomainEvent):
    package_id: int
    internal_code: str
    recipient_id: int | None
    from_status: PackageStatus | None
    to_status: PackageStatus


Handler = Callable[[DomainEvent], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers[type(event)]:
            try:
                handler(event)
            except Exception:  # noqa: BLE001 - subscribers must never break the publisher
                logger.exception("Event handler %r failed for %s", handler, type(event).__name__)
