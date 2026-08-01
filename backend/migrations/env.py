from logging.config import fileConfig
import logging

from sqlalchemy import engine_from_config, pool
from alembic import context

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger("alembic.env")

from models.base import Base
from config.settings import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url_async)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Import all models so Alembic can detect them
import models.user
import models.resume
import models.chunk
import models.report
import models.chat_message


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    sync_url = settings.database_url_async.replace("+asyncpg", "+psycopg")
    connectable = engine_from_config(
        {"sqlalchemy.url": sync_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        from sqlalchemy import inspect as sa_inspect, text
        inspector = sa_inspect(connection)
        existing_tables = inspector.get_table_names()
        alembic_table_exists = "alembic_version" in existing_tables

        if "users" in existing_tables and not alembic_table_exists:
            logger.info("Tables exist but no alembic_version — stamping at 001")
            connection.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"))
            connection.execute(text("INSERT INTO alembic_version (version_num) VALUES ('001')"))
            connection.commit()
        else:
            # The inspector queries above started an implicit (autobegin)
            # transaction. Without clearing it, alembic treats the connection
            # as already being inside an "external transaction" and returns a
            # no-op context manager from begin_transaction() — the migration
            # statements run but are silently rolled back when the connection
            # closes, so `alembic upgrade head` exits 0 while changing nothing.
            connection.rollback()

        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
