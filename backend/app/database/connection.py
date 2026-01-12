"""Database connection and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from ..config import get_settings

settings = get_settings()


# Sync engine and session
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.database_echo
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """Dependency for sync database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables."""
    from .base import Base
    # Import all models to register them with Base
    from ..db_models import (
        ScrapeUrl, ApiCredential, UploadedFile,
        ScrapeJob, ScrapeJobLog,
        DocumentRegistry, DocumentBlob,
        GovernanceTransition,
        AuditLog,
        SystemSetting
    )
    
    Base.metadata.create_all(bind=engine)

