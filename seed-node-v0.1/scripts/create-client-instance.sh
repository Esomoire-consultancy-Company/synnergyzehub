#!/usr/bin/env bash
set -euo pipefail

# Creates a client instance folder from the seed node scaffold.
# This does not create API keys. Keys must be created by the client's authorized owner
# and stored in their own GitHub Secrets / VM secrets.

CLIENT_SLUG="${1:-}"
CLIENT_NAME="${2:-}"

if [ -z "$CLIENT_SLUG" ] || [ -z "$CLIENT_NAME" ]; then
  echo "Usage: ./scripts/create-client-instance.sh client-slug 'Client Name'"
  exit 1
fi

TARGET="../instances/$CLIENT_SLUG"
mkdir -p "$TARGET"

cat > "$TARGET/instance.json" <<JSON
{
  "client_instance_id": "$CLIENT_SLUG",
  "client_name": "$CLIENT_NAME",
  "runtime": "synnergyze-seed-node-v0.1",
  "mode": "client-workspace",
  "created_by": "synnergyze-builder-console",
  "required_secrets": [
    "OPENAI_API_KEY",
    "DATABASE_URL",
    "MINIO_ACCESS_KEY",
    "MINIO_SECRET_KEY"
  ],
  "github_policy": {
    "recommended_auth": "GitHub App or fine-grained PAT scoped to one repo",
    "never_store_tokens_in_repo": true,
    "default_branch": "main"
  }
}
JSON

echo "Client instance manifest created at $TARGET/instance.json"
