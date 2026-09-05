#!/bin/sh
set -eu

alembic upgrade head
python -m app.seeding.seed_dev
exec uvicorn app.main:app --host "${APP_HOST:-0.0.0.0}" --port "${APP_PORT:-8000}"
