// Live, passive: observe Photoshop 2026's main window through the MCP server (no actions).
// Usage: node live/observe_photoshop.mjs
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

import { Client } from "@modelcontextprotocol/client";
import { StdioClientTransport } from "@modelcontextprotocol/client/stdio";

const exe = "C:\\Program Files\\Adobe\\Adobe Photoshop 2026\\Photoshop.exe";
const server = fileURLToPath(new URL("../src/server.js", import.meta.url));
const [pid, hwnd] = execFileSync("powershell", [
  "-NoProfile",
  "-Command",
  "$p = Get-Process Photoshop | Select-Object -First 1; \"$($p.Id) $([int64]$p.MainWindowHandle)\"",
])
  .toString()
  .trim()
  .split(" ")
  .map(Number);

const client = new Client({ name: "photoshop-observe", version: "0.1.0" });
await client.connect(new StdioClientTransport({ command: process.execPath, args: [server] }));
try {
  const call = async (name, args) => {
    const result = await client.callTool({ name, arguments: args });
    let body;
    try {
      body = JSON.parse(result.content[0].text);
    } catch {
      throw new Error(`${name} replied: ${result.content[0].text.slice(0, 800)}`);
    }
    if (result.isError) throw new Error(`${name}: ${JSON.stringify(body).slice(0, 600)}`);
    return body;
  };
  await call("open_binary", { path: exe });
  const started = Date.now();
  const evidence = await call("observe_native_ui", { pid, window_id: hwnd, max_nodes: 300 });
  const initial = evidence.normalized_result.initial;
  const roles = {};
  for (const node of initial.nodes) roles[node.role ?? "?"] = (roles[node.role ?? "?"] ?? 0) + 1;
  const actionable = initial.nodes.filter((n) => n.actions.length > 0);
  console.log(`observed in ${Date.now() - started} ms; evidence ${evidence.evidence_id.slice(0, 15)}`);
  console.log(`nodes ${initial.nodes.length}, truncated ${initial.truncated}, gaps ${initial.gaps.length}, screenshot ${initial.screenshot?.width}x${initial.screenshot?.height}`);
  console.log("roles:", JSON.stringify(roles));
  console.log("actionable:", actionable.length, actionable.slice(0, 8).map((n) => `${n.role}:${n.title ?? ""}:${n.actions.join("/")}`).join(" | "));
} finally {
  await client.close();
}
