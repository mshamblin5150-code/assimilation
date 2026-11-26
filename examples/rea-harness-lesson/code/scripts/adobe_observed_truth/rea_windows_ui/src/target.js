// The active target: the one Windows executable this session's observations are bound to,
// identified by path and SHA-256 like REA's open_binary target.
import { createHash } from "node:crypto";
import { createReadStream } from "node:fs";
import { open, realpath } from "node:fs/promises";

const MACHINES = { 0x8664: "x86_64", 0xaa64: "arm64", 0x14c: "x86" };

/** Format and architecture from a PE header, or null if the bytes are not a PE file. */
export function peIdentity(bytes) {
  if (bytes.length < 0x40 || bytes.toString("latin1", 0, 2) !== "MZ") return null;
  const offset = bytes.readUInt32LE(0x3c);
  if (bytes.length < offset + 24 || bytes.toString("latin1", offset, offset + 4) !== "PE\0\0") return null;
  const architecture = MACHINES[bytes.readUInt16LE(offset + 4)];
  const isDll = (bytes.readUInt16LE(offset + 22) & 0x2000) !== 0; // COFF Characteristics: IMAGE_FILE_DLL
  return architecture && !isDll ? { format: "pe", architecture } : null;
}

/** Bind the executable at `path`: canonical path, SHA-256, format and architecture. */
export async function openTarget(path) {
  const canonical = await realpath(path);
  const handle = await open(canonical, "r");
  let header;
  try {
    const { buffer, bytesRead } = await handle.read(Buffer.alloc(4096), 0, 4096, 0);
    header = buffer.subarray(0, bytesRead);
  } finally {
    await handle.close();
  }
  const identity = peIdentity(header);
  if (identity === null) throw new Error(`${canonical} is not a Windows (PE) executable`);
  const sha256 = await new Promise((resolve, reject) => {
    const hash = createHash("sha256");
    createReadStream(canonical)
      .on("data", (chunk) => hash.update(chunk))
      .on("end", () => resolve(hash.digest("hex")))
      .on("error", reject);
  });
  return { path: canonical, sha256, ...identity };
}
