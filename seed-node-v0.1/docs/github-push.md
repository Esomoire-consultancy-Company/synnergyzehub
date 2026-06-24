# GitHub Push Guide

## Option A: GitHub CLI

On your local machine or VM:

```bash
gh auth login
gh repo create OWNER/REPO --private --source=. --remote=origin --push
```

## Option B: Existing repository with SSH

```bash
git init
git add .
git commit -m "Initial Synnergyze Seed Node v0.1 scaffold"
git branch -M main
git remote add origin git@github.com:OWNER/REPO.git
git push -u origin main
```

## Option C: Existing repository with HTTPS

Use a credential manager or GitHub CLI. Do not paste tokens into code.

```bash
git init
git add .
git commit -m "Initial Synnergyze Seed Node v0.1 scaffold"
git branch -M main
git remote add origin https://github.com/OWNER/REPO.git
git push -u origin main
```

## Recommended repository name

```text
synnergyze-seed-node
```

For client instances:

```text
client-slug-synnergyze-instance
```

## Minimum repository secrets for deployment

- OPENAI_API_KEY
- DATABASE_URL
- MINIO_ACCESS_KEY
- MINIO_SECRET_KEY
- DEPLOY_HOST
- DEPLOY_USER
- DEPLOY_SSH_KEY
