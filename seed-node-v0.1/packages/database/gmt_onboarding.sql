-- VSR Grow My Trade R0.1
-- Mutable Synnergyze onboarding state. RiverOS remains the immutable evidence layer.
-- Apply after packages/database/init.sql and packages/riveros/schema.sql.

CREATE SCHEMA IF NOT EXISTS gmt;

CREATE TABLE IF NOT EXISTS gmt.onboarding_cases (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  workspace_id UUID NOT NULL REFERENCES workspace.workspaces(id) ON DELETE RESTRICT,
  digitalme_principal TEXT NOT NULL,
  digitalme_verification_ref TEXT NOT NULL,

  state TEXT NOT NULL DEFAULT 'IDENTITY_VERIFIED'
    CHECK (state IN (
      'IDENTITY_VERIFIED',
      'BUSINESS_DECLARED',
      'PLAN_READY',
      'HOLD_FOR_ESTATE_LICENSE',
      'BLOCKED',
      'CLOSED'
    )),

  business_declaration JSONB NOT NULL DEFAULT '{}'::jsonb,
  network_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
  capability_claims JSONB NOT NULL DEFAULT '[]'::jsonb,
  business_plan JSONB NOT NULL DEFAULT '{}'::jsonb,

  rights_version TEXT NOT NULL,
  rights_context JSONB NOT NULL,
  rights_acknowledged_at TIMESTAMPTZ NOT NULL,

  estate_licence_id TEXT,
  warden_decision_id TEXT,

  create_idempotency_key TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (workspace_id, create_idempotency_key)
);

CREATE INDEX IF NOT EXISTS gmt_onboarding_cases_workspace_state_idx
  ON gmt.onboarding_cases (workspace_id, state, updated_at DESC);

CREATE INDEX IF NOT EXISTS gmt_onboarding_cases_principal_idx
  ON gmt.onboarding_cases (workspace_id, digitalme_principal, updated_at DESC);

COMMENT ON TABLE gmt.onboarding_cases IS
  'Synnergyze mutable state for Grow My Trade. It does not transfer ownership of a participant business, customers, IP, banking, tax responsibilities, or lawful external trade to VSR.';
