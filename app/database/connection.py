"""Database connection and session management."""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator

from ..config import get_settings

settings = get_settings()


# ========================================
# ASYNC DATABASE (Primary for Application)
# ========================================


def get_async_database_url(url: str) -> str:
    """Convert sync postgres URL to async asyncpg URL."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


async_database_url = get_async_database_url(settings.database_url)

# Async engine with connection pooling
async_engine = create_async_engine(
    async_database_url,
    pool_pre_ping=True,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
    echo=settings.database_echo,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Async dependency for database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ========================================
# SYNC DATABASE (Only for init_db)
# ========================================

try:
    sync_engine = create_engine(
        settings.database_url, pool_pre_ping=True, echo=settings.database_echo, pool_size=50,max_overflow=100,      # Increase from 20
    pool_timeout=80,       
    )
except Exception:
    sync_engine = None


def init_db() -> None:
    """Initialize database tables."""
    from .base import Base
    from ..db_models import (
        ScrapeUrl,
        ApiCredential,
        ScrapeJob,
        ScrapeJobLog,
        DocumentRegistry,
        DocumentBlob,
        GovernanceTransition,
        AuditLog,
        SystemSetting,
    )

    if sync_engine:
        Base.metadata.create_all(bind=sync_engine)
    else:
        import asyncio

        async def async_init():
            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        asyncio.run(async_init())
