"""Enumerations shared by every layer. Stored in the database as strings."""
from enum import StrEnum


class Role(StrEnum):
    LEARNER = "LEARNER"
    SECURITY = "SECURITY"
    ADMIN = "ADMIN"


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
