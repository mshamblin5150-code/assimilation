// The helper seam's real adapter: run the Windows helper (helper/ReaWindowsUi) with one JSON
// request and read its one JSON response, as REA runs ReaNativeUI.swift on macOS. The request
// goes on stdin (a Windows command line is capped near 32K characters; macOS argv near 1 MB).
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

import { NATIVE_UI_HELPER_MAX_BUFFER } from "rea-agents/dist/native/NativeUiOutputBudget.js";

export const HELPER_PATH = fileURLToPath(
  new URL("../helper/ReaWindowsUi/bin/Release/net9.0-windows/ReaWindowsUi.exe", import.meta.url),
);

/**
 * One helper request; resolves to `{ok: true, result}` or `{ok: false, code, message}`.
 * Rejects with code ETIMEDOUT past `timeoutMs`, AbortError when `signal` aborts, or an error
 * when the helper fails, overflows the output allowance, or prints malformed JSON.
 */
export function invokeHelper(
  request,
  { signal, timeoutMs, helper = { command: HELPER_PATH, args: [] } } = {},
) {
  return new Promise((resolve, reject) => {
    const child = spawn(helper.command, helper.args, { signal, windowsHide: true });
    let stdout = "";
    let bytes = 0;
    let settled = false;
    const finish = (error, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (error) reject(error);
      else resolve(value);
    };
    const timer =
      timeoutMs === undefined
        ? undefined
        : setTimeout(() => {
            child.kill();
            finish(Object.assign(new Error(`Native helper exceeded ${timeoutMs} ms`), { code: "ETIMEDOUT" }));
          }, timeoutMs);
    child.stdout.setEncoding("utf8");
    child.stdout.on("data", (chunk) => {
      bytes += Buffer.byteLength(chunk);
      if (bytes > NATIVE_UI_HELPER_MAX_BUFFER) {
        child.kill();
        finish(new Error("Native helper output exceeded the scenario output allowance"));
      } else stdout += chunk;
    });
    child.on("error", (error) => finish(error));
    child.on("close", (code) => {
      if (code !== 0) return finish(new Error(`Native helper exited with code ${code}`));
      try {
        finish(undefined, JSON.parse(stdout));
      } catch (cause) {
        finish(new Error("Native helper returned malformed capture data", { cause }));
      }
    });
    child.stdin.on("error", () => {}); // a helper that exits early surfaces through "close"
    child.stdin.end(JSON.stringify(request));
  });
}
