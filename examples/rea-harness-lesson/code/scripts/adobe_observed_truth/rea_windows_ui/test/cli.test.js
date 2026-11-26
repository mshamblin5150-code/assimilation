// The commands the Python harness runs: a parity observation per Photoshop process, and the
// linked bundle. Driven through the same tool handlers an MCP client gets.
import assert from "node:assert/strict";
import { test } from "node:test";

import { observeForHarness } from "../src/cli.js";
import { createTools } from "../src/server.js";

const TARGET = { path: "C:\\Apps\\Photoshop.exe", sha256: "c".repeat(64), format: "pe", architecture: "x86_64" };
const SNAPSHOT = {
  window: { pid: 900, window_id: 55, executable: TARGET.path, launch_time: 1762700000.25, title: "Adobe Photoshop 2026" },
  nodes: [],
  truncated: false,
  screenshot: null,
  gaps: [],
};
const tools = (invoke) => createTools({ invoke, openTarget: async () => TARGET });

test("observing for the harness returns the observation's Evidence and the process it saw", async () => {
  const outcome = await observeForHarness(
    { exe: TARGET.path, pid: 900, window: 55 },
    tools(async () => ({ ok: true, result: SNAPSHOT })),
  );

  assert.deepEqual(
    [outcome.parity.evidence_id, outcome.parity.launch_time, outcome.evidence.evidence_id],
    [outcome.evidence.evidence_id, 1762700000.25, outcome.evidence.evidence_id],
  );
});

test("an observation that fails gives the harness REA's error, remediation included", async () => {
  const outcome = await observeForHarness(
    { exe: TARGET.path, pid: 900, window: 55 },
    tools(async () => ({ ok: false, code: "accessibility-denied", message: "UI Automation refused access" })),
  );

  assert.deepEqual(
    [outcome.evidence, typeof outcome.parity.error.remediation.action, outcome.parity.error.code],
    [null, "string", "capability_unavailable"],
  );
});
