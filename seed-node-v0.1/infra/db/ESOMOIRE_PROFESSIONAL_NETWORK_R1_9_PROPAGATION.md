# ESOMOIRE-PROFESSIONAL-NETWORK-001 R1.9 — Database Propagation

Canonical migration: `migrations/20260830_esomoire_professional_network_r1_9.sql`

## Authority boundaries

- Esomoire: professional registry, platform commercial entitlements, Genesis-device commercial projection.
- Professional / CA firm: professional engagement and professional-fee economic ownership.
- Warden: authority/admissibility decisions.
- River: immutable evidence/receipt provenance.
- Synnergyze: workflow orchestration.
- SILK: settlement authority. R1.9 stores only SILK references/projections; it does not create a competing settlement ledger.
- WhatsApp and Linemate: interaction/operational surfaces, never canonical financial or professional authority systems.

## Database-source propagation matrix

| Source | Role | R1.9 action | Current status |
|---|---|---|---|
| Neon `vsr-public-services` | Shared VSR professional-service runtime | Apply canonical migration to governed branch, verify, then promote | Source prepared; live migration pending connector-safe branch execution |
| Supabase `vsr-merchant-integration-hub` | Merchant/Linemate operational projection | Apply compatible migration/projection after connection health is restored | Blocked by DB connection refusal during 2026-08-30 run |
| Airtable | Operator-facing auxiliary surface only | No new Esomoire base; do not create duplicate source of truth | Intentionally unchanged |
| GitHub `Esomoire-consultancy-Company/synnergyzehub` | Source-of-deployment / migration lineage | Store canonical R1.9 schema and propagation manifest | Updated on branch `esomoire-professional-network-r1-9` |

## R1.9 service catalogue seeds

- `ESOMOIRE_REGISTRY`
- `CONTINUOUS_READINESS`
- `QUARTER_CLOSE`
- `FILING_RELEASE`
- `PROFESSIONAL_REVIEW`
- `NOTICE_RESPONSE`
- `GENESIS_DEVICE`

## Core invariants

1. `ProfessionalContribution != PlatformRevenue` unless separately contracted and permitted.
2. `EsomoirePlatformCharge != PercentageOfProfessionalFee`.
3. `CapacityReservation != ProfessionalAuthority`.
4. `ServiceEntitlement != ProfessionalEngagement`.
5. `WhatsAppMessage != AccountingRecord`.
6. `LinemateEvent != ProfessionalSignoff`.
7. `SILKProjection != SILKAuthoritativePosition`.
8. `No Warden admission => no governed consumption/execution` where an authority gate is required.
9. Every governed consumption may carry a River receipt reference.
10. Historical events retain their source and control versions.

## Promotion checklist

- Verify migration against a temporary/preview database branch.
- Verify table/view creation and seeded catalogue.
- Verify professional-fee/platform-charge separation.
- Verify no duplicate SILK settlement authority is created.
- Verify RLS/privilege posture for any schema exposed through Supabase Data API.
- Verify Linemate/WhatsApp adapters write structured cases/consumption references rather than canonical ledger truth.
- Register propagation receipt in the existing deployment/runtime registry after target deployment.
