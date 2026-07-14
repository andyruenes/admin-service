"""Async SQLAlchemy engine and session factory.

Uses asyncpg via create_async_engine. Session factory is suitable for
FastAPI Depends(get_session); no scoped_session.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings


def _asyncpg_url(url: str) -> str:
    """Normalize DATABASE_URL for SQLAlchemy async engine (asyncpg)."""
    if "+asyncpg" in url:
        return url
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url.removeprefix("postgresql://")
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url.removeprefix("postgres://")
    return url


engine = create_async_engine(_asyncpg_url(settings.DATABASE_URL))

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
