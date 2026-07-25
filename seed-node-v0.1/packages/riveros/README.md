# RiverOS Repository

RiverOS is the canonical operational event and evidence layer for the Synnergyze Seed Node.

Its purpose is to convert physical and digital activity into an accountable, append-only sequence of events that can be verified, projected into current state, retrieved by authorised agents, and linked to downstream commercial consequences.

> RiverOS proves what happened. Silk Dam determines what value may move because it happened.

## Position in the VSR stack

```text
Reality or system activity
        ↓
Observation and identity resolution
        ↓
RiverOS event validation
        ↓
Accepted append-only event
        ↓
State projection and evidence linkage
        ↓
Commercial consequence, if applicable
        ↓
Silk Dam obligation, reserve and release
        ↓
Settlement confirmation returned to RiverOS
```

RiverOS is not a payment processor, wallet, mutable business table, document store, or general-purpose analytics warehouse.

It is the network's:

- canonical event ledger;
- evidence router;
- state-transition record;
- operational timeline;
- audit backbone;
- settlement eligibility source.

## Repository contract

The RiverOS package owns the contracts for:

1. event envelopes;
2. evidence-object references;
3. event streams;
4. event relationships;
5. state projections;
6. event lifecycle rules;
7. RiverOS-to-Silk handoff metadata.

The package does not own:

- authentication credentials;
- tenant master data;
- source documents themselves;
- payment execution;
- mutable ERP or workflow records;
- agent prompts or model configuration.

## Non-negotiable invariants

### 1. Events are immutable; state is derived

A historical event is never rewritten to make the current state appear correct.

Corrections use additive relationships:

```text
Original event
    ↓
Correction, reversal or supersession event
    ↓
Updated state projection
```

### 2. No orphan commercial consequence

Every Silk obligation must reference:

- a RiverOS event ID;
- the governing contract or rule;
- the payer and beneficiary;
- the calculation basis;
- the approval record, where required.

### 3. Tenant and workspace context is mandatory

Every accepted event must resolve its workspace and authority context before it can affect a projection or settlement decision.

### 4. Evidence is referenced, not silently embedded

Large files remain in governed object storage. RiverOS records their checksum, storage URI, classification, retention rule and relationship to the event.

### 5. Duplicate delivery must not duplicate effect

Producers must supply an idempotency key or stable source reference. Replaying the same source event must not produce a second accepted business effect.

### 6. Time is multi-dimensional

RiverOS distinguishes:

- `occurred_at`: when the activity happened;
- `observed_at`: when a person, device or system observed it;
- `received_at`: when RiverOS received it;
- `effective_at`: when it became operationally effective;
- `recorded_at`: when it was committed to the ledger.

## Canonical event envelope

The machine-readable contract is in [`event.schema.json`](./event.schema.json).

Minimum fields:

```text
Event ID
Event Type
Event Version
Workspace ID
Source System
Actor or Agent
Object Type and Object ID
Action
Previous State
New State
Authority Basis
Evidence References
Lifecycle Status
Trace ID
Correlation ID
Causation ID
Commercial Relevance
Settlement Eligibility
Occurred / Observed / Received / Effective / Recorded timestamps
Hash and signature metadata
```

## Event streams

RiverOS is divided into governed streams rather than one undifferentiated log.

### Identity stream

Authentication, consent, delegation, role changes, device binding and revocation.

### Knowledge stream

Ingestion, review, approval, publication, vector indexing, retrieval, supersession and revocation.

### Workflow stream

Task creation, assignment, acceptance, evidence capture, handoff, closure and escalation.

### Asset stream

Machine activity, maintenance, production, inspection, custody, movement and disposal.

### Commerce stream

Catalogue, quotation, order, dispatch, delivery, return, invoice and payment-state events.

### Agent stream

Prompt receipt, retrieval, tool proposal, tool execution, guardrail decision, response and human escalation.

### Settlement stream

Obligation creation, reserve, approval, release, bank confirmation, reversal, dispute and reconciliation.

## Event lifecycle

Normal path:

```text
RECEIVED
→ VALIDATING
→ VERIFIED
→ ACCEPTED
→ APPLIED
→ SETTLEMENT_ELIGIBLE
→ CLOSED
```

Exception states:

```text
REJECTED
QUARANTINED
DISPUTED
SUSPENDED
REVERSED
SUPERSEDED
```

An event may be commercially relevant without being settlement eligible. Settlement eligibility must be explicitly earned through evidence, authority and policy checks.

## RiverOS and Silk Dam boundary

RiverOS and Silk Dam are separate control systems.

| Layer | RiverOS | Silk Dam |
|---|---|---|
| Primary concern | Operational truth | Economic consequence |
| Primary object | Event | Obligation or entitlement |
| Input | Activity and evidence | Verified commercial event |
| Output | Accepted state transition | Authorised settlement instruction |
| Main controls | Identity, evidence, authority, sequence | Contract, amount, reserve, approval, release |
| Historical record | What happened | What became payable and what settled |

RiverOS must never directly transfer money.

Silk Dam must never accept a commercial claim without an accepted RiverOS event, an authorised contractual source, or an explicitly governed manual adjustment.

## Knowledge Shack, Vector Bay and RAG integration

RiverOS records knowledge lifecycle events but does not replace the knowledge repository.

```text
Source object
→ Knowledge Shack review
→ approved knowledge object
→ Vector Bay indexing
→ authorised retrieval
→ RAG answer or action
→ RiverOS retrieval and decision event
```

A RAG agent should emit RiverOS events for:

- retrieval requested;
- knowledge objects selected;
- answer issued;
- inference declared;
- missing evidence detected;
- tool proposed or executed;
- escalation requested.

The authoritative source remains in the Uber Repository or source system. Vector Bay remains a retrieval index. RiverOS records the event and evidence relationship.

## Database objects

The additive PostgreSQL schema is in [`schema.sql`](./schema.sql).

It introduces:

- `riveros.event_streams`;
- `riveros.events`;
- `riveros.evidence_objects`;
- `riveros.event_evidence_links`;
- `riveros.event_relations`;
- `riveros.state_projections`.

The existing `riveros.evidence_events` table is retained as a legacy compatibility surface. New implementations should write to `riveros.events` and link evidence through the dedicated evidence tables.

## Applying the schema

Run after the seed-node database initialisation:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f seed-node-v0.1/packages/riveros/schema.sql
```

The schema is additive and uses `IF NOT EXISTS` so it can be applied safely to a fresh Seed Node or an existing development database. Production migrations should still be versioned and reviewed through the deployment pipeline.

## Producer requirements

Every event producer should provide:

- a stable source-system identifier;
- a source event reference or idempotency key;
- the workspace context;
- actor, agent or device identity;
- event type and version;
- affected object reference;
- occurred and observed timestamps;
- evidence references;
- authority and consent context;
- commercial relevance and settlement eligibility flags.

## Consumer requirements

Consumers must:

- process events idempotently;
- respect workspace and classification boundaries;
- derive state instead of rewriting history;
- record projection versions;
- reject unsupported event versions;
- preserve trace, correlation and causation identifiers;
- treat settlement eligibility as a controlled status, not an inference.

## Initial Seed Node flow

```text
Physical swatch received
→ material passport created
→ BOM version approved
→ tech pack generated
→ payment metadata recorded
→ RiverOS evidence event accepted
→ Silk obligation calculated, when contractually eligible
→ settlement confirmation returned to RiverOS
```

## Version

This repository contract is **RiverOS v0.2**.

It extends the original evidence-ledger placeholder into an append-only event repository with explicit evidence, state projection, agent retrieval and Silk Dam boundaries.
