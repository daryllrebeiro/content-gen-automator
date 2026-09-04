#!/usr/bin/env bash
set -e

PORT="${PORT:-3000}"
HOST="${HOST:-0.0.0.0}"

echo "✨ [Replit Managed Workflow] Starting Frontend on $HOST:$PORT..."
cd frontend
if [ ! -d "node_modules" ]; then
  npm install
fi

# Supports Next.js server on dynamic $PORT (dev or production)
if [ "$NODE_ENV" = "production" ] || [ "$APP_ENV" = "production" ]; then
  if [ ! -d ".next" ]; then
    echo "🏗️ Building Next.js for production..."
    npm run build
  fi
  exec npm run start -- -p "$PORT" -H "$HOST"
else
  exec npm run dev -- -p "$PORT" -H "$HOST"
fi
