"""A tiny persistence session: shared database handle, an identity map and
dirty-field tracking.

Repositories record every entity they load or insert here. `flush()` writes
back only the fields that actually changed (compared with the snapshot taken
when the entity was loaded), and never the guarded `occupied_count`, which is
only ever changed by atomic conditional updates.

This gives the services the same "mutate the object, then commit" ergonomics
they had with the ORM, without MongoDB needing multi-document transactions.
"""
from __future__ import annotations

from dataclasses import fields
from typing import Any

from pymongo.database import Database

from app.core.time import utcnow
from app.infrastructure.database import get_db
from app.infrastructure.models import Document


def _serialise(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


class Store:
    PROTECTED_FIELDS = {"occupied_count"}

    def __init__(self, db: Database | None = None) -> None:
        self.db = db if db is not None else get_db()
        self._tracked: dict[tuple[str, int], tuple[Document, dict[str, Any]]] = {}

    # -- identity map ------------------------------------------------------
    def collection(self, model: type[Document]):  # noqa: ANN201
        return self.db[model.COLLECTION]

    def track(self, obj: Document) -> Document:
        snapshot = {k: _serialise(v) for k, v in obj.to_doc().items() if k != "_id"}
        self._tracked[(obj.COLLECTION, obj.id)] = (obj, snapshot)
        return obj

    def snapshot(self, obj: Document) -> None:
        self._tracked[(obj.COLLECTION, obj.id)] = (
            obj,
            {k: _serialise(v) for k, v in obj.to_doc().items() if k != "_id"},
        )

    def get_local(self, model: type[Document], obj_id: int) -> Document | None:
        entry = self._tracked.get((model.COLLECTION, obj_id))
        return entry[0] if entry else None

    # -- persistence -------------------------------------------------------
    def flush(self) -> None:
        for (collection, obj_id), (obj, snapshot) in list(self._tracked.items()):
            current = {k: _serialise(v) for k, v in obj.to_doc().items() if k != "_id"}
            changed = {
                key: value
                for key, value in current.items()
                if key not in self.PROTECTED_FIELDS and snapshot.get(key) != value
            }
            if not changed:
                continue
            if "updated_at" in {f.name for f in fields(obj)}:
                changed["updated_at"] = utcnow()
                obj.updated_at = changed["updated_at"]
            self.db[collection].update_one({"_id": obj_id}, {"$set": changed})
            snapshot.update(changed)
            self._tracked[(collection, obj_id)] = (obj, snapshot)

    def refresh(self, obj: Document) -> None:
        if obj.id is None:
            return
        doc = self.collection(type(obj)).find_one({"_id": obj.id})
        if doc is not None:
            obj.apply_doc(doc)
            self.snapshot(obj)

    def commit(self) -> None:
        self.flush()
