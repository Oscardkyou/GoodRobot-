#!/usr/bin/env python3
"""
Скрипт для исправления проблем с миграциями в базе данных.
Напрямую удаляет проблемные ENUM типы и сбрасывает статус миграций.
"""

import asyncio
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Подключение к базе данных
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://masterbot:masterbot@postgres:5432/masterbot")
engine = create_async_engine(DATABASE_URL)
SessionFactory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def fix_migrations():
    """Исправляет проблемы с миграциями в базе данных."""
    print("🔧 Начинаем исправление проблем с миграциями...")
    
    async with SessionFactory() as session:
        # 1. Проверяем существование проблемных ENUM типов
        print("🔍 Проверяем существование типа chat_session_status_enum...")
        result = await session.execute(
            text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chat_session_status_enum')")
        )
        exists = result.scalar()
        
        if exists:
            print("⚠️  Найден проблемный тип chat_session_status_enum, удаляем...")
            try:
                # Удаляем зависимые таблицы, если они существуют
                await session.execute(text("DROP TABLE IF EXISTS chat_sessions CASCADE"))
                await session.execute(text("DROP TABLE IF EXISTS chat_messages CASCADE"))
                
                # Удаляем ENUM типы
                await session.execute(text("DROP TYPE IF EXISTS chat_session_status_enum CASCADE"))
                await session.execute(text("DROP TYPE IF EXISTS chat_message_type_enum CASCADE"))
                
                print("✅ Типы успешно удалены.")
            except Exception as e:
                print(f"❌ Ошибка при удалении типов: {e}")
                return
        else:
            print("✅ Тип chat_session_status_enum не найден, пропускаем.")
        
        # 2. Проверяем таблицу миграций alembic_version
        print("🔍 Проверяем таблицу миграций alembic_version...")
        try:
            result = await session.execute(text("SELECT version_num FROM alembic_version"))
            versions = result.scalars().all()
            
            if versions:
                print(f"📊 Текущие версии миграций: {', '.join(versions)}")
                
                # Находим миграцию перед проблемной
                if 'd90c3fb44c85' in versions:
                    print("⚠️  Найдена проблемная миграция d90c3fb44c85, сбрасываем до предыдущей...")
                    await session.execute(
                        text("DELETE FROM alembic_version WHERE version_num = 'd90c3fb44c85'")
                    )
                    print("✅ Миграция удалена из alembic_version.")
                else:
                    print("✅ Проблемная миграция не найдена в alembic_version.")
            else:
                print("⚠️  Таблица alembic_version пуста или не существует.")
        except Exception as e:
            print(f"❌ Ошибка при проверке таблицы миграций: {e}")
            return
        
        # Фиксируем изменения
        await session.commit()
        print("✅ Изменения успешно сохранены.")
    
    print("🎉 Исправление миграций завершено. Теперь перезапустите проект.")


if __name__ == "__main__":
    asyncio.run(fix_migrations())