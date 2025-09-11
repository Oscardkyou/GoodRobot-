"""SQLAlchemy model for Payouts (комиссии и выплаты)."""
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .order import Order
    from .user import User


class Payout(Base):
    __tablename__ = "payouts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("orders.id"), unique=True, nullable=False)
    master_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)

    amount_master: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_service: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_partner: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    status: Mapped[str] = mapped_column(
        Enum("pending", "paid", "failed", name="payout_status_enum"),
        default="pending",
        nullable=False,
        index=True,
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relations
    order: Mapped["Order"] = relationship("Order", back_populates="payout")
    master: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<Payout(order_id={self.order_id}, master_id={self.master_id}, "
            f"status='{self.status}')>"
        )
