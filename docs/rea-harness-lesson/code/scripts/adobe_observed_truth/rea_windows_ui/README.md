# rea-windows-native-ui

A local MCP server giving Windows the same two desktop-UI tools REA 6.8.0 has on macOS,
`observe_native_ui` and `capture_native_ui_scenario`, with 1:1 parity of inputs, step grammar,
results, sequencing, limits, error codes and Evidence. How it is used: the REA harness
lesson's guide (04-guide.md).

- `src/` Node server. Reuses REA 6.8.0's own input/result schemas, output budget and
  `createEvidence` / bundle code, so REA's checks are the parity checks.
- `helper/ReaWindowsUi` the Windows helper (C#, .NET 9, Microsoft UI Automation), the
  counterpart of REA's `ReaNativeUI.swift`: one JSON request in, one snapshot out.
- `helper/ReaWindowsUi.Fixture` a small WPF window with a known tree, for live proofs.

## Build and test

```
npm install                                   # in this folder
dotnet build helper/ReaWindowsUi.sln -c Release
npm test                                      # Node seams (sequencing, Evidence, target)
dotnet test helper/ReaWindowsUi.sln           # helper seams (tree walk, actions)
node live/prove_fixture.mjs <bundle.json>     # live, needs a desktop: every step kind
node live/observe_photoshop.mjs               # live, passive: Photoshop's main window
```

## Use from an MCP client

Register `node <this folder>/src/server.js` as a stdio MCP server. Tools: `open_binary`
(bind the target executable), `observe_native_ui`, `capture_native_ui_scenario`,
`export_evidence_bundle`, `close_binary`. Import an exported bundle into REA with its
`import_evidence_bundle`.

Proven live on 2026-11-09: fixture window (press, slider +1, text entry, wait; an action an
element cannot do fails with `action-failed`, no fallback); REA's `import_evidence_bundle`
accepted the exported Evidence; Photoshop observed passively (UI Automation sees its window
chrome and docked panel tabs; Photoshop's own drawn UI appears as panes without children).

Registered in Claude Code at user scope as `rea-windows-ui`
(`claude mcp add --scope user rea-windows-ui -- node <this folder>/src/server.js`). The
registration names this worktree's path; re-register if the folder moves.

## Linking the Photoshop harness

The Photoshop runner (`../runner_photoshop.py`, through `../parity.py`) takes one parity
observation per Photoshop process and records it in every result row as `parity`: its Evidence
ID, or REA's error with its remediation. To hand the results to REA:

    node src/cli.js bundle --exe "C:\Program Files\Adobe\Adobe Photoshop 2026\Photoshop.exe" \
      --results <dataset>/results.jsonl \
      --observations <corpus>\parity-observations.jsonl --out <bundle.json>

then REA's `import_evidence_bundle`. Harness records (provider `adobe-observed-truth`,
`authority: controlled-replay`) link to the observation of their process; record what UI
Automation cannot read with REA's `record_unknown` and resolve it with `update_unknown` citing
the harness Evidence (design doc section 8).
