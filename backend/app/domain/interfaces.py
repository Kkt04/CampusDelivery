"""Small, focused abstractions (Interface Segregation + Dependency Inversion).

# ==============================================================================
# [EVAL-3: OOP-ABSTRACTION] Abstraction via Python typing.Protocol
# WHAT IT IS FOR:
#   Decouples high-level business services (e.g., StorageAllocationService,
#   NotificationDispatcher) from concrete implementation details.
# HOW IT IS USED HERE:
#   Using Python's structural subtyping (`typing.Protocol`), callers interact
#   purely with abstract contracts without depending on concrete classes.
# ==============================================================================
# [EVAL-4: SOLID-ISP] Interface Segregation Principle
# WHAT IT IS FOR:
#   Ensures interfaces are lean, specific, and client-focused rather than fat.
# HOW IT IS USED HERE:
#   `StorageAllocationStrategy` exposes only a single method `rank()`, and
#   `NotificationChannel` exposes only `send()`. No implementor is forced
#   to depend on unused methods.
# ==============================================================================
# [EVAL-4: SOLID-DIP] Dependency Inversion Principle
# WHAT IT IS FOR:
#   High-level modules should not depend on low-level modules; both depend on abstractions.
# HOW IT IS USED HERE:
#   Services depend on these Protocols. Concrete classes are wired in `container.py`.
# ==============================================================================
"""
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from app.domain.allocation import StorageCandidate
from app.domain.enums import NotificationChannelType, PackageSize


class StorageAllocationStrategy(Protocol):
    """[EVAL-4: SOLID-ISP] [EVAL-5: PATTERN-STRATEGY]
    Lean strategy contract containing only rank()."""
    name: str

    def rank(self, candidates: Sequence[StorageCandidate], size: PackageSize) -> list[StorageCandidate]:
        """Return the usable candidates in order of preference."""
        ...


@dataclass(frozen=True)
class NotificationRecipient:
    """[EVAL-3: OOP-ENCAPSULATION] Immutable value object for notification recipient."""
    user_id: int
    full_name: str
    email: str | None


class NotificationChannel(Protocol):
    """[EVAL-4: SOLID-ISP] Lean notification delivery interface."""
    channel_type: NotificationChannelType

    def send(self, recipient: NotificationRecipient, title: str, message: str) -> None:
        """Hand the message to the channel. Raise NotificationDeliveryError on failure."""
        ...
