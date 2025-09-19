from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from admin.app import create_app
from admin.app.auth import get_current_admin
from core.db import get_session
from app.models.base import Base


@pytest.mark.asyncio
async def test_admin_specialties_crud_and_assign(test_engine):
    """Проверяем CRUD по специальностям и назначение специальностей мастеру."""
    # Создаем FastAPI app и переопределяем зависимости
    app = create_app()

    # Готовим sessionmaker на базе test_engine
    async_session = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_session():
        async with async_session() as session:
            yield session

    def override_get_current_admin():
        return SimpleNamespace(username="admin", is_active=True)

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_admin] = override_get_current_admin

    client = TestClient(app)

    # 1) Создаем специальность
    resp = client.post(
        "/specialties/api/specialties",
        json={"name": "Электрика", "is_active": True},
    )
    assert resp.status_code == 200, resp.text
    spec = resp.json()
    assert spec["name"] == "Электрика"
    spec_id = spec["id"]

    # 2) Список специальностей
    resp = client.get("/specialties/api")
    assert resp.status_code == 200
    data = resp.json()
    assert any(s["id"] == spec_id for s in data)

    # 3) Обновляем специальность
    resp = client.put(
        f"/specialties/api/specialties/{spec_id}",
        json={"name": "Электромонтаж", "is_active": False},
    )
    assert resp.status_code == 200
    upd = resp.json()
    assert upd["name"] == "Электромонтаж"
    assert upd["is_active"] is False

    # 4) Создаем мастера через админ-API
    # минимально уникальные данные
    master_payload = {
        "telegram_id": 987654321,
        "username": "master_user",
        "full_name": "Тест Мастер",
        "phone": "+70000000000",
        "password": "pass",
        "specialty_ids": [],
    }
    resp = client.post("/masters/api", json=master_payload)
    assert resp.status_code == 201 or resp.status_code == 200
    master = resp.json()
    master_id = master["id"]

    # 5) Назначаем мастеру специальность
    resp = client.post(
        f"/specialties/api/masters/{master_id}/specialties",
        json={"specialty_ids": [spec_id]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "success"

    # 6) Негатив: назначение несуществующей специальности
    resp = client.post(
        f"/specialties/api/masters/{master_id}/specialties",
        json={"specialty_ids": [999999]},
    )
    assert resp.status_code == 400

    # 7) Удаляем специальность
    resp = client.delete(f"/specialties/api/specialties/{spec_id}")
    assert resp.status_code == 204
