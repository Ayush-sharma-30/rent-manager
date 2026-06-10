#!/bin/sh
# Container entrypoint for the web service: apply migrations, seed demo data
# (idempotent — skips if an org already exists), then start the API on the port
# the host assigns ($PORT on Render; defaults to 8000 locally).
set -e

alembic upgrade head
python -m scripts.seed_dev_data
exec uvicorn rent_manager.main:app --host 0.0.0.0 --port "${PORT:-8000}"
