"""Модель для логирования действий клиента в админке."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class ClientAction(Base):
    """Модель для логирования действий клиента в админке."""
    
    __tablename__ = "client_actions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action_type = Column(String, nullable=False)  # create_order, view_master, select_master, etc.
    description = Column(Text, nullable=True)
    action_data = Column(Text, nullable=True)  # JSON с дополнительными данными
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Отношения
    user = relationship("User", backref="actions")