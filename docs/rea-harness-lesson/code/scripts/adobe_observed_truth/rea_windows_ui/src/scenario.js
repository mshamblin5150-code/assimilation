// Scenario sequencing for observe_native_ui and capture_native_ui_scenario on Windows.
// Mirrors rea-agents 6.8.0 dist/native/NativeUiObservation.js (observeWithHelper) and
// NativeUiInterruptionControl.js. Schemas, the output budget and error classes (so their
// messages, used as step reasons) are REA's own.
import {
  AnalysisCancelledError,
  AnalysisCapabilityUnavailableError,
  AnalysisInputError,
  AnalysisTimeoutError,
} from "rea-agents/dist/domain/analysisErrorCore.js";
import {
  DEFAULT_NATIVE_UI_DEADLINE_MS,
  nativeDeadlineRecovery,
} from "rea-agents/dist/domain/native/nativeDeadlines.js";
import { ProviderAdapterError } from "rea-agents/dist/domain/providerAdapterError.js";
import {
  nativeUiObservationInputSchema,
  nativeUiResultSchema,
  nativeUiScenarioInputSchema,
  nativeUiSnapshotSchema,
} from "rea-agents/dist/domain/native/nativeUiObservation.js";
import {
  NATIVE_UI_OUTPUT_BUDGET_BYTES,
  NATIVE_UI_OUTPUT_WEIGHT,
} from "rea-agents/dist/native/NativeUiOutputBudget.js";
import { z } from "zod";

export const PROVIDER_ID = "native-windows";

const passiveInputSchema = nativeUiObservationInputSchema.transform((input) => ({
  ...input,
  steps: [],
}));

/** Every helper response is checked like REA checks the Swift helper's. */
const responseSchema = z.discriminatedUnion("ok", [
  z.strictObject({ ok: z.literal(true), result: nativeUiSnapshotSchema }),
  z.strictObject({ ok: z.literal(false), code: z.string(), message: z.string() }),
]);

/** Selection failures on the first capture are the caller's input, as on macOS. */
const INITIAL_SELECTION_FIELDS = {
  "pid-not-application": "pid",
  "target-mismatch": "pid",
  "window-mismatch": "window_id",
  "ambiguous-window": "window_id",
};

/**
 * Run one observation or scenario through `invoke(request, signal)`, the helper seam: one
 * request in, `{ok: true, result: snapshot}` or `{ok: false, code, message}` out; the signal
 * aborts when the caller cancels or the deadline passes.
 * Returns `{ok: true, report}` or `{ok: false, error, partial?}`; `error.kind` is one of input,
 * capability, cancelled, timeout, and `error.message` is REA's message for that error.
 */
export async function runScenario({
  operation,
  parameters,
  target,
  invoke,
  signal,
  deadline,
  sleep = abortableSleep,
  outputBudgetBytes = NATIVE_UI_OUTPUT_BUDGET_BYTES,
}) {
  const fromRea = (kind, rea, extra = {}) => ({ ok: false, error: { kind, message: rea.message, rea, ...extra } });
  const unavailable = (reason, extra = {}, options) =>
    fromRea("capability", new AnalysisCapabilityUnavailableError(PROVIDER_ID, operation, reason, options), extra);
  const parsed = (
    operation === "observe_native_ui" ? passiveInputSchema : nativeUiScenarioInputSchema
  ).safeParse(parameters);
  if (!parsed.success) return fromRea("input", new AnalysisInputError(operation, { cause: parsed.error }));
  if (target.format !== "pe")
    return unavailable("Native UI observation requires an active Windows (PE) executable target");
  const input = parsed.data;
  if (!input.screenshot && !input.accessibility)
    return fromRea("input", new AnalysisInputError(operation, { cause: new Error("Enable screenshot or accessibility capture") }));

  const deadlineMs = input.native_ui_deadline_ms ?? DEFAULT_NATIVE_UI_DEADLINE_MS;
  const interruption = new Interruption(signal, deadline ?? AbortSignal.timeout(deadlineMs));
  const interrupted = () => {
    if (interruption.kind === "cancelled") return fromRea("cancelled", new AnalysisCancelledError(operation)).error;
    if (interruption.kind === "timeout")
      return fromRea(
        "timeout",
        new AnalysisTimeoutError(operation, deadlineMs, {
          ...nativeDeadlineRecovery({
            timeoutMs: deadlineMs,
            setting: "native_ui_deadline_ms",
            cliFlag: "--native-ui-deadline-ms",
            defaultMs: DEFAULT_NATIVE_UI_DEADLINE_MS,
            phase: "native UI observation deadline",
            detail: " A partial observation may already be retained.",
            unchanged: "The 67108864-byte scenario output allowance and the 180000 ms cap on one wait step have no runtime override.",
          }),
        }),
      ).error;
    return undefined;
  };

  let launchTime;
  let outputBytes = 0;
  const take = async (action) => {
    const stopped = interrupted();
    if (stopped) return { ok: false, error: stopped };
    let raw;
    try {
      raw = await invoke(
        {
          pid: input.pid,
          window_id: input.window_id,
          executable: target.path,
          sha256: target.sha256,
          ...(launchTime === undefined ? {} : { launch_time: launchTime }),
          screenshot: input.screenshot,
          accessibility: input.accessibility,
          max_nodes: input.max_nodes,
          ...(action === undefined ? {} : { action }),
        },
        interruption.signal,
      );
    } catch (cause) {
      const stoppedNow = interrupted();
      if (stoppedNow) return { ok: false, error: stoppedNow };
      if (cause?.code === "ETIMEDOUT") {
        interruption.interrupt("timeout");
        return { ok: false, error: interrupted() };
      }
      return fromRea(
        "capability",
        new ProviderAdapterError(PROVIDER_ID, operation, {
          cause,
          diagnostics: {
            reason: cause instanceof Error ? cause.message : String(cause),
            remediation:
              "Native helper failed, timed out, or returned malformed capture data; build helper/ReaWindowsUi (dotnet build -c Release) and check UI Automation access to the target",
          },
        }),
        { code: "helper-failed" },
      );
    }
    const response = responseSchema.safeParse(raw);
    if (!response.success)
      return fromRea(
        "capability",
        new ProviderAdapterError(PROVIDER_ID, operation, {
          cause: response.error,
          diagnostics: {
            reason: "Native helper returned malformed capture data",
            remediation: "Rebuild helper/ReaWindowsUi so its output matches REA's native UI snapshot schema",
          },
        }),
        { code: "helper-malformed" },
      );
    const answer = response.data;
    if (!answer.ok) {
      const field = INITIAL_SELECTION_FIELDS[answer.code];
      if (launchTime === undefined && field !== undefined)
        return fromRea(
          "input",
          new AnalysisInputError(operation, { userMessage: answer.message }, [
            { path: [field], reason: "invalid_value", message: `${answer.code}: ${answer.message}` },
          ]),
          { field, code: answer.code },
        );
      return unavailable(`${answer.code}: ${answer.message}`, { code: answer.code }, { userMessage: answer.message });
    }
    const { window } = answer.result;
    if (
      window.pid !== input.pid ||
      window.window_id !== input.window_id ||
      window.executable !== target.path ||
      (launchTime !== undefined && window.launch_time !== launchTime)
    )
      return unavailable("Native helper returned a different target process or window", { code: "target-changed" });
    launchTime = window.launch_time;
    outputBytes += NATIVE_UI_OUTPUT_WEIGHT * Buffer.byteLength(JSON.stringify(answer.result));
    if (outputBytes > outputBudgetBytes)
      return unavailable(
        `Scenario captures exceeded the fixed 64 MiB output budget (${outputBudgetBytes} bytes). This release has no runtime override. native_ui_deadline_ms does not raise it.`,
        { code: "output-budget" },
        {
          userMessage: `Scenario captures exceeded the fixed 64 MiB output budget (${outputBudgetBytes} bytes). This release has no runtime override.`,
          remediationAction: `The scenario output allowance is ${outputBudgetBytes} bytes. This release has no runtime override. Waiting, additional host memory, and native_ui_deadline_ms do not raise it. Repeating the unchanged request fails the same way.`,
        },
      );
    return { ok: true, value: answer.result };
  };
  const report = (initial, steps) =>
    nativeUiResultSchema.parse({
      target_sha256: target.sha256,
      initial,
      steps,
      restore: "leave-as-is",
      limitations: limitations(deadlineMs),
    });

  try {
    const initial = await take();
    if (!initial.ok) return initial;
    const steps = [];
    let before = initial.value;
    for (const [index, step] of input.steps.entries()) {
      if (step.kind === "wait") await sleep(step.milliseconds, interruption.signal);
      const after = await take(step.kind === "wait" ? undefined : step);
      if (!after.ok) {
        steps.push({
          index,
          kind: step.kind,
          before,
          after: null,
          outcome: after.error.kind === "cancelled" ? "cancelled" : "failed",
          reason: after.error.message,
        });
        return { ok: false, error: after.error, partial: report(initial.value, steps) };
      }
      steps.push({ index, kind: step.kind, before, after: after.value, outcome: "completed", reason: null });
      before = after.value;
    }
    const finished = report(initial.value, steps);
    // As REA's finishNativeUiObservation: an interruption seen at the end still wins.
    const late = interrupted();
    return late ? { ok: false, error: late, partial: finished } : { ok: true, report: finished };
  } finally {
    interruption.dispose();
  }
}

/** Caller cancellation or the deadline, whichever came first (NativeUiInterruptionControl). */
class Interruption {
  #controller = new AbortController();
  #listeners = [];
  kind;
  signal = this.#controller.signal;

  constructor(caller, deadline) {
    if (caller?.aborted) this.interrupt("cancelled");
    else if (deadline.aborted) this.interrupt("timeout");
    else {
      this.#watch(caller, "cancelled");
      this.#watch(deadline, "timeout");
    }
  }

  interrupt(kind) {
    if (this.kind !== undefined) return;
    this.kind = kind;
    this.#controller.abort(kind);
  }

  dispose() {
    for (const [source, listener] of this.#listeners) source.removeEventListener("abort", listener);
  }

  #watch(source, kind) {
    if (!source) return;
    const listener = () => this.interrupt(kind);
    source.addEventListener("abort", listener, { once: true });
    this.#listeners.push([source, listener]);
  }
}

function abortableSleep(ms, signal) {
  return new Promise((resolve) => {
    if (signal?.aborted) return resolve();
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => (clearTimeout(timer), resolve()), { once: true });
  });
}

/** The macOS limitations (NativeUiObservation.js), stated for the Windows methods. */
function limitations(deadlineMs) {
  return [
    "Only the explicitly selected already-running process/window is admitted. No target process is started, and permissions, foreground applications and application data are not changed or restored.",
    "Accessibility is read through Microsoft UI Automation (control view); roles and actions are UI Automation names (control types and patterns), not macOS AX names. Click uses the Invoke pattern; scroll uses RangeValue small-change increment/decrement; key-entry uses the Value pattern's SetValue. Unsupported elements fail; there is no synthesized global input fallback.",
    "Each completed action is followed immediately by capture; delayed UI changes require explicit wait steps. A failed after-capture can follow a completed action, so failure does not prove absence of application effects.",
    "Scenarios can change app data, cause app network activity and persist changes. The caller explicitly chooses leave-as-is; automatic restoration is unsupported.",
    `Window matching uses the exact process ID and top-level window handle; the UI Automation element is taken from that handle. Accessibility paths can change as the UI changes; stale paths fail. Screenshots are scaled to at most 2048 pixels; scenario output is budgeted at 64 MiB. Execution uses the selected native_ui_deadline_ms of ${deadlineMs} ms (omitted means ${DEFAULT_NATIVE_UI_DEADLINE_MS}). One wait step stays capped at 180000 ms.`,
  ];
}
