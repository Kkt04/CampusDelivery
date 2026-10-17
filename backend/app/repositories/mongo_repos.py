"""MongoDB implementations of the repositories.

Concurrency-critical writes are *conditional* single-document updates: the
precondition lives in the query filter, so two racing requests can never both
win. Unique indexes are the last line of defence for double collection and
idempotent retries.
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from pymongo import DESCENDING, ReturnDocument

from app.domain.allocation import StorageCandidate
from app.domain.enums import (
    AWAITING_COLLECTION_STATUSES,
    NotificationChannelType,
    NotificationStatus,
    PackageCondition,
    PackageSize,
    PackageStatus,
    Role,
)
from app.domain.overdue import overdue_cutoff
from app.infrastructure.database import next_id
from app.infrastructure.models import (
    AuditLog,
    Document,
    IdempotencyKey,
    Incident,
    Notification,
    Package,
    PackageStatusHistory,
    PickupRecord,
    PickupToken,
    StorageLocation,
    User,
)
from app.infrastructure.store import Store, _serialise
from app.repositories.filters import AuditFilters, IncidentFilters, Page, PackageFilters


def _ci(value: str) -> dict[str, str]:
    return {"$regex": re.escape(value), "$options": "i"}


class _Repo:
    model: type[Document]

    def __init__(self, store: Store) -> None:
        self._store = store
        self.collection = store.collection(self.model)

    def _track(self, obj: Document) -> Document:
        return self._store.track(obj)


# -- relation hydration (untracked) ---------------------------------------
def _user(store: Store, user_id: int | None) -> User | None:
    if user_id is None:
        return None
    doc = store.db[User.COLLECTION].find_one({"_id": user_id})
    return User.from_doc(doc) if doc else None


def _users(store: Store, ids: set[int]) -> dict[int, User]:
    if not ids:
        return {}
    docs = store.db[User.COLLECTION].find({"_id": {"$in": list(ids)}})
    return {d["_id"]: User.from_doc(d) for d in docs}


def _storage(store: Store, location_id: int | None) -> StorageLocation | None:
    if location_id is None:
        return None
    doc = store.db[StorageLocation.COLLECTION].find_one({"_id": location_id})
    return StorageLocation.from_doc(doc) if doc else None


def _hydrate_package(store: Store, obj: Package) -> Package:
    obj.recipient = _user(store, obj.recipient_id)
    obj.received_by = _user(store, obj.received_by_id)
    obj.storage_location = _storage(store, obj.storage_location_id)
    return obj


def _hydrate_package_many(store: Store, objs: list[Package]) -> list[Package]:
    users = _users(store, {o.recipient_id for o in objs if o.recipient_id} | {o.received_by_id for o in objs})
    locations = {o.storage_location_id for o in objs if o.storage_location_id}
    locs = {
        d["_id"]: StorageLocation.from_doc(d)
        for d in store.db[StorageLocation.COLLECTION].find({"_id": {"$in": list(locations)}})
    } if locations else {}
    for obj in objs:
        obj.recipient = users.get(obj.recipient_id) if obj.recipient_id else None
        obj.received_by = users.get(obj.received_by_id)
        obj.storage_location = locs.get(obj.storage_location_id) if obj.storage_location_id else None
    return objs


class MongoUserRepository(_Repo):
    model = User

    def get(self, user_id: int) -> User | None:
        if (local := self._store.get_local(User, user_id)) is not None:
            return local  # type: ignore[return-value]
        doc = self.collection.find_one({"_id": user_id})
        return self._track(User.from_doc(doc)) if doc else None  # type: ignore[return-value]

    def get_by_institutional_id(self, institutional_id: str) -> User | None:
        doc = self.collection.find_one({"institutional_id": institutional_id.strip().upper()})
        return self._track(User.from_doc(doc)) if doc else None  # type: ignore[return-value]

    def get_by_email(self, email: str) -> User | None:
        doc = self.collection.find_one({"email": email.strip().lower()})
        return self._track(User.from_doc(doc)) if doc else None  # type: ignore[return-value]

    def get_by_login(self, identifier: str) -> User | None:
        identifier = identifier.strip()
        if "@" in identifier:
            return self.get_by_email(identifier)
        return self.get_by_institutional_id(identifier)

    def add(self, user: User) -> User:
        user.id = next_id(User.COLLECTION)
        self.collection.insert_one(user.to_doc())
        return self._track(user)  # type: ignore[return-value]

    def search(self, q: str | None, role: Role | None, active_only: bool,
               page: int, page_size: int) -> Page[User]:
        query: dict[str, Any] = {}
        if role:
            query["role"] = role.value
        if active_only:
            query["is_active"] = True
        if q:
            query["$or"] = [
                {"full_name": _ci(q.strip())},
                {"institutional_id": _ci(q.strip())},
                {"email": _ci(q.strip())},
                {"phone": {"$regex": re.escape(q.strip())}},
            ]
        return _page(self.collection, query, [("role", 1), ("full_name", 1)], page, page_size, User)


class MongoPackageRepository(_Repo):
    model = Package

    def get(self, package_id: int) -> Package | None:
        if (local := self._store.get_local(Package, package_id)) is not None:
            return local  # type: ignore[return-value]
        doc = self.collection.find_one({"_id": package_id})
        return self._track(_hydrate_package(self._store, Package.from_doc(doc))) if doc else None  # type: ignore[return-value]

    def get_for_update(self, package_id: int) -> Package | None:
        # Standalone MongoDB has no row locks; the conditional updates below
        # provide the serialisation instead.
        return self.get(package_id)

    def get_by_code_for_update(self, internal_code: str) -> Package | None:
        doc = self.collection.find_one({"internal_code": internal_code.strip().upper()})
        return self._track(_hydrate_package(self._store, Package.from_doc(doc))) if doc else None  # type: ignore[return-value]

    def get_by_tracking_id(self, tracking_id: str) -> Package | None:
        doc = self.collection.find_one({"tracking_id": tracking_id})
        return self._track(_hydrate_package(self._store, Package.from_doc(doc))) if doc else None  # type: ignore[return-value]

    def code_exists(self, internal_code: str) -> bool:
        return self.collection.find_one({"internal_code": internal_code}, {"_id": 1}) is not None

    def add(self, package: Package) -> Package:
        package.id = next_id(Package.COLLECTION)
        self.collection.insert_one(package.to_doc())
        _hydrate_package(self._store, package)
        return self._track(package)  # type: ignore[return-value]

    def compare_and_set_status(self, package_id: int, expected: PackageStatus, new: PackageStatus,
                               values: dict[str, Any]) -> bool:
        update = {"$set": {"status": new.value, **{k: _serialise(v) for k, v in values.items()}},
                  "$inc": {"version": 1}}
        doc = self.collection.find_one_and_update(
            {"_id": package_id, "status": expected.value}, update, return_document=ReturnDocument.AFTER
        )
        if doc is None:
            return False
        local = self._store.get_local(Package, package_id)
        if isinstance(local, Package):
            local.apply_doc(doc)
            self._store.snapshot(local)
        return True

    def add_history(self, entry: PackageStatusHistory) -> None:
        entry.id = next_id(PackageStatusHistory.COLLECTION)
        self._store.db[PackageStatusHistory.COLLECTION].insert_one(entry.to_doc())

    def history(self, package_id: int) -> list[PackageStatusHistory]:
        docs = self._store.db[PackageStatusHistory.COLLECTION].find(
            {"package_id": package_id}
        ).sort([("created_at", 1), ("_id", 1)])
        entries = [PackageStatusHistory.from_doc(d) for d in docs]
        users = _users(self._store, {e.changed_by_id for e in entries})
        for entry in entries:
            entry.changed_by = users.get(entry.changed_by_id)
        return entries

    def search(self, filters: PackageFilters, page: int, page_size: int, now: datetime) -> Page[Package]:
        query: dict[str, Any] = {}
        if filters.q:
            raw = filters.q.strip()
            recipient_ids = [
                d["_id"] for d in self._store.db[User.COLLECTION].find(
                    {"$or": [{"full_name": _ci(raw)}, {"institutional_id": _ci(raw)}]}, {"_id": 1}
                )
            ]
            query["$or"] = [
                {"internal_code": _ci(raw)},
                {"tracking_id": _ci(raw)},
                {"courier_name": _ci(raw)},
                {"recipient_hint": _ci(raw)},
                {"recipient_id": {"$in": recipient_ids}},
            ]
        if filters.statuses:
            query["status"] = {"$in": [s.value for s in filters.statuses]}
        if filters.recipient_id is not None:
            query["recipient_id"] = filters.recipient_id
        if filters.condition:
            query["condition"] = filters.condition.value
        if filters.storage_location_id is not None:
            query["storage_location_id"] = filters.storage_location_id
        if filters.arrived_from:
            query.setdefault("arrived_at", {})["$gte"] = filters.arrived_from
        if filters.arrived_to:
            query.setdefault("arrived_at", {})["$lt"] = filters.arrived_to
        if filters.overdue_only:
            query["status"] = {"$in": [s.value for s in AWAITING_COLLECTION_STATUSES]}
            query.setdefault("arrived_at", {})["$lt"] = overdue_cutoff(now, filters.overdue_deadline_days)
        result = _page(self.collection, query, [("arrived_at", DESCENDING), ("_id", DESCENDING)],
                       page, page_size, Package)
        _hydrate_package_many(self._store, result.items)
        return result

    def count_by_status(self) -> dict[PackageStatus, int]:
        rows = self.collection.aggregate([{"$group": {"_id": "$status", "n": {"$sum": 1}}}])
        return {PackageStatus(r["_id"]): r["n"] for r in rows}

    def count_overdue(self, now: datetime, deadline_days: int) -> int:
        return self.collection.count_documents({
            "status": {"$in": [s.value for s in AWAITING_COLLECTION_STATUSES]},
            "arrived_at": {"$lt": overdue_cutoff(now, deadline_days)},
        })

    def count_damaged_condition(self) -> int:
        return self.collection.count_documents({"condition": PackageCondition.DAMAGED.value})

    def count_arrived_since(self, start: datetime) -> int:
        return self.collection.count_documents({"arrived_at": {"$gte": start}})

    def arrival_times_between(self, start: datetime, end: datetime) -> list[datetime]:
        docs = self.collection.find({"arrived_at": {"$gte": start, "$lt": end}}, {"arrived_at": 1})
        return [d["arrived_at"] for d in docs]


class MongoStorageRepository(_Repo):
    model = StorageLocation

    def get(self, location_id: int) -> StorageLocation | None:
        if (local := self._store.get_local(StorageLocation, location_id)) is not None:
            return local  # type: ignore[return-value]
        doc = self.collection.find_one({"_id": location_id})
        return self._track(StorageLocation.from_doc(doc)) if doc else None  # type: ignore[return-value]

    def get_by_code(self, code: str) -> StorageLocation | None:
        doc = self.collection.find_one({"code": code.strip().upper()})
        return self._track(StorageLocation.from_doc(doc)) if doc else None  # type: ignore[return-value]

    def list_locations(self, active_only: bool = False) -> list[StorageLocation]:
        query = {"is_active": True} if active_only else {}
        docs = self.collection.find(query).sort("code", 1)
        return [self._track(StorageLocation.from_doc(d)) for d in docs]  # type: ignore[misc]

    def add(self, location: StorageLocation) -> StorageLocation:
        location.id = next_id(StorageLocation.COLLECTION)
        self.collection.insert_one(location.to_doc())
        return self._track(location)  # type: ignore[return-value]

    def candidates(self) -> Sequence[StorageCandidate]:
        docs = self.collection.find({
            "is_active": True,
            "$expr": {"$lt": ["$occupied_count", "$capacity"]},
        })
        return [
            StorageCandidate(
                id=d["_id"], code=d["code"], capacity=d["capacity"], occupied=d["occupied_count"],
                max_package_size=PackageSize(d["max_package_size"]), is_active=d["is_active"],
            )
            for d in docs
        ]

    def try_reserve(self, location_id: int) -> bool:
        doc = self.collection.find_one_and_update(
            {"_id": location_id, "is_active": True, "$expr": {"$lt": ["$occupied_count", "$capacity"]}},
            {"$inc": {"occupied_count": 1}},
            return_document=ReturnDocument.AFTER,
        )
        if doc is not None and (local := self._store.get_local(StorageLocation, location_id)) is not None:
            local.occupied_count = doc["occupied_count"]
            self._store.snapshot(local)
        return doc is not None

    def release(self, location_id: int) -> None:
        self.collection.update_one(
            {"_id": location_id, "occupied_count": {"$gt": 0}}, {"$inc": {"occupied_count": -1}}
        )

    def totals(self) -> tuple[int, int]:
        rows = list(self.collection.aggregate([
            {"$match": {"is_active": True}},
            {"$group": {"_id": None, "capacity": {"$sum": "$capacity"}, "occupied": {"$sum": "$occupied_count"}}},
        ]))
        if not rows:
            return 0, 0
        return int(rows[0]["capacity"]), int(rows[0]["occupied"])


class MongoPickupTokenRepository(_Repo):
    model = PickupToken

    def add(self, token: PickupToken) -> PickupToken:
        token.id = next_id(PickupToken.COLLECTION)
        self.collection.insert_one(token.to_doc())
        return self._track(token)  # type: ignore[return-value]

    def latest_for_package(self, package_id: int) -> PickupToken | None:
        doc = self.collection.find_one({"package_id": package_id}, sort=[("_id", DESCENDING)])
        return self._track(PickupToken.from_doc(doc)) if doc else None  # type: ignore[return-value]

    def revoke_active(self, package_id: int, now: datetime) -> int:
        result = self.collection.update_many(
            {"package_id": package_id, "used_at": None, "revoked_at": None},
            {"$set": {"revoked_at": now}},
        )
        return result.modified_count

    def mark_used(self, token_id: int, now: datetime) -> bool:
        doc = self.collection.find_one_and_update(
            {"_id": token_id, "used_at": None, "revoked_at": None},
            {"$set": {"used_at": now}},
            return_document=ReturnDocument.AFTER,
        )
        if doc is not None and (local := self._store.get_local(PickupToken, token_id)) is not None:
            local.used_at = doc["used_at"]
            self._store.snapshot(local)
        return doc is not None

    def increment_failed_attempts(self, token_id: int) -> None:
        self.collection.update_one({"_id": token_id}, {"$inc": {"failed_attempts": 1}})


class MongoPickupRecordRepository(_Repo):
    model = PickupRecord

    def add(self, record: PickupRecord) -> PickupRecord:
        record.id = next_id(PickupRecord.COLLECTION)
        self.collection.insert_one(record.to_doc())
        self._hydrate(record)
        return self._track(record)  # type: ignore[return-value]

    def get(self, record_id: int) -> PickupRecord | None:
        if (local := self._store.get_local(PickupRecord, record_id)) is not None:
            return local  # type: ignore[return-value]
        doc = self.collection.find_one({"_id": record_id})
        return self._track(self._hydrate(PickupRecord.from_doc(doc))) if doc else None  # type: ignore[return-value]

    def _hydrate(self, record: PickupRecord) -> PickupRecord:
        record.package = MongoPackageRepository(self._store).get(record.package_id)
        record.handed_over_by = _user(self._store, record.handed_over_by_id)
        return record

    def list_records(self, learner_id: int | None, page: int, page_size: int) -> Page[PickupRecord]:
        query = {"learner_id": learner_id} if learner_id is not None else {}
        result = _page(self.collection, query, [("collected_at", DESCENDING)], page, page_size, PickupRecord)
        for record in result.items:
            self._hydrate(record)
        return result

    def collection_times_between(self, start: datetime, end: datetime) -> list[datetime]:
        docs = self.collection.find({"collected_at": {"$gte": start, "$lt": end}}, {"collected_at": 1})
        return [d["collected_at"] for d in docs]


class MongoNotificationRepository(_Repo):
    model = Notification

    def add(self, notification: Notification) -> Notification:
        notification.id = next_id(Notification.COLLECTION)
        self.collection.insert_one(notification.to_doc())
        return self._track(notification)  # type: ignore[return-value]

    def get(self, notification_id: int) -> Notification | None:
        if (local := self._store.get_local(Notification, notification_id)) is not None:
            return local  # type: ignore[return-value]
        doc = self.collection.find_one({"_id": notification_id})
        return self._track(Notification.from_doc(doc)) if doc else None  # type: ignore[return-value]

    def list_in_app(self, user_id: int, page: int, page_size: int) -> Page[Notification]:
        return _page(self.collection,
                     {"user_id": user_id, "channel": NotificationChannelType.IN_APP.value},
                     [("created_at", DESCENDING), ("_id", DESCENDING)], page, page_size, Notification)

    def unread_count(self, user_id: int) -> int:
        return self.collection.count_documents({
            "user_id": user_id, "channel": NotificationChannelType.IN_APP.value, "read_at": None,
        })

    def mark_all_read(self, user_id: int, now: datetime) -> int:
        return self.collection.update_many(
            {"user_id": user_id, "read_at": None}, {"$set": {"read_at": now}}
        ).modified_count

    def retryable(self, max_attempts: int) -> list[Notification]:
        docs = self.collection.find({
            "delivery_status": {"$in": [NotificationStatus.FAILED.value, NotificationStatus.PENDING.value]},
            "attempts": {"$lt": max_attempts},
        }).sort("_id", 1)
        return [Notification.from_doc(d) for d in docs]

    def count_by_status(self, status: NotificationStatus) -> int:
        return self.collection.count_documents({"delivery_status": status.value})


class MongoIncidentRepository(_Repo):
    model = Incident

    def add(self, incident: Incident) -> Incident:
        incident.id = next_id(Incident.COLLECTION)
        self.collection.insert_one(incident.to_doc())
        self._hydrate(incident)
        return self._track(incident)  # type: ignore[return-value]

    def get(self, incident_id: int) -> Incident | None:
        if (local := self._store.get_local(Incident, incident_id)) is not None:
            return local  # type: ignore[return-value]
        doc = self.collection.find_one({"_id": incident_id})
        return self._track(self._hydrate(Incident.from_doc(doc))) if doc else None  # type: ignore[return-value]

    def _hydrate(self, incident: Incident) -> Incident:
        if incident.package_id is not None:
            incident.package = MongoPackageRepository(self._store).get(incident.package_id)
        incident.reported_by = _user(self._store, incident.reported_by_id)
        incident.resolved_by = _user(self._store, incident.resolved_by_id)
        return incident

    def open_for_package(self, package_id: int) -> list[Incident]:
        docs = self.collection.find({"package_id": package_id, "status": "OPEN"})
        return [self._track(Incident.from_doc(d)) for d in docs]  # type: ignore[misc]

    def search(self, filters: IncidentFilters, page: int, page_size: int) -> Page[Incident]:
        query: dict[str, Any] = {}
        if filters.status:
            query["status"] = filters.status.value
        if filters.type:
            query["type"] = filters.type.value
        if filters.package_id is not None:
            query["package_id"] = filters.package_id
        if filters.reported_by_id is not None:
            query["reported_by_id"] = filters.reported_by_id
        result = _page(self.collection, query, [("created_at", DESCENDING), ("_id", DESCENDING)],
                       page, page_size, Incident)
        for incident in result.items:
            self._hydrate(incident)
        return result

    def count_open(self) -> int:
        return self.collection.count_documents({"status": "OPEN"})


class MongoAuditRepository(_Repo):
    model = AuditLog

    def add(self, entry: AuditLog) -> None:
        entry.id = next_id(AuditLog.COLLECTION)
        self.collection.insert_one(entry.to_doc())

    def search(self, filters: AuditFilters, page: int, page_size: int) -> Page[AuditLog]:
        query: dict[str, Any] = {}
        if filters.action:
            query["action"] = {"$regex": f"^{re.escape(filters.action)}"}
        if filters.entity_type:
            query["entity_type"] = filters.entity_type
        if filters.entity_id:
            query["entity_id"] = filters.entity_id
        if filters.actor_id is not None:
            query["actor_id"] = filters.actor_id
        if filters.date_from:
            query.setdefault("created_at", {})["$gte"] = filters.date_from
        if filters.date_to:
            query.setdefault("created_at", {})["$lt"] = filters.date_to
        result = _page(self.collection, query, [("created_at", DESCENDING), ("_id", DESCENDING)],
                       page, page_size, AuditLog)
        actors = _users(self._store, {e.actor_id for e in result.items if e.actor_id})
        for entry in result.items:
            entry.actor = actors.get(entry.actor_id) if entry.actor_id else None
        return result


class MongoIdempotencyRepository(_Repo):
    model = IdempotencyKey

    def get(self, user_id: int, scope: str, key: str) -> IdempotencyKey | None:
        doc = self.collection.find_one({"user_id": user_id, "scope": scope, "key": key})
        return self._track(IdempotencyKey.from_doc(doc)) if doc else None  # type: ignore[return-value]

    def add(self, record: IdempotencyKey) -> None:
        record.id = next_id(IdempotencyKey.COLLECTION)
        self.collection.insert_one(record.to_doc())


def _page(collection, query: dict[str, Any], sort: list[tuple[str, int]], page: int, page_size: int,
          model: type[Document]):  # noqa: ANN001, ANN202
    total = collection.count_documents(query)
    docs = collection.find(query).sort(sort).skip((page - 1) * page_size).limit(page_size)
    return Page(items=[model.from_doc(d) for d in docs], total=total, page=page, page_size=page_size)
