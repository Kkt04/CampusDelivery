"""Pure validation rules for pickup tokens (no database access)."""
from dataclasses import dataclass
from datetime import datetime

from app.core.exceptions import PickupCodeError


@dataclass(frozen=True)
class TokenState:
    learner_id: int
    expires_at: datetime
    used_at: datetime | None
    revoked_at: datetime | None
    failed_attempts: int


def ensure_token_usable(token: TokenState | None, *, now: datetime, max_attempts: int,
                        expected_learner_id: int | None) -> None:
    """Raise PickupCodeError unless the token could still be redeemed.

    Order matters: report 'used' before 'expired' so a reused code gets the
    clearest message.
    """
    if token is None:
        raise PickupCodeError("No active pickup code for this package. Ask the learner to request one.",
                              code="PICKUP_CODE_NOT_ISSUED")
    if token.used_at is not None:
        raise PickupCodeError("This pickup code has already been used.", code="PICKUP_CODE_USED")
    if token.revoked_at is not None:
        raise PickupCodeError("This pickup code was replaced by a newer one.", code="PICKUP_CODE_REVOKED")
    if token.failed_attempts >= max_attempts:
        raise PickupCodeError("Too many wrong attempts. The learner must request a new code.",
                              code="PICKUP_CODE_LOCKED")
    if now >= token.expires_at:
        raise PickupCodeError("This pickup code has expired. The learner must request a new code.",
                              code="PICKUP_CODE_EXPIRED")
    if expected_learner_id is None or token.learner_id != expected_learner_id:
        raise PickupCodeError("This pickup code does not belong to the package's recipient.",
                              code="PICKUP_WRONG_RECIPIENT")
