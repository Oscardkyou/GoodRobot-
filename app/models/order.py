"""SQLAlchemy model for Order."""
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship

from .base import Base


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_category_zone_status", "category", "zone", "status"),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    client_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    category = Column(String, nullable=False, index=True)
    zone = Column(String, index=True)
    address = Column(String)
    when_at = Column(DateTime)
    description = Column(Text)
    media = Column(ARRAY(String))
    status = Column(
        Enum(
            "new", "assigned", "done", "cancelled", name="order_status_enum"
        ),
        default="new",
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    client = relationship("User", back_populates="orders")
    bids = relationship("Bid", back_populates="order")
    rating = relationship("Rating", back_populates="order", uselist=False)
    payout = relationship("Payout", back_populates="order", uselist=False)

    def __repr__(self):
        return f"<Order(id={self.id}, client_id={self.client_id}, status='{self.status}')>"
