# Data Weaver Studio R0.4 Interface Coverage Addendum

> **Required companion to:** `docs/superpowers/plans/2026-09-12-data-weaver-r0.4-production-intelligence.md`

This addendum closes the external-interface coverage gap found during implementation-plan self-review. It does not change the approved domain design or implementation order; it makes the R0.3, R0.2, production-console, and QA command surfaces explicit.

## Required Additional Route Files

```text
app/api/dws-production/
  capacity/release/route.ts
  capacity/quote-projection/route.ts
  lmos/[lmoId]/route.ts
  lmos/[lmoId]/cancel/route.ts
  work/[assignmentId]/start/route.ts
  work/[assignmentId]/block/route.ts
  work/[assignmentId]/resume/route.ts
  work/[assignmentId]/submit/route.ts
  qa/inspections/[inspectionId]/result/route.ts
  qa/nonconformances/[ncrId]/rework/route.ts
  qa/nonconformances/[ncrId]/close/route.ts
```

## Required Service Interfaces

Add these exact functions to the services already defined by the main plan:

```ts
// lib/dws-production/services/capacity.ts
export async function releaseCapacityHold(input: {
  tenantId: string;
  idempotencyKey: string;
  reservationGroupId: string;
}): Promise<{ reservationGroupId: string; state: "released" | "expired" }>;

export async function quoteDeliveryProjection(input: {
  tenantId: string;
  configurationId: string;
  requestedStartAt: Date;
  requiredCompletionAt?: Date;
}): Promise<{
  feasible: boolean;
  earliestStart: Date | null;
  earliestFeasibleCompletion: Date | null;
  forecastProductionCost: number | null;
  scheduleConfidence: number;
  scheduleConfidenceComponents: {
    capacityCoverage: number;
    effortModelCoverage: number;
    dependencyCompleteness: number;
    performanceHistoryCoverage: number;
    qaDurationCoverage: number;
  };
  bottlenecks: BottleneckReport[];
}>;

// lib/dws-production/services/decomposition.ts
export async function cancelLmo(input: {
  tenantId: string;
  idempotencyKey: string;
  lmoId: string;
  reason: string;
  actorPrincipalId: string;
}): Promise<{ lmoId: string; state: "cancelled" }>;

export async function getLmoStatus(input: {
  tenantId: string;
  lmoId: string;
}): Promise<{
  lmo: LmoRecord;
  workPackages: WorkPackageRecord[];
  assignments: AssignmentRecord[];
  inspections: QaInspectionRecord[];
  nonconformances: NonconformanceRecord[];
  events: ProductionEvent[];
}>;

// lib/dws-production/services/execution.ts
export async function startWork(input: WorkCommand): Promise<WorkCommandResult>;
export async function blockWork(input: WorkCommand & { reason: string }): Promise<WorkCommandResult>;
export async function resumeWork(input: WorkCommand): Promise<WorkCommandResult>;
export async function submitWork(input: WorkCommand & {
  artifactRefs: string[];
  evidenceRefs: string[];
}): Promise<WorkCommandResult>;

export type WorkCommand = {
  tenantId: string;
  idempotencyKey: string;
  assignmentId: string;
  actorPrincipalId: string;
};

export type WorkCommandResult = {
  assignmentId: string;
  workPackageId: string;
  state: "in_progress" | "blocked" | "submitted";
  eventId: string;
};

// lib/dws-production/services/quality.ts
export async function recordInspectionResult(...args: Parameters<typeof existingRecordInspectionResult>): ReturnType<typeof existingRecordInspectionResult>;
export async function requestRework(input: {
  tenantId: string;
  idempotencyKey: string;
  nonconformanceId: string;
  actorPrincipalId: string;
}): Promise<{ nonconformanceId: string; state: "rework" }>;

export async function closeNonconformance(input: {
  tenantId: string;
  idempotencyKey: string;
  nonconformanceId: string;
  actorPrincipalId: string;
  closureEvidenceReceiptId: string;
}): Promise<{ nonconformanceId: string; state: "closed" }>;
```

The `recordInspectionResult` line above means the already-defined result service remains the canonical function; the HTTP layer must expose it through the explicit inspection-result route rather than inventing a second implementation.

## HTTP Mapping

Every route uses the authentication/context/error pattern defined in Task 8 of the main plan.

```text
POST /api/dws-production/capacity/simulate
  → simulateCapacity

POST /api/dws-production/capacity/hold
  → holdCapacity

POST /api/dws-production/capacity/release
  → releaseCapacityHold

POST /api/dws-production/capacity/commit
  → commitReservationGroup

POST /api/dws-production/capacity/quote-projection
  → quoteDeliveryProjection

POST /api/dws-production/lmos
  → decomposeConfiguration / create LMO

GET /api/dws-production/lmos/:lmoId
  → getLmoStatus

POST /api/dws-production/lmos/:lmoId/release
  → releaseLmo

POST /api/dws-production/lmos/:lmoId/cancel
  → cancelLmo

POST /api/dws-production/work/:assignmentId/start
  → startWork

POST /api/dws-production/work/:assignmentId/block
  → blockWork

POST /api/dws-production/work/:assignmentId/resume
  → resumeWork

POST /api/dws-production/work/:assignmentId/submit
  → submitWork

POST /api/dws-production/qa/inspections
  → startInspection

POST /api/dws-production/qa/inspections/:inspectionId/result
  → recordInspectionResult

POST /api/dws-production/qa/nonconformances
  → openNonconformance

POST /api/dws-production/qa/nonconformances/:ncrId/rework
  → requestRework

POST /api/dws-production/qa/nonconformances/:ncrId/close
  → closeNonconformance
```

## Command-Specific Tests

Add these cases to `tests/dws-production/http.test.ts` and `qualification.integration.test.ts`:

```ts
it("releases a tentative capacity hold idempotently", async () => {
  const first = await releaseCapacityHold(releaseInput);
  const second = await releaseCapacityHold(releaseInput);
  expect(second).toEqual(first);
});

it("cancellation releases remaining active reservations", async () => {
  await cancelLmo(cancelInput);
  expect(await activeReservationsForLmo(cancelInput.lmoId)).toHaveLength(0);
});

it("work commands enforce state sequence", async () => {
  await startWork(startInput);
  await blockWork({ ...startInput, idempotencyKey: "block-0001", reason: "dependency unavailable" });
  await resumeWork({ ...startInput, idempotencyKey: "resume-0001" });
  await submitWork({ ...startInput, idempotencyKey: "submit-0001", artifactRefs: ["artifact://build-1"], evidenceRefs: ["river://receipt-1"] });
});

it("LMO status returns the complete production trace for its tenant", async () => {
  const trace = await getLmoStatus({ tenantId, lmoId });
  expect(trace.lmo.lmo_id).toBe(lmoId);
  expect(trace.workPackages.length).toBeGreaterThan(0);
  expect(trace.events.length).toBeGreaterThan(0);
});
```

## Updated Spec-Coverage Matrix

```text
R0.3 simulate_capacity             covered
R0.3 hold_capacity                 covered
R0.3 release_capacity_hold         covered by this addendum
R0.3 quote_delivery_projection     covered by this addendum
R0.2 create_lmo                    covered
R0.2 commit_capacity               covered
R0.2 release_lmo                   covered
R0.2 cancel_lmo                    covered by this addendum
R0.2 get_lmo_status                covered by this addendum
Console start_work                 covered by this addendum
Console block_work                 covered by this addendum
Console resume_work                covered by this addendum
Console submit_work                covered by this addendum
QA start_inspection                covered
QA record_inspection_result        covered explicitly by this addendum
QA open_nonconformance             covered
QA request_rework                  covered explicitly by this addendum
QA close_nonconformance            covered explicitly by this addendum
```

Execution is not considered complete until the main plan and this addendum both pass the qualification suite.