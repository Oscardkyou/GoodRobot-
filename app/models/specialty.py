from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship

from app.models.base import Base

# Таблица связи между мастерами и специальностями (many-to-many)
master_specialties = Table(
    "master_specialties",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("specialty_id", Integer, ForeignKey("specialties.id"), primary_key=True),
)


class Specialty(Base):
    """Модель специальности мастера"""
    __tablename__ = "specialties"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)

    # Связь с мастерами (many-to-many)
    masters = relationship(
        "User",
        secondary=master_specialties,
        back_populates="specialties"
    )
