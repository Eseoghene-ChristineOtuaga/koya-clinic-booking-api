"""Alembic migrations using DATABASE_URL from environment, never from Git."""
import os

from alembic import context
from sqlalchemy import create_engine, pool

from src.models import Base

config = context.config
target_metadata = Base.metadata


def database_url() -> str:
    value = os.getenv("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL is required to run database migrations")
    return value


def run_migrations_offline() -> None:
    context.configure(url=database_url(), target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"}, version_table_schema="koya_clinic", include_schemas=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(database_url(), poolclass=pool.NullPool, connect_args={"prepare_threshold": None})
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata, compare_type=True, version_table_schema="koya_clinic", include_schemas=True)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
