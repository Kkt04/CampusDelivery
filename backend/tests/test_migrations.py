"""The Alembic migration builds the same schema the ORM expects, on a fresh database."""
import os
import tempfile

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.infrastructure.database import Base

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_upgrade_and_downgrade_on_fresh_database():
    url = os.environ.get("TEST_MIGRATION_DATABASE_URL") or f"sqlite:///{tempfile.mkdtemp()}/migrate.db"
    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    cfg.attributes["database_url"] = url
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")
    tables = set(inspect(create_engine(url)).get_table_names())
    assert set(Base.metadata.tables) <= tables
    command.downgrade(cfg, "base")
    assert set(inspect(create_engine(url)).get_table_names()) <= {"alembic_version"}
