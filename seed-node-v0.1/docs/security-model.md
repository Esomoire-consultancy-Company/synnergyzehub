# Security Model

## Core security doctrine

Secrets stay in the client's control.  
The agent receives only the minimum permission required for the approved task.  
Every action is logged as evidence.  
Access can be revoked.

## What must never be committed

- OpenAI API keys
- GitHub tokens
- Database passwords
- Payment provider secrets
- Private keys
- Card numbers
- CVV
- PIN
- OTP
- Production .env files

## OpenAI key handling

Use one key per client instance or one service account per client project.

The key must be stored only in:

- VM secret manager
- GitHub Actions secrets
- Cloud secret manager
- Server-side environment variable

Never put the key in browser code, mobile apps, public repos, screenshots, or chat messages.

## GitHub key handling

Preferred order:

1. GitHub App installation
2. Fine-grained PAT scoped to one repository
3. SSH deploy key scoped to one repository
4. GitHub CLI on the authorized user's own machine

## Agent permission modes

### Read-only mode

The agent can inspect files and prepare recommendations.

### Draft mode

The agent can create files but cannot push.

### Commit mode

The agent can commit to a branch but cannot merge.

### Deploy mode

The agent can trigger deployment after approval.

### Admin mode

Restricted. Used only for trusted internal projects.

## Client-instance isolation

Each client should have:

- Separate repository
- Separate OpenAI project/key
- Separate database/schema
- Separate object storage bucket
- Separate environment variables
- Separate audit/evidence trail
- Separate payment metadata profile

## Revocation

The client must be able to revoke:

- GitHub access
- OpenAI key
- VM access
- Storage access
- Payment connector
- Domain/DNS access

## Handover principle

No code hostage.  
No hidden admin access.  
No undocumented backend.  
No secret retained after handover unless contractually required.
