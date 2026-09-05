#!/usr/bin/env bash
# ==============================================================================
# ContentGenAutomator: Hardened Pull & Deploy Automation Script
# ==============================================================================
# Robust, idempotent script to safely update, build, and deploy the Studio.
# Solves:
#   - Divergent git branch collisions & dirty workspace conflicts
#   - Permission denied errors on helper scripts
#   - Stale / corrupted Next.js build caches
#   - Port collision (EADDRINUSE) between backend & frontend
#   - Secret leakage pre-flight verification
#   - Post-deployment healthcheck polling
# ==============================================================================

set -euo pipefail

# Color palette for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info()    { echo -e "${CYAN}ℹ [DEPLOY]${NC} $1"; }
log_success() { echo -e "${GREEN}✓ [DEPLOY]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}⚠ [DEPLOY]${NC} $1"; }
log_error()   { echo -e "${RED}✗ [DEPLOY]${NC} $1" >&2; }

START_TIME=$(date +%s)
BRANCH="${BRANCH:-master}"
REMOTE="${REMOTE:-origin}"
DO_START=false
DO_BUILD=true
DO_CLEAN=false
USE_REBASE=false
PORT="${PORT:-3000}"

# ── Argument Parsing ──────────────────────────────────────────────────────────

show_help() {
  cat << EOF
Usage: ./scripts/pull-and-deploy.sh [OPTIONS]

Hardened pull, build, and deployment automation for ContentGenAutomator.

Options:
  -s, --start       Start / restart the multi-process server after successful build
  -b, --branch <B>  Specify target branch to pull (default: master)
  -r, --rebase      Use 'git rebase' instead of 'git reset --hard'
  -c, --clean       Aggressively purge .next cache and node_modules before building
  --no-build        Skip Next.js bundle compilation (dependencies only)
  -h, --help        Show this help message
EOF
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -s|--start)
      DO_START=true
      shift
      ;;
    -b|--branch)
      BRANCH="$2"
      shift 2
      ;;
    -r|--rebase)
      USE_REBASE=true
      shift
      ;;
    -c|--clean)
      DO_CLEAN=true
      shift
      ;;
    --no-build)
      DO_BUILD=false
      shift
      ;;
    -h|--help)
      show_help
      ;;
    *)
      log_warn "Unknown option: $1 (ignoring)"
      shift
      ;;
  esac
done

# ── 1. Workspace Verification ─────────────────────────────────────────────────

log_info "Step 1/7: Verifying repository workspace..."

if [ ! -f "backend/requirements.txt" ] || [ ! -f "frontend/package.json" ]; then
  log_error "Must run from repository root! Cannot locate backend/requirements.txt or frontend/package.json."
  exit 1
fi

for cmd in git python3 npm; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    log_error "Required tool '$cmd' is not installed or not in PATH."
    exit 1
  fi
done

# Detect Replit environment
if [ -n "${REPL_ENVIRONMENT:-}" ] || [ -n "${DEPLOYMENT_ID:-}" ] || [ -n "${REPL_ID:-}" ]; then
  log_info "Replit Cloud environment detected. Enforcing production settings."
  export NODE_ENV="production"
  export APP_ENV="production"
  export BYOK_ENFORCED="true"
fi

# ── 2. Git Synchronization & Divergent Branch Protection ─────────────────────

log_info "Step 2/7: Synchronizing code from ${REMOTE}/${BRANCH}..."

PREV_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "initial")

# Stash uncommitted changes if workspace is dirty
if [ -n "$(git status --porcelain)" ]; then
  STASH_TAG="autodeploy-backup-$(date +%s)"
  log_warn "Local modifications detected. Stashing changes to: ${STASH_TAG}"
  git stash push -u -m "$STASH_TAG" >/dev/null 2>&1 || true
fi

# Fetch remote changes
log_info "Fetching ${REMOTE}/${BRANCH}..."
git fetch "$REMOTE" "$BRANCH" --prune --quiet

if [ "$USE_REBASE" = true ]; then
  log_info "Reconciling using git rebase..."
  git rebase "${REMOTE}/${BRANCH}"
else
  log_info "Ensuring clean atomic sync via git reset --hard ${REMOTE}/${BRANCH}..."
  git checkout "$BRANCH" --quiet 2>/dev/null || true
  git reset --hard "${REMOTE}/${BRANCH}" --quiet
fi

NEW_HASH=$(git rev-parse --short HEAD)

if [ "$PREV_HASH" = "$NEW_HASH" ]; then
  log_success "Repository already up to date at commit ${NEW_HASH}."
else
  log_success "Successfully updated repository: ${PREV_HASH} -> ${NEW_HASH}"
  git log --oneline -n 3
fi

# ── 3. Script Permissions Hardening ──────────────────────────────────────────

log_info "Step 3/7: Hardening script permissions..."
if [ -d "scripts" ]; then
  chmod +x scripts/*.sh 2>/dev/null || true
  chmod +x scripts/*.py 2>/dev/null || true
  log_success "Executable permissions applied to all scripts in scripts/."
fi

# ── 4. Security & Zero-Leak Secret Pre-Flight Scan ────────────────────────────

log_info "Step 4/7: Running pre-flight security scan for committed secrets..."
if [ -f "scripts/check_no_secrets.py" ]; then
  if python3 scripts/check_no_secrets.py; then
    log_success "Zero secrets detected. Repository security verified."
  else
    log_error "Security scan failed! Secrets or private keys were detected in the repository."
    exit 1
  fi
fi

# ── 5. Backend Dependency Verification ────────────────────────────────────────

log_info "Step 5/7: Verifying Python backend dependencies..."
if ! python3 -c "import fastapi, uvicorn, pydantic, google.genai" 2>/dev/null; then
  log_info "Installing backend dependencies from backend/requirements.txt..."
  python3 -m pip install --no-cache-dir -r backend/requirements.txt --quiet || \
  python3 -m pip install --no-cache-dir --break-system-packages -r backend/requirements.txt --quiet
else
  log_success "Backend core dependencies verified."
fi

# ── 6. Frontend Dependency & Production Compilation ──────────────────────────

if [ "$DO_BUILD" = true ]; then
  log_info "Step 6/7: Building Next.js frontend production bundle..."
  cd frontend

  if [ "$DO_CLEAN" = true ]; then
    log_warn "Aggressively purging frontend/.next and node_modules..."
    rm -rf .next node_modules
  else
    # Always clear .next cache to avoid stale SSR or hydration bugs
    rm -rf .next
  fi

  # Install frontend dependencies if needed
  if [ ! -d "node_modules" ] || [ ! -d "node_modules/next" ]; then
    log_info "Installing frontend dependencies with npm..."
    if [ -f "package-lock.json" ]; then
      npm ci --include=dev --quiet || npm install --include=dev --quiet
    else
      npm install --include=dev --quiet
    fi
  fi

  log_info "Compiling Next.js production build..."
  npm run build
  cd ..
  log_success "Production Next.js bundle compiled successfully."
else
  log_info "Step 6/7: Skipping frontend compilation (--no-build specified)."
fi

# ── 7. Optional Start / Healthcheck ──────────────────────────────────────────

if [ "$DO_START" = true ]; then
  log_info "Step 7/7: Starting ContentGenAutomator Studio services..."

  # Terminate conflicting processes on active ports
  TARGET_PORTS=("${PORT}" "8000" "8001")
  for p in "${TARGET_PORTS[@]}"; do
    if command -v fuser >/dev/null 2>&1; then
      fuser -k "${p}/tcp" 2>/dev/null || true
    fi
  done

  log_info "Invoking ./scripts/replit_start.sh in background..."
  ./scripts/replit_start.sh &
  START_PID=$!

  # Poll healthcheck endpoint
  HEALTH_URL="http://127.0.0.1:${PORT}/health"
  log_info "Waiting for service to become healthy at ${HEALTH_URL}..."

  HEALTHY=false
  for i in {1..15}; do
    sleep 2
    if curl -s -f "$HEALTH_URL" >/dev/null 2>&1; then
      HEALTHY=true
      break
    fi
    echo -n "."
  done
  echo ""

  if [ "$HEALTHY" = true ]; then
    log_success "Studio successfully running and responding healthy on port ${PORT}!"
  else
    log_warn "Health check timed out after 30s. The service is still starting up."
  fi
else
  log_info "Step 7/7: Build complete. Run './scripts/replit_start.sh' or deploy via Replit UI."
fi

ELAPSED=$(( $(date +%s) - START_TIME ))
log_success "Hardened deployment flow completed in ${ELAPSED}s! 🚀"
exit 0
