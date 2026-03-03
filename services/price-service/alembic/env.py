"""
alembic/env.py — Alembic migration environment.

This file is executed by Alembic every time you run an `alembic` command.
It is responsible for:
  1. Connecting Alembic to our database (via our app's config, not alembic.ini)
  2. Telling Alembic about our SQLAlchemy models so --autogenerate works
  3. Running migrations asynchronously (required for asyncpg)

Why async here?
  Our app uses SQLAlchemy's async engine with asyncpg. Alembic historically
  ran synchronous migrations, but since SQLAlchemy 1.4 it supports async via
  a synchronous "proxy" connection that wraps the async one. This is the
  recommended pattern from the SQLAlchemy docs.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.pool import NullPool

# Import our settings so DATABASE_URL comes from the environment, not alembic.ini.
from price_service.config import settings

# Import Base so Alembic can inspect our models for --autogenerate.
# As you add model files, import them here so Alembic sees them.
from price_service.database import Base  # noqa: F401
from price_service.models import product  # noqa: F401

# Alembic Config object — provides access to values in alembic.ini.
config = context.config

# Wire up Python's logging using the [loggers] section in alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This is the MetaData object that --autogenerate inspects.
# It must include all your models' metadata.
target_metadata = Base.metadata

# Override sqlalchemy.url with the value from our pydantic-settings config.
# This ensures migrations always use the same DATABASE_URL as the app itself.
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Offline mode generates SQL scripts without connecting to the database.
    Useful for reviewing changes or applying them manually in production.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode (connects to a live database).

    We use NullPool here because Alembic migrations are short-lived CLI
    commands — connection pooling would be wasted overhead and can cause
    issues with some async drivers.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=NullPool,
    )

    async with connectable.connect() as connection:
        # run_sync bridges the gap between Alembic's sync API and our async
        # connection — Alembic runs its migrations inside this sync wrapper.
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
