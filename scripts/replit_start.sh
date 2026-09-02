#!/usr/bin/env bash
set -e

echo "🎬 Starting ContentGenAutomator Studio on Replit..."

# Install backend dependencies if needed
echo "📦 Checking Python backend dependencies..."
pip install -r backend/requirements.txt --quiet

# Install frontend dependencies if needed
echo "🎨 Checking Next.js frontend dependencies..."
cd frontend
if [ ! -d "node_modules" ]; then
  npm install
fi
cd ..

# Start FastAPI backend in background
echo "🚀 Launching FastAPI Backend on port 8000..."
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Start Next.js frontend
echo "✨ Launching Next.js Studio UI on port 3000..."
cd frontend && npm run dev -- -p 3000

# Cleanup on exit
trap "kill $BACKEND_PID" EXIT
