// Photoshop harness results (results.jsonl rows) as REA Evidence, made with REA's own
// createEvidence and bundle code, each linked to the parity observation (observe_native_ui
// Evidence) of the Photoshop process it ran in. The harness reaches what UI Automation cannot:
// Photoshop shows UI Automation only its window chrome (design doc section 8).
import { createEvidence } from "rea-agents/dist/domain/evidence.js";

import { evidenceBundleText } from "./evidence.js";

export const HARNESS_PROVIDER = Object.freeze({
  id: "adobe-observed-truth",
  name: "Adobe observed-truth harness",
  version: "0.2.0",
});

const COMMON_LIMITATIONS = [
  "One controlled replay on one Windows workstation (Photoshop 2026 preferences factory-reset on 2026-11-09). Results are what Photoshop reported through scripting or what was captured on screen; no dialog, history state or pixel change observed does not prove the command has no effect.",
  "Document, history, panel and tool state is read through Photoshop's ExtendScript (COM DoJavaScript). Dialogs that opened were captured with PrintWindow and cancelled (Cancel button, WM_CLOSE or Escape, by dialog kind) unless the spec accepted them at their default settings.",
  "Linked to the observe_native_ui Evidence of the same Photoshop process (taken when the harness connected). An unlinked result was recorded before results named their process, or its observation is not in this bundle.",
];

const METHOD = {
  menu: "Menu commands are run by number through Photoshop's UXP core.performMenuCommand, from a developer plug-in the harness loaded; menu commands Photoshop greys out are reported as refused.",
  tool: "Tools are selected by ExtendScript action (select tool by its id), not by clicking the toolbar.",
  panel: "Panels are shown by the Window menu command that shows them, then hidden again.",
  sweep:
    "Setting sweeps replay the command by ExtendScript executeAction with no dialog: every setting recorded at its defaults, one changed (the same key its dialog control sets). Proof the value was applied is the result's exact pixel hash (pixels.after_sha256) differing from the default replay's; the descriptor Photoshop returns (sweep.used) is not proof, as some plug-ins (Unsharp Mask) return their defaults while applying the value. The default replay runs three times; equal hashes show the command is deterministic on this chart.",
  shortcut: "Shortcuts are pressed as synthesized keyboard input (SendInput) to the focused Photoshop window; chords another program owns system-wide are refused, not pressed.",
};

/** One results.jsonl row as REA Evidence. `row.parity` names its process's observation
 * (`{evidence_id}`) or carries REA's projected error from taking it (`{error}`). */
export function harnessEvidence(target, row, { link = true } = {}) {
  const kind = row.item_id.split(":", 1)[0];
  const parityId = row.parity?.evidence_id;
  return createEvidence(target, HARNESS_PROVIDER, {
    operation: `photoshop_${kind}`,
    parameters: { item_id: row.item_id },
    result: {
      status: row.status,
      observations: row.observations,
      error: row.error,
      cleanup_errors: row.cleanup_errors,
      at: row.at,
      parity: row.parity ?? null,
    },
    authority: "controlled-replay",
    // The workstation the replay ran on, unisolated (Photoshop runs on the person's desktop).
    environment: { id: "windows-workstation", platform: "win32", architecture: target.architecture, isolation: "none" },
    limitations: [...(METHOD[kind] ? [METHOD[kind]] : []), ...COMMON_LIMITATIONS],
    evidenceLinks: link && parityId !== undefined ? [parityId] : [],
  });
}

const CONTROL_METHOD =
  "Controls inside Photoshop's dialogs are drawn by Photoshop, so UI Automation (REA observe_native_ui) sees none of them; the harness works from the dialog's pixels instead. Focusable controls are found by walking the dialog with Tab and named by how they answer keys (Up, Alt+Down, a typed digit, Space); controls Tab cannot reach are placed through the catalogue (dialog-controls.jsonl) as the drawn thing of the right shape nearest their label as OCR reads it, and driven by mouse. Input is synthesized (SendInput) only while the person is away. An action's `changed` means the dialog's pixels changed (a blinking caret masked); OK, Cancel and buttons whose effect outlives Cancel are never pressed, and the dialog is cancelled afterwards, so no setting is kept. Text read off the dialog is published only as its length and SHA-256.";

const CODE_METHOD =
  "`code` is where the control's code is in the decompiled binaries (control-code.jsonl, from scripts/adobe_observed_truth/control_code.py): the binary (its path in the app's install folder) is the filter plug-in that adds the dialog's menu item, or the app itself; `via` setting means the functions compare a descriptor key against the four-letter code of the plug-in's setting of the same name, `via` ui_string that they carry the interface string literal whose key is `anchor` and whose text is the label, `via` ui_string_data that the binary keeps that string only in its data (a layout description or resource), so no function is named: look for references to the key; `via` sampled or runtime (or both, sampled+runtime) that no name placed the control and it was seen live while the harness drove the dialog: sampled, the app's interface thread was suspended from outside hundreds of times a second and its stack read for the decompiled functions it returned into (scripts/adobe_observed_truth/stack_sampler.py); runtime, the decomp callees of what sampling caught were hooked by REA's Frida session while the dialog was driven again. The functions are those seen only while this control was driven (never while the dialog sat idle, never for another control), and `anchor` names the sample file's digest or the Frida observation (runtime-discovery.jsonl). Sampling misses functions quicker than its interval; the hooks catch those the decomp says the caught ones call. A place to read, matched by name, not proof the function handles this control; `waiting` means the binary is still being decompiled.";

const RUNTIME_METHOD =
  "`runtime` is what REA saw the control's mapped functions do in the running app (runtime-links-pilot.jsonl; scripts/adobe_observed_truth/runtime_links.py): REA's Frida session hooked them at their offsets in the loaded module while the harness drove every control of the dialog, and across the filter's life cycle (dialog open, cancel, and a scripted apply changing one setting at a time). Level `filter`: they ran once per run of the filter, reading or writing its settings, and never while a control was driven, so they hold this control's setting but do not handle the control live. Level `control`: one fired while a control was driven. Level `not seen`: hooked, never fired. `frida_evidence` names the REA Frida observation; phases are the harness's labels for the windows the calls fell in.";

/** One control-actions.jsonl row (a control driven or read inside a dialog) as REA Evidence,
 * linked like a results row; `code` is its control-code.jsonl record, if any. */
export function controlEvidence(target, row, { link = true, code = null } = {}) {
  const parityId = row.parity?.evidence_id;
  const { item_id, dialog, kind, rect, label, source, at, parity, ...outcome } = row;
  const where = code && {
    status: code.status, binary: code.binary, via: code.via, anchor: code.anchor, functions: code.functions,
    ...(code.runtime ? { runtime: code.runtime } : {}),
  };
  return createEvidence(target, HARNESS_PROVIDER, {
    operation: "photoshop_control",
    parameters: { item_id, dialog, kind, rect: rect ?? null, label: label ?? null, source },
    result: { ...outcome, at, parity: parity ?? null, code: where ?? null },
    authority: "controlled-replay",
    environment: { id: "windows-workstation", platform: "win32", architecture: target.architecture, isolation: "none" },
    limitations: [CONTROL_METHOD, ...(where ? [CODE_METHOD] : []), ...(where?.runtime ? [RUNTIME_METHOD] : []), ...COMMON_LIMITATIONS],
    evidenceLinks: link && parityId !== undefined ? [parityId] : [],
  });
}

/** The observations, every result row's Evidence and every control row's Evidence as one REA
 * bundle; a row links only to an observation the bundle carries. Evidence IDs are content
 * digests, so an unchanged window observed twice, or an identical result, is one record (REA
 * refuses duplicate IDs). `linked`/`unlinked` count rows of both kinds. `code` (control-code.jsonl
 * records) says where each control's code is, matched by dialog and label. */
export function linkedBundle({ target, rows, observations, controls = [], code = [] }) {
  const carried = new Set(observations.map((o) => o.evidence_id));
  const codeOf = new Map(code.map((c) => [`${c.dialog}\u0000${c.label}`, c]));
  let linked = 0;
  const evidence = (make) => (row) => {
    const link = carried.has(row.parity?.evidence_id);
    if (link) linked += 1;
    return make(target, row, { link, code: codeOf.get(`${row.dialog}\u0000${row.label}`) ?? null });
  };
  const records = [...rows.map(evidence(harnessEvidence)), ...controls.map(evidence(controlEvidence))];
  rows = [...rows, ...controls];
  const all = [...new Map([...observations, ...records].map((r) => [r.evidence_id, r])).values()];
  return { text: evidenceBundleText(all), records: all, linked, unlinked: rows.length - linked };
}
