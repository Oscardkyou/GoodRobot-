"""SQLAlchemy model for User."""
from sqlalchemy import BigInteger, Column, DateTime, Enum, Float, String, func
from sqlalchemy.orm import relationship

from .base import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(BigInteger, primary_key=True, index=True)
    tg_id = Column(BigInteger, unique=True, nullable=False, index=True)
    role = Column(Enum('client', 'master', 'partner', 'admin', name='user_role_enum'), default='client', nullable=False)
    name = Column(String)
    phone = Column(String, unique=True)
    rating_avg = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())

        # Relationships
    orders = relationship("Order", back_populates="client")
    bids = relationship("Bid", back_populates="master")
    ratings_given = relationship("Rating", foreign_keys="[Rating.rater_id]", back_populates="rater")
    ratings_received = relationship("Rating", foreign_keys="[Rating.ratee_id]", back_populates="ratee")
    partner_details = relationship("Partner", back_populates="user", uselist=False)

    def __repr__(self):
        return f"<User(id={self.id}, tg_id={self.tg_id}, role='{self.role}')>"
