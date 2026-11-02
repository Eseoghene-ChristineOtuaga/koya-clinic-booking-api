"""Database connection infrastructure; no credentials are stored in Git."""
import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    # Supabase Postgres uses TLS. Keep sslmode in the configured URL.
    # pool_pre_ping checks connections reused by warm serverless functions.
    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=1,
        pool_timeout=10,
    )


def get_session():
    session = sessionmaker(bind=get_engine(), expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
