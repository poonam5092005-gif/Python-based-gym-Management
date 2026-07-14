"""SQLAlchemy engine, session factory, and FastAPI dependency."""

from __future__ import annotations

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from utils.config import settings


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model in the project."""


connect_args: dict = {}
if settings.DATABASE_URL.startswith("sqlite"):
    # Make sure the parent folder exists for SQLite files
    db_path = settings.DATABASE_URL.replace("sqlite:///", "", 1)
    if db_path and not db_path.startswith(":"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    # Needed so the same SQLite connection can be used across threads
    connect_args = {"check_same_thread": False}


engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, future=True
)


def init_db() -> None:
    """Create all tables. Called on app startup."""
    # Import here to avoid circular imports while ensuring models are registered.
    from models import db_models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped DB session and closes it after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
