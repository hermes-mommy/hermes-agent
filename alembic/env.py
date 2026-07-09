"""Alembic env.py -- async + multi-schema for Guinevere PostgreSQL 16."""
import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from guinevere.memory.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

GUINEVERE_SCHEMAS = frozenset({
    "memory", "persona", "surveillance", "financial",
    "projects", "social", "agents", "consent",
    "security", "audit", "ops", "extensions",
})

db_url = config.get_main_option("sqlalchemy.url")
password = os.environ.get("GUINEVERE_DB_PASSWORD", "")
if password:
    db_url = db_url.replace(":****@", f":{password}@")
    config.set_main_option("sqlalchemy.url", db_url)


def include_name(name: str, type_: str, parent_names: dict) -> bool:
    """Filter schemas to only include guinevere canonical schemas."""
    if type_ == "schema":
        return name in GUINEVERE_SCHEMAS
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_name=include_name,
        version_table_schema="ops",
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=include_name,
        version_table_schema="ops",
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()