"""SQLAlchemy model for Payouts (комиссии и выплаты)."""
from sqlalchemy import BigInteger, Column, DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.orm import relationship

from .base import Base


class Payout(Base):
    __tablename__ = "payouts"

    id = Column(BigInteger, primary_key=True, index=True)
    order_id = Column(BigInteger, ForeignKey("orders.id"), unique=True, nullable=False)
    master_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)

    amount_master = Column(Integer, nullable=False)
    amount_service = Column(Integer, nullable=False)
    amount_partner = Column(Integer, nullable=False, default=0)

    status = Column(
        Enum("pending", "paid", "failed", name="payout_status_enum"),
        default="pending",
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, server_default=func.now())

    # Relations
    order = relationship("Order", back_populates="payout")
    master = relationship("User")

    def __repr__(self):
        return (
            f"<Payout(order_id={self.order_id}, master_id={self.master_id}, "
            f"status='{self.status}')>"
        )
