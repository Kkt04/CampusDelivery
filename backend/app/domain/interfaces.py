"""Small, focused abstractions (Interface Segregation + Dependency Inversion).

Each protocol has only the operations its callers need. Services depend on
these, and concrete classes live in app/domain/allocation.py and
app/infrastructure/notifications.py. Repository protocols are in
app/repositories/interfaces.py.
"""
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from app.domain.allocation import StorageCandidate
from app.domain.enums import NotificationChannelType, PackageSize


class StorageAllocationStrategy(Protocol):
    name: str

    def rank(self, candidates: Sequence[StorageCandidate], size: PackageSize) -> list[StorageCandidate]:
        """Return the usable candidates in order of preference."""
        ...


@dataclass(frozen=True)
class NotificationRecipient:
    user_id: int
    full_name: str
    email: str | None


class NotificationChannel(Protocol):
    channel_type: NotificationChannelType

    def send(self, recipient: NotificationRecipient, title: str, message: str) -> None:
        """Hand the message to the channel. Raise NotificationDeliveryError on failure."""
        ...
