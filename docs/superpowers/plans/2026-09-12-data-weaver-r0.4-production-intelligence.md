# Data Weaver Studio R0.4 Production Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the smallest auditable R0.4 production kernel that registers production nodes, decomposes approved configurations into work packages, routes work deterministically, reserves capacity without overbooking, records execution/QA evidence, and updates node performance.

**Architecture:** Add an isolated server-side TypeScript domain under `lib/dws-production/`, backed by PostgreSQL 16 and exposed through thin Next.js route handlers. Domain rules stay independent of HTTP and database adapters. The existing Genesis Seed MCP surface remains unchanged. Production-event history is append-only; capacity reservation uses transactional row locking; all tenant-bound mutations are idempotent and execute in a tenant-scoped transaction.

**Tech Stack:** Next.js 15.5.18, React 18.3.1, TypeScript 5.6.2, Zod 3.25+, PostgreSQL 16, `postgres`, Vitest, `tsx`, Node.js 22.

**Spec:** `docs/superpowers/specs/2026-09-12-data-weaver-r0.4-production-intelligence-design.md`

## Global Constraints

- R0.4.0 is deterministic: no predictive ML scheduling, autonomous reassignment, contractor marketplace, billing, or self-modifying routing weights.
- PostgreSQL is the canonical transaction store. Airtable and Lovable may consume projections later; they are not authoritative in this plan.
- `production_node_id` is stable identity. Historical decisions and assignments bind an immutable `production_node_version_id`.
- Only `active` nodes enter automatic routing. `conditional` nodes require a Warden-authorized override. `suspended` and `retired` nodes receive no new work.
- Base routing weights are capability 0.25, capacity 0.20, quality 0.15, delivery 0.15, cost 0.10, governance 0.10, client history 0.05.
- If client-history is absent, its 0.05 weight is redistributed proportionally across the other six factors.
- Tentative capacity reservations expire. Reservation-group conversion to committed capacity is all-or-nothing.
- Every material mutation requires an idempotency key.
- Production events are append-only. Effective state must be replayable from the event stream.
- QA pass/authorized exception and closure/authorized acceptance of blocking NCRs are prerequisites for acceptance/completion.
- Every license-linked row carries `tenant_id`; services must execute tenant-bound queries through a tenant-scoped transaction.
- Genesis, Warden, and River remain external authorities. R0.4 persists their stable references but does not implement their policy/evidence engines.
- Existing `/api/mcp` and `/api/mcp-selftest` behavior is unchanged.

## Target File Map

```text
lib/dws-production/
  domain/
    ids.ts
    schemas.ts
    errors.ts
    state-machines.ts
    scoring.ts
    scheduling.ts
    metrics.ts
  db/
    client.ts
    migrate.ts
    repositories.ts
  services/
    nodes.ts
    decomposition.ts
    capacity.ts
    routing.ts
    execution.ts
    quality.ts
    performance.ts
  http/
    auth.ts
    response.ts

db/dws-production/
  001_r04_core.sql
  002_r04_indexes.sql

app/api/dws-production/
  nodes/route.ts
  lmos/route.ts
  lmos/[lmoId]/release/route.ts
  capacity/simulate/route.ts
  capacity/hold/route.ts
  capacity/commit/route.ts
  events/route.ts
  qa/inspections/route.ts
  qa/nonconformances/route.ts
  health/route.ts

tests/dws-production/
  db-smoke.integration.test.ts
  schema.integration.test.ts
  domain.test.ts
  nodes.integration.test.ts
  scheduling.test.ts
  lmo.integration.test.ts
  routing.test.ts
  routing.integration.test.ts
  capacity.integration.test.ts
  quality.integration.test.ts
  performance.test.ts
  http.test.ts
  qualification.integration.test.ts

infra/dws-production/docker-compose.yml
.github/workflows/dws-production.yml
docs/dws-production/R0.4-QUALIFICATION.md
```

---

### Task 1: Establish the TypeScript, test, and PostgreSQL harness

**Files:**
- Modify: `package.json`
- Create: `tsconfig.json`
- Create: `vitest.config.ts`
- Create: `infra/dws-production/docker-compose.yml`
- Create: `lib/dws-production/db/client.ts`
- Create: `tests/dws-production/db-smoke.integration.test.ts`

**Interfaces:**
- `getDb(): Sql`
- `withTransaction<T>(fn): Promise<T>`
- `withTenantTransaction<T>(tenantId, fn): Promise<T>`

- [ ] **Step 1: Add dependencies and exact scripts**

Run:

```bash
npm install postgres
npm install -D vitest tsx
```

Set `package.json` scripts to include:

```json
{
  "test": "vitest run",
  "test:unit": "vitest run tests/dws-production/domain.test.ts tests/dws-production/routing.test.ts tests/dws-production/scheduling.test.ts tests/dws-production/performance.test.ts",
  "test:integration": "vitest run tests/dws-production/*.integration.test.ts",
  "dws:migrate": "tsx lib/dws-production/db/migrate.ts"
}
```

- [ ] **Step 2: Add exact compiler/test config**

Create `tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "strict": true,
    "noEmit": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "baseUrl": ".",
    "paths": { "@/*": ["./*"] },
    "plugins": [{ "name": "next" }]
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules", "seed-node-v0.1"]
}
```

Create `vitest.config.ts`:

```ts
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: { "@": fileURLToPath(new URL("./", import.meta.url)) },
  },
  test: {
    environment: "node",
    include: ["tests/dws-production/**/*.test.ts"],
    sequence: { concurrent: false },
  },
});
```

- [ ] **Step 3: Add dedicated PostgreSQL 16 local service**

Create `infra/dws-production/docker-compose.yml`:

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: dws
      POSTGRES_PASSWORD: dws_dev_password
      POSTGRES_DB: dws_production
    ports:
      - "55432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dws -d dws_production"]
      interval: 2s
      timeout: 2s
      retries: 20
```

- [ ] **Step 4: Write the failing DB smoke test**

```ts
import { expect, it } from "vitest";
import { getDb } from "@/lib/dws-production/db/client";

it("connects to DWS PostgreSQL", async () => {
  const rows = await getDb()<[{ ok: number }]>`select 1::int as ok`;
  expect(rows[0].ok).toBe(1);
});
```

Run:

```bash
docker compose -f infra/dws-production/docker-compose.yml up -d
DWS_TEST_DATABASE_URL=postgresql://dws:dws_dev_password@127.0.0.1:55432/dws_production npm run test:integration -- db-smoke
```

Expected: FAIL because `client.ts` does not exist.

- [ ] **Step 5: Implement database and tenant transaction helpers**

Create `lib/dws-production/db/client.ts`:

```ts
import postgres, { type Sql, type TransactionSql } from "postgres";

let db: Sql | undefined;

export function getDb(): Sql {
  const url = process.env.DWS_TEST_DATABASE_URL ?? process.env.DWS_DATABASE_URL;
  if (!url) throw new Error("DWS_DATABASE_URL is required");
  db ??= postgres(url, { max: 10, prepare: false });
  return db;
}

export async function withTransaction<T>(
  fn: (tx: TransactionSql) => Promise<T>,
): Promise<T> {
  return getDb().begin(fn);
}

export async function withTenantTransaction<T>(
  tenantId: string,
  fn: (tx: TransactionSql) => Promise<T>,
): Promise<T> {
  return getDb().begin(async (tx) => {
    await tx`select set_config('app.tenant_id', ${tenantId}, true)`;
    return fn(tx);
  });
}
```

Run the smoke test again; expected PASS.

- [ ] **Step 6: Verify the current app still builds**

```bash
npm run build
```

Expected: Next.js build passes and existing MCP code is untouched.

- [ ] **Step 7: Commit**

```bash
git add package.json package-lock.json tsconfig.json vitest.config.ts infra/dws-production lib/dws-production/db/client.ts tests/dws-production/db-smoke.integration.test.ts
git commit -m "chore: establish DWS production test harness"
```

---

### Task 2: Define exact domain IDs, schemas, errors, and state machines

**Files:**
- Create: `lib/dws-production/domain/ids.ts`
- Create: `lib/dws-production/domain/schemas.ts`
- Create: `lib/dws-production/domain/errors.ts`
- Create: `lib/dws-production/domain/state-machines.ts`
- Create: `tests/dws-production/domain.test.ts`

**Interfaces:**
- `makeDwsId(prefix, sequence): string`
- `DwsError`
- `assertLmoTransition(from, to): void`
- `assertWorkPackageTransition(from, to): void`
- Zod command schemas used by HTTP/services

- [ ] **Step 1: Write failing domain tests**

```ts
import { expect, it } from "vitest";
import { makeDwsId } from "@/lib/dws-production/domain/ids";
import { assertLmoTransition, assertWorkPackageTransition } from "@/lib/dws-production/domain/state-machines";

it("formats canonical IDs", () => {
  expect(makeDwsId("LMO-DWS", 42)).toBe("LMO-DWS-000042");
});

it("rejects illegal LMO transition", () => {
  expect(() => assertLmoTransition("planned", "completed")).toThrow("DWS_ILLEGAL_STATE_TRANSITION");
});

it("allows QA rework loop", () => {
  expect(() => assertWorkPackageTransition("qa", "rework")).not.toThrow();
  expect(() => assertWorkPackageTransition("rework", "submitted")).not.toThrow();
});
```

- [ ] **Step 2: Implement canonical IDs and errors**

`ids.ts`:

```ts
export function makeDwsId(prefix: string, sequence: number): string {
  if (!Number.isInteger(sequence) || sequence < 1) throw new Error("sequence must be a positive integer");
  return `${prefix}-${String(sequence).padStart(6, "0")}`;
}
```

`errors.ts`:

```ts
export type DwsErrorCode =
  | "DWS_CAPACITY_UNAVAILABLE"
  | "DWS_CAPACITY_CONFLICT"
  | "DWS_RESERVATION_EXPIRED"
  | "DWS_INELIGIBLE_NODE"
  | "DWS_NO_ELIGIBLE_ROUTE"
  | "DWS_ILLEGAL_STATE_TRANSITION"
  | "DWS_DEPENDENCY_INCOMPLETE"
  | "DWS_QA_REQUIRED"
  | "DWS_QA_FAILED"
  | "DWS_NONCONFORMANCE_OPEN"
  | "DWS_GOVERNANCE_DENIED"
  | "DWS_IDEMPOTENCY_CONFLICT"
  | "DWS_CONFIGURATION_VERSION_MISMATCH";

export class DwsError extends Error {
  constructor(
    public readonly code: DwsErrorCode,
    message: string,
    public readonly retryable = false,
    public readonly aggregateId?: string,
  ) {
    super(`${code}: ${message}`);
  }
}
```

- [ ] **Step 3: Implement exact LMO and work-package transition tables**

`state-machines.ts`:

```ts
import { DwsError } from "./errors";

export const LMO_TRANSITIONS = {
  planned: ["capacity_checked", "cancelled"],
  capacity_checked: ["reserved", "cancelled"],
  reserved: ["released", "cancelled"],
  released: ["in_progress", "cancelled"],
  in_progress: ["qa_hold", "completed", "cancelled"],
  qa_hold: ["in_progress", "completed", "cancelled"],
  completed: [],
  cancelled: [],
} as const;

export const WORK_PACKAGE_TRANSITIONS = {
  planned: ["reserved", "cancelled"],
  reserved: ["released", "cancelled"],
  released: ["in_progress", "cancelled"],
  in_progress: ["blocked", "submitted", "cancelled"],
  blocked: ["in_progress", "cancelled"],
  submitted: ["qa", "cancelled"],
  qa: ["rework", "accepted", "cancelled"],
  rework: ["submitted", "cancelled"],
  accepted: [],
  cancelled: [],
} as const;

function assertTransition(map: Record<string, readonly string[]>, from: string, to: string) {
  if (!map[from]?.includes(to)) {
    throw new DwsError("DWS_ILLEGAL_STATE_TRANSITION", `${from} -> ${to}`);
  }
}

export const assertLmoTransition = (from: string, to: string) => assertTransition(LMO_TRANSITIONS, from, to);
export const assertWorkPackageTransition = (from: string, to: string) => assertTransition(WORK_PACKAGE_TRANSITIONS, from, to);
```

- [ ] **Step 4: Implement exact command schemas**

`schemas.ts` exports these shapes:

```ts
import { z } from "zod";

const mutation = {
  tenantId: z.string().min(1),
  idempotencyKey: z.string().min(8),
};

export const RegisterNodeSchema = z.object({
  ...mutation,
  productionNodeId: z.string().regex(/^PN-DWS-\d{6}$/),
  nodeType: z.enum(["internal_team", "contractor", "qa_cell", "automation", "deployment_cell"]),
  operatorId: z.string().min(1),
  name: z.string().min(1),
  status: z.enum(["active", "conditional", "suspended", "retired"]),
  genesisPrincipalId: z.string().min(1),
  wardenPolicyId: z.string().min(1),
  securityClassification: z.string().min(1),
  approvedProductClasses: z.array(z.string().min(1)),
});

export const CreateLmoSchema = z.object({
  ...mutation,
  licenseId: z.string().min(1),
  configurationId: z.string().min(1),
  productVersionIds: z.array(z.string().min(1)).min(1),
  productionReason: z.enum(["initial", "upgrade", "expansion", "remediation", "connector_addition"]),
  routePolicy: z.enum(["internal", "contracted", "hybrid", "client_operated"]),
  priority: z.enum(["standard", "urgent", "critical"]),
  requestedStartAt: z.string().datetime(),
  requiredCompletionAt: z.string().datetime(),
});

export const CapacityHoldSchema = z.object({
  ...mutation,
  sourceType: z.enum(["simulation", "quote", "lmo"]),
  sourceId: z.string().min(1),
  expiresAt: z.string().datetime(),
  allocations: z.array(z.object({
    productionNodeId: z.string().regex(/^PN-DWS-\d{6}$/),
    date: z.string().date(),
    capacityUnit: z.enum(["engineering_hour", "qa_hour", "deployment_slot", "build_slot"]),
    reservedUnits: z.number().positive(),
  })).min(1),
});

export const ProductionEventSchema = z.object({
  ...mutation,
  aggregateType: z.enum(["lmo", "work_package", "assignment", "qa_inspection"]),
  aggregateId: z.string().min(1),
  eventType: z.string().min(1),
  occurredAt: z.string().datetime(),
  actorPrincipalId: z.string().min(1),
  payload: z.record(z.unknown()).default({}),
  wardenDecisionId: z.string().min(1).optional(),
  riverReceiptId: z.string().min(1).optional(),
});

export const InspectionResultSchema = z.object({
  ...mutation,
  qaInspectionId: z.string().min(1),
  result: z.enum(["pass", "pass_with_exception", "fail"]),
  score: z.number().min(0).max(100).optional(),
  criticalFailures: z.number().int().nonnegative(),
  majorFailures: z.number().int().nonnegative(),
  minorFailures: z.number().int().nonnegative(),
  evidenceReceiptId: z.string().min(1).optional(),
});

export const NonconformanceSchema = z.object({
  ...mutation,
  qaInspectionId: z.string().min(1),
  workPackageId: z.string().min(1),
  severity: z.enum(["critical", "major", "minor"]),
  category: z.string().min(1),
  description: z.string().min(1),
  ownerNodeId: z.string().regex(/^PN-DWS-\d{6}$/),
});
```

- [ ] **Step 5: Run unit tests and build**

```bash
npm run test:unit
npm run build
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add lib/dws-production/domain tests/dws-production/domain.test.ts
git commit -m "feat: define DWS production domain contracts"
```

---

### Task 3: Create canonical PostgreSQL schema, RLS boundary, append-only ledger, and migrations

**Files:**
- Create: `db/dws-production/001_r04_core.sql`
- Create: `db/dws-production/002_r04_indexes.sql`
- Create: `lib/dws-production/db/migrate.ts`
- Create: `tests/dws-production/schema.integration.test.ts`

**Interfaces:**
- Schemas: `dws_core`, `dws_capacity`, `dws_routing`, `dws_quality`, `dws_ledger`
- Migration command: `npm run dws:migrate`

- [ ] **Step 1: Write failing schema invariants test**

```ts
import { expect, it } from "vitest";
import { getDb } from "@/lib/dws-production/db/client";

it("installs the R0.4 canonical relations", async () => {
  const rows = await getDb()<Array<{ table_schema: string; table_name: string }>>`
    select table_schema, table_name
    from information_schema.tables
    where table_schema like 'dws_%'
  `;
  const names = new Set(rows.map((r) => `${r.table_schema}.${r.table_name}`));
  for (const required of [
    "dws_core.production_nodes",
    "dws_core.production_node_versions",
    "dws_core.node_capabilities",
    "dws_core.manufacturing_recipes",
    "dws_core.manufacturing_recipe_steps",
    "dws_core.lmos",
    "dws_core.work_packages",
    "dws_core.work_package_dependencies",
    "dws_core.assignments",
    "dws_capacity.capacity_buckets",
    "dws_capacity.reservation_groups",
    "dws_capacity.reservation_allocations",
    "dws_routing.routing_decisions",
    "dws_routing.routing_candidates",
    "dws_quality.inspections",
    "dws_quality.nonconformances",
    "dws_quality.performance_snapshots",
    "dws_ledger.production_events",
    "dws_ledger.idempotency_keys",
  ]) expect(names.has(required)).toBe(true);
});
```

- [ ] **Step 2: Implement `001_r04_core.sql` with exact table families**

Use this skeleton and preserve the listed columns/constraints when expanding foreign keys:

```sql
create schema if not exists dws_core;
create schema if not exists dws_capacity;
create schema if not exists dws_routing;
create schema if not exists dws_quality;
create schema if not exists dws_ledger;

create table dws_core.production_nodes (
  production_node_id text primary key,
  tenant_id text not null,
  operator_id text not null,
  name text not null,
  created_at timestamptz not null default now()
);

create table dws_core.production_node_versions (
  production_node_version_id text primary key,
  production_node_id text not null references dws_core.production_nodes,
  tenant_id text not null,
  node_type text not null check (node_type in ('internal_team','contractor','qa_cell','automation','deployment_cell')),
  status text not null check (status in ('active','conditional','suspended','retired')),
  genesis_principal_id text not null,
  warden_policy_id text not null,
  security_classification text not null,
  approved_product_classes text[] not null default '{}',
  effective_from timestamptz not null,
  effective_to timestamptz,
  supersedes_version_id text references dws_core.production_node_versions
);

create table dws_core.node_capabilities (
  node_capability_id text primary key,
  production_node_version_id text not null references dws_core.production_node_versions,
  tenant_id text not null,
  capability_code text not null,
  skill_level int not null check (skill_level between 1 and 5),
  max_parallel_units int not null check (max_parallel_units > 0),
  capacity_unit text not null check (capacity_unit in ('engineering_hour','qa_hour','deployment_slot','build_slot')),
  product_class_allowlist text[] not null default '{}',
  required_policy_ids text[] not null default '{}',
  effective_from timestamptz not null,
  effective_to timestamptz
);

create table dws_core.manufacturing_recipes (
  manufacturing_recipe_id text primary key,
  tenant_id text not null,
  product_version_id text not null,
  recipe_version text not null,
  effective_from timestamptz not null,
  unique (tenant_id, product_version_id, recipe_version)
);

create table dws_core.manufacturing_recipe_steps (
  recipe_step_id text primary key,
  manufacturing_recipe_id text not null references dws_core.manufacturing_recipes on delete cascade,
  tenant_id text not null,
  sequence_key text not null,
  name text not null,
  work_type text not null,
  required_capability_code text not null,
  minimum_skill_level int not null check (minimum_skill_level between 1 and 5),
  estimated_effort_units numeric(14,4) not null check (estimated_effort_units > 0),
  capacity_unit text not null,
  qa_specification_id text not null,
  security_classification text not null,
  predecessor_sequence_keys text[] not null default '{}'
);

create table dws_core.lmos (
  lmo_id text primary key,
  tenant_id text not null,
  license_id text not null,
  configuration_id text not null,
  product_version_ids text[] not null,
  production_reason text not null check (production_reason in ('initial','upgrade','expansion','remediation','connector_addition')),
  route_policy text not null check (route_policy in ('internal','contracted','hybrid','client_operated')),
  priority text not null check (priority in ('standard','urgent','critical')),
  requested_start_at timestamptz not null,
  required_completion_at timestamptz not null,
  state text not null check (state in ('planned','capacity_checked','reserved','released','in_progress','qa_hold','completed','cancelled')),
  warden_decision_id text,
  river_receipt_id text,
  created_at timestamptz not null default now()
);

create table dws_core.work_packages (
  work_package_id text primary key,
  tenant_id text not null,
  lmo_id text not null references dws_core.lmos on delete cascade,
  sequence_key text not null,
  name text not null,
  work_type text not null,
  required_capability_code text not null,
  minimum_skill_level int not null,
  estimated_effort_units numeric(14,4) not null,
  capacity_unit text not null,
  security_classification text not null,
  qa_specification_id text not null,
  planned_start_at timestamptz,
  planned_finish_at timestamptz,
  state text not null check (state in ('planned','reserved','released','in_progress','blocked','submitted','qa','rework','accepted','cancelled')),
  unique (tenant_id, lmo_id, sequence_key)
);

create table dws_core.work_package_dependencies (
  dependency_id text primary key,
  tenant_id text not null,
  predecessor_work_package_id text not null references dws_core.work_packages,
  successor_work_package_id text not null references dws_core.work_packages,
  dependency_type text not null default 'finish_to_start' check (dependency_type = 'finish_to_start'),
  minimum_lag_units numeric(14,4) not null default 0,
  lag_unit text not null default 'hour' check (lag_unit in ('hour','day'))
);

create table dws_capacity.capacity_buckets (
  tenant_id text not null,
  production_node_id text not null references dws_core.production_nodes,
  capacity_date date not null,
  capacity_unit text not null,
  nominal_units numeric(14,4) not null check (nominal_units >= 0),
  maintenance_units numeric(14,4) not null default 0 check (maintenance_units >= 0),
  leave_units numeric(14,4) not null default 0 check (leave_units >= 0),
  primary key (tenant_id, production_node_id, capacity_date, capacity_unit)
);

create table dws_capacity.reservation_groups (
  reservation_group_id text primary key,
  tenant_id text not null,
  reservation_type text not null check (reservation_type in ('tentative','committed')),
  source_type text not null check (source_type in ('simulation','quote','lmo')),
  source_id text not null,
  state text not null check (state in ('active','converted','released','expired','cancelled')),
  expires_at timestamptz,
  authority_ref text,
  predecessor_group_id text references dws_capacity.reservation_groups,
  created_at timestamptz not null default now(),
  check ((reservation_type = 'tentative' and expires_at is not null) or reservation_type = 'committed')
);

create table dws_capacity.reservation_allocations (
  reservation_group_id text not null references dws_capacity.reservation_groups on delete cascade,
  tenant_id text not null,
  production_node_id text not null references dws_core.production_nodes,
  work_package_id text references dws_core.work_packages,
  capacity_date date not null,
  capacity_unit text not null,
  reserved_units numeric(14,4) not null check (reserved_units > 0),
  primary key (reservation_group_id, production_node_id, capacity_date, capacity_unit)
);

create table dws_routing.routing_decisions (
  routing_decision_id text primary key,
  tenant_id text not null,
  work_package_id text not null references dws_core.work_packages,
  algorithm_version text not null,
  weight_profile_id text not null,
  selected_node_id text,
  selected_node_version_id text,
  selected_performance_snapshot_id text,
  final_score numeric(8,4),
  warden_decision_id text,
  river_receipt_id text,
  decided_at timestamptz not null default now()
);

create table dws_routing.routing_candidates (
  routing_decision_id text not null references dws_routing.routing_decisions on delete cascade,
  tenant_id text not null,
  production_node_id text not null,
  production_node_version_id text not null,
  eligible boolean not null,
  reasons text[] not null default '{}',
  component_scores jsonb not null default '{}'::jsonb,
  final_score numeric(8,4),
  primary key (routing_decision_id, production_node_id)
);

create table dws_core.assignments (
  assignment_id text primary key,
  tenant_id text not null,
  work_package_id text not null references dws_core.work_packages,
  production_node_id text not null references dws_core.production_nodes,
  production_node_version_id text not null references dws_core.production_node_versions,
  reservation_group_id text not null references dws_capacity.reservation_groups,
  routing_decision_id text references dws_routing.routing_decisions,
  manual_override_warden_decision_id text,
  assigned_by_principal_id text not null,
  state text not null check (state in ('assigned','active','completed','revoked')),
  assigned_at timestamptz not null default now(),
  check (routing_decision_id is not null or manual_override_warden_decision_id is not null)
);

create table dws_quality.inspections (
  qa_inspection_id text primary key,
  tenant_id text not null,
  work_package_id text not null references dws_core.work_packages,
  lmo_id text not null references dws_core.lmos,
  qa_specification_id text not null,
  inspector_node_id text not null references dws_core.production_nodes,
  inspection_round int not null check (inspection_round > 0),
  started_at timestamptz not null,
  completed_at timestamptz,
  result text not null check (result in ('pending','pass','pass_with_exception','fail')),
  score numeric(6,2),
  critical_failures int not null default 0,
  major_failures int not null default 0,
  minor_failures int not null default 0,
  evidence_receipt_id text
);

create table dws_quality.nonconformances (
  nonconformance_id text primary key,
  tenant_id text not null,
  qa_inspection_id text not null references dws_quality.inspections,
  work_package_id text not null references dws_core.work_packages,
  severity text not null check (severity in ('critical','major','minor')),
  category text not null,
  description text not null,
  state text not null check (state in ('open','rework','accepted_exception','closed')),
  owner_node_id text not null references dws_core.production_nodes,
  warden_exception_decision_id text,
  opened_at timestamptz not null default now(),
  closed_at timestamptz,
  closure_evidence_receipt_id text
);

create table dws_quality.performance_snapshots (
  node_performance_snapshot_id text primary key,
  tenant_id text not null,
  production_node_id text not null references dws_core.production_nodes,
  period_start timestamptz not null,
  period_end timestamptz not null,
  sample_size int not null,
  on_time_rate numeric(8,6),
  first_pass_yield numeric(8,6),
  defect_escape_rate numeric(8,6),
  average_cycle_time numeric(14,4),
  cost_adherence numeric(8,6),
  client_defect_rate numeric(8,6),
  quality_score numeric(8,4),
  delivery_score numeric(8,4),
  composite_vendor_score numeric(8,4),
  algorithm_version text not null,
  calculated_at timestamptz not null default now()
);

create table dws_ledger.event_type_registry (
  event_type text primary key
);

insert into dws_ledger.event_type_registry(event_type) values
('LMO_CREATED'),('CAPACITY_CHECKED'),('CAPACITY_RESERVED'),('CAPACITY_RESERVATION_EXPIRED'),
('WORK_PACKAGE_RELEASED'),('WORK_ASSIGNED'),('WORK_STARTED'),('WORK_BLOCKED'),('WORK_RESUMED'),
('BUILD_SUBMITTED'),('QA_STARTED'),('QA_FAILED'),('NONCONFORMANCE_OPENED'),('REWORK_REQUESTED'),
('REWORK_SUBMITTED'),('QA_PASSED'),('DEPLOYMENT_APPROVED'),('WORK_COMPLETED'),('LMO_COMPLETED'),('ASSIGNMENT_REVOKED')
on conflict do nothing;

create table dws_ledger.production_events (
  production_event_id text primary key,
  tenant_id text not null,
  aggregate_type text not null check (aggregate_type in ('lmo','work_package','assignment','qa_inspection')),
  aggregate_id text not null,
  event_type text not null references dws_ledger.event_type_registry,
  occurred_at timestamptz not null,
  recorded_at timestamptz not null default now(),
  actor_principal_id text not null,
  payload jsonb not null default '{}'::jsonb,
  warden_decision_id text,
  river_receipt_id text,
  idempotency_key text not null,
  supersedes_event_id text references dws_ledger.production_events,
  unique (tenant_id, idempotency_key)
);

create table dws_ledger.idempotency_keys (
  tenant_id text not null,
  idempotency_key text not null,
  request_hash text not null,
  response_json jsonb not null,
  created_at timestamptz not null default now(),
  primary key (tenant_id, idempotency_key)
);

create or replace function dws_ledger.prevent_event_mutation() returns trigger language plpgsql as $$
begin
  raise exception 'production_events is append-only';
end;
$$;

create trigger production_events_no_update
before update or delete on dws_ledger.production_events
for each row execute function dws_ledger.prevent_event_mutation();
```

Enable RLS on every tenant-bound table. For each table `T`, use the same policy pattern:

```sql
alter table dws_core.lmos enable row level security;
create policy lmos_tenant_policy on dws_core.lmos
using (tenant_id = current_setting('app.tenant_id', true))
with check (tenant_id = current_setting('app.tenant_id', true));
```

Apply the equivalent policy to all tenant-bound tables created above.

- [ ] **Step 3: Add exact performance/concurrency indexes**

`002_r04_indexes.sql`:

```sql
create index on dws_core.production_node_versions (tenant_id, production_node_id, effective_from desc);
create index on dws_core.node_capabilities (tenant_id, capability_code, production_node_version_id);
create index on dws_core.work_packages (tenant_id, lmo_id, state);
create index on dws_core.work_package_dependencies (tenant_id, successor_work_package_id);
create index on dws_capacity.reservation_groups (tenant_id, state, reservation_type, expires_at);
create index on dws_capacity.reservation_allocations (tenant_id, production_node_id, capacity_date, capacity_unit);
create index on dws_routing.routing_decisions (tenant_id, work_package_id, decided_at desc);
create index on dws_quality.inspections (tenant_id, work_package_id, inspection_round desc);
create index on dws_quality.nonconformances (tenant_id, work_package_id, state, severity);
create index on dws_quality.performance_snapshots (tenant_id, production_node_id, calculated_at desc);
create index on dws_ledger.production_events (tenant_id, aggregate_type, aggregate_id, recorded_at, production_event_id);
```

- [ ] **Step 4: Implement checksum-aware migration runner**

`lib/dws-production/db/migrate.ts`:

```ts
import { createHash } from "node:crypto";
import { readdir, readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { getDb } from "./client";

const db = getDb();
await db`create schema if not exists dws_ledger`;
await db`create table if not exists dws_ledger.schema_migrations (
  filename text primary key,
  sha256 text not null,
  applied_at timestamptz not null default now()
)`;

for (const filename of (await readdir(resolve("db/dws-production"))).filter((x) => x.endsWith(".sql")).sort()) {
  const sqlText = await readFile(resolve("db/dws-production", filename), "utf8");
  const sha256 = createHash("sha256").update(sqlText).digest("hex");
  const [prior] = await db<Array<{ sha256: string }>>`select sha256 from dws_ledger.schema_migrations where filename=${filename}`;
  if (prior) {
    if (prior.sha256 !== sha256) throw new Error(`Applied migration changed: ${filename}`);
    continue;
  }
  await db.begin(async (tx) => {
    await tx.unsafe(sqlText);
    await tx`insert into dws_ledger.schema_migrations(filename, sha256) values (${filename}, ${sha256})`;
  });
}
await db.end();
```

- [ ] **Step 5: Run migration and schema tests**

```bash
export DWS_TEST_DATABASE_URL=postgresql://dws:dws_dev_password@127.0.0.1:55432/dws_production
npm run dws:migrate
npm run test:integration -- schema
```

Expected: PASS. Also verify `update dws_ledger.production_events ...` fails in a dedicated test.

- [ ] **Step 6: Commit**

```bash
git add db/dws-production lib/dws-production/db/migrate.ts tests/dws-production/schema.integration.test.ts
git commit -m "feat: add canonical DWS production schema"
```

---

### Task 4: Implement production-node registry, capacity projection, manufacturing recipes, and LMO scheduling

**Files:**
- Create: `lib/dws-production/db/repositories.ts`
- Create: `lib/dws-production/services/nodes.ts`
- Create: `lib/dws-production/services/decomposition.ts`
- Create: `lib/dws-production/domain/scheduling.ts`
- Create: `tests/dws-production/nodes.integration.test.ts`
- Create: `tests/dws-production/scheduling.test.ts`
- Create: `tests/dws-production/lmo.integration.test.ts`

**Interfaces:**
- `registerProductionNode()`
- `createProductionNodeVersion()`
- `addNodeCapability()`
- `upsertCapacityBucket()`
- `getAvailableCapacity()`
- `decomposeConfiguration()`
- `validateDag()`
- `forwardSchedule()`

- [ ] **Step 1: Define repository interfaces with caller-owned transactions**

`repositories.ts` starts with:

```ts
import type { TransactionSql } from "postgres";

export type SqlTx = TransactionSql;

export async function lockCapacityBucket(
  tx: SqlTx,
  tenantId: string,
  productionNodeId: string,
  capacityDate: string,
  capacityUnit: string,
) {
  const [row] = await tx`
    select * from dws_capacity.capacity_buckets
    where tenant_id=${tenantId}
      and production_node_id=${productionNodeId}
      and capacity_date=${capacityDate}::date
      and capacity_unit=${capacityUnit}
    for update
  `;
  return row;
}
```

Add focused functions for node/version/capability insert/read, recipe read, LMO/work-package/dependency insert, active reservation aggregation, and event insert. Do not open nested transactions in repositories.

- [ ] **Step 2: Write node/version/capacity tests**

Test that changing a capability/governance profile creates a new version row while the old version remains queryable. Test capacity projection:

```ts
expect(await getAvailableCapacity(key)).toEqual({
  nominalUnits: 8,
  maintenanceUnits: 1,
  leaveUnits: 1,
  tentativeReservedUnits: 2,
  committedReservedUnits: 1,
  availableUnits: 3,
});
```

- [ ] **Step 3: Implement node/version and capacity services**

Use tenant transactions for every write:

```ts
export async function getAvailableCapacity(key: CapacityBucketKey) {
  return withTenantTransaction(key.tenantId, async (tx) => {
    const bucket = await readCapacityBucket(tx, key);
    const reserved = await sumActiveReservations(tx, key);
    const availableUnits = Math.max(0,
      Number(bucket.nominal_units)
      - Number(bucket.maintenance_units)
      - Number(bucket.leave_units)
      - reserved.tentative
      - reserved.committed,
    );
    return {
      nominalUnits: Number(bucket.nominal_units),
      maintenanceUnits: Number(bucket.maintenance_units),
      leaveUnits: Number(bucket.leave_units),
      tentativeReservedUnits: reserved.tentative,
      committedReservedUnits: reserved.committed,
      availableUnits,
    };
  });
}
```

- [ ] **Step 4: Write DAG/scheduling tests**

```ts
expect(() => validateDag([
  { predecessor: "A", successor: "B" },
  { predecessor: "B", successor: "A" },
])).toThrow("DWS_DEPENDENCY_INCOMPLETE");
```

For an acyclic fixture, assert deterministic topological order and critical path.

- [ ] **Step 5: Implement Kahn DAG validation and deterministic forward schedule**

`scheduling.ts` uses lexical ordering when multiple nodes have indegree zero:

```ts
export function validateDag(nodes: string[], edges: WorkDependency[]): string[] {
  const indegree = new Map(nodes.map((n) => [n, 0]));
  const outgoing = new Map(nodes.map((n) => [n, [] as string[]]));
  for (const e of edges) {
    if (!indegree.has(e.predecessor) || !indegree.has(e.successor)) {
      throw new DwsError("DWS_DEPENDENCY_INCOMPLETE", "dependency references missing work package");
    }
    indegree.set(e.successor, indegree.get(e.successor)! + 1);
    outgoing.get(e.predecessor)!.push(e.successor);
  }
  const queue = [...nodes.filter((n) => indegree.get(n) === 0)].sort();
  const order: string[] = [];
  while (queue.length) {
    const n = queue.shift()!;
    order.push(n);
    for (const next of outgoing.get(n)!.sort()) {
      indegree.set(next, indegree.get(next)! - 1);
      if (indegree.get(next) === 0) queue.push(next), queue.sort();
    }
  }
  if (order.length !== nodes.length) throw new DwsError("DWS_DEPENDENCY_INCOMPLETE", "cycle detected");
  return order;
}
```

`forwardSchedule()` walks this order and calculates each package's earliest start as the max of requested start, predecessor finish, and first capacity-feasible assigned-node window. It returns `planned`, `criticalPath`, `earliestFeasibleCompletion`, `bottleneckCapability`, and affected capacity dates.

- [ ] **Step 6: Implement deterministic recipe decomposition**

`decomposeConfiguration()` accepts exact product-version IDs and configuration version, loads matching recipes, emits work packages/dependencies, validates the DAG, creates the LMO in one transaction, and appends `LMO_CREATED`. Same tenant/idempotency-key + same request hash returns the prior result; same key + different hash throws `DWS_IDEMPOTENCY_CONFLICT`.

```ts
export type DecomposeConfigurationInput = {
  tenantId: string;
  idempotencyKey: string;
  licenseId: string;
  configurationId: string;
  configurationVersion: string;
  productVersionIds: string[];
  requestedStartAt: Date;
  requiredCompletionAt: Date;
  productionReason: "initial" | "upgrade" | "expansion" | "remediation" | "connector_addition";
  routePolicy: "internal" | "contracted" | "hybrid" | "client_operated";
  priority: "standard" | "urgent" | "critical";
};
```

- [ ] **Step 7: Run and commit**

```bash
npm run test:unit -- scheduling
npm run test:integration -- nodes lmo
git add lib/dws-production/db/repositories.ts lib/dws-production/services/nodes.ts lib/dws-production/services/decomposition.ts lib/dws-production/domain/scheduling.ts tests/dws-production
git commit -m "feat: add DWS node registry and LMO scheduling"
```

---

### Task 5: Implement eligibility, routing scores, deterministic tie-breaking, and persisted route evidence

**Files:**
- Create: `lib/dws-production/domain/scoring.ts`
- Create: `lib/dws-production/services/routing.ts`
- Create: `tests/dws-production/routing.test.ts`
- Create: `tests/dws-production/routing.integration.test.ts`

**Interfaces:**
- `evaluateEligibility(input): EligibilityResult`
- `scoreRouteCandidate(input): ScoredCandidate`
- `selectRoute(candidates): ScoredCandidate`
- `persistRoutingDecision(...)`

- [ ] **Step 1: Write hard-predicate eligibility tests**

Include all predicates and this conditional-node case:

```ts
expect(evaluateEligibility({ ...base, nodeStatus: "conditional", override: undefined })).toEqual({
  eligible: false,
  reasons: ["CONDITIONAL_REQUIRES_OVERRIDE"],
});
```

- [ ] **Step 2: Implement exact eligibility function**

```ts
export function evaluateEligibility(i: EligibilityInput): EligibilityResult {
  const reasons: string[] = [];
  if (i.nodeStatus === "conditional" && !(i.override?.authorized && i.override.wardenDecisionId)) reasons.push("CONDITIONAL_REQUIRES_OVERRIDE");
  if (!["active", "conditional"].includes(i.nodeStatus)) reasons.push("NODE_NOT_ASSIGNABLE");
  if (!i.capabilityExists) reasons.push("CAPABILITY_MISSING");
  if (i.skillLevel < i.minimumSkillLevel) reasons.push("SKILL_TOO_LOW");
  if (!i.nodeTypeAllowed) reasons.push("NODE_TYPE_BLOCKED");
  if (!i.productClassAllowed) reasons.push("PRODUCT_CLASS_BLOCKED");
  if (!i.securityAllowed) reasons.push("SECURITY_BLOCKED");
  if (!i.wardenAllowed) reasons.push("WARDEN_DENIED");
  if (i.explicitlyBlocked) reasons.push("NODE_EXPLICITLY_BLOCKED");
  if (!i.capacityUnitSupported) reasons.push("CAPACITY_UNIT_UNSUPPORTED");
  return { eligible: reasons.length === 0, reasons };
}
```

- [ ] **Step 3: Implement exact routing weight behavior**

```ts
const BASE = { capability: .25, capacity: .20, quality: .15, delivery: .15, cost: .10, governance: .10, clientHistory: .05 } as const;

export function effectiveWeights(hasClientHistory: boolean) {
  if (hasClientHistory) return BASE;
  const scale = 1 / 0.95;
  return {
    capability: BASE.capability * scale,
    capacity: BASE.capacity * scale,
    quality: BASE.quality * scale,
    delivery: BASE.delivery * scale,
    cost: BASE.cost * scale,
    governance: BASE.governance * scale,
    clientHistory: 0,
  };
}
```

`scoreRouteCandidate` normalizes all components to 0–100, stores the component breakdown, and computes the weighted sum.

- [ ] **Step 4: Implement deterministic tie-breaking**

```ts
export function compareCandidates(a: ScoredCandidate, b: ScoredCandidate): number {
  const ar = Math.round(a.finalScore * 100) / 100;
  const br = Math.round(b.finalScore * 100) / 100;
  return br - ar
    || b.governanceScore - a.governanceScore
    || b.firstPassYield - a.firstPassYield
    || a.earliestFinish.getTime() - b.earliestFinish.getTime()
    || a.forecastCost - b.forecastCost
    || a.productionNodeId.localeCompare(b.productionNodeId);
}
```

- [ ] **Step 5: Persist complete route evidence**

One transaction inserts a `routing_decisions` row plus one `routing_candidates` row for every considered node, including ineligible reasons, selected node-version ID, performance-snapshot ID, weight-profile ID, algorithm version `R0.4.0`, Warden/River refs, and component scores.

- [ ] **Step 6: Run replay test and commit**

```bash
npm run test:unit -- routing
npm run test:integration -- routing
git add lib/dws-production/domain/scoring.ts lib/dws-production/services/routing.ts tests/dws-production/routing*
git commit -m "feat: add deterministic DWS routing engine"
```

Expected: repeated evaluation of the same fixture produces the same selected node and component scores.

---

### Task 6: Implement transactional capacity holds, atomic commit, expiry, release, and idempotency

**Files:**
- Create: `lib/dws-production/services/capacity.ts`
- Create: `tests/dws-production/capacity.integration.test.ts`

**Interfaces:**
- `simulateCapacity()`
- `holdCapacity()`
- `commitReservationGroup()`
- `releaseReservationGroup()`
- `expireTentativeReservations()`

- [ ] **Step 1: Write concurrent overbooking test before code**

Create one 8-hour bucket; issue two concurrent 6-hour holds:

```ts
const results = await Promise.allSettled([
  holdCapacity(request("idem-a", 6)),
  holdCapacity(request("idem-b", 6)),
]);
expect(results.filter((x) => x.status === "fulfilled")).toHaveLength(1);
expect(await activeReservedUnits(bucketKey)).toBeLessThanOrEqual(8);
```

- [ ] **Step 2: Implement canonical request hashing/idempotency helper**

```ts
import { createHash } from "node:crypto";

export function requestHash(value: unknown): string {
  return createHash("sha256").update(JSON.stringify(value, Object.keys(value as object).sort())).digest("hex");
}
```

Before a mutation, read `(tenant_id,idempotency_key)`: same hash returns stored response; different hash throws `DWS_IDEMPOTENCY_CONFLICT`.

- [ ] **Step 3: Implement row-locking hold transaction**

Sort bucket keys lexically, then in one tenant transaction:

```ts
for (const key of sortedKeys) {
  const bucket = await lockCapacityBucket(tx, input.tenantId, key.productionNodeId, key.date, key.capacityUnit);
  if (!bucket) throw new DwsError("DWS_CAPACITY_UNAVAILABLE", "capacity bucket missing");
  const used = await sumActiveReservationsTx(tx, key);
  const allocatable = Number(bucket.nominal_units) - Number(bucket.maintenance_units) - Number(bucket.leave_units) - used;
  if (allocatable < key.reservedUnits) throw new DwsError("DWS_CAPACITY_CONFLICT", "requested hold exceeds available capacity", true);
}
await insertTentativeReservationGroupAndAllocations(tx, input);
await appendProductionEventTx(tx, capacityReservedEvent(input));
await saveIdempotentResponseTx(tx, input, response);
```

- [ ] **Step 4: Implement all-or-nothing tentative→committed conversion**

Lock the tentative group and the same sorted capacity buckets. Validate `state='active'`, `reservation_type='tentative'`, `expires_at > now()`, and non-empty `authorityRef`. Mark predecessor `converted`, insert one committed successor group with `predecessor_group_id`, copy all allocations, append event, and save idempotent response in the same transaction. Any failure rolls the full transaction back.

- [ ] **Step 5: Implement expiry/release**

`expireTentativeReservations(now)` updates only active tentative groups with `expires_at <= now`, appends `CAPACITY_RESERVATION_EXPIRED`, and relies on active-state filtering to restore availability. `releaseReservationGroup()` changes active group to `released` and is idempotent.

- [ ] **Step 6: Stress the concurrency invariant and commit**

```bash
for i in 1 2 3 4 5; do npm run test:integration -- capacity || exit 1; done
git add lib/dws-production/services/capacity.ts tests/dws-production/capacity.integration.test.ts
git commit -m "feat: add transactional DWS capacity reservations"
```

---

### Task 7: Implement assignments, append-only execution events, QA/NCR gates, and performance intelligence

**Files:**
- Create: `lib/dws-production/services/execution.ts`
- Create: `lib/dws-production/services/quality.ts`
- Create: `lib/dws-production/domain/metrics.ts`
- Create: `lib/dws-production/services/performance.ts`
- Modify: `lib/dws-production/domain/scheduling.ts`
- Create: `tests/dws-production/quality.integration.test.ts`
- Create: `tests/dws-production/performance.test.ts`

**Interfaces:**
- `assignWorkPackage()`
- `appendProductionEvent()`
- `projectWorkPackageState()`
- `startInspection()` / `recordInspectionResult()`
- `openNonconformance()` / `requestRework()` / `closeNonconformance()`
- `acceptWorkPackage()`
- `calculateScheduleConfidence()`
- `createPerformanceSnapshot()`

- [ ] **Step 1: Write the exact QA failure→rework→pass test**

Exercise:

```text
WORK_ASSIGNED → WORK_STARTED → BUILD_SUBMITTED → QA_STARTED → QA_FAILED
→ NONCONFORMANCE_OPENED → REWORK_REQUESTED → REWORK_SUBMITTED
→ QA_STARTED → QA_PASSED → WORK_COMPLETED
```

Assert `acceptWorkPackage()` before QA pass throws `DWS_QA_FAILED`; with a blocking open NCR it throws `DWS_NONCONFORMANCE_OPEN`.

- [ ] **Step 2: Implement append-only event and replay projection**

```ts
export function projectWorkPackageState(events: ProductionEvent[]): WorkPackageState {
  let state: WorkPackageState = "released";
  for (const e of [...events].sort(byOccurredRecordedAndId)) {
    const next = WORK_EVENT_TO_STATE[e.eventType];
    if (!next) continue;
    assertWorkPackageTransition(state, next);
    state = next;
  }
  return state;
}
```

`appendProductionEvent()` only inserts; the database trigger provides a second line of defense against update/delete.

- [ ] **Step 3: Enforce assignment prerequisites**

`assignWorkPackage()` verifies: committed active reservation exists for the selected node/work package; routing decision selected the same immutable node version OR a Warden-authorized manual override exists; dependencies are accepted; node is still assignable under the recorded decision context. Persist assignment and `WORK_ASSIGNED` together.

- [ ] **Step 4: Implement QA/NCR acceptance gate**

`acceptWorkPackage()` loads the latest required inspection and all open/rework NCRs. It permits completion only if result is `pass`, or `pass_with_exception` with evidence/authority, and every blocking NCR is `closed` or `accepted_exception` with `warden_exception_decision_id`.

- [ ] **Step 5: Implement exact metric formulas**

`metrics.ts`:

```ts
export const ratio = (n: number, d: number): number | null => d === 0 ? null : n / d;
export const calculateFirstPassYield = (acceptedFirstPass: number, firstInspections: number) => ratio(acceptedFirstPass, firstInspections);
export const calculateOnTimeRate = (onTime: number, completed: number) => ratio(onTime, completed);
export const calculateReworkRate = (reworked: number, submitted: number) => ratio(reworked, submitted);
export const calculateDefectEscapeRate = (postQaDefects: number, accepted: number) => ratio(postQaDefects, accepted);

export function calculateScheduleConfidence(i: {
  capacityCoverage: number;
  effortModelCoverage: number;
  dependencyCompleteness: number;
  performanceHistoryCoverage: number;
  qaDurationCoverage: number;
}) {
  return i.capacityCoverage * .25
    + i.effortModelCoverage * .25
    + i.dependencyCompleteness * .20
    + i.performanceHistoryCoverage * .15
    + i.qaDurationCoverage * .15;
}
```

Exact test:

```ts
expect(calculateScheduleConfidence({
  capacityCoverage: 100,
  effortModelCoverage: 80,
  dependencyCompleteness: 100,
  performanceHistoryCoverage: 60,
  qaDurationCoverage: 80,
})).toBe(86);
```

- [ ] **Step 6: Implement immutable performance snapshots and bottleneck report**

At LMO completion, aggregate the configured reporting period and insert a new snapshot with `algorithm_version='R0.4.0'`; never update prior snapshots. Extend scheduling output:

```ts
export type BottleneckReport = {
  capabilityCode: string;
  productionNodeIds: string[];
  affectedWorkPackageIds: string[];
  affectedCapacityDates: string[];
  delayHours: number;
};
```

Select the constrained capability/node group on the critical path with highest utilized allocatable capacity; tie-break by capability code lexical order.

- [ ] **Step 7: Run and commit**

```bash
npm run test:unit -- performance scheduling
npm run test:integration -- quality
git add lib/dws-production/services/execution.ts lib/dws-production/services/quality.ts lib/dws-production/domain/metrics.ts lib/dws-production/services/performance.ts lib/dws-production/domain/scheduling.ts tests/dws-production
git commit -m "feat: add DWS execution quality and performance intelligence"
```

---

### Task 8: Add governed internal HTTP adapters and health surface

**Files:**
- Create: `lib/dws-production/http/auth.ts`
- Create: `lib/dws-production/http/response.ts`
- Create all `app/api/dws-production/**/route.ts` files from Target File Map
- Create: `tests/dws-production/http.test.ts`

**Interfaces:**
- Bearer auth: `DWS_INTERNAL_API_TOKEN`
- Context headers: `x-dws-tenant-id`, `x-dws-principal-id`, optional `x-dws-warden-decision-id`

- [ ] **Step 1: Write auth/error mapping tests**

Test missing/incorrect token → 401, missing tenant/principal → 400, Warden-required command without decision ID → 403, `DWS_CAPACITY_CONFLICT` → 409, `DWS_NO_ELIGIBLE_ROUTE` → 422.

- [ ] **Step 2: Implement constant-time internal authentication**

```ts
import { timingSafeEqual } from "node:crypto";

export type DwsRequestContext = { tenantId: string; principalId: string; wardenDecisionId?: string };

export function authenticateDwsRequest(request: Request): DwsRequestContext {
  const expected = process.env.DWS_INTERNAL_API_TOKEN;
  const actual = request.headers.get("authorization")?.replace(/^Bearer\s+/i, "");
  if (!expected || !actual) throw new HttpAuthError(401, "missing credentials");
  const a = Buffer.from(actual); const b = Buffer.from(expected);
  if (a.length !== b.length || !timingSafeEqual(a, b)) throw new HttpAuthError(401, "invalid credentials");
  const tenantId = request.headers.get("x-dws-tenant-id");
  const principalId = request.headers.get("x-dws-principal-id");
  if (!tenantId || !principalId) throw new HttpAuthError(400, "missing DWS request context");
  return { tenantId, principalId, wardenDecisionId: request.headers.get("x-dws-warden-decision-id") ?? undefined };
}
```

- [ ] **Step 3: Implement common error response mapper**

```ts
export function errorResponse(error: unknown): Response {
  if (error instanceof HttpAuthError) return Response.json({ code: "DWS_HTTP_AUTH", message: error.message }, { status: error.status });
  if (error instanceof DwsError) {
    const status = error.code === "DWS_GOVERNANCE_DENIED" ? 403
      : ["DWS_CAPACITY_CONFLICT","DWS_ILLEGAL_STATE_TRANSITION","DWS_IDEMPOTENCY_CONFLICT"].includes(error.code) ? 409
      : ["DWS_CAPACITY_UNAVAILABLE","DWS_NO_ELIGIBLE_ROUTE","DWS_QA_FAILED","DWS_NONCONFORMANCE_OPEN"].includes(error.code) ? 422
      : 400;
    return Response.json({ code: error.code, message: error.message, retryable: error.retryable }, { status });
  }
  const correlationId = crypto.randomUUID();
  console.error("DWS internal error", { correlationId, error });
  return Response.json({ code: "DWS_INTERNAL", correlationId }, { status: 500 });
}
```

- [ ] **Step 4: Implement thin route pattern**

Every mutation route follows:

```ts
export async function POST(request: Request) {
  try {
    const context = authenticateDwsRequest(request);
    const body = CommandSchema.parse(await request.json());
    if (body.tenantId !== context.tenantId) throw new DwsError("DWS_GOVERNANCE_DENIED", "tenant mismatch");
    const result = await service(body, context);
    return Response.json(result);
  } catch (error) {
    return errorResponse(error);
  }
}
```

Map routes exactly to spec service operations: simulate/hold/commit capacity, create/release LMO, append execution event, create/record QA inspection, create/update NCR, register nodes.

- [ ] **Step 5: Add read-only health route**

`GET /api/dws-production/health` runs `select 1`; success:

```json
{"service":"DWS-PRODUCTION-R0.4","version":"R0.4.0","database":"reachable"}
```

DB failure returns 503 with `database:"unreachable"` and no connection detail.

- [ ] **Step 6: Verify HTTP tests and build**

```bash
npm test -- http
npm run build
```

Expected: PASS; `/api/mcp` files are unchanged.

- [ ] **Step 7: Commit**

```bash
git add lib/dws-production/http app/api/dws-production tests/dws-production/http.test.ts
git commit -m "feat: expose governed DWS production API"
```

---

### Task 9: Prove R0.4 end-to-end qualification and CI invariants

**Files:**
- Create: `tests/dws-production/qualification.integration.test.ts`
- Create: `.github/workflows/dws-production.yml`
- Create: `docs/dws-production/R0.4-QUALIFICATION.md`

**Interfaces:**
- Consumes all prior domain/services
- Produces one deterministic qualification fixture and CI gate

- [ ] **Step 1: Write exact qualification fixture**

The integration test must execute these stable fixtures:

```text
PN-DWS-000001  internal API integration node
PN-DWS-000002  contractor API integration node
LMO-DWS-000001
NCR-DWS-000001
WDN-TEST-000001
```

Test sequence:

```text
1 Register both nodes and immutable versions.
2 Give both API_INTEGRATION capability; contractor has lower cost but weaker quality.
3 Seed five daily capacity buckets.
4 Seed one manufacturing recipe and exact approved configuration version.
5 Decompose to LMO-DWS-000001 and DAG.
6 Simulate capacity and prove both candidates pass hard eligibility.
7 Persist R0.4.0 routing decision and assert exact selected node from fixture scores.
8 Create tentative hold.
9 Convert reservation group atomically using WDN-TEST-000001.
10 Release/assign work to selected immutable node version.
11 Append WORK_STARTED and BUILD_SUBMITTED.
12 Fail QA round 1; open NCR-DWS-000001.
13 Prove acceptance/completion is blocked.
14 Request/submit rework; pass QA round 2; close NCR.
15 Accept work; complete LMO.
16 Create immutable node-performance snapshot.
17 Replay work-package event history and assert reconstructed state equals persisted state.
18 Race two conflicting reservations against one capacity bucket and prove no overbooking.
19 Re-run the original fixture inputs and prove the persisted historical routing record did not change after the new performance snapshot.
20 Verify a different tenant cannot read the LMO through tenant-scoped transaction/RLS.
```

- [ ] **Step 2: Add dedicated PostgreSQL CI workflow**

Create `.github/workflows/dws-production.yml`:

```yaml
name: DWS Production R0.4 validation

on:
  pull_request:
    branches: [main]
    paths:
      - "lib/dws-production/**"
      - "app/api/dws-production/**"
      - "db/dws-production/**"
      - "tests/dws-production/**"
      - "infra/dws-production/**"
      - "package.json"
      - "package-lock.json"
      - "tsconfig.json"
      - "vitest.config.ts"
      - ".github/workflows/dws-production.yml"
  push:
    branches: ["feature/data-weaver-r0.4-production-intelligence"]

permissions:
  contents: read

jobs:
  validate:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: dws
          POSTGRES_PASSWORD: dws_test_password
          POSTGRES_DB: dws_production
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U dws -d dws_production"
          --health-interval 2s
          --health-timeout 2s
          --health-retries 20
    env:
      DWS_TEST_DATABASE_URL: postgresql://dws:dws_test_password@127.0.0.1:5432/dws_production
      DWS_INTERNAL_API_TOKEN: ci-only-dws-internal-token
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
      - run: npm ci --no-audit --no-fund
      - run: npm run dws:migrate
      - run: npm test
      - run: npm run build
```

Do not modify `.github/workflows/genesis-seed-mcp.yml`.

- [ ] **Step 3: Write qualification receipt template with actual fixture fields**

`docs/dws-production/R0.4-QUALIFICATION.md` must contain:

```markdown
# DWS Production R0.4 Qualification

- Algorithm version: R0.4.0
- Internal node: PN-DWS-000001
- Contractor node: PN-DWS-000002
- Qualification LMO: LMO-DWS-000001
- Qualification NCR: NCR-DWS-000001
- Warden test decision: WDN-TEST-000001
- No-overbooking invariant: PASS/FAIL from automated test
- Deterministic routing replay: PASS/FAIL
- Event replay equality: PASS/FAIL
- QA fail → NCR → rework → pass: PASS/FAIL
- Tenant isolation: PASS/FAIL
- Build: PASS/FAIL
```

Populate PASS only from test/build results produced during execution.

- [ ] **Step 4: Run full local qualification**

```bash
docker compose -f infra/dws-production/docker-compose.yml up -d
export DWS_TEST_DATABASE_URL=postgresql://dws:dws_dev_password@127.0.0.1:55432/dws_production
export DWS_INTERNAL_API_TOKEN=local-dws-internal-token
npm run dws:migrate
npm test
npm run build
```

Expected: all tests pass, including concurrency/RLS/event replay, and Next.js production build succeeds.

- [ ] **Step 5: Commit**

```bash
git add tests/dws-production/qualification.integration.test.ts .github/workflows/dws-production.yml docs/dws-production/R0.4-QUALIFICATION.md
git commit -m "test: qualify DWS production intelligence R0.4"
```

---

## Execution Order

```text
1 Harness
→ 2 Domain contracts
→ 3 PostgreSQL/RLS/ledger
→ 4 Node registry + LMO scheduling
→ 5 Routing
→ 6 Capacity concurrency
→ 7 Execution + QA + performance
→ 8 HTTP adapters
→ 9 Qualification + CI
```

Do not begin a later task while an earlier task has failing tests or unresolved review findings.

## Definition of Done

R0.4.0 is complete only when automated evidence proves:

- one internal and one contracted Production Node with immutable versions;
- deterministic recipe/configuration decomposition to an LMO DAG;
- hard eligibility exclusion with persisted reasons and conditional-node Warden override path;
- reproducible route scoring, missing-history behavior, and tie-breaking;
- tentative hold, expiry/release, and atomic committed-capacity conversion;
- concurrent holds cannot overbook allocatable capacity;
- assignments bind the recorded immutable node version and committed reservation;
- append-only event replay reconstructs effective state;
- QA failure opens a blocking path through NCR/rework;
- completion cannot bypass required QA/NCR gates;
- completed work can create an immutable R0.4.0 performance snapshot;
- critical-path, bottleneck, and schedule-confidence outputs are deterministic;
- every material mutation is idempotent and tenant scoped;
- cross-tenant access is blocked by transaction context/RLS;
- existing Genesis Seed MCP surface remains unaffected;
- dedicated PostgreSQL CI and `npm run build` pass.
