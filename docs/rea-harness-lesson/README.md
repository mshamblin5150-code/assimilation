# Teaching REA to see what it cannot: an observed-truth harness for self-drawn Windows apps

REA (reverse-engineer-anything, the `rea-agents` MCP toolkit) reads binaries, packages and
runtimes, and records what it finds as Evidence in one ledger. It cannot see inside a Windows
app that draws its own interface: Photoshop's dialogs are pixels, not controls, so UI
Automation finds nothing to observe.

This package is the end-to-end record of closing that gap, told from the moment the operator
first set REA up. An AI coding agent (Claude) built the harness; the operator drove it. It
teaches two things together:

- **The technique.** A harness that finds and drives every control of a self-drawn dialog from
  its pixels, records each action as REA Evidence linked to an observation of the same
  process, and points each control at the decompiled code that handles it. A Windows bridge
  gives REA native UI observation with Evidence it accepts.
- **How the agent was driven.** Every instruction, correction and ruling the operator gave,
  and the rule each live incident became. Most of the harness's safety rules exist because the
  operator caught something the agent did not.

## Contents

| File | What it is |
|---|---|
| [01-story.md](01-story.md) | The ticket, end to end, in phases: from setting REA up to REA plus the harness reaching what REA cannot natively see. |
| [02-operator-log.md](02-operator-log.md) | Every meaningful operator message in time order, with what the agent did in response. |
| [03-rules.md](03-rules.md) | The operator's standing rulings, the bugs found live (symptom, cause, rule, test), and how to steer an agent like this. |
| [04-guide.md](04-guide.md) | The technical guide: the seams, how a dialog is driven, safety mechanisms, bringing up another self-drawn app, running it. |
| [code/](../../examples/rea-harness-lesson/code/) | The harness (`scripts/adobe_observed_truth`), the REA Windows bridge (`scripts/adobe_observed_truth/rea_windows_ui`) and their tests, ready to run on their own. |

In this repository the `code/` folder is at
[`examples/rea-harness-lesson/code/`](../../examples/rea-harness-lesson/code/), beside the other lab
fixtures. Paths written as `code/...` in this lesson start there.

## Running the code

From `code/`, with Python 3.12, `numpy`, `Pillow`, `opencv-python` and `pytest` installed:

```
python -m pytest
```

The tests need nothing outside `code/`. The bridge's own tests need Node: in
`code/scripts/adobe_observed_truth/rea_windows_ui`, run `npm ci`, then `node --test test/`.
Driving a real app needs Windows, the app, REA, and a local working folder named by the
`ADOBE_REA_CORPUS` environment variable; see [04-guide.md](04-guide.md).

## What is not here, on purpose

- **The image platform's text and code.** No dialog text, interface strings, help pages or decompiled code.
  Interface-string examples use the made-up form `$$$/Example/Key=Label`. Each control is
  linked to code by binary name, setting code, string key and function address only.
- **The operator's identity and machine.** No names, accounts, paths or folders.
- **The private repository the work was built in.** It is mentioned only as "a private
  repository".

These exclusions are enforced, not promised. In the source repository, a redaction gate scans
every file of this package and fails on any personal identifier, machine path, private
repository term, image-platform interface string or agent system text. A second test fails if any file
under `code/` differs from the live harness, so the copy here is never stale.

## Sources and their limits

The story and the log come from the agent's own session transcripts, starting with REA's
setup. Long sessions were compacted: where the record comes from the agent's compaction
summaries instead of the live exchange, the log says so. The operator's words are quoted as
he wrote them, with typos and grammar lightly cleaned. Work done by other agents (Codex)
appears only as the operator relayed it.
