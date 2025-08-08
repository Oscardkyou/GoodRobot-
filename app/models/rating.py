"""SQLAlchemy model for Rating."""
from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .base import Base


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(BigInteger, primary_key=True, index=True)
    order_id = Column(BigInteger, ForeignKey("orders.id"), unique=True, nullable=False)
    rater_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    ratee_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    stars = Column(Integer, nullable=False)
    comment = Column(String)

    # Relationships
    order = relationship("Order", back_populates="rating")
    rater = relationship("User", foreign_keys=[rater_id], back_populates="ratings_given")
    ratee = relationship("User", foreign_keys=[ratee_id], back_populates="ratings_received")

    def __repr__(self):
        return f"<Rating(id={self.id}, order_id={self.order_id}, stars={self.stars})>"
