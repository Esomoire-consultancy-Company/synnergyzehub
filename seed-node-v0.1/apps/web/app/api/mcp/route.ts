import { createMcpHandler } from "mcp-handler";

const SEED = {
  seedId: "GEN-SEED-001",
  name: "Genesis Capability Seed 001",
  version: "0.1.0",
  capabilityClass: "read-only-discovery",
  transport: "streamable-http",
  endpoint: "/api/mcp",
  governance: {
    discoveryIsAuthorization: false,
    mutatingToolsEnabled: false,
    wardenRequiredForFutureMutation: true,
    evidenceRequiredForFutureStateChange: true,
  },
} as const;

const handler = createMcpHandler(
  (server) => {
    server.tool(
      "seed_status",
      "Return the canonical identity and governance posture of Genesis Seed 001.",
      {},
      async () => ({
        content: [
          {
            type: "text",
            text: JSON.stringify(
              {
                ...SEED,
                environment: process.env.VERCEL_ENV ?? "development",
              },
              null,
              2,
            ),
          },
        ],
      }),
    );

    server.tool(
      "governance_contract",
      "Return the VSR capability execution sequence and authorization boundary for this Seed.",
      {},
      async () => ({
        content: [
          {
            type: "text",
            text: JSON.stringify(
              {
                seedId: SEED.seedId,
                sequence: [
                  "DISCOVER",
                  "IDENTIFY",
                  "RESOLVE_REGISTRY_ID",
                  "CHECK_WARDEN",
                  "ISSUE_CAPABILITY",
                  "INVOKE_MCP",
                  "RECORD_EVIDENCE",
                ],
                rules: [
                  "Discovery is not authorization.",
                  "This Seed is read-only.",
                  "No mutating VSR capability is enabled.",
                  "Future mutation must be Warden-authorized and evidence-recorded.",
                ],
              },
              null,
              2,
            ),
          },
        ],
      }),
    );
  },
  {},
  { basePath: "/api" },
);

export { handler as GET, handler as POST, handler as DELETE };
