import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Load .env from project root so DATABASE_URL is available
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.isfile(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

# this is the Alembic Config object, which provides
# access to the values within the alembic.ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Register all models on Base.metadata (side effect of importing app.models)
from app.db.base import Base  # noqa: E402, I001

import app.models  # noqa: F401, E402, I001

target_metadata = Base.metadata


def _to_asyncpg_url(url: str) -> str:
    """Ensure URL uses asyncpg driver for async engine."""
    if "+asyncpg" in url:
        return url
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url.split("://", 1)[1]
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url.split("://", 1)[1]
    if url.startswith("postgresql+psycopg2://") or url.startswith(
        "postgresql+psycopg://"
    ):
        return "postgresql+asyncpg://" + url.split("://", 1)[1]
    return url


def get_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError(
            "Set DATABASE_URL in the environment or .env, or set sqlalchemy.url "
            "in alembic.ini"
        )
    return _to_asyncpg_url(url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table="__alembic",
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations inside run_sync; connection is sync wrapper."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table="__alembic",
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using asyncpg."""
    connectable = create_async_engine(get_url(), poolclass=pool.NullPool)

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
