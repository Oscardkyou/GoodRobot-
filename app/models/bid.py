"""SQLAlchemy model for Bid."""
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .order import Order
    from .user import User


class Bid(Base):
    __tablename__ = "bids"
    __table_args__ = (
        Index("ix_bids_order_created_at", "order_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("orders.id"), nullable=False)
    master_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    price: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(
        Enum("active", "selected", "rejected", name="bid_status_enum"),
        default="active",
        nullable=False,
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="bids")
    master: Mapped["User"] = relationship("User", back_populates="bids")

    def __repr__(self) -> str:
        return f"<Bid(id={self.id}, order_id={self.order_id}, master_id={self.master_id})>"
