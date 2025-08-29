import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.user import User
from app.models.order import Order
from admin.app.main import app

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

@pytest.fixture
async def test_client_user(db: AsyncSession):
    client_user = User(
        username="test_client",
        hashed_password="$2b$12$test_hash",
        email="client@example.com",
        role="client",
        tg_id=12345,
        name="Test Client",
        is_active=True
    )
    db.add(client_user)
    await db.commit()
    await db.refresh(client_user)
    return client_user

@pytest.fixture
async def test_order(db: AsyncSession, test_client_user):
    order = Order(
        client_id=test_client_user.id,
        category="Test Category",
        address="Test Address",
        latitude="55.7558",
        longitude="37.6173",
        status="new"
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order

@pytest.mark.asyncio
async def test_get_orders_list(client, test_admin_user):
    # Тест получения списка заказов
    response = client.get("/api/orders", headers={"Authorization": f"Bearer {test_admin_user.id}"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_get_order_by_id(client, test_admin_user, test_order):
    # Тест получения информации о конкретном заказе
    response = client.get(f"/api/orders/{test_order.id}", headers={"Authorization": f"Bearer {test_admin_user.id}"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_order.id
    assert data["category"] == "Test Category"

@pytest.mark.asyncio
async def test_update_order_status(client, test_admin_user, test_order, db: AsyncSession):
    # Тест обновления статуса заказа
    response = client.put(
        f"/api/orders/{test_order.id}", 
        json={"status": "in_progress"},
        headers={"Authorization": f"Bearer {test_admin_user.id}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "in_progress"

    # Проверяем, что статус обновился в базе
    await db.refresh(test_order)
    assert test_order.status == "in_progress"
