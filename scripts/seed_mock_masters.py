import asyncio

from sqlalchemy import or_, select

from admin.app.auth import get_password_hash
from app.models.user import User
from core.db import SessionFactory

MASTERS = [
    {
        "tg_id": 900001,
        "username": "mock_master1",
        "name": "Mock Master One",
        "phone": "+77010000001",
        "zones": ["1", "2"],
        "password": "Password123!",
    },
    {
        "tg_id": 900002,
        "username": "mock_master2",
        "name": "Mock Master Two",
        "phone": "+77010000002",
        "zones": ["2", "3"],
        "password": "Password123!",
    },
    {
        "tg_id": 900003,
        "username": "mock_master3",
        "name": "Mock Master Three",
        "phone": "+77010000003",
        "zones": ["3"],
        "password": "Password123!",
    },
]


async def main() -> None:
    created = 0
    async with SessionFactory() as session:
        for m in MASTERS:
            # Пропускаем, если уже есть по tg_id/username/phone
            res = await session.execute(
                select(User).filter(
                    or_(
                        User.tg_id == m["tg_id"],
                        User.username == m["username"],
                        User.phone == m["phone"],
                    )
                )
            )
            if res.scalar_one_or_none():
                continue

            user = User(
                tg_id=m["tg_id"],
                username=m["username"],
                name=m["name"],
                phone=m["phone"],
                zones=m["zones"],  # В БД хранится ARRAY(String)
                role="master",
                is_active=True,
                hashed_password=get_password_hash(m["password"]),
            )
            session.add(user)
            created += 1
        await session.commit()
    print(f"Seed completed: created {created} masters")


if __name__ == "__main__":
    asyncio.run(main())
