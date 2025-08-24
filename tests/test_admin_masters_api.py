"""
Async API tests for admin masters management endpoints.

This test covers:
- Creating an admin (helper) and obtaining a JWT token
- Creating a master via /masters/api
- Deleting the created master via /masters/api/{id}
"""
from __future__ import annotations

import asyncio
import random
import string
from typing import Any, Dict

import pytest
import httpx

from admin.app import create_app
from core.db import SessionFactory
from admin.app.auth import get_password_hash
from sqlalchemy import select
from app.models.user import User


def _rand_suffix(n: int = 6) -> str:
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(n))


@pytest.mark.asyncio
async def test_create_and_delete_master():
    # Arrange: create admin directly in DB to avoid tg_id unique conflicts
    admin_username = f"admin_test_{_rand_suffix()}"
    admin_password = "Adm1n_test_pass!"
    async with SessionFactory() as session:
        admin = User(
            username=admin_username,
            hashed_password=get_password_hash(admin_password),
            role="admin",
            tg_id=random.randint(1_000_000_000, 9_999_999_999),
            name="Admin Test",
            is_active=True,
        )
        session.add(admin)
        await session.commit()

    app = create_app()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Obtain admin token
        token_resp = await client.post(
            "/token",
            data={"username": admin_username, "password": admin_password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert token_resp.status_code == 200, token_resp.text
        access_token = token_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Create master
        master_username = f"master_{_rand_suffix()}"
        phone_rand = f"+77{random.randint(100000000, 999999999)}"
        payload: Dict[str, Any] = {
            "username": master_username,
            "full_name": "Test Master",
            "phone": phone_rand,
            "role": "master",
            "is_active": True,
            "password": "MasterP@ss1",
            "telegram_id": random.randint(10_000_000, 99_999_999),
            "zones": [1, 2],
        }
        create_resp = await client.post("/masters/api", json=payload, headers=headers)
        assert create_resp.status_code == 201, create_resp.text
        created = create_resp.json()
        assert created["username"] == master_username
        assert created["role"] == "master"
        master_id = created["id"]

        # Verify exists in DB
        async with SessionFactory() as session:
            db_master = (
                await session.execute(select(User).where(User.id == master_id))
            ).scalars().first()
            assert db_master is not None
            assert db_master.role == "master"

        # Delete master
        del_resp = await client.delete(f"/masters/api/{master_id}", headers=headers)
        assert del_resp.status_code == 200, del_resp.text

        # Verify deleted from DB
        async with SessionFactory() as session:
            db_master = (
                await session.execute(select(User).where(User.id == master_id))
            ).scalars().first()
            assert db_master is None
