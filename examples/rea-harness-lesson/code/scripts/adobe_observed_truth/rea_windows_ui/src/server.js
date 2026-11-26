// Local MCP server: REA's macOS observe_native_ui and capture_native_ui_scenario with 1:1 parity
// on Windows (the REA harness lesson's guide, 04-guide.md).
//   node src/server.js        (stdio)
import { writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

import { McpServer } from "@modelcontextprotocol/server";
import { serveStdio } from "@modelcontextprotocol/server/stdio";
import { z } from "zod";

import {
  AnalysisCapabilityUnavailableError,
  AnalysisUnsupportedTargetError,
} from "rea-agents/dist/domain/analysisErrorCore.js";
import { projectAnalysisError } from "rea-agents/dist/domain/analysisErrorProjection.js";
import { DEFAULT_NATIVE_UI_DEADLINE_MS } from "rea-agents/dist/domain/native/nativeDeadlines.js";
import {
  nativeUiObservationInputSchema,
  nativeUiScenarioInputSchema,
} from "rea-agents/dist/domain/native/nativeUiObservation.js";

import { evidenceBundleText, observationEvidence } from "./evidence.js";
import { invokeHelper } from "./helper.js";
import { PROVIDER_ID, runScenario } from "./scenario.js";
import { openTarget as openPeTarget } from "./target.js";

const success = (value) => ({ content: [{ type: "text", text: JSON.stringify(value) }], structuredContent: value });
const failure = (error) => ({ content: [{ type: "text", text: JSON.stringify(error) }], structuredContent: error, isError: true });

/** A tool failure exactly as REA projects its own errors: code, category, message, retryable,
 * remediation, recovery and details, the partial observation retained inside the error. */
const toolError = ({ error, partial }) => {
  if (partial !== undefined) error.rea.retainPartialObservation(partial);
  return projectAnalysisError(error.rea);
};

/**
 * The tool handlers, `(arguments, context) => result`: one active target, its Evidence, and
 * one operation at a time (as REA serializes native UI work), opening and closing included.
 */
export function createTools({ invoke = invokeHelper, openTarget = openPeTarget } = {}) {
  let target;
  const records = [];
  let tail = Promise.resolve();
  const serialized = (work) => {
    const call = tail.then(work, work);
    tail = call.then(
      () => undefined,
      () => undefined,
    );
    return call;
  };

  const observation = (operation) => (parameters, context) =>
    serialized(async () => {
      const bound = target; // fixed for the whole operation
      if (bound === undefined)
        return failure(
          projectAnalysisError(
            new AnalysisCapabilityUnavailableError(PROVIDER_ID, operation, "No active target is open", {
              userMessage: `${operation} requires an active Windows executable target.`,
              remediationAction: "Call open_binary with the target executable path, then retry.",
            }),
          ),
        );
      const signal = context?.mcpReq?.signal;
      const timeoutMs = parameters?.native_ui_deadline_ms ?? DEFAULT_NATIVE_UI_DEADLINE_MS;
      const outcome = await runScenario({
        operation,
        parameters,
        target: bound,
        invoke: (request, helperSignal) => invoke(request, { signal: helperSignal, timeoutMs }),
        signal,
      });
      if (!outcome.ok) return failure(toolError(outcome));
      const evidence = observationEvidence({ target: bound, operation, parameters, report: outcome.report });
      records.push(evidence);
      return success(evidence);
    });

  return {
    open_binary: ({ path }) =>
      serialized(async () => {
        try {
          target = await openTarget(path);
          return success({ target });
        } catch (error) {
          return failure(projectAnalysisError(new AnalysisUnsupportedTargetError("open_binary", path, error.message, { cause: error })));
        }
      }),
    close_binary: () =>
      serialized(async () => {
        target = undefined;
        return success({ closed: true });
      }),
    observe_native_ui: observation("observe_native_ui"),
    capture_native_ui_scenario: observation("capture_native_ui_scenario"),
    export_evidence_bundle: ({ path }) =>
      serialized(async () => {
        try {
          await writeFile(path, evidenceBundleText(records), "utf8");
          return success({ path, records: records.length });
        } catch (error) {
          return failure(
            projectAnalysisError(
              new AnalysisCapabilityUnavailableError(PROVIDER_ID, "export_evidence_bundle", `Evidence bundle could not be written: ${error.message}`, {
                remediationAction: "Choose a writable path for the bundle, then retry.",
              }),
            ),
          );
        }
      }),
  };
}

/** The MCP server exposing those handlers with REA's input schemas. */
export function createServer(options) {
  const handlers = createTools(options);
  const server = new McpServer({ name: "rea-windows-native-ui", version: "0.1.0" }, { capabilities: { tools: {} } });
  const register = (name, description, inputSchema) =>
    server.registerTool(name, { description, inputSchema }, (args, context) => handlers[name](args, context));
  register(
    "open_binary",
    "Bind the Windows executable that native UI observations are checked against (path, SHA-256, format, architecture).",
    z.strictObject({ path: z.string().min(1) }),
  );
  register("close_binary", "Release the active target.", z.strictObject({}));
  register(
    "observe_native_ui",
    "Observe an already-running Windows app by PID and top-level window handle, bound to the active PE target. Captures a bounded UI Automation tree and a selected-window screenshot. Never launches or changes the target.",
    nativeUiObservationInputSchema,
  );
  register(
    "capture_native_ui_scenario",
    "Run selected-element Invoke, RangeValue increment/decrement, Value text entry and bounded wait steps in one exact Windows app window. Returns ordered before/after captures and action/capture failures. Actions can change app data; state is left as-is; no synthesized global input is used.",
    nativeUiScenarioInputSchema,
  );
  register(
    "export_evidence_bundle",
    "Write this session's Evidence as a canonical REA bundle that REA's import_evidence_bundle accepts.",
    z.strictObject({ path: z.string().min(1) }),
  );
  return server;
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) serveStdio(() => createServer());
