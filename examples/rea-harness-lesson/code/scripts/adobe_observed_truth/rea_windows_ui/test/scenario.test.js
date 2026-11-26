// Seam 1: scenario sequencing, driven by a fake helper. Behaviour mirrors rea-agents 6.8.0
// dist/native/NativeUiObservation.js (observeWithHelper) for the macOS tools.
import assert from "node:assert/strict";
import { test } from "node:test";

import { runScenario } from "../src/scenario.js";

const TARGET = {
  path: "C:\\Program Files\\Adobe\\Adobe Photoshop 2026\\Photoshop.exe",
  sha256: "a".repeat(64),
  format: "pe",
  architecture: "x86_64",
};

const snapshot = (overrides = {}) => ({
  window: {
    pid: 4242,
    window_id: 77,
    executable: TARGET.path,
    launch_time: 1762700000.5,
    title: "Untitled",
  },
  nodes: [],
  truncated: false,
  screenshot: null,
  gaps: [],
  ...overrides,
});

/** A helper that answers each request with the next canned response and records requests. */
const fakeHelper = (...responses) => {
  const requests = [];
  const invoke = async (request) => {
    requests.push(request);
    return responses.length > 1 ? responses.shift() : responses[0];
  };
  return { invoke, requests };
};

test("a passive observation is one capture of the selected window, left as-is", async () => {
  const helper = fakeHelper({ ok: true, result: snapshot() });

  const outcome = await runScenario({
    operation: "observe_native_ui",
    parameters: { pid: 4242, window_id: 77 },
    target: TARGET,
    invoke: helper.invoke,
  });

  assert.equal(outcome.ok, true);
  assert.deepEqual(
    {
      target: outcome.report.target_sha256,
      steps: outcome.report.steps,
      restore: outcome.report.restore,
      initial: outcome.report.initial,
    },
    { target: TARGET.sha256, steps: [], restore: "leave-as-is", initial: snapshot() },
  );
});

test("each step is followed by a capture, chaining before and after", async () => {
  const [a, b, c] = ["A", "B", "C"].map((title) =>
    snapshot({ window: { ...snapshot().window, title } }),
  );
  const helper = fakeHelper({ ok: true, result: a }, { ok: true, result: b }, { ok: true, result: c });

  const outcome = await runScenario({
    operation: "capture_native_ui_scenario",
    parameters: {
      pid: 4242,
      window_id: 77,
      steps: [{ kind: "click", path: [0, 1] }, { kind: "wait", milliseconds: 0 }],
    },
    target: TARGET,
    invoke: helper.invoke,
  });

  assert.deepEqual(outcome.report.steps, [
    { index: 0, kind: "click", before: a, after: b, outcome: "completed", reason: null },
    { index: 1, kind: "wait", before: b, after: c, outcome: "completed", reason: null },
  ]);
});

test("the action goes to the helper, and later captures carry the first launch time", async () => {
  const helper = fakeHelper({ ok: true, result: snapshot() });

  await runScenario({
    operation: "capture_native_ui_scenario",
    parameters: {
      pid: 4242,
      window_id: 77,
      steps: [{ kind: "key-entry", path: [2], text: "12" }, { kind: "wait", milliseconds: 0 }],
    },
    target: TARGET,
    invoke: helper.invoke,
  });

  assert.deepEqual(
    helper.requests.map((r) => [r.action ?? null, r.launch_time ?? null]),
    [
      [null, null],
      [{ kind: "key-entry", path: [2], text: "12" }, 1762700000.5],
      [null, 1762700000.5],
    ],
  );
});

test("a wait step sleeps for its milliseconds before its capture", async () => {
  const slept = [];

  await runScenario({
    operation: "capture_native_ui_scenario",
    parameters: { pid: 4242, window_id: 77, steps: [{ kind: "wait", milliseconds: 1500 }] },
    target: TARGET,
    invoke: fakeHelper({ ok: true, result: snapshot() }).invoke,
    sleep: async (ms) => slept.push(ms),
  });

  assert.deepEqual(slept, [1500]);
});

test("the first failing step stops the scenario and the partial report is kept", async () => {
  const helper = fakeHelper(
    { ok: true, result: snapshot() },
    { ok: false, code: "element-missing", message: "Selected accessibility path no longer exists" },
  );

  const outcome = await runScenario({
    operation: "capture_native_ui_scenario",
    parameters: {
      pid: 4242,
      window_id: 77,
      steps: [{ kind: "click", path: [9] }, { kind: "click", path: [0] }],
    },
    target: TARGET,
    invoke: helper.invoke,
  });

  assert.equal(outcome.ok, false);
  assert.equal(outcome.error.code, "element-missing");
  assert.deepEqual(outcome.partial.steps, [
    {
      index: 0,
      kind: "click",
      before: snapshot(),
      after: null,
      outcome: "failed",
      reason:
        "Provider native-windows cannot execute capture_native_ui_scenario: element-missing: Selected accessibility path no longer exists",
    },
  ]);
  assert.equal(helper.requests.length, 2); // the second step never ran
});

test("a wrong process or window on the first capture is an input error on that field", async () => {
  const outcome = await runScenario({
    operation: "observe_native_ui",
    parameters: { pid: 4242, window_id: 77 },
    target: TARGET,
    invoke: fakeHelper({ ok: false, code: "window-mismatch", message: "Selected window is absent" }).invoke,
  });

  assert.deepEqual(
    [outcome.ok, outcome.error.kind, outcome.error.field, outcome.error.code],
    [false, "input", "window_id", "window-mismatch"],
  );
});

test("a capture from a relaunched process fails the step", async () => {
  const replaced = snapshot({ window: { ...snapshot().window, launch_time: 1762700999 } });

  const outcome = await runScenario({
    operation: "capture_native_ui_scenario",
    parameters: { pid: 4242, window_id: 77, steps: [{ kind: "wait", milliseconds: 0 }] },
    target: TARGET,
    invoke: fakeHelper({ ok: true, result: snapshot() }, { ok: true, result: replaced }).invoke,
    sleep: async () => {},
  });

  assert.deepEqual(
    [outcome.ok, outcome.error.message, outcome.partial.steps[0].outcome],
    [
      false,
      "Provider native-windows cannot execute capture_native_ui_scenario: Native helper returned a different target process or window",
      "failed",
    ],
  );
});

test("only a Windows executable target is admitted", async () => {
  const outcome = await runScenario({
    operation: "observe_native_ui",
    parameters: { pid: 4242, window_id: 77 },
    target: { ...TARGET, format: "mach-o" },
    invoke: fakeHelper({ ok: true, result: snapshot() }).invoke,
  });

  assert.deepEqual([outcome.ok, outcome.error.kind], [false, "capability"]);
});

test("a request for neither screenshot nor accessibility is refused as input", async () => {
  const outcome = await runScenario({
    operation: "observe_native_ui",
    parameters: { pid: 4242, window_id: 77, screenshot: false, accessibility: false },
    target: TARGET,
    invoke: fakeHelper({ ok: true, result: snapshot() }).invoke,
  });

  assert.deepEqual([outcome.ok, outcome.error.kind], [false, "input"]);
});

test("captures are charged at twice their size against the output budget", async () => {
  const outcome = await runScenario({
    operation: "observe_native_ui",
    parameters: { pid: 4242, window_id: 77 },
    target: TARGET,
    invoke: fakeHelper({ ok: true, result: snapshot() }).invoke,
    outputBudgetBytes: 2 * JSON.stringify(snapshot()).length - 1,
  });

  assert.deepEqual([outcome.ok, outcome.error.code], [false, "output-budget"]);
});

test("a caller cancellation stops the scenario and marks the step cancelled", async () => {
  const caller = new AbortController();
  const helper = fakeHelper({ ok: true, result: snapshot() });
  const invoke = async (request) => {
    const answer = await helper.invoke(request);
    caller.abort("caller stopped"); // stop right after the initial capture
    return answer;
  };

  const outcome = await runScenario({
    operation: "capture_native_ui_scenario",
    parameters: { pid: 4242, window_id: 77, steps: [{ kind: "click", path: [0] }] },
    target: TARGET,
    invoke,
    signal: caller.signal,
  });

  assert.deepEqual(
    [outcome.ok, outcome.error.kind, outcome.partial.steps[0].outcome],
    [false, "cancelled", "cancelled"],
  );
});

test("reaching the deadline fails the step as a timeout", async () => {
  const deadline = new AbortController();
  const invoke = async () => {
    deadline.abort("deadline");
    return { ok: true, result: snapshot() };
  };

  const outcome = await runScenario({
    operation: "capture_native_ui_scenario",
    parameters: { pid: 4242, window_id: 77, steps: [{ kind: "click", path: [0] }] },
    target: TARGET,
    invoke,
    deadline: deadline.signal,
  });

  assert.deepEqual(
    [outcome.ok, outcome.error.kind, outcome.partial.steps[0].outcome],
    [false, "timeout", "failed"],
  );
});

test("the limitations state the Windows methods and that no global input is synthesized", async () => {
  const outcome = await runScenario({
    operation: "observe_native_ui",
    parameters: { pid: 4242, window_id: 77 },
    target: TARGET,
    invoke: fakeHelper({ ok: true, result: snapshot() }).invoke,
  });

  const text = outcome.report.limitations.join(" ");
  for (const phrase of ["UI Automation", "Invoke", "RangeValue", "SetValue", "no synthesized global input", "leave-as-is"])
    assert.ok(text.includes(phrase), phrase);
});

// Review of 16a1ca79: helper failures, the deadline and cancellation must reach the helper call
// itself, keep the partial report, and use REA's own error messages.
const scenario = (steps, extra) =>
  runScenario({
    operation: "capture_native_ui_scenario",
    parameters: { pid: 4242, window_id: 77, steps },
    target: TARGET,
    sleep: async () => {},
    ...extra,
  });

test("a helper that dies mid-scenario fails the step and keeps the partial report", async () => {
  let calls = 0;
  const outcome = await scenario([{ kind: "click", path: [0] }], {
    invoke: async () => {
      calls += 1;
      if (calls === 1) return { ok: true, result: snapshot() };
      throw new Error("helper exited with code 3221225477");
    },
  });

  assert.deepEqual(
    [outcome.error.kind, outcome.partial.steps[0].outcome, outcome.partial.steps[0].after],
    ["capability", "failed", null],
  );
});

test("the helper call gets a signal that aborts at the deadline", async () => {
  const deadline = new AbortController();
  let abortedDuringCall;
  await scenario([{ kind: "wait", milliseconds: 0 }], {
    deadline: deadline.signal,
    invoke: async (request, signal) => {
      deadline.abort("deadline"); // the deadline passes while the helper is working
      abortedDuringCall = signal.aborted;
      return { ok: true, result: snapshot() };
    },
  });

  assert.equal(abortedDuringCall, true);
});

test("a helper call stopped by the caller marks the step cancelled with REA's message", async () => {
  const caller = new AbortController();
  let calls = 0;
  const outcome = await scenario([{ kind: "click", path: [0] }], {
    signal: caller.signal,
    invoke: async () => {
      calls += 1;
      if (calls === 1) return { ok: true, result: snapshot() };
      caller.abort("caller stopped");
      throw Object.assign(new Error("The operation was aborted"), { name: "AbortError" });
    },
  });

  assert.deepEqual(
    [outcome.partial.steps[0].outcome, outcome.partial.steps[0].reason],
    ["cancelled", "Analysis operation was cancelled: capture_native_ui_scenario"],
  );
});

test("a capture that is not a valid snapshot fails the step instead of breaking the report", async () => {
  const broken = snapshot({ screenshot: { mime_type: "image/png", base64: "AAAA", sha256: "0".repeat(64), width: 1, height: 1 } });
  const outcome = await scenario([{ kind: "wait", milliseconds: 0 }], {
    invoke: fakeHelper({ ok: true, result: snapshot() }, { ok: true, result: broken }).invoke,
  });

  assert.deepEqual([outcome.error.kind, outcome.partial.steps[0].outcome], ["capability", "failed"]);
});

test("a deadline reached during the last capture still fails the scenario, keeping all steps", async () => {
  const deadline = new AbortController();
  let calls = 0;
  const outcome = await scenario([{ kind: "wait", milliseconds: 0 }], {
    deadline: deadline.signal,
    invoke: async () => {
      calls += 1;
      if (calls === 2) deadline.abort("deadline");
      return { ok: true, result: snapshot() };
    },
  });

  assert.deepEqual(
    [outcome.ok, outcome.error.kind, outcome.partial.steps[0].outcome],
    [false, "timeout", "completed"],
  );
});

test("whichever interruption came first is the one reported", async () => {
  const caller = new AbortController();
  const deadline = new AbortController();
  const outcome = await scenario([{ kind: "click", path: [0] }], {
    signal: caller.signal,
    deadline: deadline.signal,
    invoke: async () => {
      deadline.abort("deadline");
      caller.abort("caller");
      return { ok: true, result: snapshot() };
    },
  });

  assert.equal(outcome.error.kind, "timeout");
});