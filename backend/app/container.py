"""Composition root: the one place where concrete classes are chosen and wired.

Swapping the allocation strategy or notification channels is a configuration
change here, not an edit to the business services (Open/Closed + DIP).
"""
# ==============================================================================
# [EVAL-4: SOLID-DIP] Dependency Inversion Principle (Composition Root)
# WHAT IT IS FOR:
#   High-level modules (services) do not construct low-level modules (channels,
#   strategies, databases). The Container wires concrete classes to abstractions.
# HOW IT IS USED HERE:
#   Container resolves Settings -> instantiates EventBus, NotificationDispatcher,
#   StorageAllocationStrategy, SlidingWindowRateLimiter -> provides uow() factory.
# ==============================================================================
# [EVAL-5: PATTERN-SINGLETON] Module-Level Singleton Instance
# WHAT IT IS FOR:
#   Ensures a single configured dependency graph exists across request lifecycles.
# HOW IT IS USED HERE:
#   `container = Container(get_settings())` is initialized once at import time.
# VIVA DEFENSE TIP:
#   Module-level singletons in Python avoid the boilerplate of classic GoF Singletons
#   while keeping unit testability intact (tests can instantiate Container directly
#   with custom settings).
# ==============================================================================
# [EVAL-4: SOLID-OCP] Open/Closed Principle
# WHAT IT IS FOR:
#   New allocation strategies or notification channels can be plugged into the
#   system by modifying this dictionary mapping without altering business services.
# ==============================================================================
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
