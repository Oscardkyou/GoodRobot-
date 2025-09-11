
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from admin.app.main import app
from app.models.user import User


@pytest.fixture
async def client():
    return TestClient(app)

@pytest.fixture
async def test_admin_user(db: AsyncSession):
    admin = User(
        username="test_admin",
        hashed_password="$2b$12$test_hash",  # Предполагается, что пароль захеширован
        email="admin@example.com",
        role="admin",
        tg_id=0,
        name="Test Admin",
        is_active=True
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    return admin

@pytest.mark.asyncio
async def test_get_users_list(client, test_admin_user):
    # Тест получения списка пользователей
    response = client.get("/api/users", headers={"Authorization": f"Bearer {test_admin_user.id}"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_get_user_by_id(client, test_admin_user):
    # Тест получения информации о конкретном пользователе
    response = client.get(f"/api/users/{test_admin_user.id}", headers={"Authorization": f"Bearer {test_admin_user.id}"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_admin_user.id
    assert data["username"] == "test_admin"

@pytest.mark.asyncio
async def test_block_user(client, test_admin_user, db: AsyncSession):
    # Создаем тестового пользователя для блокировки
    user = User(
        username="test_block_user",
        hashed_password="$2b$12$test_hash",
        email="user@example.com",
        role="client",
        tg_id=12345,
        name="Test User",
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Блокируем пользователя
    response = client.post(f"/api/users/{user.id}/block", headers={"Authorization": f"Bearer {test_admin_user.id}"})
    assert response.status_code == 200
    assert response.json()["message"] == "Пользователь заблокирован"

    # Проверяем, что пользователь заблокирован
    await db.refresh(user)
    assert user.is_active == False

@pytest.mark.asyncio
async def test_unblock_user(client, test_admin_user, db: AsyncSession):
    # Создаем тестового пользователя для разблокировки
    user = User(
        username="test_unblock_user",
        hashed_password="$2b$12$test_hash",
        email="user2@example.com",
        role="client",
        tg_id=12346,
        name="Test User 2",
        is_active=False
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Разблокируем пользователя
    response = client.post(f"/api/users/{user.id}/unblock", headers={"Authorization": f"Bearer {test_admin_user.id}"})
    assert response.status_code == 200
    assert response.json()["message"] == "Пользователь разблокирован"

    # Проверяем, что пользователь разблокирован
    await db.refresh(user)
    assert user.is_active == True
