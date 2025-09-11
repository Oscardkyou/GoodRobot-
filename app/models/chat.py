"""Chat models: ChatSession and ChatMessage."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("orders.id"), nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    master_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        Enum("active", "closed", name="chat_session_status_enum"),
        default="active",
        nullable=False,
        index=True,
    )
    started_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    closed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    last_activity_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # relationships
    order = relationship("Order")
    client = relationship("User", foreign_keys=[client_id])
    master = relationship("User", foreign_keys=[master_id])
    messages: Mapped[list["ChatMessage"]] = relationship("ChatMessage", back_populates="session")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ChatSession(id={self.id}, order_id={self.order_id}, status={self.status})>"


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    sender_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    receiver_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    message_type: Mapped[str] = mapped_column(
        Enum("text", "photo", "video", "voice", "document", name="chat_message_type_enum"),
        default="text",
        nullable=False,
        index=True,
    )
    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped[ChatSession] = relationship("ChatSession", back_populates="messages")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ChatMessage(id={self.id}, session_id={self.session_id}, type={self.message_type})>"
