"""Audit logging. Entries are added to the current transaction, so an audit
record exists if and only if the audited change was committed."""
from typing import Any

from app.infrastructure.models import AuditLog, User
from app.repositories.interfaces import AuditRepository


class AuditService:
    def __init__(self, repository: AuditRepository) -> None:
        self._repository = repository

    def record(self, actor: User | None, action: str, entity_type: str,
               entity_id: int | str | None, details: dict[str, Any] | None = None) -> None:
        self._repository.add(
            AuditLog(
                actor_id=actor.id if actor else None,
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id is not None else None,
                details=details or {},
            )
        )
