"""MongoDB connection, index setup and auto-increment id counters.

The application is synchronous, so we use the standard PyMongo driver. Each
repository receives the shared `Database` handle and writes directly.

Concurrency notes
-----------------
MongoDB standalone servers do not support multi-document transactions. The
domain's "one transaction per use case" therefore becomes a sequence of
condition-guarded single-document writes plus unique indexes:

* slot reservation, code consumption and status changes use
  `find_one_and_update` with the precondition in the filter, so two racing
  requests can never both win;
* `pickup_records.package_id` and `idempotency_keys` have unique indexes, so a
  double collection or a duplicate retry is rejected by the database.
"""
from pymongo import ASCENDING, MongoClient, ReturnDocument
from pymongo.database import Database

from app.core.config import get_settings

_client: MongoClient | None = None
_db: Database | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = MongoClient(settings.mongo_url, tz_aware=True, serverSelectionTimeoutMS=5000)
    return _client


def get_db() -> Database:
    global _db
    if _db is None:
        _db = get_client()[get_settings().mongo_db]
    return _db


def next_id(collection: str) -> int:
    """Atomically allocate the next integer id for a collection."""
    doc = get_db()["counters"].find_one_and_update(
        {"_id": collection}, {"$inc": {"seq": 1}}, upsert=True, return_document=ReturnDocument.AFTER
    )
    return int(doc["seq"])


def init_db() -> None:
    """Create the indexes the application relies on. Safe to call repeatedly."""
    db = get_db()

    def unique(collection: str, keys: list[tuple[str, int]], **kwargs: object) -> None:
        db[collection].create_index(keys, unique=True, **kwargs)  # type: ignore[arg-type]

    unique("users", [("institutional_id", ASCENDING)])
    unique("users", [("email", ASCENDING)])
    unique("packages", [("internal_code", ASCENDING)])
    unique("packages", [("tracking_id", ASCENDING)], partialFilterExpression={"tracking_id": {"$type": "string"}})
    unique("pickup_records", [("package_id", ASCENDING)])
    unique("pickup_records", [("token_id", ASCENDING)])
    unique("idempotency_keys", [("user_id", ASCENDING), ("scope", ASCENDING), ("key", ASCENDING)])
    unique("password_reset_tokens", [("token_hash", ASCENDING)])
    unique("refresh_tokens", [("token_hash", ASCENDING)])

    db["packages"].create_index([("status", ASCENDING), ("arrived_at", ASCENDING)])
    db["notifications"].create_index([("user_id", ASCENDING), ("created_at", ASCENDING)])
    db["password_reset_tokens"].create_index([("user_id", ASCENDING), ("created_at", ASCENDING)])
    db["refresh_tokens"].create_index([("user_id", ASCENDING), ("created_at", ASCENDING)])



def reset_db() -> None:
    """Drop every collection. Used by the test suite only."""
    db = get_db()
    for name in db.list_collection_names():
        db[name].drop()
    init_db()
