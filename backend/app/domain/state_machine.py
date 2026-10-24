"""Explicit package lifecycle state machine (State pattern, table-driven form).

Every allowed status change is a `Transition` object that names the source and
target status, the roles allowed to perform it, an optional guard (precondition)
and a human-readable action. Anything not in the table is rejected. Services
never assign `package.status` directly; they go through this class.
"""
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from app.core.exceptions import InvalidTransitionError, PermissionDeniedError
from app.domain.enums import PackageStatus as S
from app.domain.enums import Role


@dataclass(frozen=True)
class PackageContext:
    """Facts about a package that guards need. Keeps the machine DB-independent."""

    has_recipient: bool
    has_storage: bool


Guard = Callable[[PackageContext], str | None]  # returns a failure reason, or None


def needs_recipient(ctx: PackageContext) -> str | None:
    return None if ctx.has_recipient else "a recipient learner must be identified first"


def needs_no_recipient(ctx: PackageContext) -> str | None:
    return None if not ctx.has_recipient else "package already has a recipient"


def needs_storage(ctx: PackageContext) -> str | None:
    return None if ctx.has_storage else "a storage location must be assigned first"


def needs_recipient_and_storage(ctx: PackageContext) -> str | None:
    return needs_recipient(ctx) or needs_storage(ctx)


def needs_recipient_without_storage(ctx: PackageContext) -> str | None:
    if reason := needs_recipient(ctx):
        return reason
    return "package already has storage; it moves to STORED instead" if ctx.has_storage else None


@dataclass(frozen=True)
class Transition:
    source: S
    target: S
    roles: frozenset[Role]
    action: str
    label: str
    guard: Guard | None = None
    requires_dedicated_endpoint: bool = False  # e.g. pickup needs a code, store needs a shelf


STAFF = frozenset({Role.SECURITY, Role.ADMIN})
ADMIN = frozenset({Role.ADMIN})
SECURITY = frozenset({Role.SECURITY})
LEARNER = frozenset({Role.LEARNER})
# A learner may ask for their own package to go back to the courier while it is still on campus.
ADMIN_OR_LEARNER = frozenset({Role.ADMIN, Role.LEARNER})


def _t(source, target, roles, action, label, guard=None, dedicated=False) -> Transition:
    return Transition(source, target, roles, action, label, guard, dedicated)


TRANSITIONS: tuple[Transition, ...] = (
    # Intake validation (performed automatically when security registers a package)
    _t(S.RECEIVED, S.VERIFIED, STAFF, "verify", "Verify", needs_recipient),
    _t(S.RECEIVED, S.UNIDENTIFIED, STAFF, "mark_unidentified", "Mark unidentified", needs_no_recipient),
    _t(S.RECEIVED, S.DAMAGED, STAFF, "mark_damaged", "Hold as damaged"),
    # Unidentified workflow
    _t(S.UNIDENTIFIED, S.VERIFIED, STAFF, "identify_recipient", "Identify recipient",
       needs_recipient_without_storage, dedicated=True),
    _t(S.UNIDENTIFIED, S.STORED, STAFF, "identify_recipient", "Identify recipient",
       needs_recipient_and_storage, dedicated=True),
    _t(S.UNIDENTIFIED, S.UNDER_INVESTIGATION, STAFF, "investigate", "Open investigation"),
    _t(S.UNIDENTIFIED, S.RETURN_REQUESTED, ADMIN, "request_return", "Request return to courier"),
    # Damage hold
    _t(S.DAMAGED, S.VERIFIED, STAFF, "release_damage_hold", "Release damage hold",
       needs_recipient_without_storage),
    _t(S.DAMAGED, S.STORED, STAFF, "release_damage_hold", "Release damage hold",
       needs_recipient_and_storage),
    _t(S.DAMAGED, S.UNDER_INVESTIGATION, STAFF, "investigate", "Open investigation"),
    _t(S.DAMAGED, S.RETURN_REQUESTED, STAFF, "request_return", "Request return to courier"),
    # Happy path
    _t(S.VERIFIED, S.STORED, STAFF, "store", "Assign storage", needs_storage, dedicated=True),
    _t(S.VERIFIED, S.UNDER_INVESTIGATION, STAFF, "investigate", "Open investigation"),
    _t(S.STORED, S.READY_FOR_PICKUP, STAFF, "mark_ready", "Mark ready for pickup",
       needs_recipient_and_storage),
    _t(S.READY_FOR_PICKUP, S.PICKUP_REQUESTED, LEARNER, "request_pickup", "Request pickup",
       needs_recipient, dedicated=True),
    _t(S.PICKUP_REQUESTED, S.COLLECTED, SECURITY, "complete_handover", "Complete handover",
       needs_recipient, dedicated=True),
    # Exceptions while waiting for collection
    *(
        _t(src, S.UNDER_INVESTIGATION, STAFF, "investigate", "Open investigation")
        for src in (S.STORED, S.READY_FOR_PICKUP, S.PICKUP_REQUESTED)
    ),
    *(
        _t(src, S.RETURN_REQUESTED, ADMIN_OR_LEARNER, "request_return", "Request return to courier")
        for src in (S.VERIFIED, S.STORED, S.READY_FOR_PICKUP, S.PICKUP_REQUESTED)
    ),
    # Investigation outcomes
    _t(S.UNDER_INVESTIGATION, S.STORED, ADMIN, "resolve_investigation", "Resolve: back to storage",
       needs_recipient_and_storage),
    _t(S.UNDER_INVESTIGATION, S.VERIFIED, ADMIN, "resolve_investigation", "Resolve: awaiting storage",
       needs_recipient_without_storage),
    _t(S.UNDER_INVESTIGATION, S.UNIDENTIFIED, ADMIN, "resolve_investigation", "Resolve: unidentified",
       needs_no_recipient),
    _t(S.UNDER_INVESTIGATION, S.LOST, ADMIN, "mark_lost", "Mark lost"),
    _t(S.UNDER_INVESTIGATION, S.RETURN_REQUESTED, ADMIN, "request_return", "Request return to courier"),
    # Return to courier
    _t(S.RETURN_REQUESTED, S.RETURNED, STAFF, "complete_return", "Hand back to courier"),
)


class PackageStateMachine:
    def __init__(self, transitions: Iterable[Transition] = TRANSITIONS) -> None:
        self._by_edge: dict[tuple[S, S], Transition] = {}
        for transition in transitions:
            edge = (transition.source, transition.target)
            if edge in self._by_edge:
                raise ValueError(f"duplicate transition {edge}")
            self._by_edge[edge] = transition

    def find(self, source: S, target: S) -> Transition | None:
        return self._by_edge.get((source, target))

    def check(self, source: S, target: S, role: Role, ctx: PackageContext) -> Transition:
        """Return the transition if allowed, otherwise raise a meaningful error."""
        transition = self.find(source, target)
        if transition is None:
            raise InvalidTransitionError(
                f"A package cannot move from {source.value} to {target.value}",
                details={"from": source.value, "to": target.value},
            )
        if role not in transition.roles:
            raise PermissionDeniedError(
                f"Role {role.value} may not perform '{transition.action}'",
            )
        if transition.guard and (reason := transition.guard(ctx)):
            raise InvalidTransitionError(
                f"Cannot {transition.label.lower()}: {reason}",
                code="TRANSITION_PRECONDITION_FAILED",
            )
        return transition

    def available(self, source: S, role: Role, ctx: PackageContext) -> list[Transition]:
        """Transitions this role can perform right now (used to drive UI buttons)."""
        return [
            t
            for (src, _), t in self._by_edge.items()
            if src == source and role in t.roles and not (t.guard and t.guard(ctx))
        ]

    def targets_from(self, source: S) -> set[S]:
        return {tgt for (src, tgt) in self._by_edge if src == source}


state_machine = PackageStateMachine()
