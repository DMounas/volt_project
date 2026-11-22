"""Database connectivity and session management.

Provides a resilient database session factory that safely tests PostgreSQL
interconnection without crashing local unit tests if Postgres is offline.
"""

import os
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://volt_user:volt_secret_password@localhost:5432/volt_db",
)

Base = declarative_base()

# Resilient engine creation with pool pre-ping
try:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args={"connect_timeout": 3},
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception:
    engine = None
    SessionLocal = None


def get_db() -> Generator:
    """Dependency that yields a database session if available."""
    if SessionLocal is None:
        raise RuntimeError("Database engine not initialized")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Check whether the PostgreSQL database is reachable."""
    if engine is None:
        return False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            return True
    except Exception:
        return False
