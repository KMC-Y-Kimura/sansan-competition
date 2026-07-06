#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-${1:-}}"
REGION="${REGION:-asia-northeast1}"
SERVICE_ID="${SERVICE_ID:-sansan-competition}"
CPU="${CPU:-1}"
MEMORY="${MEMORY:-512Mi}"
CONCURRENCY="${CONCURRENCY:-20}"
MIN_INSTANCES="${MIN_INSTANCES:-0}"
MAX_INSTANCES="${MAX_INSTANCES:-1}"
TIMEOUT="${TIMEOUT:-60}"

if [[ -z "${PROJECT_ID}" ]]; then
  echo "Usage: PROJECT_ID=<gcp-project-id> $0" >&2
  echo "Example: PROJECT_ID=classroom-ai-kmc $0" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Using project: ${PROJECT_ID}"
echo "==> Using region: ${REGION}"
echo "==> Using Cloud Run service: ${SERVICE_ID}"
echo "==> Cloud Run cpu=${CPU} memory=${MEMORY} concurrency=${CONCURRENCY} min=${MIN_INSTANCES} max=${MAX_INSTANCES} timeout=${TIMEOUT}"

cd "${REPO_ROOT}"

gcloud config set project "${PROJECT_ID}"

if [[ "$(gcloud billing projects describe "${PROJECT_ID}" --format='value(billingEnabled)' | tr '[:upper:]' '[:lower:]')" != "true" ]]; then
  echo "Billing is not enabled for project ${PROJECT_ID}." >&2
  echo "Link a billing account to the exact Google Cloud project, then rerun this script." >&2
  exit 1
fi

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  cloudfunctions.googleapis.com

gcloud run deploy "${SERVICE_ID}" \
  --source . \
  --cpu "${CPU}" \
  --memory "${MEMORY}" \
  --min "${MIN_INSTANCES}" \
  --max "${MAX_INSTANCES}" \
  --concurrency "${CONCURRENCY}" \
  --min-instances "${MIN_INSTANCES}" \
  --max-instances "${MAX_INSTANCES}" \
  --region "${REGION}" \
  --timeout "${TIMEOUT}" \
  --cpu-throttling \
  --no-cpu-boost \
  --allow-unauthenticated

firebase use "${PROJECT_ID}"
firebase deploy --only hosting

echo
echo "Deploy complete."
echo "Firebase Hosting should now serve public/ and rewrite /api/** plus /oauth/google/callback to Cloud Run."
echo "Next: register https://${PROJECT_ID}.web.app/oauth/google/callback in the Google OAuth web client."
