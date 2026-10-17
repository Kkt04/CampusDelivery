import pytest

from app.core.exceptions import InvalidTransitionError, PermissionDeniedError
from app.domain.enums import TERMINAL_STATUSES, PackageStatus as S, Role
from app.domain.state_machine import TRANSITIONS, PackageContext, PackageStateMachine, Transition, state_machine

FULL = PackageContext(has_recipient=True, has_storage=True)
NO_STORAGE = PackageContext(has_recipient=True, has_storage=False)
NO_RECIPIENT = PackageContext(has_recipient=False, has_storage=False)


def test_happy_path_is_allowed_for_the_right_roles():
    state_machine.check(S.RECEIVED, S.VERIFIED, Role.SECURITY, NO_STORAGE)
    state_machine.check(S.VERIFIED, S.STORED, Role.SECURITY, FULL)
    state_machine.check(S.STORED, S.READY_FOR_PICKUP, Role.SECURITY, FULL)
    state_machine.check(S.READY_FOR_PICKUP, S.PICKUP_REQUESTED, Role.LEARNER, FULL)
    state_machine.check(S.PICKUP_REQUESTED, S.COLLECTED, Role.SECURITY, FULL)


def test_skipping_steps_is_rejected():
    with pytest.raises(InvalidTransitionError):
        state_machine.check(S.RECEIVED, S.COLLECTED, Role.SECURITY, FULL)
    with pytest.raises(InvalidTransitionError):
        state_machine.check(S.STORED, S.COLLECTED, Role.SECURITY, FULL)


def test_collected_package_can_never_become_ready_again():
    with pytest.raises(InvalidTransitionError):
        state_machine.check(S.COLLECTED, S.READY_FOR_PICKUP, Role.ADMIN, FULL)


@pytest.mark.parametrize("terminal", sorted(TERMINAL_STATUSES))
def test_terminal_states_have_no_exits(terminal):
    assert state_machine.targets_from(terminal) == set()


def test_wrong_role_is_rejected():
    with pytest.raises(PermissionDeniedError):
        state_machine.check(S.READY_FOR_PICKUP, S.PICKUP_REQUESTED, Role.SECURITY, FULL)
    with pytest.raises(PermissionDeniedError):
        state_machine.check(S.STORED, S.READY_FOR_PICKUP, Role.LEARNER, FULL)
    with pytest.raises(PermissionDeniedError):  # handover is a gate (security) action
        state_machine.check(S.PICKUP_REQUESTED, S.COLLECTED, Role.ADMIN, FULL)


def test_guards_enforce_preconditions():
    with pytest.raises(InvalidTransitionError) as err:
        state_machine.check(S.VERIFIED, S.STORED, Role.SECURITY, NO_STORAGE)
    assert err.value.code == "TRANSITION_PRECONDITION_FAILED"
    with pytest.raises(InvalidTransitionError):
        state_machine.check(S.RECEIVED, S.VERIFIED, Role.SECURITY, NO_RECIPIENT)
    with pytest.raises(InvalidTransitionError):
        state_machine.check(S.RECEIVED, S.UNIDENTIFIED, Role.SECURITY, NO_STORAGE)


def test_available_actions_respect_role_and_guards():
    learner_actions = {t.action for t in state_machine.available(S.READY_FOR_PICKUP, Role.LEARNER, FULL)}
    assert learner_actions == {"request_pickup", "request_return"}
    security_actions = {t.target for t in state_machine.available(S.UNIDENTIFIED, Role.SECURITY, NO_RECIPIENT)}
    assert S.RETURN_REQUESTED not in security_actions  # admin only
    assert S.VERIFIED not in security_actions  # guard: no recipient yet


def test_every_status_is_reachable_and_table_has_no_duplicates():
    targets = {t.target for t in TRANSITIONS} | {S.RECEIVED}
    assert targets == set(S)
    with pytest.raises(ValueError):
        PackageStateMachine([TRANSITIONS[0], Transition(S.RECEIVED, S.VERIFIED, frozenset(), "x", "x")])
