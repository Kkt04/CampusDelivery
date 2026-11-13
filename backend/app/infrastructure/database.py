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
import logging
from pymongo import ASCENDING, MongoClient, ReturnDocument
from pymongo.database import Database

from app.core.config import get_settings

logger = logging.getLogger("campus")

_client: MongoClient | None = None
_db: Database | None = None
_using_mock: bool = False
_mock_initialized: bool = False


def is_using_mock() -> bool:
    return _using_mock


def get_client() -> MongoClient:
    global _client, _using_mock
    if _client is None:
        settings = get_settings()
        if settings.mongo_url in ("memory", "mock"):
            import mongomock
            _client = mongomock.MongoClient()
            _using_mock = True
            logger.info("Using explicit in-memory mongomock database.")
        else:
            try:
                test_client = MongoClient(settings.mongo_url, tz_aware=True, serverSelectionTimeoutMS=1500)
                test_client.admin.command("ping")
                _client = test_client
                _using_mock = False
                logger.info("Connected to MongoDB at %s", settings.mongo_url)
            except Exception as exc:
                try:
                    import mongomock
                    logger.warning(
                        "MongoDB at %s unreachable (%s). Falling back to in-memory mongomock database for seamless demo/testing.",
                        settings.mongo_url,
                        exc,
                    )
                    _client = mongomock.MongoClient()
                    _using_mock = True
                except ImportError:
                    logger.error("MongoDB unreachable and mongomock not installed: %s", exc)
                    _client = MongoClient(settings.mongo_url, tz_aware=True, serverSelectionTimeoutMS=5000)
                    _using_mock = False
    return _client


def get_db() -> Database:
    global _db, _mock_initialized
    if _db is None:
        _db = get_client()[get_settings().mongo_db]
        if _using_mock and not _mock_initialized:
            _mock_initialized = True
            try:
                init_db()
                from app.seed import ensure_demo_users, seed
                ensure_demo_users(force=True)
                seed(force_environment=True)
                logger.info("Auto-initialized mock database with demo accounts and packages.")
            except Exception as e:
                logger.warning("Mock database seeding notice: %s", e)
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
