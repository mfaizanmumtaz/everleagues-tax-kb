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
    echo=settings.database_echo,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Important for async to avoid refresh issues
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async dependency for database session.

    Usage in FastAPI routes:
        async def my_route(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ========================================
# SYNC DATABASE (Only for init_db)
# ========================================

# Keep a separate sync engine ONLY for database initialization
# This uses the original psycopg driver (need to install for init only)
try:
    # Try to create sync engine, but it's optional if psycopg2 not installed
    sync_engine = create_engine(
        settings.database_url, pool_pre_ping=True, echo=settings.database_echo
    )
except Exception:
    # If sync driver not available, we can use async for init_db with run_sync
    sync_engine = None


def init_db() -> None:
    """
    Initialize database tables (synchronous).

    This is only run once during setup, so we keep it synchronous
    for simplicity.
    """
    from .base import Base
    # Import all models to register them with Base

    if sync_engine:
        Base.metadata.create_all(bind=sync_engine)
    else:
        # If no sync engine, use async engine with run_sync
        import asyncio

        async def async_init():
            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        asyncio.run(async_init())
