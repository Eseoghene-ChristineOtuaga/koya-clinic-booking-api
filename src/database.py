"""Database connection infrastructure for Vercel + Supabase."""
import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")

    # Vercel is serverless; Supabase transaction pooler is port 6543.
    # Avoid client-side connection pooling and server-side prepared statements.
    return create_engine(
        url,
        poolclass=NullPool,
        connect_args={"prepare_threshold": None},
    )


def get_session():
    session = sessionmaker(bind=get_engine(), expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
