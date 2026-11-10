# ChatGPT-only start: no coding tools necessary

A public GitHub URL is a **reference**, not a command that automatically installs skills or changes a model's memory. Chad may have a Free, Go, Plus, Pro, or other account. Without knowing his entitlements, provide two honest options:

1. **Conversation approach.** Give ChatGPT a concrete task and direct it to [START_HERE.md](../START_HERE.md) and `AGENTS.md`. If it cannot retrieve them, paste or upload those files and the selected original skill sources. Have it work an actual acceptance example and produce the deliverable, with capability limitations and a copyable run record. It may draft decisions and ADRs as text; unexecuted tests stay labeled not run, and source reading is not a native skill invocation.
2. **Persistent project approach (if supported).** Make a ChatGPT Project for Chad's own work and add the approved Markdown instructions as project sources/instructions. Keep the project separate from anyone else's private accounts. Project-file availability and tool access depend on his plan and account configuration.

For **full engineering workflows**, a capable local or cloud coding agent can read the complete upstream reference files already under `upstream/`. With Git/filesystem/terminal access it can optionally create host bridges using the documented installer, or use a publisher's supported native plugin method. Reading source does not activate plugins, execute scripts, or grant extra capabilities. To generate 3D CAD and an STL, the environment must also provide an appropriate geometry engine such as OpenSCAD or CadQuery, not merely the capability to describe geometry.

**Suggested first prompt:**

> Follow this repository’s `START_HERE.md` for my task: [outcome]. My project or supplied files are [location], and the authorized scope is [scope]. Select and read the relevant original skills, perform the task with tools actually available, and return the result, evidence and a handoff. If a necessary tool or file is unavailable, name the specific limitation and continue useful independent work. Preserve my authority over consequential actions.

## Dated capability observation: Voice subagent dispatch (November 9, 2026)

In one ChatGPT conversation conducted through Voice, the assistant inspected the available tools and **did not find a direct, callable mechanism to launch an independent research or engineering subagent from that conversation**. The same conversation successfully read Assimilation's `START_HERE.md`, `AGENTS.md`, `docs/FLEET_HANDOFF.md` and `docs/OPERATOR_METHOD.md` through GitHub access, and verified the then-current `main` commit `62e466ca03565fa132323d81580beab6fe634356`.

A written handoff was manually transferred between conversations and used to recover the repository's operating context. **No subagent was launched, no autonomous inter-chat transfer or task ownership transfer was established, and no new handoff/swarm evaluation was executed.**

**Evidence boundary:** successful repository reads and the inspected tool inventory were directly observed; the absence of a direct dispatch tool is **session-specific**, not proof of a universal limitation across ChatGPT Voice, Codex, Work or other hosts. Because no supported dispatch interface was found in this session, there is no attempted-dispatch failure or successful delegated-run receipt to report. Tool availability may vary with the runtime and configuration.

**Operational response:** before assigning a child drone, verify that the current host exposes a functioning delegation mechanism. Where it does not, work serially or transfer an appropriately redacted, verifiable [fleet handoff](FLEET_HANDOFF.md) to a separately authorized agent-capable environment. Label a manual transfer as manual; do not report a swarm or independent review without separate agent execution evidence. See the [swarm operating model](SWARMS.md).

**Next test, not yet performed in this session:** run the existing [interrupted-handoff and swarm evaluation](../evals/interrupted-handoff/README.md) in an environment with demonstrated independent agent dispatch, retaining task identities, assignments, operation receipts, artifact hashes, and independent grading.
