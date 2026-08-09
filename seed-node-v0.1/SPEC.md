# Genesis Seed 001 — MCP Capability Seed

## Purpose

Expose the first governed, read-only VSR/Genesis MCP capability from the existing Synnergyze seed-node deployment so MCP clients can discover a canonical Seed identity and its governance boundary.

## Canonical identity

- Seed ID: `GEN-SEED-001`
- Name: `Genesis Capability Seed 001`
- Environment: `development/preview` until promoted
- Host application: `seed-node-v0.1/apps/web`
- Transport: MCP Streamable HTTP via `/api/mcp`

## Capabilities

The first release is intentionally read-only and contains no external side effects.

1. `seed_status` — returns Seed identity, version, environment, capability class, and governance posture.
2. `governance_contract` — returns the required VSR execution sequence and explicitly separates discovery from authorization.

## Governance constraints

- Discovery is not authorization.
- Presence of an MCP tool never grants execution authority.
- No legal, financial, settlement, identity, device, infrastructure, or production mutation is exposed by this Seed.
- Any future mutating capability must be gated by Warden policy evaluation before execution.
- Future calls that operate on VSR state must emit evidence into the applicable evidence/RiverOS path.
- DigitalMe context must be purpose-scoped; this Seed does not ingest or persist personal memory.

## Canonical execution sequence

`DISCOVER -> IDENTIFY -> RESOLVE REGISTRY ID -> CHECK WARDEN -> ISSUE CAPABILITY -> INVOKE MCP -> RECORD EVIDENCE`

## Non-goals for Seed 001

- No authentication implementation beyond the hosting/MCP transport baseline.
- No Warden decision engine implementation.
- No Registry mutation.
- No RiverOS mutation.
- No SILK settlement.
- No external connectors.

## Promotion gates

1. Build succeeds.
2. `/api/mcp` responds as an MCP endpoint.
3. MCP initialization and `tools/list` succeed.
4. `seed_status` and `governance_contract` return deterministic read-only output.
5. Production promotion remains separate from preview validation.
