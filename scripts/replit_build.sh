#!/usr/bin/env bash
set -e

echo "📦 [Replit Build] Step 1/2: Installing Python backend requirements..."
python3 -m pip install --no-cache-dir -r backend/requirements.txt --quiet || \
python3 -m pip install --no-cache-dir --break-system-packages -r backend/requirements.txt --quiet

echo "🎨 [Replit Build] Step 2/2: Installing frontend dependencies & building Next.js bundle..."
cd frontend

# Clean up any corrupt node_modules from previous failed package manager mismatches
if [ -d "node_modules/.ignored" ]; then
  echo "🧹 Cleaning up mismatched node_modules..."
  rm -rf node_modules
fi

if command -v pnpm >/dev/null 2>&1; then
  echo "⚡ Using pnpm to install and build frontend..."
  pnpm install
  pnpm run build
else
  echo "📦 Using npm to install and build frontend..."
  npm install --include=dev
  npm run build
fi

echo "✅ [Replit Build] Complete! Production bundle ready."
