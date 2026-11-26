// The helper call: request on stdin (no command-line length cap), deadline as a timeout,
// cancellation kills the helper.
import assert from "node:assert/strict";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import { invokeHelper } from "../src/helper.js";

const fake = { command: process.execPath, args: [fileURLToPath(new URL("./fake-helper.mjs", import.meta.url))] };

test("a long text entry reaches the helper whole, through stdin", async () => {
  const text = "x".repeat(100_000); // far past Windows' ~32K command-line limit

  const reply = await invokeHelper({ action: { kind: "key-entry", path: [0], text } }, { helper: fake });

  assert.equal(reply.message, "100000");
});

test("a helper still running at the deadline is stopped and reported as ETIMEDOUT", async () => {
  await assert.rejects(
    invokeHelper({ sleep_ms: 5000 }, { helper: fake, timeoutMs: 200 }),
    (error) => error.code === "ETIMEDOUT",
  );
});

test("cancelling stops the helper", async () => {
  const caller = new AbortController();
  setTimeout(() => caller.abort("cancelled"), 100);

  await assert.rejects(
    invokeHelper({ sleep_ms: 5000 }, { helper: fake, signal: caller.signal }),
    (error) => error.name === "AbortError",
  );
});
