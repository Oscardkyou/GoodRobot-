"""Aggregate routers from individual handler modules."""
from aiogram import Router

from . import client, master, partner, tracking, chat, ai_assistant

# The individual handler modules (`client`, `master`, `partner`) each define
# their own `router` instance. They will be attached to the Dispatcher in
# `app.bot.main`, so we do NOT aggregate them here to avoid double-attachment
# errors (RuntimeError: Router is already attached).

# Re-export routers for convenience, if needed elsewhere.
routers = (
    client.router,
    master.router,
    partner.router,
    tracking.router,
    chat.router,
    ai_assistant.router,
)
