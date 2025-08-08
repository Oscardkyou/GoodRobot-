"""Client (заказчик) handlers."""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Greet client and show help."""
    await message.answer("Здравствуйте! Я помогу найти мастера. Напишите, что нужно починить.")
