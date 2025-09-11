
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from admin.app.main import app
from app.models.payout import Payout
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
async def test_payout(db: AsyncSession, test_master_user):
    payout = Payout(
        user_id=test_master_user.id,
        amount=5000.0,
        status="pending",
        payment_method="bank_transfer",
        payment_details="Bank Account: 1234567890",
        description="Test payout"
    )
    db.add(payout)
    await db.commit()
    await db.refresh(payout)
    return payout

@pytest.mark.asyncio
async def test_get_payouts_list(client, test_admin_user):
    # Тест получения списка выплат
    response = client.get("/api/payouts", headers={"Authorization": f"Bearer {test_admin_user.id}"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_get_payout_by_id(client, test_admin_user, test_payout):
    # Тест получения информации о конкретной выплате
    response = client.get(f"/api/payouts/{test_payout.id}", headers={"Authorization": f"Bearer {test_admin_user.id}"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_payout.id
    assert data["amount"] == 5000.0

@pytest.mark.asyncio
async def test_create_payout(client, test_admin_user, test_master_user):
    # Тест создания новой выплаты
    payout_data = {
        "user_id": test_master_user.id,
        "amount": 3000.0,
        "payment_method": "card",
        "payment_details": "Card ending in 1234",
        "description": "New test payout"
    }
    response = client.post("/api/payouts", json=payout_data, headers={"Authorization": f"Bearer {test_admin_user.id}"})
    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 3000.0
    assert data["status"] == "pending"

@pytest.mark.asyncio
async def test_approve_payout(client, test_admin_user, test_payout, db: AsyncSession):
    # Тест подтверждения выплаты
    response = client.post(f"/api/payouts/{test_payout.id}/approve", headers={"Authorization": f"Bearer {test_admin_user.id}"})
    assert response.status_code == 200
    assert response.json()["message"] == "Выплата подтверждена"

    # Проверяем, что статус выплаты обновился
    await db.refresh(test_payout)
    assert test_payout.status == "approved"
    assert test_payout.processed_by == test_admin_user.id
    assert test_payout.processed_at is not None

@pytest.mark.asyncio
async def test_reject_payout(client, test_admin_user, test_payout, db: AsyncSession):
    # Тест отклонения выплаты
    response = client.post(f"/api/payouts/{test_payout.id}/reject", headers={"Authorization": f"Bearer {test_admin_user.id}"})
    assert response.status_code == 200
    assert response.json()["message"] == "Выплата отклонена"

    # Проверяем, что статус выплаты обновился
    await db.refresh(test_payout)
    assert test_payout.status == "rejected"
    assert test_payout.processed_by == test_admin_user.id
    assert test_payout.processed_at is not None
