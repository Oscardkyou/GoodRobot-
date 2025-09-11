"""SQLAlchemy model for Rating."""
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .order import Order
    from .user import User


class Rating(Base):
    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("orders.id"), unique=True, nullable=False)
    rater_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    ratee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    stars: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(String)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="rating")
    rater: Mapped["User"] = relationship("User", foreign_keys=[rater_id], back_populates="ratings_given")
    ratee: Mapped["User"] = relationship("User", foreign_keys=[ratee_id], back_populates="ratings_received")

    def __repr__(self) -> str:
        return f"<Rating(id={self.id}, order_id={self.order_id}, stars={self.stars})>"
