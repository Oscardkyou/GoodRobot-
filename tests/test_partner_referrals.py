import random

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.models import User, Partner, Order
from app.models.payout import Payout
from core.db import SessionFactory, engine
from app.models.base import Base
from app.bot.handlers.partner import get_partner_statistics


@pytest_asyncio.fixture(scope="module", autouse=True)
async def _db_schema():
    # Create all tables for SQLite test DB
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_partner_statistics_counts_referrals_and_earnings():
    # Arrange: create a partner user and partner record
    tg_partner = random.randint(10_000_000, 9_999_999_999)
    tg_client1 = random.randint(10_000_000, 9_999_999_999)
    tg_client2 = random.randint(10_000_000, 9_999_999_999)
    tg_master = random.randint(10_000_000, 9_999_999_999)

    async with SessionFactory() as session:
        # Partner user
        partner_user = User(id=random.randint(1_000_000_000_000, 9_000_000_000_000), tg_id=tg_partner, role="partner", name="Partner Test")
        session.add(partner_user)
        await session.commit()

        # Partner entry with referral code
        partner = Partner(id=random.randint(1_000_000_000_000, 9_000_000_000_000), user_id=partner_user.id, slug=f"partner_{tg_partner}", referral_code=f"REF{tg_partner:08d}")
        session.add(partner)
        await session.commit()

        # Master user (needed for payouts)
        master_user = User(id=random.randint(1_000_000_000_000, 9_000_000_000_000), tg_id=tg_master, role="master", name="Master")
        session.add(master_user)
        await session.commit()

        # Two referred clients
        client1 = User(id=random.randint(1_000_000_000_000, 9_000_000_000_000), tg_id=tg_client1, role="client", name="Client1", referrer_id=partner_user.id)
        client2 = User(id=random.randint(1_000_000_000_000, 9_000_000_000_000), tg_id=tg_client2, role="client", name="Client2", referrer_id=partner_user.id)
        session.add_all([client1, client2])
        await session.commit()

        # Create completed order for client1 with paid payout
        order1 = Order(id=random.randint(1_000_000_000_000, 9_000_000_000_000), client_id=client1.id, master_id=master_user.id, category="Сантехника", description="test", status="done")
        session.add(order1)
        await session.commit()

        payout_paid = Payout(
            id=random.randint(1_000_000_000_000, 9_000_000_000_000),
            order_id=order1.id,
            master_id=master_user.id,
            amount_master=9_500,
            amount_service=0,
            amount_partner=500,
            status="paid",
        )
        session.add(payout_paid)
        await session.commit()

        # Create pending payout for client2 (not yet earned)
        order2 = Order(id=random.randint(1_000_000_000_000, 9_000_000_000_000), client_id=client2.id, master_id=master_user.id, category="Электрика", description="test2", status="done")
        session.add(order2)
        await session.commit()

        payout_pending = Payout(
            id=random.randint(1_000_000_000_000, 9_000_000_000_000),
            order_id=order2.id,
            master_id=master_user.id,
            amount_master=19_000,
            amount_service=0,
            amount_partner=1_000,
            status="pending",
        )
        session.add(payout_pending)
        await session.commit()

        # Act
        stats = await get_partner_statistics(session, partner_user.id)

        # Assert
        assert stats["referred_users"] == 2
        assert stats["completed_orders"] == 1
        assert int(stats["total_earned"]) == 500
        assert stats["pending_payouts"] == 1
        assert int(stats["pending_amount"]) == 1000

        # Cleanup
        await session.execute(delete(Payout).where(Payout.order_id.in_([order1.id, order2.id])))
        await session.execute(delete(Order).where(Order.id.in_([order1.id, order2.id])))
        await session.execute(delete(Partner).where(Partner.id == partner.id))
        await session.execute(delete(User).where(User.id.in_([client1.id, client2.id, partner_user.id, master_user.id])))
        await session.commit()
