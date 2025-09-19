import pytest
from sqlalchemy import select

from app.models import User, Order, Bid
from app.services.assignments import select_bid, AssignmentError


@pytest.mark.asyncio
async def test_select_bid_assigns_master_and_updates_statuses(test_db_session):
    async with test_db_session() as session:
        # Arrange: create client and master users
        client = User(tg_id=1111, role="client", name="Client")
        master1 = User(tg_id=2222, role="master", name="Master One")
        master2 = User(tg_id=3333, role="master", name="Master Two")
        session.add_all([client, master1, master2])
        await session.commit()
        await session.refresh(client)
        await session.refresh(master1)
        await session.refresh(master2)

        # Create order (new)
        order = Order(client_id=client.id, category="plumbing", status="new")
        session.add(order)
        await session.commit()
        await session.refresh(order)

        # Two bids
        bid1 = Bid(order_id=order.id, master_id=master1.id, price=2000, status="active")
        bid2 = Bid(order_id=order.id, master_id=master2.id, price=2500, status="active")
        session.add_all([bid1, bid2])
        await session.commit()
        await session.refresh(bid1)
        await session.refresh(bid2)

        # Act: select first bid by client
        updated_order = await select_bid(session, bid_id=bid1.id, client_tg_id=client.tg_id)

        # Assert: order assigned to master1
        assert updated_order.master_id == master1.id
        assert updated_order.status == "assigned"

        # Bids statuses
        b1 = (await session.execute(select(Bid).where(Bid.id == bid1.id))).scalars().first()
        b2 = (await session.execute(select(Bid).where(Bid.id == bid2.id))).scalars().first()
        assert b1.status == "selected"
        assert b2.status == "rejected"


@pytest.mark.asyncio
async def test_select_bid_rejects_unauthorized_user(test_db_session):
    async with test_db_session() as session:
        # Arrange: users
        client = User(tg_id=1111, role="client", name="Client")
        other_client = User(tg_id=9999, role="client", name="Other")
        master = User(tg_id=2222, role="master", name="Master One")
        session.add_all([client, other_client, master])
        await session.commit()
        await session.refresh(client)
        await session.refresh(other_client)
        await session.refresh(master)

        # Order owned by client
        order = Order(client_id=client.id, category="plumbing", status="new")
        session.add(order)
        await session.commit()
        await session.refresh(order)

        # Bid from master
        bid = Bid(order_id=order.id, master_id=master.id, price=2000, status="active")
        session.add(bid)
        await session.commit()
        await session.refresh(bid)

        # Act + Assert: other client cannot select
        with pytest.raises(AssignmentError):
            await select_bid(session, bid_id=bid.id, client_tg_id=other_client.tg_id)
