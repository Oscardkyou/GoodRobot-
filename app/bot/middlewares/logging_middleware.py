"""Aiogram 3 logging middleware for incoming updates and errors."""
from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class LoggingMiddleware(BaseMiddleware):
    """Log each Message/CallbackQuery before and after handler execution, and on errors."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("bot")

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        start = time.perf_counter()
        try:
            if isinstance(event, Message):
                user_id = getattr(event.from_user, "id", None)
                chat_id = getattr(event.chat, "id", None)
                text = event.text
                self.logger.info(
                    f"Incoming message user_id={user_id} chat_id={chat_id} text={text!r}",
                    extra={
                        "type": "message",
                        "user_id": user_id,
                        "chat_id": chat_id,
                        "text": text,
                    }
                )
            elif isinstance(event, CallbackQuery):
                user_id = getattr(event.from_user, "id", None)
                chat_id = getattr(getattr(event.message, "chat", None), "id", None)
                data_val = event.data
                self.logger.info(
                    f"Incoming callback user_id={user_id} chat_id={chat_id} data={data_val!r}",
                    extra={
                        "type": "callback",
                        "user_id": user_id,
                        "chat_id": chat_id,
                        "data": data_val,
                    }
                )
            result = await handler(event, data)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            if isinstance(event, Message):
                user_id = getattr(event.from_user, "id", None)
                chat_id = getattr(event.chat, "id", None)
                self.logger.info(
                    f"Handled message user_id={user_id} chat_id={chat_id} took_ms={elapsed_ms}",
                    extra={
                        "type": "message",
                        "user_id": user_id,
                        "chat_id": chat_id,
                        "took_ms": elapsed_ms,
                    }
                )
            elif isinstance(event, CallbackQuery):
                user_id = getattr(event.from_user, "id", None)
                chat_id = getattr(getattr(event.message, "chat", None), "id", None)
                self.logger.info(
                    f"Handled callback user_id={user_id} chat_id={chat_id} took_ms={elapsed_ms}",
                    extra={
                        "type": "callback",
                        "user_id": user_id,
                        "chat_id": chat_id,
                        "took_ms": elapsed_ms,
                    }
                )
            return result
        except Exception:
            # Log exception with context and re-raise
            if isinstance(event, Message):
                user_id = getattr(event.from_user, "id", None)
                chat_id = getattr(event.chat, "id", None)
                text = event.text
                self.logger.exception(
                    f"Handler error (message) user_id={user_id} chat_id={chat_id} text={text!r}",
                    extra={
                        "type": "message",
                        "user_id": user_id,
                        "chat_id": chat_id,
                        "text": text,
                    }
                )
            elif isinstance(event, CallbackQuery):
                user_id = getattr(event.from_user, "id", None)
                chat_id = getattr(getattr(event.message, "chat", None), "id", None)
                data_val = event.data
                self.logger.exception(
                    f"Handler error (callback) user_id={user_id} chat_id={chat_id} data={data_val!r}",
                    extra={
                        "type": "callback",
                        "user_id": user_id,
                        "chat_id": chat_id,
                        "data": data_val,
                    }
                )
            else:
                self.logger.exception("Handler error (unknown event)")
            raise
