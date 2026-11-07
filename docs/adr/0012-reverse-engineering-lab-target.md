# ADR 0012: Use a purpose-built program for the reverse-engineering lab

- Status: Accepted. Matt confirmed shared understanding and authorized local authoring.
- Date: 2026-11-07
- Owner: Matt Shamblin for the Assimilation lesson design

## Context

The advanced lesson for Chad should teach how to explain one behavior of a
compiled program using repeatable observations, static analysis, and a runtime
check. The main exercise needs a stable answer key and a target whose source can
be revealed after the investigation.

## Decision

Matt named the lesson **Assimilation Living Up to Its Name** and approved a
small native Windows program with an undocumented numeric cutoff as the main
exercise. Chad observes accepted and rejected inputs, locates the condition
in Ghidra, predicts the exact-boundary result, and verifies the branch in x64dbg.

Use a small synthetic APK for the JADX exercise so Chad can analyze an Android
artifact without an Android SDK or emulator. Keep the recorded `aapt2` session
as an optional real-world example. Use a compiled C# fixture for ILSpy.

Include the installation walkthrough in the lesson. Show how to find and
read the original Matt Pocock and P-Stack skills in Assimilation, how optional
host installation works, and how to preview, approve, apply, and verify REA
setup. Document the four tool installations and the Java and headless JADX
prerequisites used on the authoring host. Chad retains authority over setup
and execution on his machine.

## Alternatives considered

Starting with `aapt2` would provide a production artifact immediately. It would
also make the main exercise depend on the SDK version and take more effort to
keep reproducible.

Comparing two builds would teach regression diagnosis, but would require a
second build and distract from tracing one behavior through the first executable.

## Consequences

The lesson needs the three fixtures, build instructions, a learner walkthrough,
and a separate instructor key. Provide the Android fixture in a form the learner
can inspect without rebuilding it.
The main exercise can establish expected results independently of what the
decompiler or debugger reports. The follow-up should identify the SDK version
used and state what the recorded run establishes.

## Verification and references

- Observed on the authoring Windows host: Ghidra analyzed a native executable,
  ILSpy recovered a method from a compiled managed DLL, JADX decompiled a test
  APK, and x64dbg reached the entry point of Build Tools 36.0.0's `aapt2.exe`.
- [Lab results](../../examples/chad-reverse-engineering/RESULTS.md) record the
  author-run fixture builds and analysis. Independent reproduction on a fresh
  learner checkout remains planned.
- Method sources: [Matt Pocock's diagnosing-bugs](../../upstream/matt-pocock/skills/engineering/diagnosing-bugs/SKILL.md)
  and [P-Stack's prove-it-works](../../upstream/pstack/skills/principle-prove-it-works/SKILL.md).
