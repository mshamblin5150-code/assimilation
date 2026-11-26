// Seams 2 and 4: Evidence and bundles are produced and checked by REA 6.8.0's own code, so
// REA's import accepts them exactly as it accepts its macOS observations.
import assert from "node:assert/strict";
import { test } from "node:test";

import { parseEvidence } from "rea-agents/dist/domain/evidence.js";
import { parseEvidenceBundle } from "rea-agents/dist/domain/evidenceBundle.js";

import { evidenceBundleText, observationEvidence } from "../src/evidence.js";
import { runScenario } from "../src/scenario.js";

const TARGET = {
  path: "C:\\Program Files\\Adobe\\Adobe Photoshop 2026\\Photoshop.exe",
  sha256: "a".repeat(64),
  format: "pe",
  architecture: "x86_64",
};
const SNAPSHOT = {
  window: { pid: 4242, window_id: 77, executable: TARGET.path, launch_time: 1762700000.5, title: "Untitled" },
  nodes: [{ path: [], role: "Window", title: "Untitled", value: null, actions: [], children_count: 0 }],
  truncated: false,
  screenshot: null,
  gaps: [],
};

const observe = async () => {
  const parameters = { pid: 4242, window_id: 77 };
  const outcome = await runScenario({
    operation: "observe_native_ui",
    parameters,
    target: TARGET,
    invoke: async () => ({ ok: true, result: SNAPSHOT }),
  });
  return observationEvidence({ target: TARGET, operation: "observe_native_ui", parameters, report: outcome.report });
};

test("the Evidence passes REA's own schema and identity check", async () => {
  const evidence = await observe();

  assert.equal(parseEvidence(evidence).evidence_id, evidence.evidence_id);
});

test("the Evidence has the shape REA gives its macOS observations, with the Windows provider", async () => {
  const evidence = await observe();

  assert.deepEqual(
    {
      predicate: evidence.predicate_type,
      operation: evidence.operation,
      provider: evidence.provider.id,
      confidence: evidence.confidence,
      authority: evidence.authority,
      subject: [evidence.subject.digest.sha256, evidence.subject.format],
      environment: evidence.environment,
      locations: evidence.locations,
    },
    {
      predicate: "rea.analysis",
      operation: "observe_native_ui",
      provider: "native-windows",
      confidence: "observed",
      authority: "shipped-artifact",
      subject: [TARGET.sha256, "pe"],
      environment: null,
      locations: [],
    },
  );
});

test("an exported bundle is canonical and parses with REA's own bundle check", async () => {
  const text = evidenceBundleText([await observe()]);

  assert.equal(parseEvidenceBundle(JSON.parse(text)).records.length, 1);
});
