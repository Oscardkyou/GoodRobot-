"""SQLAlchemy model for Partner."""
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User


class Partner(Base):
    __tablename__ = "partners"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), unique=True, nullable=False)
    slug: Mapped[str | None] = mapped_column(String, unique=True)
    referral_code: Mapped[str | None] = mapped_column(String, unique=True)
    payout_percent: Mapped[int] = mapped_column(Integer, default=5)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="partner_details")

    def __repr__(self) -> str:
        return f"<Partner(id={self.id}, user_id={self.user_id})>"
