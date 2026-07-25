-- RiverOS v0.2 additive repository schema.
-- Apply after seed-node-v0.1/packages/database/init.sql.

CREATE SCHEMA IF NOT EXISTS riveros;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS riveros.event_streams (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  workspace_id UUID REFERENCES workspace.workspaces(id) ON DELETE CASCADE,
  code TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  classification TEXT NOT NULL DEFAULT 'internal',
  retention_class TEXT NOT NULL DEFAULT 'standard',
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'suspended', 'archived')),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (workspace_id, code)
);

CREATE TABLE IF NOT EXISTS riveros.events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  stream_id UUID REFERENCES riveros.event_streams(id),
  workspace_id UUID NOT NULL REFERENCES workspace.workspaces(id) ON DELETE RESTRICT,

  event_type TEXT NOT NULL,
  event_version TEXT NOT NULL DEFAULT '0.2',
  action TEXT NOT NULL,

  source_system TEXT NOT NULL,
  source_environment TEXT,
  source_event_ref TEXT,
  idempotency_key TEXT,

  actor_type TEXT,
  actor_user_id UUID REFERENCES platform.users(id),
  actor_id TEXT,
  digitalme_principal TEXT,
  agent_id TEXT,
  device_id TEXT,

  organisation_id TEXT,
  arc_id TEXT,
  licence_id TEXT,
  workflow_id TEXT,

  object_type TEXT NOT NULL,
  object_id TEXT NOT NULL,
  previous_state JSONB,
  new_state JSONB,

  authority_basis JSONB NOT NULL DEFAULT '{}'::jsonb,
  consent_context JSONB NOT NULL DEFAULT '{}'::jsonb,
  dam_decision_id TEXT,

  commercial_relevance BOOLEAN NOT NULL DEFAULT FALSE,
  settlement_eligibility TEXT NOT NULL DEFAULT 'not_applicable'
    CHECK (settlement_eligibility IN (
      'not_applicable',
      'not_eligible',
      'pending',
      'eligible',
      'revoked'
    )),

  lifecycle_status TEXT NOT NULL DEFAULT 'RECEIVED'
    CHECK (lifecycle_status IN (
      'RECEIVED',
      'VALIDATING',
      'VERIFIED',
      'ACCEPTED',
      'APPLIED',
      'SETTLEMENT_ELIGIBLE',
      'CLOSED',
      'REJECTED',
      'QUARANTINED',
      'DISPUTED',
      'SUSPENDED',
      'REVERSED',
      'SUPERSEDED'
    )),

  trace_id UUID NOT NULL DEFAULT uuid_generate_v4(),
  correlation_id UUID,
  causation_id UUID,

  occurred_at TIMESTAMPTZ NOT NULL,
  observed_at TIMESTAMPTZ,
  received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  effective_at TIMESTAMPTZ,
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  location JSONB NOT NULL DEFAULT '{}'::jsonb,
  confidence NUMERIC CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
  event_hash TEXT,
  signature JSONB NOT NULL DEFAULT '{}'::jsonb,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE UNIQUE INDEX IF NOT EXISTS riveros_events_idempotency_uq
  ON riveros.events (workspace_id, source_system, idempotency_key)
  WHERE idempotency_key IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS riveros_events_source_ref_uq
  ON riveros.events (workspace_id, source_system, source_event_ref)
  WHERE source_event_ref IS NOT NULL;

CREATE INDEX IF NOT EXISTS riveros_events_workspace_recorded_idx
  ON riveros.events (workspace_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS riveros_events_object_idx
  ON riveros.events (workspace_id, object_type, object_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS riveros_events_trace_idx
  ON riveros.events (trace_id);

CREATE INDEX IF NOT EXISTS riveros_events_correlation_idx
  ON riveros.events (correlation_id)
  WHERE correlation_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS riveros_events_type_status_idx
  ON riveros.events (event_type, lifecycle_status, occurred_at DESC);

CREATE INDEX IF NOT EXISTS riveros_events_settlement_idx
  ON riveros.events (workspace_id, settlement_eligibility, occurred_at DESC)
  WHERE commercial_relevance = TRUE;

CREATE TABLE IF NOT EXISTS riveros.evidence_objects (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  workspace_id UUID NOT NULL REFERENCES workspace.workspaces(id) ON DELETE RESTRICT,
  evidence_type TEXT NOT NULL,
  title TEXT,
  storage_uri TEXT,
  content_type TEXT,
  checksum_algorithm TEXT NOT NULL DEFAULT 'sha256',
  checksum TEXT NOT NULL,
  classification TEXT NOT NULL DEFAULT 'internal',
  retention_class TEXT NOT NULL DEFAULT 'standard',
  source_system TEXT,
  source_object_ref TEXT,
  captured_by_actor_id TEXT,
  occurred_at TIMESTAMPTZ,
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  revoked_at TIMESTAMPTZ,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (workspace_id, checksum_algorithm, checksum)
);

CREATE INDEX IF NOT EXISTS riveros_evidence_workspace_idx
  ON riveros.evidence_objects (workspace_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS riveros_evidence_source_idx
  ON riveros.evidence_objects (workspace_id, source_system, source_object_ref);

CREATE TABLE IF NOT EXISTS riveros.event_evidence_links (
  event_id UUID NOT NULL REFERENCES riveros.events(id) ON DELETE CASCADE,
  evidence_id UUID NOT NULL REFERENCES riveros.evidence_objects(id) ON DELETE RESTRICT,
  relation_type TEXT NOT NULL DEFAULT 'supports'
    CHECK (relation_type IN (
      'supports',
      'observes',
      'authorises',
      'contradicts',
      'replaces',
      'settles'
    )),
  linked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (event_id, evidence_id, relation_type)
);

CREATE INDEX IF NOT EXISTS riveros_event_evidence_evidence_idx
  ON riveros.event_evidence_links (evidence_id);

CREATE TABLE IF NOT EXISTS riveros.event_relations (
  source_event_id UUID NOT NULL REFERENCES riveros.events(id) ON DELETE CASCADE,
  target_event_id UUID NOT NULL REFERENCES riveros.events(id) ON DELETE RESTRICT,
  relation_type TEXT NOT NULL
    CHECK (relation_type IN (
      'causes',
      'correlates',
      'corrects',
      'reverses',
      'supersedes',
      'settles',
      'disputes'
    )),
  reason TEXT,
  authority_basis JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (source_event_id, target_event_id, relation_type),
  CHECK (source_event_id <> target_event_id)
);

CREATE INDEX IF NOT EXISTS riveros_event_relations_target_idx
  ON riveros.event_relations (target_event_id, relation_type);

CREATE TABLE IF NOT EXISTS riveros.state_projections (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  workspace_id UUID NOT NULL REFERENCES workspace.workspaces(id) ON DELETE CASCADE,
  projection_type TEXT NOT NULL,
  projection_key TEXT NOT NULL,
  current_state JSONB NOT NULL DEFAULT '{}'::jsonb,
  projection_version BIGINT NOT NULL DEFAULT 0,
  last_event_id UUID REFERENCES riveros.events(id) ON DELETE RESTRICT,
  effective_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (workspace_id, projection_type, projection_key)
);

CREATE INDEX IF NOT EXISTS riveros_state_projection_event_idx
  ON riveros.state_projections (last_event_id)
  WHERE last_event_id IS NOT NULL;

COMMENT ON TABLE riveros.events IS
  'Append-only RiverOS event ledger. Historical rows are not updated to rewrite business truth; corrections are recorded as related events.';

COMMENT ON TABLE riveros.evidence_objects IS
  'Metadata and integrity references for evidence stored in governed object storage.';

COMMENT ON TABLE riveros.state_projections IS
  'Mutable current-state projections derived from the append-only RiverOS event ledger.';

COMMENT ON COLUMN riveros.events.settlement_eligibility IS
  'Controlled RiverOS-to-Silk handoff status. Eligibility does not execute or guarantee settlement.';
