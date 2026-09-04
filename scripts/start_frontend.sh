#!/usr/bin/env bash
set -e

PORT="${PORT:-3000}"
HOST="${HOST:-0.0.0.0}"

echo "✨ [Replit Managed Workflow] Starting Frontend on $HOST:$PORT..."
if [ ! -d "frontend/node_modules" ] || [ ! -d "frontend/node_modules/next" ]; then
  (cd frontend && npm install --include=dev)
fi

cd frontend
if [ "$NODE_ENV" = "production" ] || [ "$APP_ENV" = "production" ] || [ -d ".next" ]; then
  if [ ! -d ".next" ]; then
    echo "🏗️ Building Next.js for production..."
    npm run build
  fi
  exec npm run start -- -p "$PORT" -H "$HOST"
else
  exec npm run dev -- -p "$PORT" -H "$HOST"
fi
