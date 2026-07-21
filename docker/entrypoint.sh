#!/bin/bash
set -euo pipefail

export PYTHONPATH=/app

echo "Running database migrations..."
alembic -c migrations/alembic.ini upgrade head

echo "Starting API server..."
exec uvicorn src.backend.main:app --host 0.0.0.0 --port 8000 --workers 4
