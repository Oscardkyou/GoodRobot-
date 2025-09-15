#!/usr/bin/env bash
set -euo pipefail

# Wait for Postgres to be ready
python scripts/wait_for_db.py

# Do NOT run migrations here to avoid race conditions with admin service
# alembic upgrade heads

# Start Telegram bot (long polling)
exec python -m app.bot.main
