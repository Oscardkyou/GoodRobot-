"""Placeholder handlers for партнер role."""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("help_partner"))
async def cmd_help_partner(message: Message) -> None:
    """Temporary stub."""
    await message.answer("Функционал партнера скоро будет доступен.")
