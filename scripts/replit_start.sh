#!/usr/bin/env bash
set -e

MODE="${1:-${SERVICE:-all}}"
HOST="${HOST:-0.0.0.0}"

if [ "$MODE" = "backend" ]; then
  PORT="${PORT:-8000}"
  echo "🚀 [Replit Workflow: Backend] Launching FastAPI on $HOST:$PORT..."
  pip install -r backend/requirements.txt --quiet
  cd backend && exec uvicorn app.main:app --host "$HOST" --port "$PORT"

elif [ "$MODE" = "frontend" ]; then
  PORT="${PORT:-3000}"
  echo "✨ [Replit Workflow: Frontend] Launching Studio UI on $HOST:$PORT..."
  cd frontend
  if [ ! -d "node_modules" ]; then
    npm install
  fi
  if [ "$NODE_ENV" = "production" ] || [ "$APP_ENV" = "production" ]; then
    if [ ! -d ".next" ]; then
      echo "🏗️ Building Next.js for production..."
      npm run build
    fi
    exec npm run start -- -p "$PORT" -H "$HOST"
  else
    exec npm run dev -- -p "$PORT" -H "$HOST"
  fi

else
  echo "🎬 Starting ContentGenAutomator Studio (Multi-Process Mode)..."

  # 1. Install dependencies
  echo "📦 Checking Python backend dependencies..."
  pip install -r backend/requirements.txt --quiet

  echo "🎨 Checking frontend dependencies..."
  cd frontend
  if [ ! -d "node_modules" ]; then
    npm install
  fi
  cd ..

  # 2. Dynamic Port Assignment
  FRONTEND_PORT="${PORT:-${FRONTEND_PORT:-3000}}"
  BACKEND_PORT="${BACKEND_PORT:-8000}"

  # 3. Start FastAPI backend
  echo "🚀 Launching FastAPI Backend on $HOST:$BACKEND_PORT..."
  cd backend && uvicorn app.main:app --host "$HOST" --port "$BACKEND_PORT" &
  BACKEND_PID=$!
  cd ..

  # 4. Start Frontend
  echo "✨ Launching Studio UI on $HOST:$FRONTEND_PORT..."
  cd frontend
  if [ "$NODE_ENV" = "production" ] || [ "$APP_ENV" = "production" ]; then
    if [ ! -d ".next" ]; then
      echo "🏗️ Building Next.js for production..."
      npm run build
    fi
    npm run start -- -p "$FRONTEND_PORT" -H "$HOST" &
  else
    npm run dev -- -p "$FRONTEND_PORT" -H "$HOST" &
  fi
  FRONTEND_PID=$!
  cd ..

  # Cleanup on exit
  trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true" EXIT INT TERM
  wait $FRONTEND_PID
fi
