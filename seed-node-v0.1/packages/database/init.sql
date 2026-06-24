CREATE SCHEMA IF NOT EXISTS platform;
CREATE SCHEMA IF NOT EXISTS workspace;
CREATE SCHEMA IF NOT EXISTS business;
CREATE SCHEMA IF NOT EXISTS genesis;
CREATE SCHEMA IF NOT EXISTS riveros;
CREATE SCHEMA IF NOT EXISTS silk;
CREATE SCHEMA IF NOT EXISTS textile;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS platform.users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  display_name TEXT NOT NULL,
  email TEXT UNIQUE,
  phone TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workspace.workspaces (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  owner_user_id UUID REFERENCES platform.users(id),
  name TEXT NOT NULL,
  workspace_type TEXT NOT NULL DEFAULT 'custom',
  status TEXT NOT NULL DEFAULT 'active',
  upi_id TEXT,
  pricing_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workspace.members (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  workspace_id UUID REFERENCES workspace.workspaces(id) ON DELETE CASCADE,
  user_id UUID REFERENCES platform.users(id),
  role TEXT NOT NULL DEFAULT 'member',
  status TEXT NOT NULL DEFAULT 'invited',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workspace.usage_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  workspace_id UUID REFERENCES workspace.workspaces(id),
  actor_user_id UUID REFERENCES platform.users(id),
  event_type TEXT NOT NULL,
  object_type TEXT,
  object_id UUID,
  amount_paise INTEGER DEFAULT 0,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS textile.material_passports (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  workspace_id UUID REFERENCES workspace.workspaces(id) ON DELETE CASCADE,
  material_name TEXT NOT NULL,
  colour_code TEXT,
  shade_family TEXT,
  fabric_type TEXT,
  composition TEXT,
  gsm NUMERIC,
  width_cm NUMERIC,
  stretch TEXT,
  finish TEXT,
  supplier TEXT,
  rate_paise INTEGER,
  evidence_image_url TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS textile.design_projects (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  workspace_id UUID REFERENCES workspace.workspaces(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  garment_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS textile.bom_versions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  design_project_id UUID REFERENCES textile.design_projects(id) ON DELETE CASCADE,
  version_number INTEGER NOT NULL DEFAULT 1,
  bom_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS textile.tech_packs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  design_project_id UUID REFERENCES textile.design_projects(id) ON DELETE CASCADE,
  bom_version_id UUID REFERENCES textile.bom_versions(id),
  export_url TEXT,
  status TEXT NOT NULL DEFAULT 'generated',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS business.business_profiles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  workspace_id UUID REFERENCES workspace.workspaces(id),
  legal_name TEXT NOT NULL,
  trade_name TEXT,
  gstin TEXT,
  invoice_prefix TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS genesis.registered_units (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  business_profile_id UUID REFERENCES business.business_profiles(id),
  unit_name TEXT NOT NULL,
  unit_type TEXT NOT NULL DEFAULT 'business',
  registry_status TEXT NOT NULL DEFAULT 'registered',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS silk.payment_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  workspace_id UUID REFERENCES workspace.workspaces(id),
  service_code TEXT NOT NULL,
  gross_amount_paise INTEGER NOT NULL,
  platform_fee_paise INTEGER NOT NULL DEFAULT 0,
  owner_receivable_paise INTEGER NOT NULL DEFAULT 0,
  payment_method TEXT NOT NULL DEFAULT 'upi',
  external_reference TEXT,
  status TEXT NOT NULL DEFAULT 'recorded',
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS riveros.evidence_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  workspace_id UUID,
  actor_user_id UUID,
  event_type TEXT NOT NULL,
  object_type TEXT,
  object_id UUID,
  event_hash TEXT,
  evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
