#!/usr/bin/env bash
# Content Gen Automator — Production Google Cloud Run Automated Deployment.
set -e

PROJECT_ID=${1:-$(gcloud config get-value project 2>/dev/null)}
REGION=${2:-"us-central1"}
SERVICE_NAME=${3:-"content-gen-automator-backend"}
REPO_NAME="content-gen-automator"
SECRET_NAME="google-api-key"

echo "========================================================================"
echo "   CONTENT GEN AUTOMATOR: PRODUCTION CLOUD RUN AUTOMATED DEPLOYMENT   "
echo "========================================================================"

if [ -z "$PROJECT_ID" ]; then
  echo "❌ Error: No GCP Project specified. Pass as argument 1 or set via gcloud config set project <ID>."
  exit 1
fi

ACCOUNT=$(gcloud config get-value account 2>/dev/null)
if [ -z "$ACCOUNT" ]; then
  echo "❌ Error: No authenticated gcloud account found. Run 'gcloud auth login' first."
  exit 1
fi

# Pre-flight check
echo "[0/5] Pre-Flight Prerequisite Verification..."
gcloud config set billing/quota_project "$PROJECT_ID" >/dev/null 2>&1 || true
BILLING_ENABLED=$(gcloud billing projects describe "$PROJECT_ID" --format="value(billingEnabled)" 2>/dev/null || echo "false")

echo "Account Authenticated : $ACCOUNT"
echo "Project ID            : $PROJECT_ID"
echo "Billing Enabled       : $BILLING_ENABLED"

if [ "$BILLING_ENABLED" != "True" ] && [ "$BILLING_ENABLED" != "true" ]; then
  echo "❌ GO/NO-GO VERDICT: NO-GO."
  echo "Project '$PROJECT_ID' does not have billing enabled."
  exit 1
fi
echo "✅ GO/NO-GO VERDICT: GO (Prerequisites verified)."

# 1. Enable required APIs
echo "[1/5] Enabling required Google Cloud APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  --project="$PROJECT_ID" --quiet

# 2. Artifact Registry Docker repository setup
echo "[2/5] Verifying Artifact Registry Docker repository..."
if ! gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "Creating Artifact Registry repository '$REPO_NAME' in $REGION..."
  gcloud artifacts repositories create "$REPO_NAME" \
    --repository-format=docker \
    --location="$REGION" \
    --description="Docker images for ContentGenAutomator" \
    --project="$PROJECT_ID" --quiet
else
  echo "Repository '$REPO_NAME' already exists in $REGION."
fi

# 3. Secret Manager configuration
echo "[3/5] Configuring secrets in Secret Manager..."
SECRET_VALUE=""
if [ -f ".env.production" ]; then
  SECRET_VALUE=$(grep -E '^(export )?(GEMINI_API_KEY|GOOGLE_API_KEY)=' .env.production | head -n 1 | cut -d '=' -f2- | tr -d ' "' || true)
elif [ -f "backend/.env.production" ]; then
  SECRET_VALUE=$(grep -E '^(export )?(GEMINI_API_KEY|GOOGLE_API_KEY)=' backend/.env.production | head -n 1 | cut -d '=' -f2- | tr -d ' "' || true)
fi

if [ -z "$SECRET_VALUE" ]; then
  SECRET_VALUE=${GEMINI_API_KEY:-$GOOGLE_API_KEY}
fi

if gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" >/dev/null 2>&1; then
  if [ -n "$SECRET_VALUE" ]; then
    printf "%s" "$SECRET_VALUE" | gcloud secrets versions add "$SECRET_NAME" --project="$PROJECT_ID" --data-file=- --quiet >/dev/null
    echo "Updated secret '$SECRET_NAME' in Secret Manager."
  else
    echo "Reusing existing Secret Manager secret '$SECRET_NAME'."
  fi
else
  if [ -n "$SECRET_VALUE" ]; then
    printf "%s" "$SECRET_VALUE" | gcloud secrets create "$SECRET_NAME" --project="$PROJECT_ID" --data-file=- --replication-policy=automatic --quiet >/dev/null
    echo "Created secret '$SECRET_NAME' in Secret Manager."
  else
    echo "Creating placeholder secret '$SECRET_NAME' to permit deployment..."
    printf "placeholder-key" | gcloud secrets create "$SECRET_NAME" --project="$PROJECT_ID" --data-file=- --replication-policy=automatic --quiet >/dev/null
  fi
fi

# Service account binding
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
for SA in "${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" "service-${PROJECT_NUMBER}@serverless-robot-prod.iam.gserviceaccount.com"; do
  gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
    --project="$PROJECT_ID" \
    --member="serviceAccount:$SA" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet >/dev/null 2>&1 || true
done

# 4. Build and push image
echo "[4/5] Building container image with Google Cloud Build..."
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/${SERVICE_NAME}:latest"
gcloud builds submit ./backend --tag "$IMAGE" --project="$PROJECT_ID" --quiet
echo "✅ Cloud Build succeeded."

# 5. Deploy to Cloud Run
echo "[5/5] Deploying service to Google Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --allow-unauthenticated \
  --set-secrets "GEMINI_API_KEY=${SECRET_NAME}:latest" \
  --set-env-vars "APP_ENV=production,GEMINI_MODEL=gemini-2.5-flash" \
  --port 8000 \
  --cpu 1 \
  --memory 1Gi \
  --min-instances 0 \
  --max-instances 3 \
  --timeout 120 \
  --quiet

LIVE_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --project "$PROJECT_ID" --format="value(status.url)")

echo ""
echo "========================================================================"
echo "   CLOUD RUN DEPLOYMENT SUCCESSFUL!                                   "
echo "========================================================================"
echo "Live Cloud Run URL : $LIVE_URL"
echo ""
echo "------------------------------------------------------------------------"
echo "INFRASTRUCTURE COST GUARDRAIL NOTICE (GCP Free Tier):"
echo "  * Concurrency: min-instances=0 (scales to zero when idle - \$0 cost)"
echo "  * Maximum Scale: max-instances=3 (strict ceiling against traffic spikes)"
echo "  * GCP Free Tier: 2 million requests/mo, 360,000 GB-seconds/mo free."
echo "  * Note: This infra-level guardrail works in tandem with the application-level"
echo "          Auto-Pilot FinOps Token Ceiling (HTTP 429). Both protect the budget."
echo "------------------------------------------------------------------------"
echo ""
