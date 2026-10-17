"""Storage allocation strategies (Strategy pattern).

A strategy only *orders* candidate shelves; it never writes to the database.
The StorageAllocationService then tries to reserve each candidate in order
with an atomic conditional UPDATE, so strategies stay simple and race-free.
New policies can be added by writing a class and registering it (Open/Closed).
"""
from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.enums import PackageSize


@dataclass(frozen=True)
class StorageCandidate:
    id: int
    code: str
    capacity: int
    occupied: int
    max_package_size: PackageSize
    is_active: bool

    @property
    def free_slots(self) -> int:
        return self.capacity - self.occupied

    def accepts(self, size: PackageSize) -> bool:
        return self.is_active and self.free_slots > 0 and size.rank <= self.max_package_size.rank


class FirstAvailableStrategy:
    """Pick the first suitable shelf in code order (G2-A1, G2-A2, ...)."""

    name = "first_available"

    def rank(self, candidates: Sequence[StorageCandidate], size: PackageSize) -> list[StorageCandidate]:
        return sorted((c for c in candidates if c.accepts(size)), key=lambda c: c.code)


class SuitableSizeStrategy:
    """Prefer the smallest shelf class that fits, so large bins stay free for
    large parcels. Ties go to the shelf with the most free slots."""

    name = "suitable_size"

    def rank(self, candidates: Sequence[StorageCandidate], size: PackageSize) -> list[StorageCandidate]:
        return sorted(
            (c for c in candidates if c.accepts(size)),
            key=lambda c: (c.max_package_size.rank - size.rank, -c.free_slots, c.code),
        )
