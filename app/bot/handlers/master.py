"""Placeholder handlers for мастер role."""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("help_master"))
async def cmd_help_master(message: Message) -> None:
    """Temporary stub."""
    await message.answer("Функционал мастера скоро будет доступен.")
