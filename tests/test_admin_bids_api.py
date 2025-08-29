import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.user import User
from app.models.order import Order
from app.models.bid import Bid
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
async def test_master_user(db: AsyncSession):
    master = User(
        username="test_master",
        hashed_password="$2b$12$test_hash",
        email="master@example.com",
        role="master",
        tg_id=12346,
        name="Test Master",
        is_active=True
    )
    db.add(master)
    await db.commit()
    await db.refresh(master)
    return master

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

@pytest.fixture
async def test_bid(db: AsyncSession, test_master_user, test_order):
    bid = Bid(
        master_id=test_master_user.id,
        order_id=test_order.id,
        amount=1000.0,
        status="pending"
    )
    db.add(bid)
    await db.commit()
    await db.refresh(bid)
    return bid

@pytest.mark.asyncio
async def test_get_bids_list(client, test_admin_user):
    # Тест получения списка ставок
    response = client.get("/api/bids", headers={"Authorization": f"Bearer {test_admin_user.id}"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_get_bid_by_id(client, test_admin_user, test_bid):
    # Тест получения информации о конкретной ставке
    response = client.get(f"/api/bids/{test_bid.id}", headers={"Authorization": f"Bearer {test_admin_user.id}"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_bid.id
    assert data["amount"] == 1000.0

@pytest.mark.asyncio
async def test_accept_bid(client, test_admin_user, test_bid, test_order, db: AsyncSession):
    # Тест принятия ставки
    response = client.post(f"/api/bids/{test_bid.id}/accept", headers={"Authorization": f"Bearer {test_admin_user.id}"})
    assert response.status_code == 200
    assert response.json()["message"] == "Ставка принята, мастер назначен на заказ"

    # Проверяем, что статус ставки обновился
    await db.refresh(test_bid)
    assert test_bid.status == "accepted"

    # Проверяем, что заказ обновился
    await db.refresh(test_order)
    assert test_order.status == "in_progress"
    assert test_order.master_id == test_bid.master_id
    assert test_order.price == test_bid.amount

@pytest.mark.asyncio
async def test_reject_bid(client, test_admin_user, test_bid, db: AsyncSession):
    # Тест отклонения ставки
    response = client.post(f"/api/bids/{test_bid.id}/reject", headers={"Authorization": f"Bearer {test_admin_user.id}"})
    assert response.status_code == 200
    assert response.json()["message"] == "Ставка отклонена"

    # Проверяем, что статус ставки обновился
    await db.refresh(test_bid)
    assert test_bid.status == "rejected"
