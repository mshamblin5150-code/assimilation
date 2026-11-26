// Seam 5, live: drive the real MCP server over stdio against the fixture window, as an agent
// would. Needs a desktop session. Usage: node live/prove_fixture.mjs <bundle-output-path>
import { execFileSync, spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import { fileURLToPath } from "node:url";

import { Client } from "@modelcontextprotocol/client";
import { StdioClientTransport } from "@modelcontextprotocol/client/stdio";

const fixture = fileURLToPath(
  new URL("../helper/ReaWindowsUi.Fixture/bin/Release/net9.0-windows/ReaWindowsUi.Fixture.exe", import.meta.url),
);
const server = fileURLToPath(new URL("../src/server.js", import.meta.url));
const bundlePath = process.argv[2];

const app = spawn(fixture, [], { detached: false, stdio: "ignore" });
await delay(2500);
const hwnd = Number(
  execFileSync("powershell", ["-NoProfile", "-Command", `(Get-Process -Id ${app.pid}).MainWindowHandle`]).toString().trim(),
);

const client = new Client({ name: "parity-proof", version: "0.1.0" });
await client.connect(new StdioClientTransport({ command: process.execPath, args: [server] }));
const call = async (name, args) => {
  const result = await client.callTool({ name, arguments: args });
  const body = JSON.parse(result.content[0].text);
  if (result.isError) throw new Error(`${name}: ${JSON.stringify(body).slice(0, 600)}`);
  return body;
};

try {
  console.log("tools:", (await client.listTools()).tools.map((t) => t.name).join(", "));
  const { target } = await call("open_binary", { path: fixture });
  console.log("target:", target.format, target.architecture, target.sha256.slice(0, 12));

  const observed = await call("observe_native_ui", { pid: app.pid, window_id: hwnd, max_nodes: 100 });
  const initial = observed.normalized_result.initial; // the result is the Evidence itself
  // By role and name: the window's own title-bar buttons (Minimize...) are Buttons too.
  const find = (role, title) => initial.nodes.find((n) => n.role === role && (title === undefined || n.title === title));
  const [button, slider, field] = [find("Button", "Press me"), find("Slider", "Amount"), find("Edit", "Name")];
  console.log("observed nodes:", initial.nodes.length, "screenshot:", initial.screenshot?.width, "x", initial.screenshot?.height);
  console.log("button", button.path, button.title, button.actions, "| slider", slider.path, slider.value, slider.actions, "| field", field.path, field.actions);

  const scenario = await call("capture_native_ui_scenario", {
    pid: app.pid,
    window_id: hwnd,
    max_nodes: 100,
    screenshot: false,
    steps: [
      { kind: "click", path: button.path },
      { kind: "scroll", path: slider.path, direction: "increment" },
      { kind: "key-entry", path: field.path, text: "hello" },
      { kind: "wait", milliseconds: 200 },
    ],
  });
  const steps = scenario.normalized_result.steps;
  const at = (snapshot, path) => snapshot.nodes.find((n) => n.path.join(".") === path.join("."));
  console.log("steps:", steps.map((s) => `${s.kind}:${s.outcome}`).join(" "));
  console.log("after click, button title:", at(steps[0].after, button.path).title);
  console.log("after scroll, slider value:", at(steps[1].after, slider.path).value);
  console.log("after key-entry, field value:", at(steps[2].after, field.path).value);

  const bad = await client.callTool({
    name: "capture_native_ui_scenario",
    arguments: { pid: app.pid, window_id: hwnd, screenshot: false, steps: [{ kind: "click", path: slider.path }] },
  });
  console.log("click on a slider (no Invoke):", bad.isError ? JSON.parse(bad.content[0].text).code : "unexpectedly succeeded");

  if (bundlePath) console.log("bundle:", await call("export_evidence_bundle", { path: bundlePath }));
} finally {
  await client.close();
  app.kill();
}
