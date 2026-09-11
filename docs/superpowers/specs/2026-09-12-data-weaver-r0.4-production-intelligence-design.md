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

A license is commercially committed only after the system can show a feasible route from configuration to production capacity, quality assurance, and deployment.

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

R0.4.0 MUST provide production-node and capability registration, deterministic capacity calendars, tentative and committed reservations, license manufacturing orders, work-package decomposition, eligibility filtering, deterministic routing/scoring, work assignment, immutable production-event recording, QA inspection, nonconformance/rework, node-performance aggregation, bottleneck/critical-path calculations, R0.2/R0.3 interfaces, and governance hooks for Genesis, Warden, and River.

### 3.2 Explicitly out of scope

Deferred from R0.4.0:

- autonomous AI production scheduling or reassignment;
- contractor procurement marketplace or bidding;
- financial settlement, invoicing, payroll, or HR planning;
- generative project decomposition without an approved product BOM;
- predictive ML scheduling;
- automatic product changes in response to QA outcomes;
- self-modifying routing weights.

R0.4.0 remains deterministic so routing, capacity, and quality decisions are explainable and replayable.

## 4. System Boundary

```text
R0.1 Product Registry
        │ product/version/component BOM/QA specification
        ▼
R0.3 Simulation + Configuration Engine
        │ requirements/configuration/runtime/forecast work
        ▼
┌──────────────────────────────────────┐
│ R0.4 Production Intelligence Kernel │
│ Capacity • Routing • Reservations   │
│ Execution Ledger • QA • Performance │
└──────────────────────────────────────┘
        ▼
R0.2 License + Deployment Lifecycle
        │ deployment/acceptance/support/license health
```

R0.4 MUST not own product definitions, client commercial terms, billing, or long-term client-success records. It references those systems through stable IDs.

## 5. Core Domain Objects

### 5.1 Production Node and Version

`production_node_id` is the stable identity of a capacity-bearing producer. Effective attributes are stored in immutable node versions so historical assignments can resolve the exact capability/governance state used at decision time.

```yaml
production_node_id: PN-DWS-000001
production_node_version_id: PNV-DWS-000001-V003
node_type: internal_team | contractor | qa_cell | automation | deployment_cell
operator_id: ORG-000001
name: string
status: active | conditional | suspended | retired

capability_profile_id: NCP-DWS-000001-V004
calendar_id: CAL-DWS-000001
cost_profile_id: COST-DWS-000001-V002
quality_profile_id: QP-DWS-000001-V007

governance:
  genesis_principal_id: string
  warden_policy_id: string
  security_classification: string
  approved_product_classes: []

validity:
  effective_from: timestamp
  effective_to: timestamp | null
  supersedes_version_id: PNV-DWS-000001-V002 | null
```

`active` nodes may enter automatic routing. `conditional` nodes are excluded from automatic routing and require an explicit governed manual override. `suspended` and `retired` nodes cannot receive new assignments.

### 5.2 Node Capability

```yaml
node_capability_id: NC-DWS-000001
production_node_version_id: PNV-DWS-000001-V003
capability_code: SUPABASE_SCHEMA | NEON_POSTGRES | LOVABLE_UI | API_INTEGRATION | QA_SECURITY
skill_level: 1..5
max_parallel_units: integer
capacity_unit: engineering_hour | qa_hour | deployment_slot | build_slot
product_class_allowlist: []
required_policy_ids: []
effective_from: timestamp
effective_to: timestamp | null
```

Eligibility is based on explicit capability records, never free-text tags.

### 5.3 Capacity Calendar

The canonical scheduling bucket in R0.4.0 is one day; weekly/monthly views are derived.

```yaml
capacity_bucket_id: CAP-DWS-20260918-PN000001
production_node_id: PN-DWS-000001
date: 2026-09-18
nominal_units: decimal
maintenance_units: decimal
leave_units: decimal
capacity_unit: engineering_hour | qa_hour | deployment_slot | build_slot
```

Reservation totals and available units are projections derived from reservation rows, not independent authoritative quantities:

```text
tentative_reserved = sum(active tentative reservations)
committed_reserved = sum(active committed reservations)
available = max(0,
  nominal
  - maintenance
  - leave
  - tentative_reserved
  - committed_reserved
)
```

Cached projections MAY be stored for performance but MUST be reproducible from source records.

### 5.4 License Manufacturing Order (LMO)

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

One license MAY create multiple LMOs over its lifetime.

### 5.5 Work Package

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

Dependencies are separate records.

### 5.6 Work-Package Dependency

```yaml
dependency_id: WPD-DWS-000001
predecessor_work_package_id: WP-DWS-000001
successor_work_package_id: WP-DWS-000002
dependency_type: finish_to_start
minimum_lag_units: decimal
lag_unit: hour | day
```

Only finish-to-start is supported in R0.4.0.

### 5.7 Capacity Reservation

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
authority_ref: string | null
```

Tentative reservations MUST expire. Committed reservations MUST reference accepted commercial/production authority.

### 5.8 Work Assignment

```yaml
assignment_id: ASG-DWS-000001
work_package_id: WP-DWS-000001
production_node_id: PN-DWS-000001
production_node_version_id: PNV-DWS-000001-V003
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

R0.4.0 registers at least:

`LMO_CREATED`, `CAPACITY_CHECKED`, `CAPACITY_RESERVED`, `CAPACITY_RESERVATION_EXPIRED`, `WORK_PACKAGE_RELEASED`, `WORK_ASSIGNED`, `WORK_STARTED`, `WORK_BLOCKED`, `WORK_RESUMED`, `BUILD_SUBMITTED`, `QA_STARTED`, `QA_FAILED`, `NONCONFORMANCE_OPENED`, `REWORK_REQUESTED`, `REWORK_SUBMITTED`, `QA_PASSED`, `DEPLOYMENT_APPROVED`, `WORK_COMPLETED`, `LMO_COMPLETED`, and `ASSIGNMENT_REVOKED`.

Unknown event types are rejected unless present in a versioned event-type registry.

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

Historical routing stores the snapshot/version used at decision time.

## 6. Work-Package Decomposition

R0.4 expands an approved Product BOM/Configuration using versioned manufacturing recipes; it does not generate arbitrary project plans.

Example:

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

A recipe MUST specify work-package templates, effort model, dependency order, eligible capability codes, QA gates, security classifications, and routing policy.

Changed configuration creates a new decomposition/version and never silently mutates released work packages.

## 7. Eligibility Engine

Automatic routing requires all predicates to pass:

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

Conditional nodes are considered only through a recorded manual override authorized by Warden. Ineligible nodes never receive automatic routing scores.

## 8. Routing Engine

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

All components are normalized 0–100. Routing weights are versioned configuration.

`Client-Experience History` is an imported read-only score from the R0.2 client/license outcome layer. If no statistically usable history exists, the routing weight is redistributed proportionally across the other six components for that decision; missing history is never interpreted as zero quality.

Tie-breaking, after equality to two decimals:

1. higher governance/security fit;
2. higher first-pass yield;
3. earlier feasible completion;
4. lower forecast cost;
5. lexical `production_node_id`.

Every routing decision stores algorithm version, weight profile, eligible/ineligible candidates and reasons, component scores, selected node, effective node/performance versions, authority/evidence references, and decision timestamp.

No assignment is valid without a routing-decision record or governed manual override.

## 9. Capacity Reservation Protocol

### 9.1 Tentative holds

R0.3 may request a capacity hold for a simulation/quote. R0.4 decomposes forecast work, evaluates eligible nodes, finds feasible windows, creates expiring tentative reservations, and returns feasibility plus schedule data.

R0.4's `schedule_confidence` in R0.4.0 is **not a probabilistic delivery forecast**. It is a deterministic data-completeness score indicating how much of the proposed schedule is backed by explicit node capacity, effort estimates, dependencies, and current performance history.

```text
Schedule Confidence =
25% capacity coverage
+ 25% effort-model coverage
+ 20% dependency completeness
+ 15% node-performance-history coverage
+ 15% QA-duration-model coverage
```

Each component is 0–100. R0.3 may combine this with its own commercial/simulation confidence, but R0.4 MUST return the component breakdown.

### 9.2 Conversion to committed capacity

```text
Tentative Reservation
        ↓ validate still active
Commercial acceptance / Warden authority
        ↓
Committed Reservation
        ↓
LMO release
```

Conversion is atomic at the reservation-group level. If any required reservation cannot convert, none in the group convert and the LMO remains unreleased.

### 9.3 Expiry

Expired tentative reservations release capacity and append `CAPACITY_RESERVATION_EXPIRED`.

## 10. Scheduling and Bottleneck Intelligence

R0.4.0 uses deterministic forward scheduling over the dependency DAG.

```text
earliest_start = max(
  requested_start,
  all predecessor completion times,
  first capacity-feasible time on assigned node
)

planned_finish = earliest_start + effort adjusted by assigned capacity calendar
```

Derived outputs:

- critical path;
- planned lead time;
- queue, processing, QA, rework, and blocked time;
- node utilization and WIP;
- schedule slack;
- earliest feasible completion;
- bottleneck node/capability.

A bottleneck report identifies the constrained capability/node group, affected work packages, capacity intervals, and effect on completion.

## 11. State Machines

### 11.1 LMO

```text
PLANNED → CAPACITY_CHECKED → RESERVED → RELEASED → IN_PROGRESS
                                               ↓
                                           QA_HOLD
                                               ↓
                                           COMPLETED
```

`CANCELLED` is terminal. Cancellation records an event and releases remaining reservations.

### 11.2 Work Package

```text
PLANNED → RESERVED → RELEASED → IN_PROGRESS
                                 ↕ BLOCKED
                                  ↓
                              SUBMITTED
                                  ↓
                                  QA
                         REWORK ↗  ↓
                               ACCEPTED
```

`CANCELLED` is terminal. Illegal transitions return a conflict and do not alter state.

## 12. Quality Model

R0.4 owns production quality, not master-product quality or long-term client satisfaction.

```text
First Pass Yield = first-inspection acceptances / first inspections
On-Time Completion = work completed by committed finish / completed work
Defect Escape Rate = post-QA defects / accepted work packages
Rework Rate = packages requiring rework / submitted packages
```

Internal and contracted production use the same evidence and quality mathematics.

## 13. Performance Feedback

After LMO completion and required post-deployment evidence becomes available, a new node-performance snapshot is calculated.

Historical routing decisions are never recalculated. Future decisions use the latest effective snapshot. This creates evidence-driven routing without an opaque self-learning scheduler.

## 14. Governance Integration

### Genesis

Provides stable identity for production nodes, operators, actors/principals, client/licensed-estate references, and product/version identities. R0.4 stores Genesis references but does not become the identity authority.

### Warden

Authorizes admission/suspension of nodes, restricted product assignments, manual routing overrides, high-risk reservation conversion, accepted QA exceptions, and deployment approval where required. R0.4 records Warden decision IDs and does not duplicate policy logic.

### River

Stores evidence receipts for material routing decisions, capacity commitments, submissions, QA outcomes, exceptions, deployment approvals, and final LMO completion. R0.4 maintains operational projections and evidence references; River remains the evidence authority.

## 15. External Interfaces

### R0.3 → R0.4

- `simulate_capacity(configuration_id, requested_window)`
- `hold_capacity(simulation_id, ttl)`
- `release_capacity_hold(reservation_group_id)`
- `quote_delivery_projection(configuration_id)`

Returns feasibility, candidate route, reservations, earliest start, predicted deterministic finish, bottlenecks, forecast production cost, schedule-confidence breakdown.

### R0.2 → R0.4

- `create_lmo(license_id, configuration_id, production_reason)`
- `commit_capacity(lmo_id, authority_context)`
- `release_lmo(lmo_id)`
- `cancel_lmo(lmo_id, reason)`
- `get_lmo_status(lmo_id)`

### Production consoles → R0.4

- `start_work(assignment_id)`
- `block_work(assignment_id, reason)`
- `resume_work(assignment_id)`
- `submit_work(assignment_id, artifact_refs, evidence_refs)`

### QA → R0.4

- `start_inspection(work_package_id, qa_specification_id)`
- `record_inspection_result(qa_inspection_id, result)`
- `open_nonconformance(...)`
- `request_rework(...)`
- `close_nonconformance(...)`

All mutating operations require idempotency keys.

## 16. Persistence Architecture

R0.4.0 uses transactional PostgreSQL as system of record. Supabase or Neon may host it; provider choice is deployment configuration rather than domain architecture.

```text
production_core
  production_nodes
  production_node_versions
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

Airtable may serve as an operational/control surface, but it is not the canonical transaction database for capacity reservations or event integrity. Lovable may provide UI, but no core production rule may exist only in client-side code.

## 17. Concurrency and Integrity

Capacity reservation is the primary concurrency boundary.

Required behavior:

- capacity check + reservation writes are transactional;
- concurrent writes to the same node/time bucket are serialized or use optimistic concurrency with bounded retry;
- committed capacity never exceeds allocatable capacity without an explicit governed override;
- tentative holds cannot displace committed reservations;
- idempotent retries return the prior material result;
- assignment cannot reference expired/released committed capacity;
- conversion of a reservation group is all-or-nothing.

## 18. Error Model

Minimum codes:

`DWS_CAPACITY_UNAVAILABLE`, `DWS_CAPACITY_CONFLICT`, `DWS_RESERVATION_EXPIRED`, `DWS_INELIGIBLE_NODE`, `DWS_NO_ELIGIBLE_ROUTE`, `DWS_ILLEGAL_STATE_TRANSITION`, `DWS_DEPENDENCY_INCOMPLETE`, `DWS_QA_REQUIRED`, `DWS_QA_FAILED`, `DWS_NONCONFORMANCE_OPEN`, `DWS_GOVERNANCE_DENIED`, `DWS_IDEMPOTENCY_CONFLICT`, `DWS_CONFIGURATION_VERSION_MISMATCH`.

Each error contains `code`, `message`, relevant aggregate ID, `retryable`, and evidence context where applicable.

## 19. Security

R0.4 MUST enforce tenant/estate isolation for all license-linked production data, least-privilege service identities, explicit authorization on mutation, row-level/equivalent isolation for exposed paths, auditable manual overrides, append-only event semantics, traceable evidence references, secret references instead of secret values in work payloads, and minimum-necessary contractor data access.

## 20. Observability

Minimum metrics:

- capacity utilization by node/capability;
- hold volume/expiry and commitment conflicts;
- routing success/failure and latency;
- WIP by state;
- critical-path variance;
- on-time completion;
- first-pass yield, rework and NCR rates;
- event-ledger write failures;
- idempotency conflicts.

Correlation IDs link simulation, quote, license, LMO, work package, assignment, QA, and deployment where available.

## 21. Operator Surfaces

### Factory Control

Active LMOs, WIP, blocked work, critical-path risk, utilization, capacity conflicts, QA holds.

### Production Node / Contractor Scorecard

Assigned workload, availability, delivery reliability, first-pass yield, defect/rework history, classification, authorization status.

### LMO Trace

```text
License → Configuration → LMO → Work Packages → Routing Decisions
→ Reservations → Assignments → Production Events → QA/NCR/Rework
→ Completion → Deployment Reference
```

All UIs are projections over canonical records.

## 22. Testing Strategy

### Unit tests

Eligibility predicates, normalization, routing weights, tie-breaking, capacity arithmetic, state transitions, critical-path calculation, metric calculation, schedule-confidence calculation.

### Property/invariant tests

- committed capacity cannot exceed allocatable capacity without an explicit override;
- work cannot be accepted without required QA pass/authorized exception;
- completed work cannot retain blocking open NCRs;
- assignments reference an eligible route or governed override;
- one idempotency key cannot create two material effects;
- event history is not deleted by normal flows;
- reservation-group conversion is atomic.

### Integration tests

Concurrent holds, hold conversion, expiry/release, dependency release, QA fail→NCR→rework→pass, reassignment, Warden denial, River receipt retry behavior.

### End-to-end qualification

```text
R0.3 configuration
→ capacity simulation
→ tentative hold
→ accepted license authority
→ committed reservation
→ LMO
→ decomposition
→ routed assignment
→ execution events
→ intentional QA failure
→ NCR
→ rework
→ QA pass
→ LMO completion
→ deployment handoff
→ node-performance snapshot update
```

Qualification MUST prove replayability of routing inputs and capacity history.

## 23. Rollout

**Phase A — Read-only planning:** register nodes/capabilities/capacity and run shadow routing without capacity commitment.

**Phase B — Governed reservations:** enable R0.3 tentative holds and authorized conversion; operate LMO/event lifecycle.

**Phase C — Production control:** execute assignments, make QA/NCR authoritative, and feed performance into future routing.

**Phase D — Optimization readiness:** only after sufficient evidence consider predictive scheduling, advanced optimization, or autonomous agent participation.

## 24. Acceptance Criteria

R0.4.0 is accepted when:

1. At least one internal and one contracted Production Node are registered with capabilities/capacity.
2. One approved configuration deterministically generates an LMO and work-package DAG.
3. Ineligible nodes are excluded with persisted reasons; conditional nodes require governed override.
4. Eligible nodes are scored reproducibly with versioned weights and missing-history rules.
5. Tentative capacity can be held, expired/released, and atomically converted without overbooking.
6. A work package can traverse start, block/resume, submit, QA fail, NCR, rework, and accept.
7. The event ledger reconstructs effective state.
8. Blocking QA/NCR conditions prevent completion until resolved or explicitly accepted by authority.
9. Completed LMOs update versioned node-performance snapshots.
10. The full simulation→deployment trace is inspectable through stable IDs/evidence references.
11. Concurrency tests prove no overbooking under supported transaction isolation.
12. All material mutations are idempotent and auditable.
13. Schedule-confidence output is reproducible from its five declared coverage components.

## 25. Future Extension Points

Stable extension seams are reserved for predictive duration models, Monte Carlo completion confidence, multi-objective routing, autonomous agent production nodes, contractor bidding/procurement, SILK settlement, cross-estate production markets, carbon/resource routing dimensions, dynamic recipes, and manufacturing digital twins.

Extensions remain additive: R0.4.0 IDs, event history, authority records, and evidence references stay valid under future versions.

## 26. Implementation Boundary

The first implementation plan proves the smallest kernel:

```text
Production Nodes + Node Versions + Capabilities
+ Daily Capacity Buckets + Reservations
+ LMO + Work Packages/Dependencies
+ Deterministic Routing + Assignments
+ Append-only Events + QA/NCR
+ Performance Snapshot
```

No marketplace, billing, autonomous AI, or advanced optimization enters the first implementation plan unless this specification is explicitly superseded by a separately approved design change.
