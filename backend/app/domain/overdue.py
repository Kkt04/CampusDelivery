"""Overdue is derived, never stored.

A package is overdue when it is still waiting for its learner (STORED,
READY_FOR_PICKUP or PICKUP_REQUESTED) and arrived more than the configured
number of days ago. It does not change the lifecycle status: an overdue
package is still physically on the shelf and may still be collected.
"""
from datetime import datetime, timedelta

from app.domain.enums import AWAITING_COLLECTION_STATUSES, PackageStatus


def overdue_cutoff(now: datetime, deadline_days: int) -> datetime:
    return now - timedelta(days=deadline_days)


def is_overdue(status: PackageStatus, arrived_at: datetime, now: datetime, deadline_days: int) -> bool:
    return status in AWAITING_COLLECTION_STATUSES and arrived_at < overdue_cutoff(now, deadline_days)
