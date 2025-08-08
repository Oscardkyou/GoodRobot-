"""Bot subpackage with Aiogram setup."""

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from core.config import get_settings

settings = get_settings()

bot = Bot(token=settings.bot_token, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())

__all__ = ["bot", "dp"]
