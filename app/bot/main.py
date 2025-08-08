"""Entry point for Telegram bot using Aiogram 3.x."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.bot import bot, dp
from app.bot.handlers import client, master, partner

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")


def register_handlers() -> None:
    dp.include_router(client.router)
    dp.include_router(master.router)
    dp.include_router(partner.router)


async def main() -> None:  # pragma: no cover
    """Configure dispatcher, commands and start polling."""
    # dp is imported from app.bot; already created with MemoryStorage in that module.
    register_handlers()

    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands([
        BotCommand(command="start", description="Начать работу"),
    ])

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")
