"""Composition root: the one place where concrete classes are chosen and wired.

Swapping the allocation strategy or notification channels is a configuration
change here, not an edit to the business services (Open/Closed + DIP).
"""
from collections.abc import Callable

from app.core.config import Settings, get_settings
from app.core.rate_limit import SlidingWindowRateLimiter
from app.domain.allocation import FirstAvailableStrategy, SuitableSizeStrategy
from app.domain.events import EventBus, PackageStatusChanged
from app.domain.interfaces import StorageAllocationStrategy
from app.infrastructure.notifications import channel_factory
from app.repositories.unit_of_work import UnitOfWork
from app.services.notifications import NotificationDispatcher

ALLOCATION_STRATEGIES: dict[str, Callable[[], StorageAllocationStrategy]] = {
    FirstAvailableStrategy.name: FirstAvailableStrategy,
    SuitableSizeStrategy.name: SuitableSizeStrategy,
}


def build_allocation_strategy(name: str) -> StorageAllocationStrategy:
    try:
        return ALLOCATION_STRATEGIES[name]()
    except KeyError as exc:
        raise ValueError(f"Unknown STORAGE_ALLOCATION_STRATEGY '{name}'") from exc


class Container:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.event_bus = EventBus()
        self.dispatcher = NotificationDispatcher(
            channel_factory.create_many(settings.notification_channel_names))
        self.event_bus.subscribe(PackageStatusChanged, self.dispatcher.handle)
        self.allocation_strategy = build_allocation_strategy(settings.storage_allocation_strategy)
        self.login_limiter = SlidingWindowRateLimiter(
            settings.login_rate_limit_attempts, settings.login_rate_limit_window_seconds)

    def uow(self) -> UnitOfWork:
        return UnitOfWork(self.event_bus)


container = Container(get_settings())
