# Data Weaver Studio R0.4 Production Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the smallest auditable R0.4 production kernel that can register production nodes, decompose an approved configuration into work packages, route work deterministically, reserve capacity without overbooking, record execution/QA evidence, and update node performance.

**Architecture:** Add an isolated server-side TypeScript domain under `lib/dws-production/` with PostgreSQL as the canonical transaction store and thin Next.js route adapters under `app/api/dws-production/`. The existing Genesis Seed MCP route remains unchanged. Capacity, routing, QA, state transitions, and event replay live in pure domain/services; database writes are transactional and all mutating HTTP calls are internal-token protected and idempotent.

**Tech Stack:** Next.js 15.5.18, React 18.3.1, TypeScript 5.6.2, Zod 3.25+, PostgreSQL 16 for local/CI qualification, `postgres` for database access, Vitest for unit/integration tests, Node.js 22 in CI.

**Spec:** `docs/superpowers/specs/2026-09-12-data-weaver-r0.4-production-intelligence-design.md`

## Global Constraints

- R0.4.0 remains deterministic; no predictive ML scheduling, autonomous reassignment, contractor marketplace, billing, or self-modifying routing weights.
- PostgreSQL is the authoritative transaction store; Airtable/Lovable are projections or operator surfaces only.
- `production_node_id` is stable identity; historical assignments bind an immutable `production_node_version_id`.
- Only `active` nodes enter automatic routing. `conditional` nodes require a recorded governed override. `suspended` and `retired` nodes receive no new assignments.
- Routing weights are versioned and default to 25/20/15/15/10/10/5 for capability/capacity/quality/delivery/cost/governance/client-history.
- Missing client-history redistributes its 5% proportionally across the other six routing components; missing history is never treated as zero quality.
- Tentative reservations expire. Reservation-group conversion to committed capacity is atomic.
- All material mutation APIs require an idempotency key.
- Production events are append-only. Current state is a projection and must be reconstructable from history.
- Required QA and open blocking nonconformances prevent acceptance/completion unless an explicit authorized exception exists.
- Tenant/estate isolation is mandatory on all license-linked records.
- Genesis/Warden/River remain external authorities; R0.4 stores stable references and must not duplicate their policy/evidence authority.
- Existing `/api/mcp` and `/api/mcp-selftest` behavior must remain unchanged.

---

## File Structure

Create these focused modules rather than one large service:

```text
lib/dws-production/
  domain/
    ids.ts                 canonical DWS IDs
    schemas.ts             Zod command/domain schemas
    errors.ts              typed DWS error model
    state-machines.ts      LMO/work-package transitions
    scoring.ts             pure eligibility/routing math
    scheduling.ts          DAG/critical-path/schedule-confidence math
    metrics.ts             quality/performance formulas
  db/
    client.ts              PostgreSQL connection + transaction helper
    migrate.ts             migration runner
    repositories.ts        persistence queries grouped by aggregate
  services/
    nodes.ts               node/version/capability registration
    decomposition.ts       recipe → LMO/work-package DAG
    capacity.ts            simulate/hold/commit/release
    routing.ts             eligibility + scoring + persisted decisions
    execution.ts           assignments + append-only events
    quality.ts             inspection/NCR/rework/acceptance gates
    performance.ts         performance snapshot calculation
  http/
    auth.ts                internal API authentication/context
    response.ts            domain-error → HTTP response mapping

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
  domain.test.ts
  routing.test.ts
  scheduling.test.ts
  capacity.integration.test.ts
  lmo.integration.test.ts
  quality.integration.test.ts
  qualification.integration.test.ts

infra/dws-production/docker-compose.yml
scripts/dws-migrate.mjs
.github/workflows/dws-production.yml
```

---

### Task 1: Establish TypeScript test and PostgreSQL development harness

**Files:**
- Modify: `package.json`
- Create: `tsconfig.json`
- Create: `vitest.config.ts`
- Create: `infra/dws-production/docker-compose.yml`
- Create: `lib/dws-production/db/client.ts`
- Create: `tests/dws-production/db-smoke.integration.test.ts`

**Interfaces:**
- Produces: `getDb(): postgres.Sql`, `withTransaction<T>(fn: (tx: postgres.TransactionSql) => Promise<T>): Promise<T>`
- Environment: `DWS_DATABASE_URL`, `DWS_TEST_DATABASE_URL`, `DWS_INTERNAL_API_TOKEN`

- [ ] **Step 1: Add the test/database dependencies and scripts**

Update `package.json` scripts to include:

```json
{
  "test": "vitest run",
  "test:unit": "vitest run tests/dws-production/domain.test.ts tests/dws-production/routing.test.ts tests/dws-production/scheduling.test.ts",
  "test:integration": "vitest run tests/dws-production/*.integration.test.ts",
  "dws:migrate": "node scripts/dws-migrate.mjs"
}
```

Install with:

```bash
npm install postgres
npm install -D vitest
```

Commit the generated `package-lock.json` so dependency resolution is pinned.

- [ ] **Step 2: Add compiler and test configuration**

Create `tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules", "seed-node-v0.1"]
}
```

Create `vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["tests/dws-production/**/*.test.ts"],
    sequence: { concurrent: false },
  },
});
```

- [ ] **Step 3: Add a dedicated local PostgreSQL 16 test service**

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

Local test URL:

```text
postgresql://dws:dws_dev_password@127.0.0.1:55432/dws_production
```

- [ ] **Step 4: Write the failing database smoke test**

```ts
import { describe, expect, it } from "vitest";
import { getDb } from "@/lib/dws-production/db/client";

describe("DWS database", () => {
  it("connects to the configured PostgreSQL database", async () => {
    const db = getDb();
    const rows = await db<{ ok: number }[]>`select 1 as ok`;
    expect(rows[0].ok).toBe(1);
  });
});
```

Run:

```bash
DWS_TEST_DATABASE_URL=postgresql://dws:dws_dev_password@127.0.0.1:55432/dws_production npm run test:integration -- db-smoke
```

Expected: FAIL because `client.ts` does not exist.

- [ ] **Step 5: Implement the minimal DB client**

```ts
import postgres, { type Sql, type TransactionSql } from "postgres";

let singleton: Sql | undefined;

export function getDb(): Sql {
  const url = process.env.DWS_TEST_DATABASE_URL ?? process.env.DWS_DATABASE_URL;
  if (!url) throw new Error("DWS_DATABASE_URL is required");
  singleton ??= postgres(url, { max: 10, prepare: false });
  return singleton;
}

export async function withTransaction<T>(
  fn: (tx: TransactionSql) => Promise<T>,
): Promise<T> {
  return getDb().begin(fn);
}
```

Run the smoke test again and expect PASS.

- [ ] **Step 6: Verify the existing app still builds**

```bash
npm run build
```

Expected: Next.js production build succeeds and existing MCP routes compile unchanged.

- [ ] **Step 7: Commit**

```bash
git add package.json package-lock.json tsconfig.json vitest.config.ts infra/dws-production lib/dws-production/db/client.ts tests/dws-production/db-smoke.integration.test.ts
git commit -m "chore: establish DWS production test harness"
```

---

### Task 2: Define canonical domain contracts, IDs, errors, and state transitions

**Files:**
- Create: `lib/dws-production/domain/ids.ts`
- Create: `lib/dws-production/domain/schemas.ts`
- Create: `lib/dws-production/domain/errors.ts`
- Create: `lib/dws-production/domain/state-machines.ts`
- Create: `tests/dws-production/domain.test.ts`

**Interfaces:**
- Produces: `makeDwsId(prefix, sequence)`, Zod schemas for node/LMO/work package/reservation/event/QA commands, `DwsError`, `assertLmoTransition`, `assertWorkPackageTransition`

- [ ] **Step 1: Write failing ID/state-machine tests**

```ts
import { describe, expect, it } from "vitest";
import { makeDwsId } from "@/lib/dws-production/domain/ids";
import { assertLmoTransition } from "@/lib/dws-production/domain/state-machines";

it("formats stable canonical IDs", () => {
  expect(makeDwsId("LMO-DWS", 42)).toBe("LMO-DWS-000042");
});

it("rejects illegal LMO transitions", () => {
  expect(() => assertLmoTransition("planned", "completed")).toThrow("DWS_ILLEGAL_STATE_TRANSITION");
});
```

Run `npm run test:unit`; expected FAIL.

- [ ] **Step 2: Implement canonical IDs**

```ts
export function makeDwsId(prefix: string, sequence: number): string {
  if (!Number.isInteger(sequence) || sequence < 1) throw new Error("sequence must be a positive integer");
  return `${prefix}-${String(sequence).padStart(6, "0")}`;
}
```

- [ ] **Step 3: Implement the typed error model**

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

- [ ] **Step 4: Implement exact state transition tables**

```ts
const LMO_TRANSITIONS: Record<string, readonly string[]> = {
  planned: ["capacity_checked", "cancelled"],
  capacity_checked: ["reserved", "cancelled"],
  reserved: ["released", "cancelled"],
  released: ["in_progress", "cancelled"],
  in_progress: ["qa_hold", "completed", "cancelled"],
  qa_hold: ["in_progress", "completed", "cancelled"],
  completed: [],
  cancelled: [],
};

export function assertLmoTransition(from: string, to: string): void {
  if (!LMO_TRANSITIONS[from]?.includes(to)) {
    throw new DwsError("DWS_ILLEGAL_STATE_TRANSITION", `${from} -> ${to}`);
  }
}
```

Implement the work-package transition table directly from the approved spec.

- [ ] **Step 5: Add Zod command schemas**

At minimum export `RegisterNodeSchema`, `CreateLmoSchema`, `CapacityHoldSchema`, `ProductionEventSchema`, `InspectionResultSchema`, and `NonconformanceSchema`. Every license-linked command includes `tenantId`; every mutation includes `idempotencyKey`.

Example:

```ts
export const CreateLmoSchema = z.object({
  tenantId: z.string().min(1),
  idempotencyKey: z.string().min(8),
  licenseId: z.string().min(1),
  configurationId: z.string().min(1),
  productVersionIds: z.array(z.string().min(1)).min(1),
  productionReason: z.enum(["initial", "upgrade", "expansion", "remediation", "connector_addition"]),
  routePolicy: z.enum(["internal", "contracted", "hybrid", "client_operated"]),
  priority: z.enum(["standard", "urgent", "critical"]),
  requestedStartAt: z.string().datetime(),
  requiredCompletionAt: z.string().datetime(),
});
```

- [ ] **Step 6: Run unit tests and build**

```bash
npm run test:unit
npm run build
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add lib/dws-production/domain tests/dws-production/domain.test.ts
git commit -m "feat: define DWS production domain contracts"
```

---

### Task 3: Create the canonical PostgreSQL schema and migration runner

**Files:**
- Create: `db/dws-production/001_r04_core.sql`
- Create: `db/dws-production/002_r04_indexes.sql`
- Create: `lib/dws-production/db/migrate.ts`
- Create: `scripts/dws-migrate.mjs`
- Create: `tests/dws-production/schema.integration.test.ts`

**Interfaces:**
- Produces schemas: `dws_core`, `dws_capacity`, `dws_routing`, `dws_quality`, `dws_ledger`
- Produces tables named in the approved spec plus `reservation_allocations` and `idempotency_keys` needed for exact concurrency semantics.

- [ ] **Step 1: Write a failing schema test**

Test that after migration the following relations exist: `dws_core.production_nodes`, `dws_core.production_node_versions`, `dws_core.node_capabilities`, `dws_core.manufacturing_recipes`, `dws_core.manufacturing_recipe_steps`, `dws_core.lmos`, `dws_core.work_packages`, `dws_core.work_package_dependencies`, `dws_core.assignments`, `dws_capacity.capacity_buckets`, `dws_capacity.reservation_groups`, `dws_capacity.reservations`, `dws_capacity.reservation_allocations`, `dws_routing.routing_decisions`, `dws_routing.routing_candidates`, `dws_quality.inspections`, `dws_quality.nonconformances`, `dws_quality.performance_snapshots`, `dws_ledger.production_events`, `dws_ledger.idempotency_keys`.

Use:

```ts
const rows = await db<{ table_schema: string; table_name: string }[]>`
  select table_schema, table_name
  from information_schema.tables
  where table_schema like 'dws_%'
`;
expect(new Set(rows.map(r => `${r.table_schema}.${r.table_name}`))).toContain("dws_core.production_nodes");
```

- [ ] **Step 2: Implement `001_r04_core.sql`**

Use `TEXT` canonical IDs as external primary keys, `tenant_id TEXT NOT NULL` on every tenant-bound aggregate, `TIMESTAMPTZ`, explicit `CHECK` constraints for enum-like state fields, and foreign keys between aggregate records. Use `JSONB` only for event payload/evidence metadata, not for fields needed for routing/capacity predicates.

Critical capacity tables must include:

```sql
CREATE TABLE dws_capacity.capacity_buckets (
  tenant_id TEXT NOT NULL,
  production_node_id TEXT NOT NULL,
  capacity_date DATE NOT NULL,
  capacity_unit TEXT NOT NULL,
  nominal_units NUMERIC(14,4) NOT NULL CHECK (nominal_units >= 0),
  maintenance_units NUMERIC(14,4) NOT NULL DEFAULT 0 CHECK (maintenance_units >= 0),
  leave_units NUMERIC(14,4) NOT NULL DEFAULT 0 CHECK (leave_units >= 0),
  PRIMARY KEY (tenant_id, production_node_id, capacity_date, capacity_unit)
);

CREATE TABLE dws_capacity.reservation_groups (
  reservation_group_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  reservation_type TEXT NOT NULL CHECK (reservation_type IN ('tentative','committed')),
  source_type TEXT NOT NULL CHECK (source_type IN ('simulation','quote','lmo')),
  source_id TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('active','converted','released','expired','cancelled')),
  expires_at TIMESTAMPTZ,
  authority_ref TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE dws_capacity.reservation_allocations (
  reservation_group_id TEXT NOT NULL REFERENCES dws_capacity.reservation_groups(reservation_group_id),
  tenant_id TEXT NOT NULL,
  production_node_id TEXT NOT NULL,
  capacity_date DATE NOT NULL,
  capacity_unit TEXT NOT NULL,
  reserved_units NUMERIC(14,4) NOT NULL CHECK (reserved_units > 0),
  PRIMARY KEY (reservation_group_id, production_node_id, capacity_date, capacity_unit)
);
```

- [ ] **Step 3: Implement indexes in `002_r04_indexes.sql`**

Add indexes for tenant + state + time queries, node/capability eligibility, work-package dependencies, active reservation allocation lookup, event aggregate replay, QA/NCR blocking lookup, and idempotency-key lookup.

- [ ] **Step 4: Implement migration runner**

`migrate.ts` must create `dws_ledger.schema_migrations`, read SQL files in lexical order, hash contents with SHA-256, refuse a changed already-applied migration, and apply each migration transactionally.

- [ ] **Step 5: Add the CLI wrapper**

`scripts/dws-migrate.mjs` imports the compiled/runtime TypeScript migration entry through Next-compatible module resolution by invoking `npx tsx lib/dws-production/db/migrate.ts`; therefore add `tsx` as a dev dependency and make the npm script `dws:migrate` equal to `tsx lib/dws-production/db/migrate.ts` instead of shelling recursively.

- [ ] **Step 6: Run migrations and schema test**

```bash
DWS_TEST_DATABASE_URL=postgresql://dws:dws_dev_password@127.0.0.1:55432/dws_production npm run dws:migrate
DWS_TEST_DATABASE_URL=postgresql://dws:dws_dev_password@127.0.0.1:55432/dws_production npm run test:integration -- schema
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add db/dws-production lib/dws-production/db/migrate.ts scripts/dws-migrate.mjs tests/dws-production/schema.integration.test.ts package.json package-lock.json
git commit -m "feat: add DWS production database schema"
```

---

### Task 4: Implement production-node registry and deterministic capacity projections

**Files:**
- Create: `lib/dws-production/db/repositories.ts`
- Create: `lib/dws-production/services/nodes.ts`
- Create: `tests/dws-production/nodes.integration.test.ts`

**Interfaces:**
- Produces: `registerProductionNode`, `createProductionNodeVersion`, `addNodeCapability`, `upsertCapacityBucket`, `getAvailableCapacity`

- [ ] **Step 1: Write failing node/version tests**

Test that:

1. registering a node produces stable `production_node_id`;
2. changing capability/governance creates a new immutable version rather than mutating the previous row;
3. an assignment can later reference the old version;
4. capacity availability subtracts active tentative + committed allocations but ignores released/expired groups.

- [ ] **Step 2: Implement repository primitives**

Keep SQL access explicit. Example signature:

```ts
export interface DwsRepositories {
  insertNode(tx: SqlLike, input: InsertNode): Promise<ProductionNode>;
  insertNodeVersion(tx: SqlLike, input: InsertNodeVersion): Promise<ProductionNodeVersion>;
  listEligibleCapabilities(tx: SqlLike, tenantId: string, capabilityCode: string): Promise<NodeCapabilityRow[]>;
  lockCapacityBuckets(tx: SqlLike, keys: CapacityBucketKey[]): Promise<CapacityBucketRow[]>;
}
```

Do not hide transactions inside repository methods; services own transaction boundaries.

- [ ] **Step 3: Implement capacity projection**

`getAvailableCapacity` queries the bucket plus active reservation allocations and returns:

```ts
{
  nominalUnits,
  maintenanceUnits,
  leaveUnits,
  tentativeReservedUnits,
  committedReservedUnits,
  availableUnits: Math.max(0, nominal - maintenance - leave - tentative - committed),
}
```

- [ ] **Step 4: Run integration tests**

```bash
npm run test:integration -- nodes
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/dws-production/db/repositories.ts lib/dws-production/services/nodes.ts tests/dws-production/nodes.integration.test.ts
git commit -m "feat: add production node and capacity registry"
```

---

### Task 5: Implement manufacturing recipes, LMO decomposition, DAG validation, and forward scheduling

**Files:**
- Create: `lib/dws-production/services/decomposition.ts`
- Create: `lib/dws-production/domain/scheduling.ts`
- Create: `tests/dws-production/scheduling.test.ts`
- Create: `tests/dws-production/lmo.integration.test.ts`

**Interfaces:**
- Produces: `decomposeConfiguration`, `validateDag`, `calculateCriticalPath`, `forwardSchedule`

- [ ] **Step 1: Write failing DAG tests**

```ts
it("rejects cyclic manufacturing recipes", () => {
  expect(() => validateDag([
    { predecessor: "WP-A", successor: "WP-B" },
    { predecessor: "WP-B", successor: "WP-A" },
  ])).toThrow("DWS_DEPENDENCY_INCOMPLETE");
});
```

Also test a known nine-step order recipe and assert the critical path follows the configured finish-to-start chain.

- [ ] **Step 2: Implement topological sorting and critical-path math**

Use Kahn's algorithm. Keep all scheduling pure and dependency-type fixed to `finish_to_start` for R0.4.0.

`forwardSchedule` accepts:

```ts
export type ForwardScheduleInput = {
  requestedStart: Date;
  workPackages: ScheduledWorkPackage[];
  dependencies: WorkDependency[];
  capacityWindows: Record<string, CapacityWindow[]>;
};
```

and returns planned start/finish for each package plus `criticalPath`, `earliestFeasibleCompletion`, and `bottleneckCapability`.

- [ ] **Step 3: Implement deterministic recipe decomposition**

`decomposeConfiguration` loads exact product-version recipes, verifies configuration version IDs, creates one LMO plus versioned work-package rows and dependency rows in one transaction, and appends `LMO_CREATED` only after persistence succeeds.

A second call with the same idempotency key returns the prior LMO rather than creating duplicates.

- [ ] **Step 4: Run tests**

```bash
npm run test:unit -- scheduling
npm run test:integration -- lmo
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/dws-production/services/decomposition.ts lib/dws-production/domain/scheduling.ts tests/dws-production/scheduling.test.ts tests/dws-production/lmo.integration.test.ts
git commit -m "feat: decompose DWS license manufacturing orders"
```

---

### Task 6: Implement eligibility, routing scores, deterministic tie-breaking, and governed override records

**Files:**
- Create: `lib/dws-production/domain/scoring.ts`
- Create: `lib/dws-production/services/routing.ts`
- Create: `tests/dws-production/routing.test.ts`
- Create: `tests/dws-production/routing.integration.test.ts`

**Interfaces:**
- Produces: `evaluateEligibility`, `scoreRouteCandidate`, `selectRoute`, `persistRoutingDecision`

- [ ] **Step 1: Write failing eligibility tests**

Cover every hard predicate from the spec. Explicitly assert:

```ts
expect(evaluateEligibility({ nodeStatus: "conditional", override: null, ...base })).toEqual({
  eligible: false,
  reasons: ["CONDITIONAL_REQUIRES_OVERRIDE"],
});
```

- [ ] **Step 2: Implement pure eligibility**

Automatic eligibility is exactly:

```ts
node.status === "active" &&
capabilityExists &&
skillLevel >= minimumSkillLevel &&
nodeTypeAllowed &&
productClassAllowed &&
securityAllowed &&
wardenAllowed &&
!explicitlyBlocked &&
capacityUnitSupported
```

Conditional nodes may return eligible only when `override.authorized === true` and `override.wardenDecisionId` is non-empty.

- [ ] **Step 3: Implement routing score with missing-history redistribution**

Use the base weights:

```ts
const BASE_WEIGHTS = {
  capability: 0.25,
  capacity: 0.20,
  quality: 0.15,
  delivery: 0.15,
  cost: 0.10,
  governance: 0.10,
  clientHistory: 0.05,
} as const;
```

If `clientHistory` is absent, divide each of the first six weights by `0.95` so they again sum to 1.0.

- [ ] **Step 4: Implement tie-breaking**

Sort candidates by final score rounded to two decimals, then governance score desc, first-pass yield desc, earliest finish asc, forecast cost asc, `production_node_id` lexical asc.

- [ ] **Step 5: Persist complete routing evidence**

The persisted routing decision includes all eligible candidates with component scores, all ineligible candidates with reasons, exact node-version/performance-snapshot IDs used, algorithm version `R0.4.0`, weight-profile ID, Warden decision reference, and selected node.

- [ ] **Step 6: Run unit/integration tests**

```bash
npm run test:unit -- routing
npm run test:integration -- routing
```

Expected: PASS with deterministic replay of the same fixture.

- [ ] **Step 7: Commit**

```bash
git add lib/dws-production/domain/scoring.ts lib/dws-production/services/routing.ts tests/dws-production/routing.test.ts tests/dws-production/routing.integration.test.ts
git commit -m "feat: add deterministic DWS routing engine"
```

---

### Task 7: Implement transactional tentative holds, atomic commit, expiry, release, and idempotency

**Files:**
- Create: `lib/dws-production/services/capacity.ts`
- Create: `tests/dws-production/capacity.integration.test.ts`

**Interfaces:**
- Produces: `simulateCapacity`, `holdCapacity`, `commitReservationGroup`, `releaseReservationGroup`, `expireTentativeReservations`

- [ ] **Step 1: Write the concurrent overbooking test first**

Create one bucket with `8` allocatable engineering hours. Fire two concurrent hold requests for `6` hours against the same node/date. Assert exactly one succeeds and total active allocations never exceed `8`.

```ts
const results = await Promise.allSettled([
  holdCapacity(db, request("idem-a", 6)),
  holdCapacity(db, request("idem-b", 6)),
]);
expect(results.filter(r => r.status === "fulfilled")).toHaveLength(1);
```

Expected initially: FAIL because `holdCapacity` is absent.

- [ ] **Step 2: Implement bucket locking and allocation checks**

Within one DB transaction:

1. sort requested bucket keys lexically to prevent lock-order deadlocks;
2. `SELECT ... FOR UPDATE` each `capacity_buckets` row;
3. calculate active tentative/committed allocations;
4. reject with `DWS_CAPACITY_CONFLICT` if any bucket would go negative;
5. insert reservation group + allocations;
6. insert one idempotency result record before commit;
7. append `CAPACITY_RESERVED` event.

- [ ] **Step 3: Implement atomic tentative→committed conversion**

Lock the reservation group and all allocation buckets. Reject expired/inactive groups. Update the group to `converted`, create a committed successor group referencing the authority, and transition every allocation as one transaction. If any row fails, rollback all changes.

- [ ] **Step 4: Implement expiry/release**

`expireTentativeReservations(now)` updates only active tentative groups with `expires_at <= now`, appends `CAPACITY_RESERVATION_EXPIRED`, and immediately restores availability through projection semantics.

- [ ] **Step 5: Verify idempotency conflict behavior**

Same key + same canonical request hash returns prior result. Same key + different request hash throws `DWS_IDEMPOTENCY_CONFLICT`.

- [ ] **Step 6: Run the capacity suite repeatedly**

```bash
for i in 1 2 3 4 5; do npm run test:integration -- capacity || exit 1; done
```

Expected: every run passes; no overbooking.

- [ ] **Step 7: Commit**

```bash
git add lib/dws-production/services/capacity.ts tests/dws-production/capacity.integration.test.ts
git commit -m "feat: add transactional DWS capacity reservations"
```

---

### Task 8: Implement assignments, append-only production events, QA inspections, NCR, rework, and acceptance gates

**Files:**
- Create: `lib/dws-production/services/execution.ts`
- Create: `lib/dws-production/services/quality.ts`
- Create: `tests/dws-production/quality.integration.test.ts`

**Interfaces:**
- Produces: `assignWorkPackage`, `appendProductionEvent`, `projectWorkPackageState`, `startInspection`, `recordInspectionResult`, `openNonconformance`, `requestRework`, `closeNonconformance`, `acceptWorkPackage`

- [ ] **Step 1: Write the full QA failure/rework test before implementation**

The fixture must execute:

```text
WORK_ASSIGNED
→ WORK_STARTED
→ BUILD_SUBMITTED
→ QA_STARTED
→ QA_FAILED
→ NONCONFORMANCE_OPENED
→ REWORK_REQUESTED
→ REWORK_SUBMITTED
→ QA_STARTED
→ QA_PASSED
→ WORK_COMPLETED
```

Assert acceptance before QA pass throws `DWS_QA_FAILED`, and acceptance with an open blocking NCR throws `DWS_NONCONFORMANCE_OPEN`.

- [ ] **Step 2: Implement append-only events**

`appendProductionEvent` inserts exactly one event per `(tenant_id, idempotency_key)`, validates the event type against `event_type_registry`, never updates/deletes prior event rows, and records `occurred_at` separately from `recorded_at`.

- [ ] **Step 3: Implement event-derived state projection**

`projectWorkPackageState(events)` folds the ordered event stream through the work-package transition rules. Add a test proving the resulting state equals the materialized work-package state after each command.

- [ ] **Step 4: Implement assignment validity**

Assignments require a persisted routing decision or a Warden-authorized manual override, a non-expired committed reservation, and the exact `production_node_version_id` selected at decision time.

- [ ] **Step 5: Implement QA/NCR gates**

`recordInspectionResult(..., "fail")` creates/permits NCR creation and moves work to rework/QA-hold semantics. `acceptWorkPackage` verifies latest required inspection is pass/pass_with_exception and no blocking NCR remains open unless that NCR contains a Warden-authorized accepted-exception reference.

- [ ] **Step 6: Run integration tests**

```bash
npm run test:integration -- quality
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add lib/dws-production/services/execution.ts lib/dws-production/services/quality.ts tests/dws-production/quality.integration.test.ts
git commit -m "feat: add DWS execution and QA lifecycle"
```

---

### Task 9: Implement production metrics, node-performance snapshots, bottleneck output, and schedule confidence

**Files:**
- Create: `lib/dws-production/domain/metrics.ts`
- Create: `lib/dws-production/services/performance.ts`
- Modify: `lib/dws-production/domain/scheduling.ts`
- Create: `tests/dws-production/performance.test.ts`

**Interfaces:**
- Produces: `calculateFirstPassYield`, `calculateOnTimeRate`, `calculateReworkRate`, `calculateDefectEscapeRate`, `calculateScheduleConfidence`, `createPerformanceSnapshot`

- [ ] **Step 1: Write metric tests with exact fixtures**

For 10 first inspections with 8 first-pass acceptances, assert FPY = `0.8`. For 10 completed packages with 9 on time, assert `0.9`. For schedule confidence components `100, 80, 100, 60, 80`, assert:

```ts
expect(calculateScheduleConfidence({
  capacityCoverage: 100,
  effortModelCoverage: 80,
  dependencyCompleteness: 100,
  performanceHistoryCoverage: 60,
  qaDurationCoverage: 80,
})).toBe(85);
```

because `25 + 20 + 20 + 9 + 12 = 86`; use the mathematically correct expected value `86` in the test.

- [ ] **Step 2: Implement pure metric functions**

Guard zero-denominator metrics by returning `null`, not zero, so absence of history is distinguishable from bad performance.

- [ ] **Step 3: Implement versioned performance snapshots**

At LMO completion, aggregate the configured period and persist a new immutable snapshot with `algorithm_version = 'R0.4.0'` and sample size. Routing never rewrites historical decisions when a newer snapshot appears.

- [ ] **Step 4: Add bottleneck output to scheduling**

Return the capability/node group with highest constrained utilization on the critical path, affected work-package IDs, affected capacity dates, and total completion delay attributable to the constraint.

- [ ] **Step 5: Run tests**

```bash
npm run test:unit -- performance scheduling
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add lib/dws-production/domain/metrics.ts lib/dws-production/services/performance.ts lib/dws-production/domain/scheduling.ts tests/dws-production/performance.test.ts
git commit -m "feat: add DWS production performance intelligence"
```

---

### Task 10: Add secure internal Next.js API adapters without coupling domain logic to HTTP

**Files:**
- Create: `lib/dws-production/http/auth.ts`
- Create: `lib/dws-production/http/response.ts`
- Create route files under `app/api/dws-production/**` listed in File Structure
- Create: `tests/dws-production/http.test.ts`

**Interfaces:**
- Produces: internal REST command surface for R0.2/R0.3/operator consoles
- Authentication: `Authorization: Bearer $DWS_INTERNAL_API_TOKEN`, `x-dws-tenant-id`, `x-dws-principal-id`; governed operations also accept/require `x-dws-warden-decision-id` according to service command.

- [ ] **Step 1: Write failing auth tests**

Test 401 for missing/incorrect bearer token, 400 for missing tenant/principal context, and success context parsing for valid headers.

- [ ] **Step 2: Implement constant-time bearer comparison**

Use Node `crypto.timingSafeEqual` after length equality. Never log the token.

```ts
export type DwsRequestContext = {
  tenantId: string;
  principalId: string;
  wardenDecisionId?: string;
};
```

- [ ] **Step 3: Implement HTTP error mapping**

Map:

- validation errors → 400;
- governance/authorization → 401/403;
- illegal transition/idempotency/capacity conflict → 409;
- unavailable capacity/no eligible route → 422;
- unknown errors → 500 with correlation ID and no secret internals.

- [ ] **Step 4: Add thin routes**

Each route must do only:

```ts
const context = authenticateDwsRequest(request);
const body = Schema.parse(await request.json());
const result = await service(body, context);
return Response.json(result, { status: 200 });
```

Do not put routing weights, capacity arithmetic, SQL, or QA rules in route files.

- [ ] **Step 5: Add a read-only health route**

`GET /api/dws-production/health` returns only:

```json
{
  "service": "DWS-PRODUCTION-R0.4",
  "version": "R0.4.0",
  "database": "reachable"
}
```

and returns 503 when the database probe fails.

- [ ] **Step 6: Verify routes compile and existing MCP self-test remains intact**

```bash
npm run test -- http
npm run build
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add lib/dws-production/http app/api/dws-production tests/dws-production/http.test.ts
git commit -m "feat: expose governed DWS production API"
```

---

### Task 11: Prove the complete R0.4 qualification flow and add dedicated CI

**Files:**
- Create: `tests/dws-production/qualification.integration.test.ts`
- Create: `.github/workflows/dws-production.yml`
- Create: `docs/dws-production/R0.4-QUALIFICATION.md`

**Interfaces:**
- Consumes all prior R0.4 services
- Produces one deterministic qualification receipt fixture and CI gate

- [ ] **Step 1: Write the end-to-end qualification test**

The test must perform, using stable fixture IDs:

```text
1. Register PN-DWS-000001 internal and PN-DWS-000002 contractor.
2. Give both API_INTEGRATION capability; give contractor lower cost but weaker quality.
3. Create five daily capacity buckets for both nodes.
4. Insert one manufacturing recipe and approved configuration fixture.
5. Decompose to LMO-DWS-000001 and work-package DAG.
6. Simulate capacity and prove both nodes are eligible.
7. Route using R0.4.0 weights and assert the exact selected node from fixture scores.
8. Create tentative capacity hold.
9. Convert the reservation group atomically with authority `WDN-TEST-000001`.
10. Release/assign work.
11. Append start + submit events.
12. Fail first QA inspection and open NCR-DWS-000001.
13. Prove completion is blocked.
14. Submit rework, pass second QA inspection, close NCR.
15. Complete work and LMO.
16. Create a node-performance snapshot.
17. Replay event history and assert reconstructed state = persisted state.
18. Attempt two conflicting concurrent reservations and assert no overbooking.
19. Re-run the original routing fixture and prove its persisted historical decision is unchanged by the new performance snapshot.
```

- [ ] **Step 2: Add PostgreSQL 16 GitHub Actions service**

Create `.github/workflows/dws-production.yml` with:

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

Keep the existing `genesis-seed-mcp.yml` workflow unchanged.

- [ ] **Step 3: Document the qualification receipt**

`R0.4-QUALIFICATION.md` records the fixture IDs, commands run, expected invariants, and CI workflow name. It explicitly lists:

- no-overbooking result;
- deterministic routing decision ID;
- QA fail→NCR→rework→pass sequence;
- event replay equality;
- performance snapshot version;
- build/test commands.

- [ ] **Step 4: Run the full local qualification**

```bash
docker compose -f infra/dws-production/docker-compose.yml up -d
export DWS_TEST_DATABASE_URL=postgresql://dws:dws_dev_password@127.0.0.1:55432/dws_production
export DWS_INTERNAL_API_TOKEN=local-dws-internal-token
npm run dws:migrate
npm test
npm run build
```

Expected: all DWS tests pass and the Next production build succeeds.

- [ ] **Step 5: Commit**

```bash
git add tests/dws-production/qualification.integration.test.ts .github/workflows/dws-production.yml docs/dws-production/R0.4-QUALIFICATION.md
git commit -m "test: qualify DWS production intelligence R0.4"
```

---

## Execution Order and Review Gates

Execute strictly in this order:

```text
1 Tooling
→ 2 Domain contracts
→ 3 Schema
→ 4 Node/capacity registry
→ 5 LMO decomposition/scheduling
→ 6 Routing
→ 7 Reservation concurrency
→ 8 Execution + QA
→ 9 Performance intelligence
→ 10 HTTP adapters
→ 11 Qualification + CI
```

A reviewer may reject any task independently. Do not begin a later task while an earlier task has failing tests or unresolved review findings.

## Definition of Done

R0.4 implementation is complete only when all of the following are evidenced by automated tests:

- one internal and one contracted production node with immutable versions;
- deterministic product/configuration decomposition to an LMO DAG;
- hard eligibility exclusion with persisted reasons;
- reproducible routing with versioned weights and exact tie-breaking;
- tentative capacity hold, expiry/release, and atomic commitment;
- concurrent reservation attempts cannot overbook a bucket;
- assignment binds the selected node version and committed reservation;
- event ledger replay reconstructs the same effective state;
- QA failure creates a blocking path through NCR and rework;
- completion cannot bypass required QA/NCR gates;
- completed work produces an immutable performance snapshot;
- bottleneck/critical-path and schedule-confidence outputs are reproducible;
- all mutation paths are idempotent and tenant-scoped;
- existing Genesis Seed MCP build/self-test surface remains unaffected;
- the dedicated GitHub Actions workflow passes PostgreSQL integration tests and `npm run build`.
