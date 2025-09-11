#!/usr/bin/env python3
"""
Управление администраторами GoodRobot
Единый скрипт для создания, просмотра и управления администраторами
"""

import argparse
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


class AdminManager:
    """Менеджер для управления администраторами"""

    def __init__(self, docker_mode: bool = False):
        self.docker_mode = docker_mode
        if docker_mode:
            # Подключение к БД в Docker контейнере
            self.database_url = "postgresql+asyncpg://masterbot:masterbot@postgres:5432/masterbot"
        else:
            # Локальное подключение к БД
            self.database_url = "postgresql+asyncpg://masterbot:masterbot@localhost:5432/masterbot"

        self.engine = create_async_engine(self.database_url)
        self.SessionFactory = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def create_admin_user(self, username: str, password: str, email: str | None = None,
                               name: str | None = None) -> bool:
        """Создает администратора в базе данных"""
        async with self.SessionFactory() as session:
            try:
                # Проверяем, существует ли пользователь с таким именем
                query = select(User).where(User.username == username)
                result = await session.execute(query)
                existing_user = result.scalar_one_or_none()

                if existing_user:
                    print(f"❌ Пользователь с именем '{username}' уже существует!")
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

                print(f"✅ Администратор '{username}' успешно создан!")
                print(f"   ID: {new_admin.id}")
                print(f"   Email: {new_admin.email}")
                print(f"   Имя: {new_admin.name}")
                return True

            except Exception as e:
                print(f"❌ Ошибка при создании администратора: {e}")
                return False

    async def list_admins(self) -> list[dict]:
        """Получает список всех администраторов"""
        async with self.SessionFactory() as session:
            try:
                query = select(User).filter(User.role == "admin").order_by(User.id)
                result = await session.execute(query)
                admins = result.scalars().all()

                admin_list = []
                for admin in admins:
                    admin_list.append({
                        "id": admin.id,
                        "username": admin.username,
                        "name": admin.name,
                        "email": admin.email,
                        "is_active": admin.is_active,
                        "created_at": getattr(admin, 'created_at', None)
                    })

                return admin_list

            except Exception as e:
                print(f"❌ Ошибка при получении списка администраторов: {e}")
                return []

    async def get_admin_by_username(self, username: str) -> dict | None:
        """Получает администратора по username"""
        async with self.SessionFactory() as session:
            try:
                query = select(User).filter(User.role == "admin", User.username == username)
                result = await session.execute(query)
                admin = result.scalar_one_or_none()

                if admin:
                    return {
                        "id": admin.id,
                        "username": admin.username,
                        "name": admin.name,
                        "email": admin.email,
                        "is_active": admin.is_active,
                        "created_at": getattr(admin, 'created_at', None)
                    }
                return None

            except Exception as e:
                print(f"❌ Ошибка при поиске администратора: {e}")
                return None

    async def update_admin_password(self, username: str, new_password: str) -> bool:
        """Обновляет пароль администратора"""
        async with self.SessionFactory() as session:
            try:
                query = select(User).filter(User.role == "admin", User.username == username)
                result = await session.execute(query)
                admin = result.scalar_one_or_none()

                if not admin:
                    print(f"❌ Администратор '{username}' не найден!")
                    return False

                admin.hashed_password = get_password_hash(new_password)
                await session.commit()

                print(f"✅ Пароль администратора '{username}' успешно обновлен!")
                return True

            except Exception as e:
                print(f"❌ Ошибка при обновлении пароля: {e}")
                return False

    async def toggle_admin_status(self, username: str) -> bool:
        """Включает/выключает статус администратора"""
        async with self.SessionFactory() as session:
            try:
                query = select(User).filter(User.role == "admin", User.username == username)
                result = await session.execute(query)
                admin = result.scalar_one_or_none()

                if not admin:
                    print(f"❌ Администратор '{username}' не найден!")
                    return False

                admin.is_active = not admin.is_active
                await session.commit()

                status = "активирован" if admin.is_active else "деактивирован"
                print(f"✅ Администратор '{username}' {status}!")
                return True

            except Exception as e:
                print(f"❌ Ошибка при изменении статуса: {e}")
                return False


def print_admin_table(admins: list[dict]):
    """Выводит таблицу администраторов"""
    if not admins:
        print("📝 Администраторы не найдены")
        return

    print("\n📋 Список администраторов:")
    print("-" * 80)
    print(f"{'ID':<5} {'Username':<15} {'Name':<15} {'Email':<25} {'Status':<10}")
    print("-" * 80)

    for admin in admins:
        status = "✅ Активен" if admin["is_active"] else "❌ Неактивен"
        print(f"{admin['id']:<5} {admin['username']:<15} {admin['name']:<15} {admin['email']:<25} {status:<10}")

    print("-" * 80)
    print(f"Всего администраторов: {len(admins)}")


async def main():
    parser = argparse.ArgumentParser(description="Управление администраторами GoodRobot")
    parser.add_argument("--docker", action="store_true", help="Использовать подключение к Docker БД")
    parser.add_argument("--list", action="store_true", help="Показать список администраторов")

    subparsers = parser.add_subparsers(dest="command", help="Команды")

    # Команда создания администратора
    create_parser = subparsers.add_parser("create", help="Создать администратора")
    create_parser.add_argument("username", help="Имя пользователя")
    create_parser.add_argument("password", help="Пароль")
    create_parser.add_argument("--email", help="Email (опционально)")
    create_parser.add_argument("--name", help="Полное имя (опционально)")

    # Команда изменения пароля
    password_parser = subparsers.add_parser("password", help="Изменить пароль администратора")
    password_parser.add_argument("username", help="Имя пользователя")
    password_parser.add_argument("new_password", help="Новый пароль")

    # Команда включения/выключения администратора
    toggle_parser = subparsers.add_parser("toggle", help="Включить/выключить администратора")
    toggle_parser.add_argument("username", help="Имя пользователя")

    # Команда поиска администратора
    find_parser = subparsers.add_parser("find", help="Найти администратора")
    find_parser.add_argument("username", help="Имя пользователя")

    args = parser.parse_args()

    manager = AdminManager(docker_mode=args.docker)

    if args.list:
        # Показать список администраторов
        admins = await manager.list_admins()
        print_admin_table(admins)

    elif args.command == "create":
        # Создать администратора
        success = await manager.create_admin_user(
            username=args.username,
            password=args.password,
            email=args.email,
            name=args.name
        )

        if success:
            print("\n🔑 Данные для входа в админ-панель:")
            print("   URL: http://localhost:8000/login")
            print(f"   Логин: {args.username}")
            print(f"   Пароль: {args.password}")

    elif args.command == "password":
        # Изменить пароль
        await manager.update_admin_password(args.username, args.new_password)

    elif args.command == "toggle":
        # Включить/выключить администратора
        await manager.toggle_admin_status(args.username)

    elif args.command == "find":
        # Найти администратора
        admin = await manager.get_admin_by_username(args.username)
        if admin:
            print("✅ Найден администратор:")
            print(f"   ID: {admin['id']}")
            print(f"   Username: {admin['username']}")
            print(f"   Name: {admin['name']}")
            print(f"   Email: {admin['email']}")
            print(f"   Status: {'Активен' if admin['is_active'] else 'Неактивен'}")
        else:
            print(f"❌ Администратор '{args.username}' не найден!")

    else:
        # По умолчанию создать администратора superadmin
        print("🚀 Создание администратора по умолчанию...")
        success = await manager.create_admin_user("superadmin", "admin123")
        if success:
            print("\n🔑 Данные для входа в админ-панель:")
            print("   URL: http://localhost:8000/login")
            print("   Логин: superadmin")
            print("   Пароль: admin123")


if __name__ == "__main__":
    asyncio.run(main())
