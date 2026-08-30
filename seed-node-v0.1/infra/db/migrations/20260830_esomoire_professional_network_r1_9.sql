-- ESOMOIRE-PROFESSIONAL-NETWORK-001 R1.9
-- Professional Network Capacity + Commercial Entitlement + SILK Settlement Projection Runtime
-- PostgreSQL 15+ portable migration for Neon/Supabase targets.
-- Authority boundary:
--   * Esomoire owns registry/platform/device-commercial projections.
--   * Professional fee positions remain professional/firm-owned.
--   * SILK remains settlement authority; this schema stores references/projections only.
--   * Warden decisions and River receipts are referenced, never replaced here.

begin;

create schema if not exists esomoire_professional;

create table if not exists esomoire_professional.runtime_manifest (
  runtime_code text primary key,
  semantic_version text not null,
  authority_boundary text not null,
  source_commit_ref text,
  activated_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists esomoire_professional.service_catalog (
  service_id uuid primary key default gen_random_uuid(),
  service_code text not null unique,
  service_family text not null check (service_family in ('PLATFORM','PROFESSIONAL','DEVICE','REGULATORY_WORKFLOW')),
  service_name text not null,
  consumption_unit text not null,
  professional_service_required boolean not null default false,
  active boolean not null default true,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists esomoire_professional.professional_capacity_window (
  capacity_window_id uuid primary key default gen_random_uuid(),
  professional_ref text not null,
  firm_ref text,
  service_code text not null references esomoire_professional.service_catalog(service_code),
  window_start timestamptz not null,
  window_end timestamptz not null,
  offered_units numeric(18,4) not null check (offered_units >= 0),
  capacity_state text not null check (capacity_state in ('VERIFIED_CAPACITY','AVAILABLE','OFFERED','UNAVAILABLE','CLOSED')),
  source_authority_ref text not null,
  evidence_ref text,
  source_version_ref text not null,
  created_at timestamptz not null default now(),
  check (window_end > window_start),
  unique (professional_ref, service_code, window_start, window_end)
);

create table if not exists esomoire_professional.capacity_reservation (
  reservation_id uuid primary key default gen_random_uuid(),
  capacity_window_id uuid not null references esomoire_professional.professional_capacity_window(capacity_window_id),
  client_ref text not null,
  engagement_ref text not null,
  service_code text not null references esomoire_professional.service_catalog(service_code),
  reserved_units numeric(18,4) not null check (reserved_units > 0),
  reservation_state text not null check (reservation_state in ('PROPOSED','HELD','CONFIRMED','CONSUMED','RELEASED','EXPIRED','CANCELLED')),
  warden_decision_ref text,
  river_receipt_ref text,
  idempotency_key text not null unique,
  reserved_at timestamptz not null default now(),
  expires_at timestamptz,
  released_at timestamptz
);

create table if not exists esomoire_professional.service_entitlement (
  entitlement_id uuid primary key default gen_random_uuid(),
  entitlement_code text not null unique,
  holder_ref text not null,
  engagement_ref text,
  service_code text not null references esomoire_professional.service_catalog(service_code),
  total_units numeric(18,4),
  entitlement_state text not null check (entitlement_state in ('ACTIVE','SUSPENDED','EXPIRED','CANCELLED')),
  commercial_basis_ref text not null,
  silk_entitlement_ref text,
  valid_from timestamptz not null,
  valid_until timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (total_units is null or total_units >= 0),
  check (valid_until is null or valid_until > valid_from)
);

create table if not exists esomoire_professional.service_consumption (
  consumption_id uuid primary key default gen_random_uuid(),
  entitlement_id uuid not null references esomoire_professional.service_entitlement(entitlement_id),
  reservation_id uuid references esomoire_professional.capacity_reservation(reservation_id),
  case_ref text not null,
  channel text not null check (channel in ('WHATSAPP','LINEMATE','GENESIS_TABLET','SYSTEM','OTHER')),
  consumed_units numeric(18,4) not null check (consumed_units > 0),
  consumption_state text not null check (consumption_state in ('PROPOSED','ADMITTED','CONSUMED','REVERSED')),
  warden_decision_ref text,
  river_receipt_ref text,
  idempotency_key text not null unique,
  consumed_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists esomoire_professional.commercial_charge (
  charge_id uuid primary key default gen_random_uuid(),
  charge_code text not null unique,
  charge_class text not null check (charge_class in ('PLATFORM','PROFESSIONAL','DEVICE','THIRD_PARTY')),
  service_code text references esomoire_professional.service_catalog(service_code),
  billed_party_ref text not null,
  economic_owner_ref text not null,
  engagement_ref text,
  commercial_basis_ref text not null,
  pricing_basis text not null,
  amount numeric(20,4) not null check (amount >= 0),
  currency char(3) not null,
  charge_state text not null check (charge_state in ('DRAFT','AUTHORIZED','DUE','DISPUTED','VOID','SETTLED')),
  silk_position_ref text,
  evidence_ref text,
  created_at timestamptz not null default now(),
  check (upper(pricing_basis) <> 'PERCENT_OF_PROFESSIONAL_FEE')
);

create table if not exists esomoire_professional.silk_settlement_projection (
  settlement_projection_id uuid primary key default gen_random_uuid(),
  charge_id uuid not null unique references esomoire_professional.commercial_charge(charge_id),
  settlement_owner_ref text not null,
  silk_position_ref text not null,
  projected_amount_due numeric(20,4) not null check (projected_amount_due >= 0),
  observed_amount_settled numeric(20,4) not null default 0 check (observed_amount_settled >= 0),
  currency char(3) not null,
  projection_state text not null check (projection_state in ('OPEN','PARTIALLY_SETTLED','SETTLED','DISPUTED','VOID')),
  silk_source_version_ref text not null,
  observed_at timestamptz not null default now(),
  check (observed_amount_settled <= projected_amount_due)
);

create table if not exists esomoire_professional.settlement_observation_receipt (
  settlement_observation_receipt_id uuid primary key default gen_random_uuid(),
  settlement_projection_id uuid not null references esomoire_professional.silk_settlement_projection(settlement_projection_id),
  external_receipt_ref text not null unique,
  observed_amount numeric(20,4) not null check (observed_amount > 0),
  currency char(3) not null,
  observed_at timestamptz not null,
  river_receipt_ref text,
  receipt_hash text,
  created_at timestamptz not null default now()
);

create table if not exists esomoire_professional.professional_network_event (
  event_id uuid primary key default gen_random_uuid(),
  event_type text not null,
  subject_ref text not null,
  actor_ref text,
  engagement_ref text,
  correlation_ref text,
  payload jsonb not null default '{}'::jsonb,
  source_version_ref text not null,
  warden_decision_ref text,
  river_receipt_ref text,
  occurred_at timestamptz not null,
  observed_at timestamptz not null default now(),
  idempotency_key text not null unique
);

create index if not exists idx_esomoire_capacity_window_service_time
  on esomoire_professional.professional_capacity_window(service_code, window_start, window_end);
create index if not exists idx_esomoire_capacity_reservation_window_state
  on esomoire_professional.capacity_reservation(capacity_window_id, reservation_state);
create index if not exists idx_esomoire_entitlement_holder_state
  on esomoire_professional.service_entitlement(holder_ref, entitlement_state);
create index if not exists idx_esomoire_consumption_entitlement_state
  on esomoire_professional.service_consumption(entitlement_id, consumption_state);
create index if not exists idx_esomoire_charge_owner_state
  on esomoire_professional.commercial_charge(economic_owner_ref, charge_state);
create index if not exists idx_esomoire_network_event_subject_time
  on esomoire_professional.professional_network_event(subject_ref, occurred_at desc);

create or replace view esomoire_professional.v_capacity_balance as
select
  w.capacity_window_id,
  w.professional_ref,
  w.firm_ref,
  w.service_code,
  w.window_start,
  w.window_end,
  w.offered_units,
  coalesce(sum(r.reserved_units) filter (where r.reservation_state in ('HELD','CONFIRMED','CONSUMED')), 0) as committed_units,
  greatest(w.offered_units - coalesce(sum(r.reserved_units) filter (where r.reservation_state in ('HELD','CONFIRMED','CONSUMED')), 0), 0) as available_units,
  w.capacity_state
from esomoire_professional.professional_capacity_window w
left join esomoire_professional.capacity_reservation r
  on r.capacity_window_id = w.capacity_window_id
group by w.capacity_window_id;

create or replace view esomoire_professional.v_entitlement_balance as
select
  e.entitlement_id,
  e.entitlement_code,
  e.holder_ref,
  e.engagement_ref,
  e.service_code,
  e.total_units,
  coalesce(sum(c.consumed_units) filter (where c.consumption_state = 'CONSUMED'), 0) as consumed_units,
  case
    when e.total_units is null then null
    else greatest(e.total_units - coalesce(sum(c.consumed_units) filter (where c.consumption_state = 'CONSUMED'), 0), 0)
  end as available_units,
  e.entitlement_state,
  e.silk_entitlement_ref,
  e.valid_from,
  e.valid_until
from esomoire_professional.service_entitlement e
left join esomoire_professional.service_consumption c
  on c.entitlement_id = e.entitlement_id
group by e.entitlement_id;

insert into esomoire_professional.runtime_manifest(runtime_code, semantic_version, authority_boundary)
values (
  'ESOMOIRE-PROFESSIONAL-NETWORK-001',
  'R1.9',
  'Esomoire registry/platform/device commercial projection; professional fees remain professional-owned; SILK is settlement authority; Warden and River are referenced authorities.'
)
on conflict (runtime_code) do update set
  semantic_version = excluded.semantic_version,
  authority_boundary = excluded.authority_boundary;

insert into esomoire_professional.service_catalog
  (service_code, service_family, service_name, consumption_unit, professional_service_required, metadata)
values
  ('ESOMOIRE_REGISTRY','PLATFORM','Esomoire Professional Registry','subscription_period',false,'{"r1_9":true}'::jsonb),
  ('CONTINUOUS_READINESS','PLATFORM','Continuous Filing Readiness','workflow_unit',false,'{"r1_9":true}'::jsonb),
  ('QUARTER_CLOSE','REGULATORY_WORKFLOW','Quarter Close','close_case',true,'{"r1_9":true}'::jsonb),
  ('FILING_RELEASE','REGULATORY_WORKFLOW','Filing Release','filing_case',true,'{"r1_9":true}'::jsonb),
  ('PROFESSIONAL_REVIEW','PROFESSIONAL','Professional Review','review_unit',true,'{"r1_9":true}'::jsonb),
  ('NOTICE_RESPONSE','PROFESSIONAL','Notice Response','case_unit',true,'{"r1_9":true}'::jsonb),
  ('GENESIS_DEVICE','DEVICE','Genesis Professional Device','device_period',false,'{"r1_9":true}'::jsonb)
on conflict (service_code) do update set
  service_family = excluded.service_family,
  service_name = excluded.service_name,
  consumption_unit = excluded.consumption_unit,
  professional_service_required = excluded.professional_service_required,
  active = true,
  metadata = esomoire_professional.service_catalog.metadata || excluded.metadata;

-- Defense in depth for any target where this schema is later API-exposed.
alter table esomoire_professional.runtime_manifest enable row level security;
alter table esomoire_professional.service_catalog enable row level security;
alter table esomoire_professional.professional_capacity_window enable row level security;
alter table esomoire_professional.capacity_reservation enable row level security;
alter table esomoire_professional.service_entitlement enable row level security;
alter table esomoire_professional.service_consumption enable row level security;
alter table esomoire_professional.commercial_charge enable row level security;
alter table esomoire_professional.silk_settlement_projection enable row level security;
alter table esomoire_professional.settlement_observation_receipt enable row level security;
alter table esomoire_professional.professional_network_event enable row level security;

comment on schema esomoire_professional is 'R1.9 projection runtime. Not a replacement for Genesis identity, Warden authority, River evidence, Synnergyze workflow, or SILK settlement.';
comment on table esomoire_professional.commercial_charge is 'Separates PLATFORM, PROFESSIONAL, DEVICE and THIRD_PARTY charges. Esomoire revenue must not be derived as a percentage of professional fees.';
comment on table esomoire_professional.silk_settlement_projection is 'Read/reference projection of SILK settlement position; SILK remains authoritative.';

commit;
