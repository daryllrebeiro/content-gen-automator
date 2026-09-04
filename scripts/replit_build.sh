#!/usr/bin/env bash
set -e

echo "📦 [Replit Build] Step 1/2: Installing Python backend requirements..."
python3 -m pip install --no-cache-dir -r backend/requirements.txt --quiet || \
python3 -m pip install --no-cache-dir --break-system-packages -r backend/requirements.txt --quiet

echo "🎨 [Replit Build] Step 2/2: Installing frontend dependencies & building Next.js bundle..."
cd frontend

# 1. Clean up previous .next cache and any corrupted/mismatched node_modules
echo "🧹 Clearing previous .next build cache and corrupted node_modules..."
rm -rf .next
if [ -d "node_modules/.ignored" ] || [ ! -d "node_modules/next" ]; then
  rm -rf node_modules
fi

# 2. Always use frontend's own npm lockfile
echo "📦 Installing frontend dependencies with npm using package-lock.json..."
if [ -f "package-lock.json" ]; then
  npm ci --include=dev || npm install --include=dev
else
  npm install --include=dev
fi

# 3. Build Next.js production bundle
echo "🏗️ Building Next.js production bundle..."
npm run build

echo "✅ [Replit Build] Complete! Production bundle ready."
