#!/usr/bin/env bash
set -e

PORT="${PORT:-3000}"
HOST="${HOST:-0.0.0.0}"

echo "✨ [Replit Managed Workflow] Starting Frontend on $HOST:$PORT..."
cd frontend
if [ ! -d "node_modules" ]; then
  npm install
fi

# Supports Next.js dev server on dynamic $PORT
exec npm run dev -- -p "$PORT" -H "$HOST"
