// The commands the Python harness runs (scripts/adobe_observed_truth/parity.py):
//   node src/cli.js observe --exe <Photoshop.exe> --pid <n> --window <hwnd> --evidence <observations.jsonl>
//     One observe_native_ui through the server's own tool handlers; its Evidence is appended to
//     the observations file and stdout is one JSON line: {evidence_id, pid, window_id, launch_time}
//     or {error: <REA's projected error, remediation included>}. Exit 0 either way.
//   node src/cli.js bundle --exe <Photoshop.exe> --results <results.jsonl> --observations <observations.jsonl>
//                          [--controls <control-actions.jsonl>] [--code <control-code.jsonl>] --out <bundle.json>
//     The observations, every result and every control driven as one linked REA bundle for
//     import_evidence_bundle; with --code each control carries where its code is.
import { appendFile, readFile, writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import { parseArgs } from "node:util";

import { parseEvidence } from "rea-agents/dist/domain/evidence.js";

import { linkedBundle } from "./harness.js";
import { createTools } from "./server.js";
import { openTarget } from "./target.js";

/** One parity observation of the harness's Photoshop process: `{parity, evidence}`, where
 * `parity` is what each result row records and `evidence` is null when it failed. */
export async function observeForHarness({ exe, pid, window }, tools = createTools()) {
  const opened = await tools.open_binary({ path: exe });
  if (opened.isError) return { parity: { error: opened.structuredContent }, evidence: null };
  try {
    const observed = await tools.observe_native_ui({ pid, window_id: window });
    if (observed.isError) return { parity: { error: observed.structuredContent }, evidence: null };
    const evidence = observed.structuredContent;
    const seen = evidence.normalized_result.initial.window;
    return {
      parity: { evidence_id: evidence.evidence_id, pid: seen.pid, window_id: seen.window_id, launch_time: seen.launch_time },
      evidence,
    };
  } finally {
    await tools.close_binary({});
  }
}

const jsonLines = (text) =>
  text
    .split(/\r?\n/)
    .filter((line) => line.trim() !== "")
    .flatMap((line) => {
      try {
        return [JSON.parse(line)];
      } catch {
        return []; // a line cut short when a writer stopped mid-write
      }
    });

async function main(argv) {
  const [command, ...rest] = argv;
  const { values } = parseArgs({
    args: rest,
    options: {
      exe: { type: "string" },
      pid: { type: "string" },
      window: { type: "string" },
      evidence: { type: "string" },
      results: { type: "string" },
      observations: { type: "string" },
      controls: { type: "string" },
      code: { type: "string" },
      out: { type: "string" },
    },
  });
  if (command === "observe") {
    const outcome = await observeForHarness({ exe: values.exe, pid: Number(values.pid), window: Number(values.window) });
    if (outcome.evidence !== null) await appendFile(values.evidence, `${JSON.stringify(outcome.evidence)}\n`, "utf8");
    process.stdout.write(`${JSON.stringify(outcome.parity)}\n`);
    return;
  }
  if (command === "bundle") {
    const target = await openTarget(values.exe);
    const rows = jsonLines(await readFile(values.results, "utf8"));
    const observations = jsonLines(await readFile(values.observations, "utf8").catch(() => "")).map(parseEvidence);
    const controls = values.controls ? jsonLines(await readFile(values.controls, "utf8")) : [];
    const code = values.code ? jsonLines(await readFile(values.code, "utf8")) : [];
    const bundle = linkedBundle({ target, rows, observations, controls, code });
    await writeFile(values.out, bundle.text, "utf8");
    process.stdout.write(`${JSON.stringify({ records: bundle.records.length, linked: bundle.linked, unlinked: bundle.unlinked })}\n`);
    return;
  }
  process.stderr.write("usage: cli.js observe|bundle ... (see the header of src/cli.js)\n");
  process.exitCode = 2;
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) await main(process.argv.slice(2));
