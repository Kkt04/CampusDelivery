"""Database engine, session factory and shared column types.

PostgreSQL is the production database. SQLite is supported for local
development and tests; for SQLite we start every transaction with
`BEGIN IMMEDIATE`, which serialises writers the way PostgreSQL's row locks
(`SELECT ... FOR UPDATE`) do for the rows we lock.
"""
from datetime import datetime

from sqlalchemy import DateTime, MetaData, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.core.config import get_settings
from app.core.time import ensure_utc

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UTCDateTime(TypeDecorator):
    """Always store and return timezone-aware UTC datetimes (SQLite drops tzinfo)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):  # noqa: ANN001
        return ensure_utc(value) if value is not None else None

    def process_result_value(self, value: datetime | None, dialect):  # noqa: ANN001
        return ensure_utc(value) if value is not None else None


def build_engine(url: str, echo: bool = False) -> Engine:
    if url.startswith("sqlite"):
        engine = create_engine(url, echo=echo, connect_args={"check_same_thread": False, "timeout": 30})

        @event.listens_for(engine, "connect")
        def _sqlite_connect(dbapi_connection, _record):  # noqa: ANN001
            dbapi_connection.isolation_level = None  # let SQLAlchemy emit BEGIN itself
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        @event.listens_for(engine, "begin")
        def _sqlite_begin(connection):  # noqa: ANN001
            connection.exec_driver_sql("BEGIN IMMEDIATE")

        return engine
    return create_engine(url, echo=echo, pool_pre_ping=True)


_settings = get_settings()
engine = build_engine(_settings.database_url, _settings.sql_echo)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
