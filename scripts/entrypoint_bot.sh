#!/usr/bin/env bash
set -euo pipefail

# Wait for Postgres to be ready
python scripts/wait_for_db.py

# Run migrations (handles multiple heads)
alembic upgrade heads

# Start Telegram bot (long polling)
exec python -m app.bot.main
