// open_binary binds a Windows executable target: format and architecture from its PE header.
import assert from "node:assert/strict";
import { test } from "node:test";

import { peIdentity } from "../src/target.js";

/** The first bytes of a PE file: MZ, e_lfanew = 0x40, then "PE\0\0" and the machine type. */
const peHeader = (machine, characteristics = 0x0022) => {
  const bytes = Buffer.alloc(0x60);
  bytes.write("MZ", 0, "latin1");
  bytes.writeUInt32LE(0x40, 0x3c);
  bytes.write("PE\0\0", 0x40, "latin1");
  bytes.writeUInt16LE(machine, 0x44);
  bytes.writeUInt16LE(characteristics, 0x56); // COFF Characteristics
  return bytes;
};

test("a 64-bit Intel PE header is format pe, architecture x86_64", () => {
  assert.deepEqual(peIdentity(peHeader(0x8664)), { format: "pe", architecture: "x86_64" });
});

test("an Arm64 PE header is architecture arm64", () => {
  assert.deepEqual(peIdentity(peHeader(0xaa64)), { format: "pe", architecture: "arm64" });
});

test("bytes that are not a PE file are refused", () => {
  assert.equal(peIdentity(Buffer.from("#!/bin/sh\necho hi\n")), null);
});

test("a DLL is refused: REA binds native UI observation to an executable", () => {
  assert.equal(peIdentity(peHeader(0x8664, 0x2022)), null); // IMAGE_FILE_DLL set
});