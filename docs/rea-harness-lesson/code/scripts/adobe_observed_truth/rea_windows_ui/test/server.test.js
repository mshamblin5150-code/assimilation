// The MCP tool handlers, driven directly with a fake helper and fake request contexts.
import assert from "node:assert/strict";
import { test } from "node:test";

import { createTools } from "../src/server.js";

const TARGET = {
  path: "C:\\Apps\\Fixture.exe",
  sha256: "b".repeat(64),
  format: "pe",
  architecture: "x86_64",
};
const SNAPSHOT = {
  window: { pid: 4242, window_id: 77, executable: TARGET.path, launch_time: 1762700000.5, title: "Fixture" },
  nodes: [],
  truncated: false,
  screenshot: null,
  gaps: [],
};
const context = (signal = new AbortController().signal) => ({ mcpReq: { signal } });
const tools = (invoke = async () => ({ ok: true, result: SNAPSHOT })) =>
  createTools({ invoke, openTarget: async () => TARGET });

test("a successful observation returns the Evidence itself as structured content", async () => {
  const handlers = tools();
  await handlers.open_binary({ path: TARGET.path }, context());

  const result = await handlers.observe_native_ui({ pid: 4242, window_id: 77 }, context());

  assert.deepEqual(
    [result.isError ?? false, result.structuredContent.operation, result.structuredContent.provider.id],
    [false, "observe_native_ui", "native-windows"],
  );
});

test("a request the client cancelled is reported cancelled, read from the request's own signal", async () => {
  const handlers = tools();
  await handlers.open_binary({ path: TARGET.path }, context());
  const cancelled = new AbortController();
  cancelled.abort("client cancelled");

  const result = await handlers.observe_native_ui({ pid: 4242, window_id: 77 }, context(cancelled.signal));

  assert.deepEqual([result.isError, result.structuredContent.code], [true, "cancelled"]);
});

test("closing the target waits for a running observation, which keeps its target", async () => {
  let release;
  const gate = new Promise((resolve) => (release = resolve));
  const handlers = tools(async () => {
    await gate;
    return { ok: true, result: SNAPSHOT };
  });
  await handlers.open_binary({ path: TARGET.path }, context());

  const observing = handlers.observe_native_ui({ pid: 4242, window_id: 77 }, context());
  const closing = handlers.close_binary({}, context());
  release();

  assert.equal((await observing).structuredContent.subject.digest.sha256, TARGET.sha256);
  await closing;
});

test("a failed scenario reports a REA-style error with its partial observation", async () => {
  let calls = 0;
  const handlers = tools(async () =>
    ++calls === 1 ? { ok: true, result: SNAPSHOT } : { ok: false, code: "element-missing", message: "gone" },
  );
  await handlers.open_binary({ path: TARGET.path }, context());

  const result = await handlers.capture_native_ui_scenario(
    { pid: 4242, window_id: 77, steps: [{ kind: "click", path: [3] }] },
    context(),
  );

  const error = result.structuredContent;
  assert.deepEqual(
    [result.isError, typeof error.remediation.action, error.details.partial_observation.steps[0].outcome],
    [true, "string", "failed"],
  );
  assert.match(error.message, /element-missing|gone/);
});

test("errors are REA's own projection, remediation and recovery included", async () => {
  const handlers = tools(async () => {
    throw Object.assign(new Error("helper exceeded the deadline"), { code: "ETIMEDOUT" });
  });
  await handlers.open_binary({ path: TARGET.path }, context());

  const result = await handlers.observe_native_ui({ pid: 4242, window_id: 77, native_ui_deadline_ms: 5000 }, context());

  const error = result.structuredContent;
  assert.deepEqual(
    [error.category, error.recovery?.kind, /native_ui_deadline_ms/.test(error.remediation.action)],
    ["timeout", "inspect_timeout_state", true],
  );
});

test("an export to a path that cannot be written is an error result, not a crash", async () => {
  const result = await tools().export_evidence_bundle({ path: "Z:\\no\\such\\dir\\bundle.json" }, context());

  assert.equal(result.isError, true);
});
