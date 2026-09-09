#!/usr/bin/env bash
set -e

PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"
export EXPORT_SIGNING_SECRET="${EXPORT_SIGNING_SECRET:-0f8e9b42c67d1a3e5f8b9c0d2e4a6f8b0f8e9b42c67d1a3e5f8b9c0d2e4a6f8b}"
export INTEGRATION_SERVICE_TOKEN="${INTEGRATION_SERVICE_TOKEN:-cga-replit-integration-service-token-v1-secret}"

echo "🚀 [Replit Managed Workflow] Starting FastAPI Backend on $HOST:$PORT..."
if ! python3 -c "import fastapi, uvicorn, pydantic, google.adk" 2>/dev/null; then
  echo "📦 Checking/installing Python dependencies..."
  python3 -m pip install --no-cache-dir -r backend/requirements.txt --quiet || \
  python3 -m pip install --no-cache-dir --break-system-packages -r backend/requirements.txt --quiet
fi
cd backend && exec python3 -m uvicorn app.main:app --host "$HOST" --port "$PORT"
