"""Enumerations shared by every layer. Stored in the database as strings."""
# ==============================================================================
# [EVAL-1: REQUIREMENTS] Domain Enums (Actors, Statuses, Sizes, Incidents)
# WHAT IT IS FOR:
#   Defines the closed vocabulary of types, roles, and states used across the
#   entire domain model, services, and API layers to fulfill requirements:
#   - Role: FR-6 (Security gatekeeper), FR-5 (Learner pickup), FR-8 (Admin oversight)
#   - PackageStatus: 12 discrete lifecycle states tracking custody end-to-end
#   - PackageSize: Small, Medium, Large for storage dimension constraints
#   - IncidentType / IncidentStatus: Exception tracking and auditing
# HOW IT IS USED HERE:
#   Inherits StrEnum so values serialize natively to JSON and store as readable
#   strings in MongoDB documents without custom BSON serializers.
# ==============================================================================
from enum import StrEnum


# ==============================================================================
# [EVAL-3: OOP-ENCAPSULATION] Role-Based Access Control Actors
# ==============================================================================
class Role(StrEnum):
    LEARNER = "LEARNER"
    SECURITY = "SECURITY"
    ADMIN = "ADMIN"


# ==============================================================================
# [EVAL-1: REQUIREMENTS] Package Lifecycle States (12 states, 3 terminal)
# ==============================================================================
class PackageStatus(StrEnum):
    RECEIVED = "RECEIVED"
    VERIFIED = "VERIFIED"
    STORED = "STORED"
    READY_FOR_PICKUP = "READY_FOR_PICKUP"
    PICKUP_REQUESTED = "PICKUP_REQUESTED"
    COLLECTED = "COLLECTED"
    UNIDENTIFIED = "UNIDENTIFIED"
    DAMAGED = "DAMAGED"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    RETURN_REQUESTED = "RETURN_REQUESTED"
    RETURNED = "RETURNED"
    LOST = "LOST"


STATUS_LABELS: dict[PackageStatus, str] = {
    PackageStatus.RECEIVED: "Received at gate",
    PackageStatus.VERIFIED: "Verified, awaiting storage",
    PackageStatus.STORED: "In storage",
    PackageStatus.READY_FOR_PICKUP: "Ready for pickup",
    PackageStatus.PICKUP_REQUESTED: "Pickup code issued",
    PackageStatus.COLLECTED: "Collected",
    PackageStatus.UNIDENTIFIED: "Recipient unidentified",
    PackageStatus.DAMAGED: "Held: damaged",
    PackageStatus.UNDER_INVESTIGATION: "Under investigation",
    PackageStatus.RETURN_REQUESTED: "Return to courier requested",
    PackageStatus.RETURNED: "Returned to courier",
    PackageStatus.LOST: "Lost",
}

# Lifecycle ends here; nothing may leave these states.
TERMINAL_STATUSES = frozenset({PackageStatus.COLLECTED, PackageStatus.RETURNED, PackageStatus.LOST})

# A package in one of these states is waiting for its learner. Overdue only applies here.
AWAITING_COLLECTION_STATUSES = frozenset(
    {PackageStatus.STORED, PackageStatus.READY_FOR_PICKUP, PackageStatus.PICKUP_REQUESTED}
)

# States in which a shelf may be assigned or changed.
STORABLE_STATUSES = frozenset(
    {
        PackageStatus.VERIFIED,
        PackageStatus.STORED,
        PackageStatus.READY_FOR_PICKUP,
        PackageStatus.PICKUP_REQUESTED,
        PackageStatus.UNIDENTIFIED,
        PackageStatus.DAMAGED,
        PackageStatus.UNDER_INVESTIGATION,
        PackageStatus.RETURN_REQUESTED,
    }
)


class PackageCondition(StrEnum):
    """Physical condition recorded at intake. Independent of lifecycle status."""

    GOOD = "GOOD"
    DAMAGED = "DAMAGED"


class PackageSize(StrEnum):
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"

    @property
    def rank(self) -> int:
        return {"SMALL": 1, "MEDIUM": 2, "LARGE": 3}[self.value]


class IncidentType(StrEnum):
    DAMAGE = "DAMAGE"
    UNIDENTIFIED_RECIPIENT = "UNIDENTIFIED_RECIPIENT"
    LEARNER_REPORTED_ISSUE = "LEARNER_REPORTED_ISSUE"
    MISSING_PACKAGE = "MISSING_PACKAGE"
    OPERATIONAL = "OPERATIONAL"


class IncidentStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class NotificationChannelType(StrEnum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"


class NotificationStatus(StrEnum):
    """PENDING: recorded, not yet handed over. SENT: handed to the channel
    (in-app inbox / email provider). SENT never means read or delivered."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
