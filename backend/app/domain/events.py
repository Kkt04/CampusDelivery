"""Domain events and a minimal in-process event bus (Observer pattern).

Services record events; the Unit of Work publishes them only AFTER the
database transaction commits. Each subscriber runs in isolation: if one
fails (e.g. email is down), the error is logged and the already-committed
package update is unaffected.
"""
# ==============================================================================
# [EVAL-5: PATTERN-OBSERVER] Observer Pattern (Publisher-Subscriber)
# WHAT IT IS FOR:
#   Decouples event producers (services mutating domain entities) from consumers
#   (notification dispatchers, audit loggers, analytics) so neither side depends
#   on the other's concrete implementation.
# HOW IT IS USED HERE:
#   EventBus is the Subject/Publisher maintaining a registry of Callables grouped
#   by DomainEvent subclass. Domain services push events into UnitOfWork.events;
#   on uow.commit(), the bus dispatches each event to all registered handlers.
# VIVA DEFENSE TIP:
#   Each subscriber runs inside a try/except block. If notification dispatch fails
#   (e.g., SMTP server down), the domain operation remains committed and durable.
# ==============================================================================
import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from app.core.time import utcnow
from app.domain.enums import PackageStatus

logger = logging.getLogger(__name__)


# ==============================================================================
# [EVAL-3: OOP-INHERITANCE] Base DomainEvent and Specific Event Subclasses
# WHAT IT IS FOR:
#   Provides a common contract (occurred_at timestamp) across all system events.
# HOW IT IS USED HERE:
#   DomainEvent is the base class inherited by PackageStatusChanged. Additional
#   events (e.g. StorageAllocated, TokenGenerated) extend DomainEvent without
#   changing EventBus publishing logic.
# ==============================================================================
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
        """Register an observer callback for a specific event type."""
        self._handlers[event_type].append(handler)

    def publish(self, event: DomainEvent) -> None:
        """Notify all registered observers. Exceptions in handlers are caught and logged."""
        for handler in self._handlers[type(event)]:
            try:
                handler(event)
            except Exception:  # noqa: BLE001 - subscribers must never break the publisher
                logger.exception("Event handler %r failed for %s", handler, type(event).__name__)
