"""Entry point for Telegram bot using Aiogram 3.x."""
from __future__ import annotations

import asyncio
import logging

from aiogram.types import BotCommand

from app.bot import bot, dp
from app.bot.handlers import client, master, partner
from app.bot.handlers import tracking
from app.bot.handlers import chat
from app.bot.handlers import ai_assistant
from app.bot.logging_setup import configure_logging
from app.bot.middlewares.logging_middleware import LoggingMiddleware


def register_handlers() -> None:
    dp.include_router(client.router)
    dp.include_router(master.router)
    dp.include_router(partner.router)
    dp.include_router(tracking.router)
    dp.include_router(chat.router)
    dp.include_router(ai_assistant.router)


async def main() -> None:  # pragma: no cover
    """Configure dispatcher, commands and start polling."""
    # dp is imported from app.bot; already created with MemoryStorage in that module.
    # Setup structured logging and middleware
    configure_logging()
    dp.update.middleware(LoggingMiddleware(logging.getLogger("bot")))
    register_handlers()

    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands([
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="menu", description="Главное меню"),
        BotCommand(command="partner_dashboard", description="Партнерский дашборд"),
        BotCommand(command="partner_link", description="Реферальная ссылка"),
        BotCommand(command="partner_stats", description="Статистика партнера"),
        BotCommand(command="partner_payouts", description="История выплат"),
        BotCommand(command="help_partner", description="Помощь для партнеров"),
    ])

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")
