"""SQLAlchemy model for Bid."""
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from .base import Base


class Bid(Base):
    __tablename__ = "bids"

    id = Column(BigInteger, primary_key=True, index=True)
    order_id = Column(BigInteger, ForeignKey("orders.id"), nullable=False)
    master_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    price = Column(Integer)
    note = Column(String)
    status = Column(
        Enum("active", "selected", "rejected", name="bid_status_enum"),
        default="active",
        nullable=False,
    )
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    order = relationship("Order", back_populates="bids")
    master = relationship("User", back_populates="bids")

    def __repr__(self):
        return f"<Bid(id={self.id}, order_id={self.order_id}, master_id={self.master_id})>"
