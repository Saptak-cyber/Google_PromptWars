#!/usr/bin/env bash
# ── LexGuard GCP Setup Script ──────────────────────────────────────────
# Run this ONCE to set up GCP project, Secret Manager secrets, and 
# Artifact Registry before running Cloud Build.
#
# Prerequisites: gcloud CLI installed and authenticated
# Usage: chmod +x gcp/setup.sh && ./gcp/setup.sh

set -euo pipefail

PROJECT_ID="${1:-your-gcp-project-id}"
REGION="${2:-us-central1}"

echo "🚀 Setting up LexGuard on GCP project: $PROJECT_ID"
echo "📍 Region: $REGION"

# Set project
gcloud config set project "$PROJECT_ID"

# Enable required APIs
echo "⚙️  Enabling GCP APIs..."
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  --project="$PROJECT_ID"

# Create Artifact Registry repository
echo "📦 Creating Artifact Registry repository..."
gcloud artifacts repositories create lexguard \
  --repository-format=docker \
  --location="$REGION" \
  --description="LexGuard Docker images" \
  --project="$PROJECT_ID" 2>/dev/null || echo "  (already exists)"

# Grant Cloud Build access to Artifact Registry + Cloud Run
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
CB_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/artifactregistry.writer" --quiet

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/run.admin" --quiet

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/secretmanager.secretAccessor" --quiet

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/iam.serviceAccountUser" --quiet

# Create secrets in Secret Manager
echo ""
echo "🔐 Creating Secret Manager secrets..."
echo "   You will be prompted to enter each secret value."
echo ""

create_secret() {
  local name="$1"
  local prompt="$2"
  echo -n "  $prompt: "
  read -rs value
  echo
  if gcloud secrets describe "$name" --project="$PROJECT_ID" &>/dev/null; then
    echo "$value" | gcloud secrets versions add "$name" --data-file=- --project="$PROJECT_ID" --quiet
  else
    echo "$value" | gcloud secrets create "$name" --data-file=- --project="$PROJECT_ID" --replication-policy=automatic --quiet
  fi
  echo "  ✓ $name"
}

create_secret "LLAMAPARSE_API_KEY"   "LlamaParse API key (llx-...)"
create_secret "HF_API_KEY"           "HuggingFace API key (hf_...)"
create_secret "QDRANT_URL"           "Qdrant Cloud URL (https://...)"
create_secret "QDRANT_API_KEY"       "Qdrant API key"
create_secret "NVIDIA_API_KEY"       "NVIDIA NIM API key (nvapi-...)"
create_secret "LANGSMITH_API_KEY"    "LangSmith API key (lsv2_...)"
create_secret "NEON_DATABASE_URL"    "Neon DB URL (postgresql+asyncpg://...)"

echo ""
echo "✅ GCP setup complete!"
echo ""
echo "Next steps:"
echo "  1. Deploy with Cloud Build:"
echo "     gcloud builds submit --config=gcp/cloudbuild.yaml \\"
echo "       --substitutions=_REGION=${REGION} --project=${PROJECT_ID}"
echo ""
echo "  2. After backend deploys, get its URL:"
echo "     gcloud run services describe lexguard-backend --region=${REGION} --format='value(status.url)'"
echo ""
echo "  3. Update NEXT_PUBLIC_API_URL in cloudbuild.yaml with the backend URL, then redeploy."
