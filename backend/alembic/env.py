"""Alembic environment: uses the application's DATABASE_URL and ORM metadata."""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.infrastructure import models  # noqa: F401 - registers tables on Base.metadata
from app.infrastructure.database import Base, UTCDateTime

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

url = config.attributes.get("database_url") or get_settings().database_url
config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
target_metadata = Base.metadata


def render_item(type_, obj, autogen_context):  # noqa: ANN001, ANN201
    """Render our UTCDateTime decorator as a plain timezone-aware DateTime."""
    if type_ == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime(timezone=True)"
    return False


def run_migrations_offline() -> None:
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True,
                      render_as_batch=url.startswith("sqlite"), render_item=render_item)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}),
                                     prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                          render_as_batch=connection.dialect.name == "sqlite", render_item=render_item)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
