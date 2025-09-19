#!/usr/bin/env python3
"""
Idempotent creation of a default admin user on startup.
Reads credentials from environment variables and creates an admin if missing.

ENV:
- ADMIN_DEFAULT_USERNAME (default: superadmin)
- ADMIN_DEFAULT_PASSWORD (default: admin123)
- ADMIN_DEFAULT_EMAIL    (optional)
- ADMIN_DEFAULT_NAME     (optional)

Database URL is taken from core.config.Settings (POSTGRES_DSN or parts).
"""
from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Ensure project root on PYTHONPATH
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from admin.app.auth import get_password_hash  # noqa: E402
from app.models.user import User  # noqa: E402
from core.config import get_settings  # noqa: E402


async def ensure_superadmin() -> None:
    settings = get_settings()

    username = os.getenv("ADMIN_DEFAULT_USERNAME", "superadmin")
    password = os.getenv("ADMIN_DEFAULT_PASSWORD", "admin123")
    email = os.getenv("ADMIN_DEFAULT_EMAIL") or f"{username}@example.com"
    name = os.getenv("ADMIN_DEFAULT_NAME") or username

    engine = create_async_engine(settings.database_url, echo=False)
    SessionFactory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionFactory() as session:
        # Try to find existing admin by username
        result = await session.execute(select(User).where(User.username == username))
        existing = result.scalar_one_or_none()
        if existing:
            # Ensure role and is_active are correct; do not change password silently
            changed = False
            if existing.role != "admin":
                existing.role = "admin"
                changed = True
            if existing.is_active is False:
                existing.is_active = True
                changed = True
            if changed:
                await session.commit()
            return

        # Create a new admin with random, non-conflicting tg_id
        # Use large space to avoid conflicts with real telegram IDs
        hashed_password = get_password_hash(password)
        new_admin = User(
            username=username,
            hashed_password=hashed_password,
            email=email,
            role="admin",
            tg_id=10_000_000_000 + abs(hash(username)) % 1_000_000_000,
            name=name,
            is_active=True,
        )
        session.add(new_admin)
        await session.commit()


if __name__ == "__main__":
    asyncio.run(ensure_superadmin())
