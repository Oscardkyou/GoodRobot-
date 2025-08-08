"""SQLAlchemy model for Partner."""
from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .base import Base


class Partner(Base):
    __tablename__ = "partners"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), unique=True, nullable=False)
    slug = Column(String, unique=True)
    referral_code = Column(String, unique=True)
    payout_percent = Column(Integer, default=5)

    # Relationship
    user = relationship("User", back_populates="partner_details")

    def __repr__(self):
        return f"<Partner(id={self.id}, user_id={self.user_id})>"
