# Adobe observed-truth harness: capability map

The harness turns "the help says" into "we watched it happen". It drives the
installed Adobe app on Windows and records each observation as an REA Evidence
record (`adobe-observed-truth.windows-ui-scenario`, authority `controlled-replay`), bound by
SHA-256 to the exact executable. A new behaviour should need only a new
scenario. A capability missing here is what would force a rebuild.

Sources (2026-11-08):

- A coverage pass over the 100 interaction contracts of the private repository the
  harness was built in.
- A breadth pass over the Photoshop/Illustrator inventories in the main
  checkout's `.codex_tmp/`: 2,835 Photoshop taxonomy rows, 292 UI surfaces,
  111 shortcuts, 42,633 Illustrator installed actions.
- Lessons from the earlier capture scripts.

Every contract file names Photoshop 2025 as its reference. The harness observes
2026 (27.11) and records the exact build on every record.

## Status key

- built: in the harness and run against live Photoshop
- partial: exists but incomplete
- missing: not yet built

## Input

| Capability | Status | Needed for (examples) | Approach / risk |
|---|---|---|---|
| Ordered key chords | built | Ctrl+Y vs Shift+Ctrl+Z, `[`/`]` brush size, Ctrl+D/Shift+Ctrl+I | `input_plan.chord`, SendInput |
| Drag with modifier timing (before press vs mid-drag) | built | marquee Shift, boolean selection modes, Free Transform modifiers | `input_plan.drag` |
| Click with modifiers | built | Shift-click anchors, Shift-click straight brush line, bucket, wand | `input_plan.click` |
| Timed key hold / spring-loaded tools | missing | Space temporary Hand, Ctrl temporary Direct Select, H-hold bird's-eye | add a Pause event; hold durations are plan data |
| Right-click, double-click, wheel (with Alt/Ctrl) | missing | Alt+wheel zoom anchor, Ctrl+wheel scroll, context menus | SendInput wheel/right-button events |
| Hover and dwell (no button) | missing | brush cursor outline, swatch tooltips | MouseMove plus Pause |
| Off-canvas and pasteboard pointer positions | missing | marquee past edge, selection off canvas and back, off-canvas guides | coordinate mapping beyond canvas bounds; control autoscroll |
| Text and numeric field entry, scrubby sliders | missing | options-bar opacity, dialog fields | UI Automation where exposed, else typed input after focus check |
| Keyboard-focus state | missing | shortcuts ignored while a layer name is being edited | UI Automation focus read before keys |
| Pen pressure and tilt | missing | brush pressure dynamics (excluded contract; optional) | `InjectSyntheticPointerInput` with Photoshop in Windows Ink mode; unproven |

## Canvas and view

| Capability | Status | Needed for | Approach / risk |
|---|---|---|---|
| View readback (zoom, scroll, rotation, screen mode) | built | every on-canvas scenario; zoom and pan contracts | `canvas.read_view`: `viewInfo.activeView.globalBounds` + `viewTransform` + `zoom`; matched Photoshop's drawn canvas within 1 px at 50–200%; rotation and screen mode unproven |
| Document-to-screen coordinate mapping | partial | marquee, pen, brush, bucket, transform, guides | `canvas.document_to_screen`, unit-tested; the input-side proof `canvas_mapping_check` waits for an unlocked session |
| Window topology (main, floating documents, shadow windows) | partial | choosing the correct window to capture and focus | `_main_window` matches title and image path; add floating document windows |

## State

| Capability | Status | Needed for | Approach / risk |
|---|---|---|---|
| Allowlisted state reads | partial | history, tool options, selection bounds, path points, layers, prefs | grow from per-method reads to a named-path allowlist; never dump the app descriptor (licence serial) |
| Set tool options before acting | partial | brush size/hardness/opacity/flow/smoothing, bucket tolerance, wand settings | `ps_tools`: brush, eraser, bucket set/read; user tool state snapshotted and restored byte-exact; never run in a scenario yet |
| Preference snapshot and pin | missing | `maximumStates`, `legacyFreeTransform`, Auto Add/Delete, Snap To, Overscroll | record behaviour-relevant prefs on every record; hash the settings folder |
| Factory-default preferences | missing | true default history depth, legacy-undo default, scroll-wheel zoom default | restart Photoshop with the settings folder moved aside, then restore; **needs the operator's approval** |
| Settings not reachable by scripting | missing | Use Legacy Undo Shortcuts | read from the Keyboard Shortcuts dialog or the settings files |

## Observation

| Capability | Status | Needed for | Approach / risk |
|---|---|---|---|
| Document pixel export | partial | eraser opacity, brush hardness falloff, spacing, flow, bucket leak, layer opacity | `ps_pixels.export_composite/export_layer` (PNG copy, no History effect); analysis helpers unit-tested |
| Selection mask export | partial | feather, anti-alias, wand, quick selection, boolean modes, selection moved off canvas | `ps_pixels.export_selection_mask` (temporary layer, History reverted); not yet run in a scenario |
| Window capture | built | UI-only facts: overlays, marching ants, handles, Proof Colors | `capture.py`: `PrintWindow(PW_RENDERFULLCONTENT)` with extended frame bounds; works while the workstation is locked |
| Cursor capture | missing | brush outline, Pen close/add cursors, guide cursor override, active-tool truth | `GetCursorInfo` plus cursor bitmap; GPU-drawn outlines may need window capture |
| UI Automation readback | partial | menu item enabled/checked (Undo label, Inverse greyed), dialog text | menu state via `photoshop.menu_items` (menuBarInfo, by command ID); dialog text via `blocking_dialogs`; full UI Automation not yet |
| Clicks inside panels Windows cannot see into | missing | swatch chips, color chips | template-match a window capture against panel state read by scripting |
| Frame sequence over time | missing | marching ants, smoothing lag, pan inertia | timed captures; sampling interval limits what is observable |
| ActionManager descriptor log | missing | what a UI gesture actually ran | ScriptListener-style logging during a scenario |

## Setup, safety and runtime

| Capability | Status | Needed for | Approach / risk |
|---|---|---|---|
| Version binding | built | every run; 2024, 2025 and 2026 are installed side by side | refuse unless the bound app is major version 27; record exe path, version, build, SHA-256 |
| Foreground and lock guard | built | every input scenario | input stops if any other process takes the foreground; detects the lock screen (`LockApp.exe`); `focus` first closes a running screensaver by posting `WM_CLOSE` to its windows on the separate "Screen-saver" desktop (no input spent waking it) and refuses one it cannot reach; observed live 2026-11-09: system-started Mystify (four `D3DSaverWndClass` windows) cleared in 0.11 s, twice, workstation not locked. This PC's foreground lock timeout is the maximum, so plain `SetForegroundWindow` failed 5/5 after a clear; `focus` now takes the foreground through `AttachThreadInput` (5/5, no keystroke), and `canvas_mapping_check` passed 3/3 starting behind the screensaver |
| Throwaway documents | built | every scenario | documents named `observed-truth-*`; closes only those, without saving |
| Deterministic fixtures (layers, shapes, selections, paths) | missing | most contracts | script-built documents; `displayDialogs = NO`; avoid the layer-group move that hung Photoshop before |
| Modal detection and dismissal | partial | error dialogs, GPU compatibility, generative AI credits, progress dialogs | runner turns dialogs off per scenario and fails loudly if a PSDialogBox remains; no automatic dismissal |
| Wait for idle | missing | async filters, progress dialogs | poll readiness instead of fixed sleeps |
| Hang watchdog and recovery | missing | a JSX fixture hung Photoshop once before | detect a hang; never kill without the operator's approval; detect `-Recovered` documents |
| Repeat runs | missing | quick selection determinism; any claimed determinism | replay N times on a reset fixture and diff |
| Network and account guard | missing | 600 cloud/share/generative rows | refuse cloud, Stock and generative actions; observe only their boundary UI |
| Illustrator adapter | partial | Shift-click anchors in Illustrator, smooth-handle rotation, artboard origin | `illustrator.py`: binds to 2026 (30.8.2) only, path/selection/view reads proven live; input scenario unrun |

## Out of reach with these mechanisms

- Internal brush-engine state and GPU-only previews. Only their visible effect or exported pixels can be observed.
- UXP/CEP panel internals (27 UXP, 4 CEP panels). Webviews, not driveable through COM.
- Generative and cloud results. Nondeterministic and account-gated.
- Undo memory and purge internals. Only the History list is observable.
- Transient frames shorter than the capture interval.

## The flagged behaviours and what each needs

| Behaviour | Capabilities beyond what is built |
|---|---|
| Shift before vs after starting a marquee drag | coordinate mapping, view readback, selection mask export, fixture |
| Shift-click to add anchors (Photoshop and Illustrator) | coordinate mapping, path-point reads, Illustrator adapter |
| Free Transform scales proportionally by default | coordinate mapping, layer bounds read, `legacyFreeTransform` pin, fixture |
| Selection moved off the canvas and back | off-canvas pointer, selection mask export |
| Eraser opacity | set tool options, document pixel export, fixture |
| Paint bucket on an area that isn't enclosed | set tool options, document pixel export, fixture |
| Brush hardness falloff stays inside the brush size | set tool options, document pixel export |
| Default history depth (help says 20 and 50) | factory-default preferences (approval needed); effective limit already observed: 50 |
| Ctrl+Y vs Shift+Ctrl+Z | built (`redo_shortcuts`); waiting for an unlocked session. `undo_menu_layout` already shows the modern undo menu layout |

## Contract claims the coverage pass flagged

These are reviewers' readings of the contract files, not observations. Each is a
scenario to run.

- `brush_tip_size_hardness_mask_edge`: a feather that spreads falloff outside the diameter. Photoshop brushes have no feather.
- `eraser_subtracts_from_same_alpha_target` and `brush_stroke_commit_undo_granularity` (must_match): zero-change strokes create no history.
- `fill_bucket_enclosed_seed_fill` (must_match): a fill that reaches the image edge is skipped.
- `transform_move_selection_normalized_delta` and `selection_move_normalized_delta` (must_match): selection points clamped to the canvas.
- `selection_marquee_rect_ellipse_geometry` vs `selection_modifier_boolean_modes`: both claim Shift and Shift+Alt. Photoshop tells them apart by timing.
- `selection_marquee_rect_ellipse_geometry`: a marquee dragged past the edge clamps to the canvas.
- `path_direct_vertex_selection_modifiers` and `illustrator_direct_selection_anchor_handle_supplement` (must_match): Ctrl-click toggles anchors. Adobe uses Shift-click.
- `illustrator_direct_selection_anchor_handle_supplement` and `path_bezier_handle_creation_drag`: smooth handles move independently or break symmetry.
- `zoom_percent_clamp_step_controls` (must_match): 25-point zoom steps and a 25–400 range.
- `zoom_wheel_anchor_gesture`: Ctrl+wheel zooms.
- `keyboard_undo_redo_shortcut_routing`: Ctrl+Y redoes, and viewport changes enter the undo journal.
- `swatches_panel_inventory_metadata` (must_match): the Color panel shows swatch chips with a checked state.
- `swatches_swap_picker_state_transitions`: X opens the picker.
- `brush_smoothing_stabilizer_behavior`: evidence cites Select and Mask, not brush Smoothing.
- `brush_shift_click_straight_line` (must_match): evidence is about Pen segments.
- `transform_handles_preview_bounds`: no selection falls back to the document rectangle.
- `fit_reset_default_view_state`: Fit Image sets zoom to 100.
- `history_layer_stack_review_controls`: layer edits undo like panel state.
- `selection_clear_deselect_state`: Deselect is not undoable through History.
- `keyboard_path_delete_shortcut_binding_set`: Enter closes an open path.
- `snapping_snap_to_edge_trace_assist`: cited snapping sources do not describe alpha-edge tracing.

## Known issue: intermittent "Select" refusals (2026-11-08)

While the workstation was locked and Photoshop idle, Photoshop 27.11 repeatedly
entered a state where every scripted call, even reading `app.Version` through
DoJavaScript or the foreground colour, failed with Error 8800 "The command
"Select" is not currently available." With `displayDialogs` at its default
(ERROR) the failure opened a blocking OK-only dialog. The state came and went;
tool selects worked between episodes, with and without documents open and with
the Home screen visible. Cause not established. The runner now wraps every
Photoshop scenario in `dialogs_off`, so the failure surfaces as an error, and
checks for leftover dialogs. Never kill a client mid-call: a timed-out
DoJavaScript stays queued in Photoshop and runs later.

**Likely cause, found live 2026-11-09:** Adobe's feedback survey ("How likely are
you to recommend Photoshop to a friend or colleague?", Submit/Cancel, "Never show
again"). It is a standard `#32770` dialog owned by the main window, not a
`PSDialogBox`, so the old dialog check missed it, and it can sit hidden behind
other windows. While it was open every DoJavaScript call failed, even `1+1`
(a general error saying the command was not currently available), while
COM properties such as `app.Version` still answered, the main window stayed enabled,
and Escape did not help. Pressing Cancel restored scripting; the same scenario then
passed three times. The runner's `preflight` now finds Photoshop by window class
(no scripting), declines the survey for good (ticks "Never show again", presses
Cancel, never Submit — the operator's choice), waits until it has closed, and refuses to
start behind any other dialog. Proven live against a replica (a real `#32770` dialog
in another process with the survey's question, Submit/Cancel push buttons and an
auto-checkbox): the pre-flight ticked the box, pressed Cancel, and the dialog closed
in 0.19 s, Submit untouched. The real survey's Submit, Cancel, 0–10 and "Never show
again" were separate child windows carrying those texts, consistent with standard
buttons, but their classes were not recorded before it closed; the pre-flight prints
them once a declined survey has closed, so the first reappearance settles it. A survey
counts as blocking whatever its controls are; if its Cancel is not a standard button the
pre-flight refuses to start (naming it) rather than post a click that may do nothing.

The Generative Fill popup seen at the same time (an image carousel, `#32770`) is
Adobe's one-time feature tour: hovering every point of the task bar's Generative fill
button for 3 s afterwards never brought it back. It did not block scripting: scripting
stayed refused after it was closed and returned only when the survey was cancelled.

Scenario `finally` blocks also call Photoshop, so a clean-up refused behind a modal
used to surface instead of the scenario's error. The runner now headlines the error
raised first (`explain_failure`), following only implicit "raised while handling" links:
context Python suppresses (e.g. `json.loads("")`'s StopIteration) and deliberate
`raise … from` translations are left as they are.
