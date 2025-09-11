from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core.config import get_settings

# Получаем настройки
settings = get_settings()

# Создаем асинхронный движок SQLAlchemy
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Устанавливаем echo=False, так как DB_ECHO отсутствует
    future=True,
)

# Создаем фабрику сессий
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db() -> AsyncSession:
    """
    Зависимость для получения асинхронной сессии базы данных.
    Используется в FastAPI endpoints.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
