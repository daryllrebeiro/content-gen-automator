#!/usr/bin/env bash
set -e

PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

echo "🚀 [Replit Managed Workflow] Starting FastAPI Backend on $HOST:$PORT..."
pip install -r backend/requirements.txt --quiet
cd backend && exec uvicorn app.main:app --host "$HOST" --port "$PORT"
