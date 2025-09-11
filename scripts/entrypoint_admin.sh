#!/usr/bin/env bash
set -euo pipefail

# Wait for Postgres to be ready
python scripts/wait_for_db.py

# Run migrations (handles multiple heads)
alembic upgrade heads

# Start Admin (FastAPI / Uvicorn) с hot reload
exec uvicorn run_admin:app --host 0.0.0.0 --port "${ADMIN_PORT:-8000}" --log-level info --reload
