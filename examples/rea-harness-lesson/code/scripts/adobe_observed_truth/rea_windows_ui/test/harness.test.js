// Harness results as REA Evidence, linked to the parity observation of the same Photoshop process.
import assert from "node:assert/strict";
import { test } from "node:test";

import { parseEvidence } from "rea-agents/dist/domain/evidence.js";
import { parseEvidenceBundle } from "rea-agents/dist/domain/evidenceBundle.js";

import { observationEvidence } from "../src/evidence.js";
import { controlEvidence, harnessEvidence, linkedBundle } from "../src/harness.js";

const TARGET = { path: "C:\\Apps\\Photoshop.exe", sha256: "c".repeat(64), format: "pe", architecture: "x86_64" };
const window = { pid: 900, window_id: 55, executable: TARGET.path, launch_time: 1762700000.25, title: "Adobe Photoshop 2026" };
const OBSERVATION = observationEvidence({
  target: TARGET,
  operation: "observe_native_ui",
  parameters: { pid: 900, window_id: 55 },
  report: {
    target_sha256: TARGET.sha256,
    initial: { window, nodes: [], truncated: false, screenshot: null, gaps: [] },
    steps: [],
    restore: "leave-as-is",
    limitations: ["fixture"],
  },
});
const row = (extra = {}) => ({
  item_id: "menu:2993",
  status: "ok",
  observations: { dialogs: [], history: { count: 3, last: ["New", "Rotate Canvas"] } },
  error: null,
  cleanup_errors: [],
  at: "2026-11-09T12:18:45",
  ...extra,
});

test("a harness result is REA Evidence from the harness, a controlled replay, linked to its parity observation", () => {
  const evidence = parseEvidence(
    harnessEvidence(TARGET, row({ parity: { evidence_id: OBSERVATION.evidence_id } })),
  );

  assert.deepEqual(
    [evidence.provider.id, evidence.authority, evidence.operation, evidence.parameters, evidence.evidence_links],
    ["adobe-observed-truth", "controlled-replay", "photoshop_menu", { item_id: "menu:2993" }, [OBSERVATION.evidence_id]],
  );
});

test("a setting sweep says the pixels, not Photoshop's reply, prove the value was applied", () => {
  const evidence = harnessEvidence(TARGET, row({ item_id: "sweep:unsharpMask:radius=2.0" }));

  assert.equal(evidence.operation, "photoshop_sweep");
  assert.match(evidence.limitations[0], /after_sha256/);
});

test("a harness result states the environment it was replayed in, so REA can qualify it for an unknown", () => {
  const { environment } = harnessEvidence(TARGET, row());

  assert.deepEqual([environment.platform, environment.isolation], ["win32", "none"]);
});

test("a bundle holds the parity observations and the harness Evidence, links only to observations it carries", () => {
  const rows = [
    row({ parity: { evidence_id: OBSERVATION.evidence_id } }),
    row({ item_id: "tool:paintbrushTool" }), // recorded before results named their process
    row({ item_id: "panel:x", parity: { evidence_id: `ev_${"d".repeat(64)}` } }), // observation lost
  ];

  const bundle = linkedBundle({ target: TARGET, rows, observations: [OBSERVATION] });

  const records = parseEvidenceBundle(JSON.parse(bundle.text)).records;
  assert.deepEqual(
    [records.length, bundle.linked, bundle.unlinked, records.filter((r) => r.evidence_links.length).length],
    [4, 1, 2, 1],
  );
});

test("the same observation or result seen twice is carried once, as REA refuses duplicate records", () => {
  const linkedRow = row({ parity: { evidence_id: OBSERVATION.evidence_id } });

  const bundle = linkedBundle({ target: TARGET, rows: [linkedRow, linkedRow], observations: [OBSERVATION, OBSERVATION] });

  assert.equal(parseEvidenceBundle(JSON.parse(bundle.text)).records.length, 2);
});

test("a parity observation that failed is kept in the harness Evidence with REA's remediation", () => {
  const parity = {
    error: {
      code: "capability_unavailable",
      message: "native-windows cannot observe_native_ui: accessibility-denied",
      remediation: { action: "Run the harness at the same integrity level as Photoshop, then retry." },
    },
  };

  const evidence = harnessEvidence(TARGET, row({ parity }));

  assert.deepEqual(
    [evidence.evidence_links, evidence.normalized_result.parity.error.remediation.action],
    [[], "Run the harness at the same integrity level as Photoshop, then retry."],
  );
});

const control = (extra = {}) => ({
  item_id: "menu:1170@controls",
  at: "2026-11-10T09:00:00",
  parity: { evidence_id: OBSERVATION.evidence_id },
  dialog: "Filter > Blur > Motion Blur",
  kind: "angle_dial",
  rect: [170, 110, 200, 140],
  label: "Angle",
  source: "catalogue label",
  placed: true,
  actions: [{ keys: ["drag 185,125->195,135"], changed: true, change: [150, 40, 260, 140], opened_popup: false }],
  ...extra,
});

test("a control the harness drove inside a self-drawn dialog is REA Evidence of that control, linked to its parity observation", () => {
  const evidence = parseEvidence(controlEvidence(TARGET, control()));

  assert.deepEqual(
    [evidence.operation, evidence.parameters, evidence.normalized_result.actions[0].changed, evidence.evidence_links],
    [
      "photoshop_control",
      { item_id: "menu:1170@controls", dialog: "Filter > Blur > Motion Blur", kind: "angle_dial", rect: [170, 110, 200, 140], label: "Angle", source: "catalogue label" },
      true,
      [OBSERVATION.evidence_id],
    ],
  );
  assert.match(evidence.limitations[0], /UI Automation/);
});

test("a control carries where its code is in the decompiled binaries, so REA can open it there", () => {
  const code = {
    dialog: "Filter > Blur > Motion Blur",
    label: "Angle",
    status: "found",
    binary: "Required\\Plug-ins\\Filters\\Standard MultiPlugin.8bf",
    via: "setting",
    anchor: "Angl",
    functions: ["0x180010", "0x180020"],
  };
  const bundle = linkedBundle({
    target: TARGET,
    rows: [],
    controls: [control(), control({ label: "Distance", rect: [1, 2, 3, 4] })],
    observations: [OBSERVATION],
    code: [code],
  });

  const controls = parseEvidenceBundle(JSON.parse(bundle.text)).records.filter((r) => r.operation === "photoshop_control");
  const byLabel = Object.fromEntries(controls.map((r) => [r.parameters.label, r.normalized_result.code]));
  assert.deepEqual(byLabel, {
    Angle: { status: "found", binary: code.binary, via: "setting", anchor: "Angl", functions: ["0x180010", "0x180020"] },
    Distance: null,
  });
});

test("a control's code link carries what REA saw its functions do live, and says what that level means", () => {
  const runtime = {
    level: "filter",
    functions: [{ function: "0x180010", phases: ["lifecycle open dialog"], calls: 3, fired_while_controls_driven: 0, frida_evidence: "ev_frida" }],
  };
  const code = { dialog: "Filter > Blur > Motion Blur", label: "Angle", status: "found", binary: "x.8bf", via: "setting", anchor: "Angl", functions: ["0x180010"], runtime };

  const evidence = parseEvidence(controlEvidence(TARGET, control(), { code }));

  assert.deepEqual(evidence.normalized_result.code.runtime, runtime);
  assert.ok(evidence.limitations.some((l) => /`runtime`.*level `filter`/is.test(l)));
});

test("a bundle carries the controls driven beside the results, each linked to an observation it carries", () => {
  const bundle = linkedBundle({
    target: TARGET,
    rows: [row({ parity: { evidence_id: OBSERVATION.evidence_id } })],
    controls: [control(), control({ kind: "slider", rect: [1, 2, 3, 4], parity: undefined })],
    observations: [OBSERVATION],
  });

  const records = parseEvidenceBundle(JSON.parse(bundle.text)).records;
  assert.deepEqual(
    [records.map((r) => r.operation).sort(), bundle.linked, bundle.unlinked],
    [["observe_native_ui", "photoshop_control", "photoshop_control", "photoshop_menu"], 2, 1],
  );
});
