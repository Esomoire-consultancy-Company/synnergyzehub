# Synnergyze Seed Node v0.1

First deployable prototype for Synnergyze Builder Console and Genesis Seed Node.

## First live use case

Textile Workspace Builder:

1. Create workspace
2. Invite members
3. Upload swatch
4. Create material passport
5. Generate BOM
6. Generate tech pack
7. Set usage price
8. Log payment metadata
9. Log RiverOS evidence event
10. Convert workspace into Genesis Business profile

## Doctrine

Individuals create workspaces. Creators monetize workspaces. Businesses connect to Genesis. Enterprises connect to enterprises through Genesis.

One core runtime. Many templates. Separate databases when legal/commercial identity requires it.

## GitHub handoff

```bash
./scripts/push-to-github.sh git@github.com:OWNER/REPO.git
```

See:

- docs/github-push.md
- docs/client-instance-agent.md
- docs/security-model.md


## Grow My Trade R0.1

The `/gmt` API is an additive Synnergyze onboarding path for governed business discovery. It is intentionally limited to:

1. trusted DigitalMe ingress;
2. active workspace membership;
3. independent-business-rights acknowledgement;
4. private business/network summary capture;
5. Synnergyze draft business plan recording;
6. participant approval;
7. a hard stop at `HOLD_FOR_ESTATE_LICENSE`.

R0.1 does **not** issue a Virtual Estate licence, grant Warden authority, execute a trade, move SILK, create a payment, or perform settlement.

### Required ingress headers

When `DIGITALME_TRUSTED_INGRESS=true`, the trusted VSR/DigitalMe gateway must supply:

- `X-DigitalMe-Principal`;
- `X-DigitalMe-Verification-Ref`;
- `X-Actor-User-Id`;
- `X-Idempotency-Key` on mutations.

The API then confirms that the actor user is an active member of the target workspace. Without trusted ingress the GMT API fails closed.

### Database bootstrap

Fresh development databases created through `infra/docker-compose.yml` load, in order:

1. `packages/database/init.sql`;
2. `packages/riveros/schema.sql`;
3. `packages/database/gmt_onboarding.sql`.

Existing PostgreSQL volumes are **not** re-initialized by Docker. Apply the additive schemas explicitly:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f seed-node-v0.1/packages/riveros/schema.sql

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f seed-node-v0.1/packages/database/gmt_onboarding.sql
```

Production migrations must still be versioned and reviewed before promotion.
