"""Async SQLAlchemy engine and session factory."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .config import get_settings


_settings = get_settings()

engine: AsyncEngine = create_async_engine(
    _settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

SessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:  # pragma: no cover
    """FastAPI dependency to get an async DB session."""
    async with SessionFactory() as session:
        yield session
