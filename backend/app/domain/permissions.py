"""Role-based access control. Roles are data, permissions are a lookup table.

We use one `User` model with a `role` value (composition) instead of
Learner/SecurityStaff/Admin subclasses: the roles share every attribute and
differ only in what they may do, which a permission table expresses directly.
"""
from enum import StrEnum

from app.domain.enums import Role


class Permission(StrEnum):
    PACKAGE_VIEW_OWN = "package:view_own"
    PACKAGE_VIEW_ALL = "package:view_all"
    PACKAGE_REQUEST_RETURN = "package:request_return"
    PACKAGE_REGISTER = "package:register"
    PACKAGE_MANAGE = "package:manage"  # storage, recipient, lifecycle transitions
    PICKUP_REQUEST = "pickup:request"
    PICKUP_HANDOVER = "pickup:handover"
    PICKUP_HISTORY_ALL = "pickup:history_all"
    LEARNER_SEARCH = "learner:search"
    STORAGE_VIEW = "storage:view"
    STORAGE_MANAGE = "storage:manage"
    USER_MANAGE = "user:manage"
    INCIDENT_REPORT = "incident:report"
    INCIDENT_VIEW_ALL = "incident:view_all"
    INCIDENT_RESOLVE = "incident:resolve"
    REPORT_VIEW = "report:view"
    AUDIT_VIEW = "audit:view"
    NOTIFICATION_ADMIN = "notification:admin"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.LEARNER: frozenset(
        {Permission.PACKAGE_VIEW_OWN, Permission.PICKUP_REQUEST, Permission.PACKAGE_REQUEST_RETURN,
         Permission.INCIDENT_REPORT}
    ),
    Role.SECURITY: frozenset(
        {
            Permission.PACKAGE_VIEW_ALL,
            Permission.PACKAGE_REGISTER,
            Permission.PACKAGE_MANAGE,
            Permission.PICKUP_HANDOVER,
            Permission.PICKUP_HISTORY_ALL,
            Permission.LEARNER_SEARCH,
            Permission.STORAGE_VIEW,
            Permission.INCIDENT_REPORT,
            Permission.INCIDENT_VIEW_ALL,
        }
    ),
    Role.ADMIN: frozenset(
        {
            Permission.PACKAGE_VIEW_ALL,
            Permission.PACKAGE_REGISTER,
            Permission.PACKAGE_MANAGE,
            Permission.PICKUP_HISTORY_ALL,
            Permission.LEARNER_SEARCH,
            Permission.STORAGE_VIEW,
            Permission.STORAGE_MANAGE,
            Permission.USER_MANAGE,
            Permission.INCIDENT_REPORT,
            Permission.INCIDENT_VIEW_ALL,
            Permission.INCIDENT_RESOLVE,
            Permission.REPORT_VIEW,
            Permission.AUDIT_VIEW,
            Permission.NOTIFICATION_ADMIN,
        }
    ),
}


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def can_view_package(role: Role, viewer_id: int, recipient_id: int | None) -> bool:
    """Staff see every package; a learner sees only packages addressed to them."""
    if has_permission(role, Permission.PACKAGE_VIEW_ALL):
        return True
    return has_permission(role, Permission.PACKAGE_VIEW_OWN) and recipient_id == viewer_id
