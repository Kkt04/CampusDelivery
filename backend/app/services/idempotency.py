"""Idempotency for retried POST requests.

A client sends `Idempotency-Key: <uuid>`. The first request stores
(user, scope, key, request fingerprint, resulting resource id) in the SAME
transaction as the change. A retry with the same key and same body returns the
original resource instead of repeating the change. The same key with a
different body is rejected. A UNIQUE constraint makes concurrent duplicates safe.
"""
import hashlib
import json
from typing import Any

from app.core.exceptions import IdempotencyKeyReuseError
from app.infrastructure.models import IdempotencyKey
from app.repositories.sqlalchemy_repos import SqlIdempotencyRepository


def fingerprint(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


class IdempotencyGuard:
    def __init__(self, repository: SqlIdempotencyRepository) -> None:
        self._repository = repository

    def find(self, user_id: int, scope: str, key: str | None, request_hash: str) -> int | None:
        if not key:
            return None
        record = self._repository.get(user_id, scope, key)
        if record is None:
            return None
        if record.request_hash != request_hash:
            raise IdempotencyKeyReuseError("This Idempotency-Key was already used for a different request.")
        return record.resource_id

    def remember(self, user_id: int, scope: str, key: str | None, request_hash: str, resource_id: int) -> None:
        if key:
            self._repository.add(IdempotencyKey(user_id=user_id, scope=scope, key=key,
                                                request_hash=request_hash, resource_id=resource_id))
