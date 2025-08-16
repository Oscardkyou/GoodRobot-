import asyncio
import sys
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from core.db import get_session
from admin.app.auth import get_password_hash

async def create_admin(username: str, password: str, email: str = None):
    """Создает администратора в базе данных"""
    async for session in get_session():
        # Проверяем, существует ли пользователь с таким именем
        query = select(User).where(User.username == username)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            print(f"Пользователь {username} уже существует.")
            if user.role != "admin":
                print(f"Обновляем роль пользователя {username} на admin.")
                user.role = "admin"
                await session.commit()
                print(f"Роль пользователя {username} успешно обновлена.")
            return
        
        # Создаем нового администратора
        hashed_password = get_password_hash(password)
        new_admin = User(
            username=username,
            hashed_password=hashed_password,
            email=email,
            role="admin",
            tg_id=0,  # Фиктивный tg_id для администратора
            name=username
            # is_active добавлено в модель, но может отсутствовать в базе данных
        )
        
        session.add(new_admin)
        await session.commit()
        print(f"Администратор {username} успешно создан.")
        return

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Использование: python create_admin.py <username> <password> [email]")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    email = sys.argv[3] if len(sys.argv) > 3 else None
    
    asyncio.run(create_admin(username, password, email))