"""SQLAlchemy model for User."""
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .order import Order
    from .partner import Partner
    from .rating import Rating
    from .specialty import Specialty


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    role: Mapped[str] = mapped_column(Enum('client', 'master', 'partner', 'admin', name='user_role_enum'), default='client', nullable=False)
    name: Mapped[str | None] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String, unique=True)
    # zones поле удалено
    rating_avg: Mapped[float] = mapped_column(Float, default=0.0)
    referrer_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey('users.id'))
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Поля для админ-панели
    username: Mapped[str | None] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    orders: Mapped[list["Order"]] = relationship("Order", foreign_keys="[Order.client_id]", back_populates="client")
    master_orders: Mapped[list["Order"]] = relationship("Order", foreign_keys="[Order.master_id]", back_populates="master")
    bids = relationship("Bid", back_populates="master")
    ratings_given: Mapped[list["Rating"]] = relationship("Rating", foreign_keys="[Rating.rater_id]", back_populates="rater")
    ratings_received: Mapped[list["Rating"]] = relationship("Rating", foreign_keys="[Rating.ratee_id]", back_populates="ratee")
    partner_details: Mapped[Optional["Partner"]] = relationship("Partner", back_populates="user", uselist=False)
    specialties: Mapped[list["Specialty"]] = relationship("Specialty", secondary="master_specialties", back_populates="masters")
    # Связь с категориями заказов, которые выбрал мастер
    categories: Mapped[list["Order"]] = relationship(
        "Order",
        secondary="master_categories",
        primaryjoin="User.id == master_categories.c.user_id",
        secondaryjoin="Order.category == master_categories.c.category",
        viewonly=True,
        overlaps="master_orders"
    )
    referrer: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="referred_users",
        remote_side=[id],
        foreign_keys=[referrer_id],
    )
    referred_users: Mapped[list["User"]] = relationship("User", back_populates="referrer")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, tg_id={self.tg_id}, role='{self.role}')>"
