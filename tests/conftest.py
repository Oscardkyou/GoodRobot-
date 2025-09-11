import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.models.base import Base

# Создаем тестовую in-memory SQLite базу данных
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Создает экземпляр цикла событий для каждой тестовой сессии"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Создает тестовый движок базы данных"""
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)

    # Создаем все таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Удаляем все таблицы после тестов
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    """Создает тестовую сессию базы данных"""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest.fixture
async def mock_db_session():
    """Мокает сессию базы данных для тестов"""
    async def _get_test_session():
        mock_session = AsyncMock(spec=AsyncSession)
        yield mock_session

    with patch("core.db.get_session", _get_test_session):
        yield


@pytest.fixture
def mock_bot():
    """Мокает объект бота для тестов"""
    from aiogram import Bot
    bot_mock = AsyncMock(spec=Bot)
    with patch("app.bot.handlers.client.bot", bot_mock):
        yield bot_mock
