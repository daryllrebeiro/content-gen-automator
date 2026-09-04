#!/usr/bin/env bash
set -e

MODE="${1:-${SERVICE:-all}}"
HOST="${HOST:-0.0.0.0}"

# Detect production deployment environment on Replit
if [ -n "$REPL_ENVIRONMENT" ] && [ "$REPL_ENVIRONMENT" = "production" ]; then
  export NODE_ENV="production"
  export APP_ENV="production"
fi
if [ -n "$DEPLOYMENT_ID" ]; then
  export NODE_ENV="production"
  export APP_ENV="production"
fi

install_backend_if_needed() {
  if ! python3 -c "import fastapi, uvicorn, pydantic, google.adk" 2>/dev/null; then
    echo "📦 Checking/installing Python backend dependencies..."
    python3 -m pip install --no-cache-dir -r backend/requirements.txt --quiet || \
    python3 -m pip install --no-cache-dir --break-system-packages -r backend/requirements.txt --quiet
  fi
}

install_frontend_if_needed() {
  if [ ! -d "frontend/node_modules" ] || [ ! -d "frontend/node_modules/next" ]; then
    echo "🎨 Installing frontend dependencies using npm..."
    (cd frontend && npm install --include=dev)
  fi
}

if [ "$MODE" = "backend" ]; then
  PORT="${PORT:-8000}"
  echo "🚀 [Replit Workflow: Backend] Launching FastAPI on $HOST:$PORT..."
  install_backend_if_needed
  cd backend && exec python3 -m uvicorn app.main:app --host "$HOST" --port "$PORT"

elif [ "$MODE" = "frontend" ]; then
  PORT="${PORT:-3000}"
  echo "✨ [Replit Workflow: Frontend] Launching Studio UI on $HOST:$PORT..."
  install_frontend_if_needed
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

else
  echo "🎬 Starting ContentGenAutomator Studio (Multi-Process Mode)..."

  install_backend_if_needed
  install_frontend_if_needed

  # Dynamic Port Assignment & Port Collision Prevention
  FRONTEND_PORT="${PORT:-3000}"
  if [ "$FRONTEND_PORT" = "8000" ]; then
    BACKEND_PORT="${BACKEND_PORT:-8001}"
  else
    BACKEND_PORT="${BACKEND_PORT:-8000}"
  fi
  export BACKEND_URL="http://127.0.0.1:${BACKEND_PORT}"

  # 1. Start FastAPI backend in background
  echo "🚀 Launching FastAPI Backend on $HOST:$BACKEND_PORT..."
  (cd backend && exec python3 -m uvicorn app.main:app --host "$HOST" --port "$BACKEND_PORT") &
  BACKEND_PID=$!

  # 2. Start Frontend (listening on the public $PORT)
  echo "✨ Launching Studio UI on $HOST:$FRONTEND_PORT (proxying /api to $BACKEND_URL)..."
  cd frontend
  if [ "$NODE_ENV" = "production" ] || [ "$APP_ENV" = "production" ] || [ -d ".next" ]; then
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
  trap "kill -TERM $BACKEND_PID $FRONTEND_PID 2>/dev/null || true" EXIT INT TERM
  wait -n $BACKEND_PID $FRONTEND_PID || true
fi
