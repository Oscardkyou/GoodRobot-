"""Services for assigning a master to an order based on a selected bid."""
from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Bid, Order, User


class AssignmentError(Exception):
    """Domain error for assignment failures."""


async def select_bid(session: AsyncSession, bid_id: int, client_tg_id: int) -> Order:
    """Select bid and assign master to order.

    Args:
        session: Async DB session.
        bid_id: Selected bid ID.
        client_tg_id: Telegram ID of the client performing selection.

    Returns:
        Updated Order instance.

    Raises:
        AssignmentError: if bid/order not found or user not authorized or status invalid.
    """
    bid = (await session.execute(select(Bid).where(Bid.id == bid_id))).scalars().first()
    if not bid:
        raise AssignmentError("Ставка не найдена")

    order = (await session.execute(select(Order).where(Order.id == bid.order_id))).scalars().first()
    if not order:
        raise AssignmentError("Заказ не найден")

    # Check acting user is the client who owns this order
    client = (await session.execute(select(User).where(User.tg_id == client_tg_id))).scalars().first()
    if not client or order.client_id != client.id:
        raise AssignmentError("У вас нет прав на этот заказ")

    # Allow selection only for new orders
    if order.status not in ("new",):
        raise AssignmentError("Невозможно выбрать мастера для этого заказа")

    # Assign master and update statuses
    order.master_id = bid.master_id
    order.status = "assigned"

    # Mark selected bid and reject others
    await session.execute(
        update(Bid)
        .where(Bid.order_id == order.id)
        .values(status="rejected")
    )
    await session.execute(
        update(Bid)
        .where(Bid.id == bid.id)
        .values(status="selected")
    )

    await session.commit()
    # Refresh order to return updated instance
    await session.refresh(order)
    return order
