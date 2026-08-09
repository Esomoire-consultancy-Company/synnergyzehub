import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const endpoint = new URL("/api/mcp", request.url);
  const client = new Client({
    name: "genesis-seed-001-selftest",
    version: "0.1.0",
  });
  const transport = new StreamableHTTPClientTransport(endpoint);

  try {
    await client.connect(transport);
    const listed = await client.listTools();
    const status = await client.callTool({
      name: "seed_status",
      arguments: {},
    });

    return Response.json(
      {
        ok: true,
        seedId: "GEN-SEED-001",
        endpoint: endpoint.pathname,
        tools: listed.tools.map((tool) => tool.name),
        seedStatus: status.content,
      },
      { headers: { "cache-control": "no-store" } },
    );
  } catch (error) {
    return Response.json(
      {
        ok: false,
        seedId: "GEN-SEED-001",
        endpoint: endpoint.pathname,
        error: error instanceof Error ? error.message : String(error),
      },
      {
        status: 500,
        headers: { "cache-control": "no-store" },
      },
    );
  } finally {
    try {
      await client.close();
    } catch {
      // Self-test cleanup must not mask the protocol result.
    }
  }
}
