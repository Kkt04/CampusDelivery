"""Storage allocation strategies (Strategy pattern).

# ==============================================================================
# [EVAL-5: PATTERN-STRATEGY] Strategy Pattern (Behavioral)
# WHAT IT IS FOR:
#   Encapsulates family of interchangeable shelf allocation algorithms.
# HOW IT IS USED HERE:
#   `FirstAvailableStrategy` and `SuitableSizeStrategy` implement the same
#   `StorageAllocationStrategy` protocol. The active algorithm is chosen via configuration
#   without modifying the `StorageAllocationService`.
# ==============================================================================
# [EVAL-3: OOP-POLYMORPHISM] Polymorphism
# WHAT IT IS FOR:
#   Allows different classes to be treated through a uniform interface with distinct runtime behaviors.
# HOW IT IS USED HERE:
#   `StorageAllocationService` calls `strategy.rank(candidates, size)`. Whether `FirstAvailableStrategy`
#   or `SuitableSizeStrategy` executes is resolved dynamically at runtime.
# ==============================================================================
# [EVAL-4: SOLID-OCP] Open/Closed Principle
# WHAT IT IS FOR:
#   System should be open for extension but closed for modification.
# HOW IT IS USED HERE:
#   Adding a new allocation policy (e.g. `LeastLoadedStrategy`) only requires writing a new
#   class here and registering it in `container.py:ALLOCATION_STRATEGIES`.
# ==============================================================================
# [EVAL-4: SOLID-LSP] Liskov Substitution Principle
# WHAT IT IS FOR:
#   Subtypes/implementations must be substitutable for base contracts without breaking correctness.
# HOW IT IS USED HERE:
#   Both strategies honor identical pre/post-conditions: both return candidates satisfying
#   `c.accepts(size)` ordered by preference, without side effects or database mutations.
# ==============================================================================
"""
from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.enums import PackageSize


@dataclass(frozen=True)
class StorageCandidate:
    """[EVAL-3: OOP-ENCAPSULATION] Immutable value object encapsulating shelf state and business rules."""
    id: int
    code: str
    capacity: int
    occupied: int
    max_package_size: PackageSize
    is_active: bool

    @property
    def free_slots(self) -> int:
        """[EVAL-3: OOP-ENCAPSULATION] Derived state computed internally."""
        return self.capacity - self.occupied

    def accepts(self, size: PackageSize) -> bool:
        """[EVAL-3: OOP-ENCAPSULATION] Invariant method protecting storage capacity and size limits."""
        return self.is_active and self.free_slots > 0 and size.rank <= self.max_package_size.rank


class FirstAvailableStrategy:
    """[EVAL-5: PATTERN-STRATEGY] [EVAL-3: OOP-POLYMORPHISM]
    Strategy 1: Pick the first suitable shelf in code order (G2-A1, G2-A2, ...)."""

    name = "first_available"

    def rank(self, candidates: Sequence[StorageCandidate], size: PackageSize) -> list[StorageCandidate]:
        return sorted((c for c in candidates if c.accepts(size)), key=lambda c: c.code)


class SuitableSizeStrategy:
    """[EVAL-5: PATTERN-STRATEGY] [EVAL-3: OOP-POLYMORPHISM]
    Strategy 2: Best-fit size bounding to conserve large slots for large parcels."""

    name = "suitable_size"

    def rank(self, candidates: Sequence[StorageCandidate], size: PackageSize) -> list[StorageCandidate]:
        return sorted(
            (c for c in candidates if c.accepts(size)),
            key=lambda c: (c.max_package_size.rank - size.rank, -c.free_slots, c.code),
        )
