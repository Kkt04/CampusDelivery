"""Use cases: request a pickup code, verify it, and complete the handover.

Double-collection protection (defence in depth):
1. `SELECT ... FOR UPDATE` on the package row serialises concurrent handovers.
2. The token is consumed with a conditional UPDATE (`WHERE used_at IS NULL`).
3. The status changes with a conditional UPDATE (`WHERE status = 'PICKUP_REQUESTED'`).
4. `pickup_records.package_id` is UNIQUE, so a second record can never be stored.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta

from pymongo.errors import DuplicateKeyError as IntegrityError

from app.core.config import Settings
from app.core.exceptions import AlreadyCollectedError, InvalidTransitionError, NotFoundError, PickupCodeError
from app.core.security import generate_pickup_code, generate_salt, hash_pickup_code, pickup_code_matches
from app.core.time import utcnow
from app.domain.enums import PackageStatus
from app.domain.pickup_rules import TokenState, ensure_token_usable
from app.infrastructure.models import Package, PickupRecord, PickupToken, User
from app.repositories.filters import Page
from app.repositories.unit_of_work import UnitOfWork
from app.services.audit import AuditService
from app.services.idempotency import IdempotencyGuard, fingerprint
from app.services.transitions import PackageTransitioner

_COUNTED_FAILURES = {"PICKUP_CODE_INVALID", "PICKUP_WRONG_RECIPIENT"}


@dataclass(frozen=True)
class IssuedPickupCode:
    package: Package
    code: str  # plaintext: returned to the learner once, never stored
    expires_at: datetime


class PickupService:
    SCOPE = "pickup.complete"

    def __init__(self, uow: UnitOfWork, settings: Settings) -> None:
        self._uow = uow
        self._settings = settings
        self._audit = AuditService(uow.audit)
        self._transitioner = PackageTransitioner(uow)
        self._idempotency = IdempotencyGuard(uow.idempotency)

    # ---- learner -----------------------------------------------------------
    def request_pickup(self, *, package_id: int, learner: User) -> IssuedPickupCode:
        """Safe to retry: every call issues a fresh code and revokes the previous one."""
        package = self._uow.packages.get_for_update(package_id)
        if package is None or package.recipient_id != learner.id:
            raise NotFoundError("Package not found")  # never reveal other learners' packages
        if package.status == PackageStatus.COLLECTED:
            raise AlreadyCollectedError("This package has already been collected.")
        if package.status == PackageStatus.READY_FOR_PICKUP:
            self._transitioner.apply(package, PackageStatus.PICKUP_REQUESTED, learner, "Learner requested pickup")
        elif package.status != PackageStatus.PICKUP_REQUESTED:
            raise InvalidTransitionError("Pickup can be requested once the package is ready for pickup.",
                                         code="PICKUP_NOT_AVAILABLE")

        now = utcnow()
        revoked = self._uow.tokens.revoke_active(package.id, now)
        code, salt = generate_pickup_code(), generate_salt()
        expires_at = now + timedelta(minutes=self._settings.pickup_code_ttl_minutes)
        token = self._uow.tokens.add(PickupToken(
            package_id=package.id, learner_id=learner.id, salt=salt,
            code_hash=hash_pickup_code(code, salt), expires_at=expires_at, created_at=now))
        self._audit.record(learner, "pickup.code_issued", "package", package.id,
                           {"token_id": token.id, "revoked_previous": revoked, "expires_at": expires_at.isoformat()})
        self._uow.commit()
        return IssuedPickupCode(package=package, code=code, expires_at=expires_at)

    # ---- security staff ----------------------------------------------------
    def verify(self, *, package_code: str, learner_institutional_id: str, code: str, actor: User) -> Package:
        """Check a code without handing over. Wrong codes still count as attempts."""
        package = self._locked_package(package_code)
        self._check_code(package, learner_institutional_id, code, actor)
        self._uow.rollback()  # nothing to change; release the lock
        return package

    def complete(self, *, package_code: str, learner_institutional_id: str, code: str, actor: User,
                 idempotency_key: str | None = None) -> tuple[PickupRecord, bool]:
        request_hash = fingerprint({"package": package_code.strip().upper(),
                                    "learner": learner_institutional_id.strip().upper(), "code": code})
        package = self._locked_package(package_code)
        if (record_id := self._idempotency.find(actor.id, self.SCOPE, idempotency_key, request_hash)):
            return self._uow.pickups.get(record_id), True

        token = self._check_code(package, learner_institutional_id, code, actor)
        now = utcnow()
        if not self._uow.tokens.mark_used(token.id, now):
            raise AlreadyCollectedError("This pickup code has just been used by another request.")
        location_code = package.storage_location.code if package.storage_location else None
        self._transitioner.apply(package, PackageStatus.COLLECTED, actor, "Handed over at Gate No. 2")
        record = self._uow.pickups.add(PickupRecord(
            package_id=package.id, learner_id=token.learner_id, handed_over_by_id=actor.id,
            token_id=token.id, storage_location_code=location_code, collected_at=now))
        self._idempotency.remember(actor.id, self.SCOPE, idempotency_key, request_hash, record.id)
        self._audit.record(actor, "pickup.completed", "package", package.id,
                           {"pickup_record_id": record.id, "learner_id": token.learner_id,
                            "storage_location": location_code})
        try:
            self._uow.commit()
        except IntegrityError:
            self._uow.rollback()
            if (record_id := self._idempotency.find(actor.id, self.SCOPE, idempotency_key, request_hash)):
                return self._uow.pickups.get(record_id), True
            raise AlreadyCollectedError("This package has already been collected.") from None
        return record, False

    def history(self, *, learner_id: int | None, page: int, page_size: int) -> Page[PickupRecord]:
        return self._uow.pickups.list_records(learner_id, page, page_size)

    # ---- helpers -----------------------------------------------------------
    def _locked_package(self, package_code: str) -> Package:
        package = self._uow.packages.get_by_code_for_update(package_code)
        if package is None:
            raise NotFoundError(f"No package with code {package_code.strip().upper()}")
        return package

    def _check_code(self, package: Package, learner_institutional_id: str, code: str,
                    actor: User) -> PickupToken:
        if package.status == PackageStatus.COLLECTED:
            raise AlreadyCollectedError("This package has already been collected.")
        if package.status != PackageStatus.PICKUP_REQUESTED:
            raise InvalidTransitionError(
                f"Package is {package.status.value}; it can only be handed over after the learner requests pickup.",
                code="PICKUP_NOT_REQUESTED")
        token = self._uow.tokens.latest_for_package(package.id)
        try:
            ensure_token_usable(
                TokenState(token.learner_id, token.expires_at, token.used_at, token.revoked_at,
                           token.failed_attempts) if token else None,
                now=utcnow(), max_attempts=self._settings.pickup_code_max_attempts,
                expected_learner_id=package.recipient_id)
            recipient = package.recipient
            if recipient is None or recipient.institutional_id.upper() != learner_institutional_id.strip().upper():
                raise PickupCodeError("The learner ID does not match this package's recipient.",
                                      code="PICKUP_WRONG_RECIPIENT")
            if not pickup_code_matches(code, token.salt, token.code_hash):
                raise PickupCodeError("Incorrect pickup code.", code="PICKUP_CODE_INVALID")
        except PickupCodeError as error:
            # A concurrent handover already consumed the code, so the package was collected.
            if error.code == "PICKUP_CODE_USED":
                raise AlreadyCollectedError("This package has already been collected.") from None
            # Persist the failed attempt even though the request is rejected.
            if token is not None and error.code in _COUNTED_FAILURES:
                self._uow.tokens.increment_failed_attempts(token.id)
            self._audit.record(actor, "pickup.verification_failed", "package", package.id,
                               {"reason": error.code, "learner_id_entered": learner_institutional_id})
            self._uow.commit()
            raise
        return token
