# Data Weaver Studio R0.4 — Production Intelligence & Digital Factory

**Status:** Approved design specification  
**Release:** R0.4.0  
**Date:** 2026-09-12  
**Repository:** `Esomoire-consultancy-Company/synnergyzehub`  
**Scope:** Deterministic production substrate for licensed Data Weaver products

## 1. Purpose

R0.4 introduces a production-intelligence layer between the R0.3 simulation/configuration engine and the R0.2 license/deployment lifecycle.

Its responsibility is to answer, before and after a sale:

1. What work must be performed to manufacture or configure the licensed instance?
2. Which internal or contracted production nodes are eligible to perform that work?
3. Does sufficient capacity exist within the requested delivery window?
4. What capacity should be reserved before the quote becomes binding?
5. How should work be routed when several eligible nodes exist?
6. What execution evidence is required to prove the work occurred?
7. Did the produced instance pass the required quality gates?
8. How should actual delivery and quality performance affect future routing decisions?

R0.4 is not a generic project-management tool. It is a deterministic manufacturing-control substrate for deployable software/data licenses.

## 2. Governing Principle

A license is commercially sold only after the system can show a feasible route from configuration to production capacity, quality assurance, and deployment.

The core production chain is:

```text
Approved Configuration
        ↓
License Manufacturing Order (LMO)
        ↓
Work Package Decomposition
        ↓
Eligibility + Capacity Check
        ↓
Capacity Reservation
        ↓
Work Assignment
        ↓
Execution Event Ledger
        ↓
QA / Nonconformance
        ↓
Deployment Acceptance
        ↓
Production-Node Performance Update
        ↓
Future Simulation / Routing Learning
```

## 3. Scope

### 3.1 In scope for R0.4.0

R0.4.0 MUST provide:

- production-node registration;
- production-node capability registration;
- deterministic capacity calendars;
- tentative and committed capacity reservations;
- license manufacturing orders;
- work-package decomposition;
- eligibility filtering;
- deterministic routing/scoring;
- work assignment;
- immutable production-event recording;
- QA inspection records;
- nonconformance and rework handling;
- node-performance aggregation;
- bottleneck and critical-path calculations;
- APIs/events required by R0.2 and R0.3;
- governance hooks for Genesis identity, Warden authorization, and River evidence receipts.

### 3.2 Explicitly out of scope for R0.4.0

The following are deferred:

- autonomous AI production scheduling;
- autonomous reassignment without authority approval;
- contractor procurement marketplace;
- dynamic bidding between contractors;
- financial settlement or invoicing;
- payroll/timekeeping;
- generalized HR capacity planning;
- generative project decomposition without an approved product BOM;
- predictive ML scheduling;
- automatic product changes in response to QA failures;
- self-modifying routing weights.

R0.4.0 is deliberately deterministic so routing, capacity, and quality decisions can be explained and audited.

## 4. System Boundary

R0.4 sits between existing logical layers:

```text
R0.1 Product Registry
        │
        ├── product definition
        ├── product version
        ├── component BOM
        └── QA specification
        │
R0.3 Simulation + Configuration Engine
        │
        ├── client requirements
        ├── approved configuration
        ├── runtime option
        ├── forecast work
        └── commercial feasibility
        │
        ▼
┌──────────────────────────────────────┐
│ R0.4 Production Intelligence Kernel │
│                                      │
│ Capacity                             │
│ Routing                              │
│ Reservations                         │
│ Execution Ledger                     │
│ QA                                   │
│ Performance                          │
└──────────────────────────────────────┘
        │
        ▼
R0.2 License + Deployment Lifecycle
        │
        ├── deployed instance
        ├── acceptance
        ├── support
        ├── satisfaction
        └── license health
```

R0.4 MUST not own product definitions, client commercial terms, billing, or long-term client-success records. It references those systems by stable IDs.

## 5. Core Domain Objects

### 5.1 Production Node

A Production Node is a capacity-bearing entity capable of executing one or more governed production capabilities.

Examples:

- internal engineering team;
- internal QA cell;
- contractor;
- specialist integration partner;
- deployment team;
- automated build pipeline;
- governed AI-agent production capability in a future release.

Canonical fields:

```yaml
production_node_id: PN-DWS-000001
node_type: internal_team | contractor | qa_cell | automation | deployment_cell
operator_id: ORG-000001
name: string
status: active | conditional | suspended | retired

capability_profile_id: NCP-DWS-000001
calendar_id: CAL-DWS-000001
cost_profile_id: COST-DWS-000001
quality_profile_id: QP-DWS-000001

governance:
  genesis_principal_id: string
  warden_policy_id: string
  security_classification: string
  approved_product_classes: []

validity:
  effective_from: timestamp
  effective_to: timestamp | null
  supersedes: production_node_id | null
```

Node records are versioned. Historical execution MUST retain the node version applicable at assignment time.

### 5.2 Node Capability

A capability describes work a node is authorized and technically able to perform.

```yaml
node_capability_id: NC-DWS-000001
production_node_id: PN-DWS-000001
capability_code: SUPABASE_SCHEMA | NEON_POSTGRES | LOVABLE_UI | API_INTEGRATION | QA_SECURITY
skill_level: 1..5
max_parallel_units: integer
product_class_allowlist: []
required_policy_ids: []
effective_from: timestamp
effective_to: timestamp | null
```

Eligibility is based on explicit capability records, not free-text tags.

### 5.3 Capacity Calendar

The Capacity Calendar stores deterministic available production capacity by time bucket.

The canonical bucket for R0.4.0 is one day. Weekly and monthly views are derived.

```yaml
capacity_bucket_id: CAP-DWS-20260918-PN000001
production_node_id: PN-DWS-000001
date: 2026-09-18
nominal_units: decimal
maintenance_units: decimal
leave_units: decimal
reserved_units: decimal
committed_units: decimal
available_units: decimal
capacity_unit: engineering_hour | qa_hour | deployment_slot | build_slot
```

`available_units` is derived as:

```text
available = max(0,
  nominal
  - maintenance
  - leave
  - active_tentative_reservations
  - committed_reservations
)
```

Stored derived values MAY be cached but MUST be reproducible from source records.

### 5.4 License Manufacturing Order (LMO)

The LMO is the authoritative production order for one licensed configuration or governed change to a license.

```yaml
lmo_id: LMO-DWS-000001
license_id: LIC-DWS-000001
configuration_id: CFG-DWS-000001
product_version_ids: []
production_reason: initial | upgrade | expansion | remediation | connector_addition
route_policy: internal | contracted | hybrid | client_operated
priority: standard | urgent | critical
requested_start_at: timestamp
required_completion_at: timestamp
state: planned | capacity_checked | reserved | released | in_progress | qa_hold | completed | cancelled
warden_decision_id: string | null
river_receipt_id: string | null
```

One license MAY have multiple LMOs across its lifetime.

### 5.5 Work Package

An LMO is decomposed into individually schedulable Work Packages.

```yaml
work_package_id: WP-DWS-000001
lmo_id: LMO-DWS-000001
sequence_key: string
name: string
work_type: string
required_capability_code: string
minimum_skill_level: integer
estimated_effort_units: decimal
capacity_unit: string
allowed_node_types: []
allowed_production_nodes: []
blocked_production_nodes: []
security_classification: string
qa_specification_id: string
planned_start_at: timestamp | null
planned_finish_at: timestamp | null
state: planned | reserved | released | in_progress | blocked | submitted | qa | rework | accepted | cancelled
```

Dependencies are represented separately rather than embedded as mutable arrays.

### 5.6 Work-Package Dependency

```yaml
dependency_id: WPD-DWS-000001
predecessor_work_package_id: WP-DWS-000001
successor_work_package_id: WP-DWS-000002
dependency_type: finish_to_start
minimum_lag_units: decimal
lag_unit: hour | day
```

R0.4.0 supports finish-to-start dependencies only. Additional dependency semantics are deferred.

### 5.7 Capacity Reservation

Reservations prevent simulation and sales from double-booking the same production capacity.

```yaml
reservation_id: RES-DWS-000001
reservation_type: tentative | committed
source_type: simulation | quote | lmo
source_id: string
production_node_id: PN-DWS-000001
work_package_id: WP-DWS-000001 | null
starts_at: timestamp
ends_at: timestamp
reserved_units: decimal
capacity_unit: string
state: active | converted | released | expired | cancelled
expires_at: timestamp | null
```

Tentative reservations MUST have an expiry. Committed reservations MUST reference an accepted commercial or production authority.

### 5.8 Work Assignment

```yaml
assignment_id: ASG-DWS-000001
work_package_id: WP-DWS-000001
production_node_id: PN-DWS-000001
reservation_id: RES-DWS-000001
assigned_at: timestamp
assigned_by_principal_id: string
routing_decision_id: ROUTE-DWS-000001
state: assigned | active | completed | revoked
```

Reassignment creates a new assignment and revokes/supersedes the prior assignment. Historical assignments are never overwritten.

### 5.9 Production Event

Execution history is append-only.

```yaml
production_event_id: EVT-DWS-000001
aggregate_type: lmo | work_package | assignment | qa_inspection
aggregate_id: string
event_type: string
occurred_at: timestamp
recorded_at: timestamp
actor_principal_id: string
payload: json
warden_decision_id: string | null
river_receipt_id: string | null
idempotency_key: string
supersedes_event_id: string | null
```

Supported R0.4.0 event types include:

- `LMO_CREATED`
- `CAPACITY_CHECKED`
- `CAPACITY_RESERVED`
- `CAPACITY_RESERVATION_EXPIRED`
- `WORK_PACKAGE_RELEASED`
- `WORK_ASSIGNED`
- `WORK_STARTED`
- `WORK_BLOCKED`
- `WORK_RESUMED`
- `BUILD_SUBMITTED`
- `QA_STARTED`
- `QA_FAILED`
- `NONCONFORMANCE_OPENED`
- `REWORK_REQUESTED`
- `REWORK_SUBMITTED`
- `QA_PASSED`
- `DEPLOYMENT_APPROVED`
- `WORK_COMPLETED`
- `LMO_COMPLETED`
- `ASSIGNMENT_REVOKED`

Unknown event types MUST be rejected unless registered in a versioned event-type registry.

### 5.10 QA Inspection

```yaml
qa_inspection_id: QAI-DWS-000001
work_package_id: WP-DWS-000001
lmo_id: LMO-DWS-000001
qa_specification_id: QA-DWS-000001
inspector_node_id: PN-DWS-QA-000001
inspection_round: integer
started_at: timestamp
completed_at: timestamp | null
result: pending | pass | pass_with_exception | fail
score: decimal | null
critical_failures: integer
major_failures: integer
minor_failures: integer
evidence_receipt_id: string | null
```

### 5.11 Nonconformance

```yaml
nonconformance_id: NCR-DWS-000001
qa_inspection_id: QAI-DWS-000001
work_package_id: WP-DWS-000001
severity: critical | major | minor
category: string
description: string
state: open | rework | accepted_exception | closed
owner_node_id: PN-DWS-000001
opened_at: timestamp
closed_at: timestamp | null
closure_evidence_receipt_id: string | null
```

### 5.12 Node Performance Snapshot

Performance is derived from historical production data and stored as versioned snapshots for explainable routing.

```yaml
node_performance_snapshot_id: NPS-DWS-000001
production_node_id: PN-DWS-000001
period_start: timestamp
period_end: timestamp
sample_size: integer
on_time_rate: decimal
first_pass_yield: decimal
defect_escape_rate: decimal
average_cycle_time: decimal
cost_adherence: decimal
client_defect_rate: decimal
quality_score: decimal
delivery_score: decimal
composite_vendor_score: decimal
calculated_at: timestamp
algorithm_version: R0.4.0
```

## 6. Work-Package Decomposition

R0.4 does not generate arbitrary project plans. It expands an approved Product BOM / Configuration using versioned manufacturing recipes.

Example recipe:

```text
DWS-ECOM-ORDER-001@1.2

1. Provision registry runtime
2. Install schema
3. Configure UI
4. Configure integrations
5. Migrate initial data
6. Run integration tests
7. Run security tests
8. Execute UAT
9. Deploy
```

A manufacturing recipe MUST specify:

- work-package templates;
- effort model;
- dependency order;
- eligible capability codes;
- QA gates;
- security classifications;
- allowed routing policies.

Decomposition inputs are immutable IDs for the selected product versions and approved configuration. A changed configuration creates a new decomposition/version; it does not silently mutate released work packages.

## 7. Eligibility Engine

Before scoring candidates, R0.4 performs hard eligibility filtering.

A node is eligible only when all mandatory predicates pass:

```text
node.status == active
AND capability exists
AND capability.skill_level >= required skill level
AND node type allowed
AND product class allowed
AND security classification allowed
AND Warden policy allows assignment
AND node is not explicitly blocked
AND requested capacity unit is supported
```

An ineligible node MUST never receive a routing score.

Eligibility results are persisted as part of the routing decision evidence.

## 8. Routing Engine

### 8.1 R0.4.0 routing score

For eligible nodes:

```text
Route Score =
  0.25 × Capability Fit
+ 0.20 × Capacity Fit
+ 0.15 × Quality Score
+ 0.15 × Delivery Reliability
+ 0.10 × Cost Score
+ 0.10 × Governance/Security Fit
+ 0.05 × Client-Experience History
```

All component scores are normalized to 0–100.

Weights are versioned configuration, not hard-coded constants.

### 8.2 Deterministic tie-breaking

If two candidates have the same score to two decimal places, apply in order:

1. higher governance/security fit;
2. higher first-pass yield;
3. earlier feasible completion;
4. lower forecast cost;
5. lexical order of `production_node_id`.

This guarantees deterministic replay.

### 8.3 Routing decision record

Every decision stores:

```yaml
routing_decision_id: ROUTE-DWS-000001
work_package_id: WP-DWS-000001
algorithm_version: R0.4.0
weight_profile_id: RWP-DWS-000001
eligible_candidates: []
ineligible_candidates_with_reasons: []
selected_node_id: PN-DWS-000001
component_scores: {}
final_score: decimal
decided_at: timestamp
warden_decision_id: string | null
river_receipt_id: string | null
```

No assignment is valid without a routing-decision record or a governed manual override.

## 9. Capacity Reservation Protocol

### 9.1 Tentative reservation

R0.3 may request capacity for a simulation or quote.

The kernel:

1. decomposes forecast work;
2. evaluates eligible nodes;
3. finds feasible windows;
4. creates tentative reservations;
5. assigns `expires_at`;
6. returns earliest feasible completion and confidence metrics.

Tentative reservations reduce available capacity while active.

### 9.2 Conversion to committed reservation

On approved commercial acceptance / license authority:

```text
Tentative Reservation
        ↓ validate still active
Commercial acceptance / Warden authority
        ↓
Committed Reservation
        ↓
LMO release
```

Conversion MUST be atomic at the reservation layer. If any required reservation cannot be converted, the LMO remains unreleased and a capacity conflict is raised.

### 9.3 Expiry

Expired tentative reservations are released automatically and generate `CAPACITY_RESERVATION_EXPIRED` events.

## 10. Scheduling and Bottleneck Intelligence

R0.4.0 uses deterministic forward scheduling over the dependency DAG.

For each work package:

```text
earliest_start = max(
  requested_start,
  all predecessor completion times,
  first capacity-feasible time on assigned node
)

planned_finish = earliest_start + effort adjusted for assigned capacity calendar
```

The kernel derives:

- critical path;
- total planned lead time;
- queue time;
- processing time;
- QA time;
- rework time;
- blocked time;
- node utilization;
- work in progress;
- schedule slack;
- earliest feasible completion;
- bottleneck node/capability.

A bottleneck is reported when a capability/node group has the highest constrained utilization on the critical or near-critical path and materially affects completion.

R0.4.0 MUST explain the bottleneck with supporting work packages and reservation intervals.

## 11. State Machines

### 11.1 LMO state

```text
PLANNED
  ↓
CAPACITY_CHECKED
  ↓
RESERVED
  ↓
RELEASED
  ↓
IN_PROGRESS
  ↓
QA_HOLD (optional / repeatable)
  ↓
COMPLETED
```

Terminal alternate state: `CANCELLED`.

Cancellation does not delete history; it releases remaining reservations and records an event.

### 11.2 Work package state

```text
PLANNED
  ↓
RESERVED
  ↓
RELEASED
  ↓
IN_PROGRESS
  ├── BLOCKED ──► IN_PROGRESS
  ↓
SUBMITTED
  ↓
QA
  ├── REWORK ──► IN_PROGRESS
  ↓
ACCEPTED
```

Terminal alternate state: `CANCELLED`.

Illegal transitions return a conflict error and do not modify state.

## 12. Quality Model

Quality decisions attach to product specification, production execution, and deployed-license outcome separately.

R0.4 owns production quality, not master-product quality or long-term client experience.

Primary R0.4 metrics:

```text
First Pass Yield = accepted on first inspection / first inspections

On-Time Completion = completed by committed finish / completed work

Cost Adherence = min(planned cost / actual cost, 1) where actual > planned,
                 otherwise 1

Defect Escape Rate = defects discovered after QA acceptance / accepted units

Rework Rate = work packages requiring rework / submitted work packages
```

Contractors and internal teams are scored using the same production evidence. Different commercial consequences may apply, but quality mathematics is shared.

## 13. Performance Feedback

After an LMO reaches completion and sufficient post-deployment evidence exists, node-performance snapshots are recomputed.

Historical routing decisions are never recalculated retroactively. They retain the performance snapshot and algorithm version used at decision time.

Future routing uses the latest effective performance snapshot.

This allows measured quality and delivery performance to influence future assignments without creating an opaque self-learning scheduler.

## 14. Governance Integration

### 14.1 Genesis

Genesis provides stable identity for:

- production nodes;
- operators;
- actors/principals;
- client/licensed-estate references;
- approved product/version identities where applicable.

R0.4 stores Genesis IDs but does not become the canonical identity registry.

### 14.2 Warden

Warden is the authority gate for operations including:

- admitting or suspending production nodes;
- permitting a node to work on security-restricted product classes;
- manual routing overrides;
- conversion of high-risk capacity reservations;
- acceptance with exception;
- deployment approval where required.

R0.4 records Warden decision IDs; it does not reproduce Warden policy logic internally.

### 14.3 River

River stores evidence receipts for materially governed events, including:

- routing decisions;
- capacity commitments;
- work submission;
- QA outcomes;
- accepted exceptions;
- deployment approvals;
- final LMO completion.

The local event ledger stores references and execution projections. River remains the evidence authority.

## 15. External Interfaces

### 15.1 R0.3 → R0.4

Required operations:

- `simulate_capacity(configuration_id, requested_window)`
- `hold_capacity(simulation_id, ttl)`
- `release_capacity_hold(reservation_group_id)`
- `quote_delivery_projection(configuration_id)`

Returned data includes:

- feasibility;
- candidate route;
- tentative reservations;
- earliest start;
- predicted completion;
- bottlenecks;
- forecast production cost;
- confidence inputs.

### 15.2 R0.2 → R0.4

Required operations:

- `create_lmo(license_id, configuration_id, production_reason)`
- `commit_capacity(lmo_id, authority_context)`
- `release_lmo(lmo_id)`
- `cancel_lmo(lmo_id, reason)`
- `get_lmo_status(lmo_id)`

### 15.3 Production consoles → R0.4

- `start_work(assignment_id)`
- `block_work(assignment_id, reason)`
- `resume_work(assignment_id)`
- `submit_work(assignment_id, artifact_refs, evidence_refs)`

### 15.4 QA → R0.4

- `start_inspection(work_package_id, qa_specification_id)`
- `record_inspection_result(qa_inspection_id, result)`
- `open_nonconformance(...)`
- `request_rework(...)`
- `close_nonconformance(...)`

All mutating calls require idempotency keys.

## 16. Persistence Architecture

R0.4.0 should use a transactional PostgreSQL system of record. Supabase or Neon may host it, but provider choice is deployment configuration rather than domain architecture.

Recommended logical schemas:

```text
production_core
  production_nodes
  node_capabilities
  manufacturing_recipes
  manufacturing_recipe_steps
  lmos
  work_packages
  work_package_dependencies
  assignments

capacity
  calendars
  capacity_buckets
  reservations
  reservation_groups

quality
  inspections
  nonconformances
  performance_snapshots

routing
  weight_profiles
  routing_decisions
  routing_candidates

ledger
  production_events
  event_type_registry
  idempotency_keys
```

Airtable is an operational/control surface, not the canonical transaction database for capacity reservation or event integrity.

Lovable may provide the operator UI, but no core production rule may exist only in client-side UI code.

## 17. Concurrency and Integrity

Capacity reservation is the highest-risk concurrency boundary.

R0.4 MUST prevent overbooking under concurrent quote or LMO requests.

Required behaviors:

- capacity checks and reservation writes execute transactionally;
- overlapping writes to the same node/time bucket are serialized or use optimistic concurrency with retry;
- committed capacity can never exceed allocatable capacity unless a governed override is explicitly represented;
- tentative holds cannot overwrite committed reservations;
- idempotent retries return the prior result rather than duplicate reservations/events;
- assignment cannot reference expired or released committed capacity.

## 18. Error Model

Errors are structured and machine-readable.

Minimum codes:

```text
DWS_CAPACITY_UNAVAILABLE
DWS_CAPACITY_CONFLICT
DWS_RESERVATION_EXPIRED
DWS_INELIGIBLE_NODE
DWS_NO_ELIGIBLE_ROUTE
DWS_ILLEGAL_STATE_TRANSITION
DWS_DEPENDENCY_INCOMPLETE
DWS_QA_REQUIRED
DWS_QA_FAILED
DWS_NONCONFORMANCE_OPEN
DWS_GOVERNANCE_DENIED
DWS_IDEMPOTENCY_CONFLICT
DWS_CONFIGURATION_VERSION_MISMATCH
```

Each error contains:

- `code`;
- `message`;
- `aggregate_id` when relevant;
- `retryable` boolean;
- `evidence_context` where applicable.

## 19. Security

R0.4 MUST enforce tenant/estate isolation for all license-linked production data.

Minimum requirements:

- no client-side service-role or privileged database secrets;
- least-privilege service identities;
- explicit authorization on every mutating operation;
- row-level or equivalent tenant isolation for exposed data paths;
- auditability of manual overrides;
- append-only production-event semantics;
- signed/traceable evidence references where available;
- secrets referenced by secret IDs, never copied into work-package payloads;
- contractors receive only the minimum scoped data required for assigned work.

## 20. Observability

Minimum service metrics:

- capacity utilization by node/capability;
- tentative reservation volume and expiry rate;
- committed reservation conflict rate;
- routing success/failure rate;
- average routing latency;
- work-in-progress by state;
- critical-path variance;
- on-time completion rate;
- first-pass yield;
- rework rate;
- nonconformance rate;
- event-ledger write failures;
- idempotency conflicts.

Every request should carry a correlation ID linking simulation, quote, license, LMO, work package, assignment, QA, and deployment where those IDs exist.

## 21. Operator Surfaces

R0.4 requires three primary operator views.

### 21.1 Factory Control

Shows:

- active LMOs;
- WIP;
- blocked work;
- critical-path risk;
- utilization;
- upcoming capacity conflicts;
- QA holds.

### 21.2 Production Node / Contractor Scorecard

Shows:

- assigned workload;
- available capacity;
- delivery reliability;
- first-pass yield;
- defect and rework history;
- quality classification;
- current authorization status.

### 21.3 LMO Trace

Shows the complete evidence chain:

```text
License
→ Configuration
→ LMO
→ Work Packages
→ Routing Decisions
→ Reservations
→ Assignments
→ Production Events
→ QA
→ Nonconformances / Rework
→ Completion
→ Deployment reference
```

The UI is a projection over canonical records. It must never become the source of truth.

## 22. Testing Strategy

### 22.1 Unit tests

Cover:

- eligibility predicates;
- score normalization;
- routing weights;
- deterministic tie-breaking;
- capacity arithmetic;
- state transitions;
- critical-path calculation;
- metric calculations.

### 22.2 Property/invariant tests

Required invariants:

- committed capacity never exceeds allocatable capacity without an explicit override record;
- work cannot be accepted without required QA pass/exception authority;
- completed work cannot reference an active nonconformance of blocking severity;
- assignments always reference an eligible node decision or governed override;
- the same idempotency key cannot create two material effects;
- historical events are never deleted through normal application flows.

### 22.3 Integration tests

Cover:

- concurrent tentative holds against the same capacity bucket;
- tentative-to-committed conversion;
- hold expiry and release;
- LMO release with multiple dependent work packages;
- QA fail → NCR → rework → QA pass;
- assignment revocation/reassignment;
- Warden denial;
- River receipt recording failure and retry policy.

### 22.4 End-to-end qualification scenario

R0.4.0 is not production-qualified until a reference license can execute this trace:

```text
R0.3 configuration
→ capacity simulation
→ tentative hold
→ accepted quote/license authority
→ committed reservation
→ LMO
→ work package decomposition
→ routed assignment
→ execution events
→ one intentional QA failure
→ nonconformance
→ rework
→ QA pass
→ LMO completion
→ deployment handoff
→ node-performance snapshot update
```

The test must prove replayability of routing inputs and capacity history.

## 23. Rollout

### Phase A — Read-only planning

- register production nodes;
- import/manual-enter capability and capacity profiles;
- run shadow routing;
- compare proposed routing with human decisions;
- no automatic capacity commitment.

### Phase B — Governed reservations

- enable tentative holds from R0.3;
- enable manual/authorized conversion to committed capacity;
- operate LMO state machine;
- maintain evidence ledger.

### Phase C — Production control

- production nodes execute through assignments;
- QA/NCR loop becomes authoritative;
- node performance affects future routing scores.

### Phase D — Optimization readiness

Only after sufficient evidence exists should later releases consider optimization, predictive scheduling, or autonomous agent participation.

## 24. Acceptance Criteria for R0.4.0

R0.4.0 is accepted when all of the following are demonstrated:

1. At least one internal and one contracted Production Node can be registered with capabilities and capacity.
2. One approved configuration can deterministically generate an LMO and work-package DAG.
3. Ineligible nodes are excluded with recorded reasons.
4. Eligible nodes are scored reproducibly using a versioned weight profile.
5. Tentative capacity can be held, expired/released, and converted to committed capacity without overbooking.
6. A work package can be assigned, started, blocked, resumed, submitted, inspected, failed, reworked, and accepted.
7. The production-event ledger reconstructs the effective current state.
8. A QA failure creates a nonconformance and prevents completion until resolved or explicitly accepted by authority.
9. A completed LMO updates a versioned node-performance snapshot.
10. The complete trace from simulation/configuration to deployment handoff is inspectable by stable IDs and evidence references.
11. Concurrent reservation tests prove no capacity overbooking under supported transaction isolation.
12. All material mutating operations are idempotent and auditable.

## 25. Future Extension Points

The design intentionally leaves stable extension seams for:

- predictive duration models;
- Monte Carlo completion confidence;
- multi-objective routing optimization;
- autonomous agent production nodes;
- contractor bidding/procurement;
- SILK-linked settlement;
- cross-estate production markets;
- carbon/resource intensity as routing dimensions;
- dynamic product-manufacturing recipes;
- manufacturing digital twins.

These extensions must remain additive. R0.4.0 event history, IDs, authority records, and evidence references remain valid when later versions are introduced.

## 26. Implementation Boundary

The first implementation plan should create the smallest production slice that proves the kernel:

```text
Production Nodes
+ Capabilities
+ Daily Capacity Buckets
+ Reservations
+ LMO
+ Work Packages / Dependencies
+ Deterministic Routing
+ Assignments
+ Append-only Events
+ QA / NCR
+ Performance Snapshot
```

No additional marketplace, billing, autonomous AI, or advanced optimization feature should enter the first implementation plan unless this specification is explicitly superseded by a separately approved design change.
