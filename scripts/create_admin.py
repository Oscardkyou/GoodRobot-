import asyncio
import os
import random
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from admin.app.auth import get_password_hash
from app.models.user import User

# Создаем локальное подключение к базе данных
DATABASE_URL = "postgresql+asyncpg://masterbot:masterbot@localhost:5432/masterbot"
engine = create_async_engine(DATABASE_URL)
SessionFactory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_admin_user(username, password, email=None, name=None):
    """Создает администратора в базе данных"""
    async with SessionFactory() as session:
        # Проверяем, существует ли пользователь с таким именем
        query = select(User).where(User.username == username)
        result = await session.execute(query)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"Пользователь с именем {username} уже существует!")
            return False

        # Создаем нового администратора
        hashed_password = get_password_hash(password)
        # Генерируем случайный tg_id, который не будет конфликтовать с реальными пользователями
        random_tg_id = random.randint(1_000_000_000, 9_999_999_999)
        new_admin = User(
            username=username,
            hashed_password=hashed_password,
            email=email or f"{username}@example.com",
            role="admin",
            tg_id=random_tg_id,  # Случайный tg_id для администратора
            name=name or username,
            is_active=True
        )

        session.add(new_admin)
        await session.commit()
        await session.refresh(new_admin)

        print(f"Администратор {username} успешно создан с ID: {new_admin.id}")
        return True


async def main():
    username = "superadmin"
    password = "admin123"

    success = await create_admin_user(username, password)
    if success:
        print("Используйте следующие данные для входа:")
        print(f"Логин: {username}")
        print(f"Пароль: {password}")


if __name__ == "__main__":
    asyncio.run(main())
