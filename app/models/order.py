"""SQLAlchemy model for Order."""
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .bid import Bid
    from .payout import Payout
    from .rating import Rating
    from .user import User


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_category_status", "category", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    master_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)  # ID мастера, которому назначен заказ
    category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # zone поле удалено
    address: Mapped[str | None] = mapped_column(String)
    latitude: Mapped[str | None] = mapped_column(String, nullable=True)  # Широта в формате строки для совместимости
    longitude: Mapped[str | None] = mapped_column(String, nullable=True)  # Долгота в формате строки для совместимости
    location_updated_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)  # Время последнего обновления геолокации
    when_at: Mapped[DateTime | None] = mapped_column(DateTime)
    description: Mapped[str | None] = mapped_column(Text)
    media: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    status: Mapped[str] = mapped_column(
        Enum(
            "new", "assigned", "done", "cancelled", name="order_status_enum"
        ),
        default="new",
        nullable=False,
        index=True,
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    client: Mapped["User"] = relationship("User", foreign_keys=[client_id], back_populates="orders")
    master: Mapped[Optional["User"]] = relationship("User", foreign_keys=[master_id], back_populates="master_orders")
    bids: Mapped[list["Bid"]] = relationship("Bid", back_populates="order")
    rating: Mapped[Optional["Rating"]] = relationship("Rating", back_populates="order", uselist=False)
    payout: Mapped[Optional["Payout"]] = relationship("Payout", back_populates="order", uselist=False)

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, client_id={self.client_id}, status='{self.status}')>"
