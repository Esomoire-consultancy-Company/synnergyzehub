#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./scripts/push-to-github.sh git@github.com:OWNER/REPO.git
# or:
#   ./scripts/push-to-github.sh https://github.com/OWNER/REPO.git
#
# Do not paste tokens into this script.
# Use GitHub CLI auth, SSH deploy key, or credential manager.

REMOTE_URL="${1:-}"

if [ -z "$REMOTE_URL" ]; then
  echo "Missing remote URL."
  echo "Example: ./scripts/push-to-github.sh git@github.com:OWNER/REPO.git"
  exit 1
fi

if [ ! -d ".git" ]; then
  git init
fi

git add .
git commit -m "Initial Synnergyze Seed Node v0.1 scaffold" || true

git branch -M main

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REMOTE_URL"
else
  git remote add origin "$REMOTE_URL"
fi

git push -u origin main
