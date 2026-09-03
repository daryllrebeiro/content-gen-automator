# Content Gen Automator — Production Google Cloud Run Automated Deployment.
#
# Prerequisites:
#   1. gcloud CLI installed and authenticated (gcloud auth login)
#   2. A GCP project with billing enabled
#   3. Optional: .env.production file containing secrets (e.g. GEMINI_API_KEY=...)
#
# Usage:
#   .\scripts\deploy-cloudrun.ps1 -ProjectId supportmaster -Region us-central1

param(
    [Parameter(Mandatory = $false)][string]$ProjectId,
    [string]$Region = "us-central1",
    [string]$ServiceName = "content-gen-automator-backend",
    [string]$RepoName = "content-gen-automator",
    [string]$SecretName = "google-api-key"
)

$ErrorActionPreference = "Continue"

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "   CONTENT GEN AUTOMATOR: PRODUCTION CLOUD RUN AUTOMATED DEPLOYMENT   " -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

# 0. Check prerequisites: gcloud CLI and authentication
if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    throw "❌ Error: gcloud CLI not found. Please install Google Cloud SDK."
}

if (-not $ProjectId) {
    $ProjectId = gcloud config get-value project 2>$null
    if (-not $ProjectId) {
        throw "❌ Error: No GCP Project specified. Pass -ProjectId <ID> or run 'gcloud config set project <ID>'."
    }
}

$account = gcloud config get-value account 2>$null
if (-not $account) {
    throw "❌ Error: No authenticated gcloud account found. Run 'gcloud auth login' first."
}

# Verify billing status
Write-Host "`n[0/5] Pre-Flight Prerequisite Verification..." -ForegroundColor Yellow
gcloud config set billing/quota_project $ProjectId 2>$null | Out-Null
$billingInfo = gcloud billing projects describe $ProjectId --format="json" 2>$null | ConvertFrom-Json
$billingEnabled = $billingInfo.billingEnabled

Write-Host "Account Authenticated : $account"
Write-Host "Project ID            : $ProjectId"
Write-Host "Billing Enabled       : $(if ($billingEnabled) { 'YES (PASS)' } else { 'NO (FAIL)' })"

if (-not $billingEnabled) {
    Write-Host "❌ GO/NO-GO VERDICT: NO-GO." -ForegroundColor Red
    throw "Project '$ProjectId' does not have billing enabled. Please enable billing in Google Cloud Console."
}
Write-Host "✅ GO/NO-GO VERDICT: GO (Prerequisites verified)." -ForegroundColor Green

# 1. Enable required APIs (idempotent)
Write-Host "`n[1/5] Enabling required Google Cloud APIs..." -ForegroundColor Yellow
gcloud services enable `
    run.googleapis.com `
    cloudbuild.googleapis.com `
    secretmanager.googleapis.com `
    artifactregistry.googleapis.com `
    --project=$ProjectId --quiet

# 2. Artifact Registry repository setup (idempotent)
Write-Host "`n[2/5] Verifying Artifact Registry Docker repository..." -ForegroundColor Yellow
$existingRepo = gcloud artifacts repositories describe $RepoName --location=$Region --project=$ProjectId --format="value(name)" 2>$null
if (-not $existingRepo) {
    Write-Host "Creating Artifact Registry repository '$RepoName' in $Region..."
    gcloud artifacts repositories create $RepoName `
        --repository-format=docker `
        --location=$Region `
        --description="Docker images for ContentGenAutomator" `
        --project=$ProjectId --quiet
} else {
    Write-Host "Repository '$RepoName' already exists in $Region."
}

# 3. Secret Manager configuration (reads from .env.production if present)
Write-Host "`n[3/5] Configuring secrets in Secret Manager..." -ForegroundColor Yellow
$secretValue = $null

# Check .env.production in root or backend
$envProdPaths = @(".env.production", "backend\.env.production")
foreach ($path in $envProdPaths) {
    if (Test-Path $path) {
        Write-Host "Reading secrets from $path..."
        $lines = Get-Content $path
        foreach ($line in $lines) {
            if ($line -match "^(?:export\s+)?(GEMINI_API_KEY|GOOGLE_API_KEY)\s*=\s*(.+)$") {
                $secretValue = $matches[2].Trim(" '`"")
                break
            }
        }
        if ($secretValue) { break }
    }
}

if (-not $secretValue -and $env:GEMINI_API_KEY) {
    $secretValue = $env:GEMINI_API_KEY
}
if (-not $secretValue -and $env:GOOGLE_API_KEY) {
    $secretValue = $env:GOOGLE_API_KEY
}

$secretExists = gcloud secrets describe $SecretName --project=$ProjectId --format="value(name)" 2>$null

if ($secretValue) {
    if ($secretExists) {
        $secretValue | gcloud secrets versions add $SecretName --project=$ProjectId --data-file=- --quiet | Out-Null
        Write-Host "Updated secret '$SecretName' in Secret Manager."
    } else {
        $secretValue | gcloud secrets create $SecretName --project=$ProjectId --data-file=- --replication-policy=automatic --quiet | Out-Null
        Write-Host "Created secret '$SecretName' in Secret Manager."
    }
} elseif ($secretExists) {
    Write-Host "Reusing existing Secret Manager secret '$SecretName'."
} else {
    Write-Host "⚠️ Warning: No local GEMINI_API_KEY found, and '$SecretName' does not exist in Secret Manager."
    Write-Host "Creating placeholder secret to permit deployment..."
    "placeholder-key-add-in-console" | gcloud secrets create $SecretName --project=$ProjectId --data-file=- --replication-policy=automatic --quiet | Out-Null
}

# Grant Secret Accessor permissions to Cloud Run runtime service accounts
$projectNumber = gcloud projects describe $ProjectId --format="value(projectNumber)"
$runtimeSas = @(
    "$projectNumber-compute@developer.gserviceaccount.com",
    "service-$projectNumber@serverless-robot-prod.iam.gserviceaccount.com"
)
foreach ($sa in $runtimeSas) {
    gcloud secrets add-iam-policy-binding $SecretName `
        --project=$ProjectId `
        --member="serviceAccount:$sa" `
        --role="roles/secretmanager.secretAccessor" `
        --quiet 2>$null | Out-Null
}

# 4. Build and push image via Cloud Build
Write-Host "`n[4/5] Building container image with Google Cloud Build..." -ForegroundColor Yellow
$image = "$Region-docker.pkg.dev/$ProjectId/$RepoName/${ServiceName}:latest"
Write-Host "Submitting build to Cloud Build: $image"
gcloud builds submit .\backend --tag $image --project=$ProjectId --quiet
if ($LASTEXITCODE -ne 0) { throw "Cloud Build failed." }
Write-Host "✅ Cloud Build succeeded." -ForegroundColor Green

# 5. Deploy to Google Cloud Run
Write-Host "`n[5/5] Deploying service to Google Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $ServiceName `
    --image $image `
    --region $Region `
    --project $ProjectId `
    --allow-unauthenticated `
    --set-secrets "GEMINI_API_KEY=${SecretName}:latest" `
    --set-env-vars "APP_ENV=production,GEMINI_MODEL=gemini-2.5-flash" `
    --port 8000 `
    --cpu 1 `
    --memory 1Gi `
    --min-instances 0 `
    --max-instances 3 `
    --timeout 120 `
    --quiet

if ($LASTEXITCODE -ne 0) { throw "Cloud Run deployment failed." }

$liveUrl = gcloud run services describe $ServiceName --region $Region --project $ProjectId --format="value(status.url)"

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Green
Write-Host "   CLOUD RUN DEPLOYMENT SUCCESSFUL!                                   " -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Green
Write-Host "Live Cloud Run URL : $liveUrl" -ForegroundColor Cyan
Write-Host ""
Write-Host "------------------------------------------------------------------------"
Write-Host "INFRASTRUCTURE COST GUARDRAIL NOTICE (GCP Free Tier):" -ForegroundColor Yellow
Write-Host "  * Concurrency: min-instances=0 (scales to zero when idle - $0 cost)"
Write-Host "  * Maximum Scale: max-instances=3 (strict ceiling against traffic spikes)"
Write-Host "  * GCP Free Tier: 2 million requests/mo, 360,000 GB-seconds/mo free."
Write-Host "  * Note: This infra-level guardrail works in tandem with the application-level"
Write-Host "          Auto-Pilot FinOps Token Ceiling (HTTP 429). Both protect the budget."
Write-Host "------------------------------------------------------------------------"
Write-Host ""

return $liveUrl
