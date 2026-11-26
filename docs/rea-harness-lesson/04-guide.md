# Give REA reach into Windows apps that draw their own UI

REA (`rea-agents` on npm) observes desktop UI through the operating system's accessibility tree. Many large Windows apps draw their dialogs themselves, so that tree shows an empty pane where the controls are. This guide shows how the code in `code/` reaches those controls anyway: it reads the dialog's pixels, sends real keyboard and mouse input, and places what the keyboard cannot reach from a catalogue. Every action lands as REA Evidence linked to an REA observation of the same process.

The worked example is Photoshop 2026. You will bring the same technique up for another self-drawn app, so the guide separates what is Photoshop-specific from what carries over.

All paths in this guide are relative to `code/`. The harness lives in `scripts/adobe_observed_truth/`, the Node bridge in `scripts/adobe_observed_truth/rea_windows_ui/`, and the tests in `tests/unit/`. Each test named here is a worked example of the rule it guards. Most of their docstrings tell the incident that made the rule.

## 1. Why REA cannot see a self-drawn dialog, and what fills the gap

### What REA sees natively

REA 6.8.0 has two desktop UI tools: `observe_native_ui` (a snapshot of a window's accessibility tree plus a capture) and `capture_native_ui_scenario` (a sequence of steps against that tree). On macOS they run REA's own Swift helper. The bridge in `rea_windows_ui/` gives Windows the same two tools with the same inputs, results, error codes and Evidence. `src/server.js` reuses REA's own input schemas and error projection. A .NET helper (`helper/ReaWindowsUi`) walks the window with Microsoft UI Automation and returns one JSON snapshot.

That is enough for an app built from standard controls. Each button, slider and field is an element with a role and a name, and a scenario step can act on it by name.

### Why a self-drawn dialog is invisible

A self-drawn app paints its controls into one window with its own rendering code. There is no button object for UI Automation to find, only pixels. In Photoshop, UI Automation sees the main window's frame and the docked panel tabs. A dialog such as Levels appears as a pane with no children. The few Win32 child windows that exist belong to a window class of Photoshop's own, and they carry no role or name a scenario could use.

You can confirm this for any target before you write any code: observe its dialog with the bridge (see `live/observe_photoshop.mjs`). If the dialog is a childless pane, this guide applies.

### The shape of the answer

The harness works the way a person at the keyboard does. Three things fill the gap:

- **Pixels.** `capture.grab` takes the dialog window's own rendering with `PrintWindow`. OCR reads its text. Comparing shots before and after a key press shows whether, and where, the dialog answered.
- **Synthesized input.** `win_input.perform` sends key presses and mouse events with `SendInput`, one event at a time, and only while the target process owns the foreground.
- **A catalogue.** `dialog-controls.jsonl` lists, per dialog, the controls a reader saw in its capture, with a kind, a label and an optional box. The harness finds keyboard controls without it. It uses the catalogue only to place controls that Tab never reaches (dials, curves, swatches, previews) and controls that only show something (text, pictures).

Every result and every driven control becomes an REA Evidence record, made by REA's own `createEvidence` in `rea_windows_ui/src/harness.js`. Each record links to the parity observation: the `observe_native_ui` Evidence of the same Photoshop process, bound by executable SHA-256, process ID and window handle. One bundle carries both, so REA holds one ledger: what UI Automation saw, and what the harness did where UI Automation could not see.

```
Photoshop process (exe SHA-256, pid, hwnd)
    |                                  |
observe_native_ui (bridge)        harness: pixels + SendInput + catalogue
    |                                  |
parity observation Evidence  <--  results.jsonl and control-actions.jsonl rows ("parity": {"evidence_id": ...})
    \_______________ cli.js bundle _______________/
                         |
            REA import_evidence_bundle
```

A third link points into the binary. `control_code.py` maps each driven control to the decompiled functions that compare its setting code or carry its interface string. `cli.js bundle --code` attaches that map to each control's Evidence as its `code` field.

Why pixels and input rather than hooking the app's drawing code? Hooks are specific to one app and one build, and they show what the code does, not what the operator sees. Pixels and input work on any Windows app and record the visible behavior. The code map then says where in the binary to read next. The cost is speed and certainty: OCR misreads, animation looks like an answer, and every rule in section 4 exists because the harness once pressed something it should not have.

## 2. The seams and their interfaces

The harness has six seams. Each one is an interface you can fake in a test or replace for another app.

### The surface: one dialog as pixels and input

`controls.Surface` and its extensions are `typing.Protocol` classes. The walk, the probe and the drivers depend only on them.

| Method | Defined on | Contract |
|---|---|---|
| `shot() -> np.ndarray` | `controls.Surface` | The dialog as an H x W x 3 image, in dialog coordinates. Raises `DialogClosed` once the window is gone. |
| `send(events: list[Event]) -> None` | `controls.Surface` | Sends `input_plan` events (`KeyDown`, `KeyUp`, `MouseMove`, `MouseDown`, `MouseUp`) with mouse positions in dialog coordinates. Raises `DialogClosed`. |
| `popups() -> int` | `controls.ProbedSurface` | How many windows the dialog has open on top of it: lists, menus, pickers. |
| `read_text(rect) -> str` | `controls.ProbedSurface` | OCR of one part of the dialog. `Rect` is `(x0, y0, x1, y1)`, end exclusive. |
| `words() -> list[dict]` | `control_pass.WordSurface` | OCR of the whole dialog. Each word has `text`, `x`, `y`, `w`, `h` and `line`. |

Three members are optional. The code looks them up with `getattr`:

- `popup_lines() -> list[str]`: the text lines of what the dialog has open. The probe reads a dropdown's list with it before closing the list.
- `close_popups() -> None`: closes what the dialog opened, never the dialog. Without it, `controls.close_popups` sends Escape, which is safe only on a fake.
- `flicker_s: float`: the pause between the two shots that detect blinking. `DialogSurface` sets 0.6 s, longer than one caret blink.

`dialog_surface.DialogSurface(hwnd, pid, ocr, should_stop)` is the Win32 adapter:

- `shot` calls `capture.grab(hwnd)`.
- `send` maps mouse positions to the screen with `to_screen` and `capture.frame_bounds`, calls `win_input.focus`, then `win_input.perform`. It skips `focus` while a popup is open, because focusing the dialog closes the popup and the Escape meant for the popup then cancels the dialog.
- `popups` counts visible windows of the process that appeared after the surface was made, apart from the dialog itself. `is_popup` leaves out `tooltips_class32` and `SysShadow`: a tooltip once counted as an open list and drew an Escape that canceled the dialog (`test_a_tooltip_or_a_shadow_is_not_something_the_dialog_opened`).
- `read_text` crops with a `READ_MARGIN` of 6 px, because text cropped tight reads worse (`test_a_region_is_read_with_a_margin_of_the_dialog_round_it_kept_inside_the_dialog`).
- `close_popups` is described in section 4.
- `is_file_dialog`, `go_to_folder` and `file_dialog_parts` handle Windows file dialogs (section 4).

OCR runs in one long-lived process, `dialog_surface.Ocr`. It uses RapidOCR when `<corpus>/ocr-venv` exists (`rapid_ocr_server.py`), else Windows OCR (`win_ocr/`). Both read one image path per line and answer one JSON line. `prepare_for_ocr` turns light-on-dark text dark-on-light and scales it by `OCR_SCALE` (3). `ocr_correct.Corrector` then fixes a word only when the app never shows it and a word the app does show differs only by characters OCR confuses (`0` and `O`, `1` and `l`). Numbers are never changed, because a field's value must be read as shown.

The tests use small fakes in place of `DialogSurface`. `FakeDialog` in `test_adobe_observed_truth_controls.py` draws gray controls and a focus ring and moves focus on Tab. `Widget` in `test_adobe_observed_truth_control_drivers.py` is one control. `Dialog` in `test_adobe_observed_truth_control_pass.py` is a whole dialog with OCR words. Write the same kind of fake for your app.

### The app adapter: opening, listing and canceling dialogs

`photoshop.py` knows the app as Windows and COM see it:

- `Photoshop()` binds the running app over COM and refuses any major version other than 27. `identity()` returns `Identity(version, build, executable_path, executable_sha256, pid, hwnd)`. `_main_window` finds the main window by class and executable path, not by title, because the title carries the open document's name.
- `list_dialogs(pid) -> list[Dialog]` returns every visible top-level window of the process except the main window. Each `Dialog` has `hwnd`, `class_name` and its visible child `Control`s (`hwnd`, `class_name`, `text`, `checked`, `enabled`).
- `blocking(dialogs)` keeps the ones that hold the app modal.
- `cancel_action(dialog) -> (action, control)` decides how to dismiss a dialog as Cancel: `"click"` a real Cancel button, `"cancel_command"` (post `IDCANCEL` to a standard Windows dialog), `"escape"`, or `"close"` (`WM_CLOSE`). `accept_action` decides how to accept one at defaults. `answer(dialog, action, control)` carries out either. `click(control)` posts `BM_CLICK`, so the pointer never moves.

`runner_photoshop.PhotoshopAdapter` runs spec steps. `step(name, *args)` calls the method `_<name>`. Opening a dialog to drive works like this:

1. `_drive_dialog_controls(command, path, where)` looks up the catalogue for `path` and runs the menu command through the UXP helper plug-in (`uxp_bridge.Bridge`, kind `menu_command`). That call returns only when the dialog closes, so it runs in a worker thread inside `_drive`, with a timeout of 3 hours.
2. While the worker waits, `_drive` calls `_capture_and_cancel_dialogs` every 0.3 s. That method captures each blocking dialog. On the first one, while `dialog_task` is `"controls"`, it calls `_drive_controls(dialog)`.
3. `_drive_controls` builds a `DialogSurface` and calls `control_pass.drive_dialog`. On the next round the dialog is listed again and canceled with `cancel_action`.

The process identity is the link to REA. `observe_process()` takes the parity observation of `self.identity` at start and after every relaunch, and `self.parity` is stamped on every row.

### The catalogue: labeled boxes per dialog

The catalogue is `dialog-controls.jsonl` in the dataset folder. It is not part of this package, because it is built from the app's own dialogs. Each line is one captured dialog:

```json
{"command": "Filter > Example > Sample", "image": "sample-dialog.png",
	"controls": [
		{"type": "number_field", "label": "Example amount"},
		{"type": "angle_dial", "label": "Example angle", "box": [0.62, 0.31, 0.71, 0.44]},
		{"type": "static_text", "label": "Example note"}]}
```

- `type` is one control kind. `control_catalogue.normalise` maps the names different readers used onto one name per thing (`ALIASES`). `PASSIVE` kinds are read, never driven.
- `label` is what a person calls the control. It can describe the control rather than quote it, as in "Example preset options" for a gear icon that has no text.
- `box` is optional: the control's area as fractions of the capture, so it holds at any scale. `catalogue_positions.py prepare` draws numbered overlays of what the harness itself finds in each capture (drawn things and OCR lines). An annotator names the items that make up each control, and `merge` writes their union as `box`.

`control_pass.catalogued(rows)` returns a lookup from a menu path to its controls. It matches paths by their words, so a lost ampersand still matches, and keeps the capture with the most controls.

### The drivers: one per control kind

A driver is `Callable[[ProbedSurface, Control], list[Action]]`, in `control_drivers.py`:

- `Control(kind, rect, label, target)`. `target` is the dialog's preview, for tools that act on it.
- `Action(keys, changed, change, opened_popup, text_after)`. `change` is the bounding box of everything that changed.

Every driver measures through `act` or `act_events`. They take a steady shot, read the control's text, send the events, take a second steady shot, compute the changed pixels, close any popup that opened, and read the text again. `changed` is true when pixels changed or the control's text changed. The text matters because a focused Photoshop field blinks its whole box, and the blink mask hides every pixel inside it (`test_a_driven_field_whose_box_blinks_still_shows_its_changes_through_its_text`).

The blink mask is `controls._Steady`. Each `shot()` takes two shots `flicker_s` apart. Pixels that differ between them are blinking. `changed(before, after)` counts a pixel when it is steady in both shots and different, or when it blinks in exactly one of them: focus arriving at a field or leaving it. A pixel blinking in both shots is a caret, which is noise.

Three tables select the driver:

| Table | Used for | Examples |
|---|---|---|
| `DRIVERS` | Controls found by the Tab walk, and catalogued kinds that need the mouse anyway | `number_field`: `drive_number_field` types each sweep value, then the start value. `dropdown` and `radio_group`: `drive_options` goes Home, then Down until the control's own pixels stop changing or repeat, then back. `slider`: `drive_slider`. `checkbox`: Space twice. `button`: `drive_button`. `curve_graph`, `angle_dial`, `histogram_sliders` and the other mouse kinds have click and drag drivers. |
| `PLACED_DRIVERS` | Kinds the probe knows, when the catalogue placed them because Tab never reached them | A checkbox is clicked twice. A dropdown or button is clicked once and what opened is closed. A list box or radio group has each item clicked. |
| `READERS` | Passive kinds | `static_text`, `group_box`, `progress_bar` and `help_link` are read by OCR. `static_image` is read as a pixel hash. A help link opens a browser, so it is only read. |

Drivers put a control back where they can read its start value. `drive_options` stops on the control's own pixels, not the whole dialog, because a pulsing default button or a redrawing preview kept the dialog changing and Down was once pressed 300 times on a five-option list (`test_options_stop_at_the_last_one_while_something_else_in_the_dialog_keeps_moving`).

### The Evidence layer: rows into REA bundles

`parity.observe(identity, observations)` runs `node rea_windows_ui/src/cli.js observe --exe --pid --window --evidence`. That command calls the bridge's own `open_binary` and `observe_native_ui` handlers, appends the Evidence to the observations file, and prints `{evidence_id, pid, window_id, launch_time}`. On failure it prints REA's projected error with its remediation. If Node cannot run at all, `parity.observe` returns an error with `"source": "harness"`. Either way the runner stores the result as `parity` on every row (`test_each_result_row_names_the_parity_observation_of_its_photoshop_process`).

`cli.js bundle` turns the rows into one REA bundle with `linkedBundle({target, rows, observations, controls, code})` in `src/harness.js`:

- `harnessEvidence` makes one record per `results.jsonl` row, with operation `photoshop_<kind>`.
- `controlEvidence` makes one record per `control-actions.jsonl` row, with operation `photoshop_control`. Its parameters are `item_id`, `dialog`, `kind`, `rect`, `label` and `source`. Its result holds the rest of the row, `parity`, and `code`.
- Both use provider `adobe-observed-truth`, authority `controlled-replay`, and an environment with isolation `none`. Their limitations state the method in words (`CONTROL_METHOD`, `CODE_METHOD`).
- `evidenceLinks` holds the parity observation's ID only when the bundle carries that observation. The command prints how many rows are `linked` and `unlinked`.
- Evidence IDs are content digests, so an identical record appears once. REA refuses duplicate IDs.

`rea_evidence.py` is an older, Python-only path used by `run.py` scenarios. It reproduces REA's Evidence ID and bundle manifests, pinned against a bundle REA accepted (`tests/unit/fixtures/rea_accepted_harness_bundle.json`). `_reject_floats` refuses float values, because Python and JavaScript print some floats differently and the ID check then fails. Prefer the Node path for new work: it calls REA's own code.

### The control-to-code map

Three commands build the map, all writing to the local corpus folder or the dataset:

1. `rea_corpus.py` lists every native binary of the install (`manifest`), runs REA's engine-free PE inspections (`inspect`), decompiles image-platform binaries with REA and Ghidra (`decompile`), and wraps REA's Evidence into one bundle (`bundle`). Each step resumes.
2. `plugin_params.py build` reads each filter plug-in's `JSON_PIPL` resource: its menu path, scripting event, and each setting's name and four-letter code. `code_number` turns a code into the 32-bit constant a decompiler prints (`"Exmp"` becomes `0x45786d70`). `functions_using` finds the functions that use it as a whole constant. It writes `plugin-parameters.jsonl`.
3. `control_code.py` writes `control-code.jsonl`. For each `(dialog, label)` in `control-actions.jsonl`, `link_control` returns:
	- `status`: `found`, `waiting` (the binary is not decompiled yet) or `not_found`.
	- `binary`: the plug-in that adds the dialog's menu item, else the app.
	- `via`: `setting` when a plug-in setting of that name exists, else `ui_string` when a decompiled function carries an interface-string literal of the form `"$$$/Example/Key=Label"` whose text is the label.
	- `anchor`: the setting code or the string key.
	- `functions`: the addresses of those functions.

A label with fewer than three letters links to nothing (`test_a_label_that_names_nothing_is_not_linked`). The map is a place to read, matched by name, not proof that a function handles the control. `CODE_METHOD` says so in every record.

## 3. How one dialog is driven, end to end

`control_pass.drive_dialog(surface, expected, dialog, off_limits)` drives one open dialog and returns one row per control. `expected` is the catalogue entry for the dialog, and `off_limits` lists rectangles never to touch.

### Read the labels once

`_drive` reads every word in the dialog first, with `surface.words()`, and groups them into lines. Driving can rename labels, so placement later uses the labels as the dialog opened (`test_controls_are_placed_by_their_labels_as_the_dialog_opened_not_as_driving_left_them`). It also turns the boxes of catalogued command menus into rectangles to avoid.

### Walk the tab stops

`focus_walk` presses Tab up to 80 times and records the changed regions after each press. Focus leaving one control and arriving at the next changes both, so a control is the area that changed on two consecutive Tabs. `_focus_landed` also requires that the area did not change on the Tab before. Something that changes on three Tabs in a row is animation, such as a default button that pulses (`test_a_default_button_that_pulses_on_every_tab_is_not_taken_for_focus`). The walk ends when the first control comes round again. It then rotates the list to start at the control that had focus when the dialog opened.

### Probe each stop, most harmless key first

For each stop, `_drive` skips it if it lies in `off_limits` or on a command menu. Otherwise `focus_on` brings focus there by Tab. A change at the target can be focus arriving or leaving, so one more Tab and a Shift+Tab confirm it. Then `probe(surface, rect, known=stops)` decides the kind from how the control answers keys:

1. **Read the label.** If the control's own text is OK, Cancel or a never-press word, the probe names it a button and sends nothing.
2. **Alt+Down.** If a popup opens, the control is a dropdown. The probe reads the list with `popup_lines`, closes it, and sets `commands` when `lists_commands` finds an entry that ends in an ellipsis or starts with a command word.
3. **Up, then Down if Up did nothing.** A change inside the control means it steps. A change at another tab stop means the arrow keys move focus (WPF does this), so focus is brought back by Tab. A change at a spot that is not a tab stop is the next option of a radio group. `_still` drops changes that also happen with no key pressed.
4. **A typed `7`.** The control is a field only if `7` appears in its text. It is a `number_field` if the arrow keys also changed its text, else a `text_field`.
5. **Slider.** A control that stepped but took no digit is a slider.
6. **Space, last.** A popup means a button that opens a window, and the window is closed. A visible change means a checkbox (no label) or a button. No answer leaves a button or `unknown`.

Alt+Down comes before any arrow key because on some dropdowns an arrow key chooses an entry, and the entry can be a command. In File Info, the probe's first Up ran an entry of a folder dropdown and opened Explorer. Alt+Down opens a list without choosing from it (`test_a_dropdown_listing_commands_is_found_by_opening_its_list_before_any_arrow_key`).

The typed digit must show in the text because pixels alone misled the probe. A button's box redrew when a digit was typed, the probe called it a text field, and the text driver then typed a phrase whose space pressed it (`test_a_button_whose_box_changes_when_a_digit_is_typed_is_not_taken_for_a_field`).

### Drive each walked control

A dropdown whose list holds commands is recorded as `"skipped": "lists commands: opened and read, never chosen"`. A button the probe already pressed is recorded from that press, because a second press can show nothing new (`test_a_button_the_probe_pressed_is_recorded_from_that_press_not_pressed_again`). Every other kind goes to its driver in `DRIVERS`.

### Place what the walk missed

After the walk, `_drive` takes one more shot and works out the catalogued controls still to place:

1. `mouse_candidates` finds everything drawn that is neither a tab stop nor a line of text.
2. `_not_walked` matches walked controls to catalogue entries. An entry with a `box` matches the walked control at that box, and the walked row gets `name` and `catalogued_as`. If the probe called it a different kind, the entry is also placed and driven as the catalogue's kind (`test_a_walked_control_the_catalogue_calls_another_kind_is_driven_as_that_kind_too`). An entry without a box matches a walked control of the same kind within 40 px of its label.
3. `place` positions what is left. An entry with a `box` takes the drawn thing that mostly fills the box, else the box itself, scaled to the dialog as it is now. A passive kind is its label's line. A resize grip is the bottom-right 16 px. The preview is the largest drawn thing left. Any other kind is the nearest drawn thing of its shape (`_fits`) and size (`_sized`) beside its label: same row first, up to 400 px along the row or 200 px away. Each drawn thing is claimed once.
4. `_with_handles` joins a slider track to its pieces on the same row and the small handles just under it.
5. `_place_runs` places kinds no label names, such as a row of three eyedroppers: one onto the only drawn thing that fits, or several onto the one run of like things with exactly that count. Anything less certain stays unplaced (`test_a_run_is_not_guessed_when_the_counts_do_not_match`).

An entry that cannot be placed gets a row with `"placed": false`. Nothing is guessed.

### Drive each placed control

For each placed control, `_drive` checks in this order:

1. A passive kind is read with its `READERS` entry.
2. A tool gets the preview as its `target`.
3. A label that is never pressed is skipped.
4. A catalogued command menu is skipped.
5. Text drawn inside the control's rectangle that is never pressed is skipped. What is drawn where a click lands decides, not the catalogue's label. A dropdown was once placed on a self-drawn OK button, and the click accepted the dialog (`test_a_placed_control_that_shows_ok_is_never_clicked_whatever_the_catalogue_calls_it`).
6. The control goes to `PLACED_DRIVERS`, else `DRIVERS`.

### Retry controls hidden until a button shows them

Some controls exist but answer nothing until a button reveals them. `_drive` keeps every placed control whose actions all had `changed: false` in a `quiet` list. When a placed button changes the dialog, `_retry_shown` drives each quiet control again and records the rows with `retried_after`. If one answers now, the button showed it. The app keeps that layout after Cancel, so the button is pressed once more and that row gets `"put_back": true` (`test_a_control_hidden_until_a_later_button_shows_it_is_driven_then_and_the_panel_put_back`).

### Record what nobody catalogued

A drawn thing that no catalogue entry claimed gets a row with `"source": "drawn"` and `"clicked": false`. An unlabelled icon might delete a preset, so the harness records it for a catalogue update and never clicks it.

### Stop cleanly

`drive_dialog` turns three exceptions into a last row and keeps the rows so far:

- `DialogClosed` gives `"closed_dialog": true`. The row names the control being driven, so you can see what closed the dialog.
- `WindowLeftOpen` gives `"window_left_open": true`.
- `Interrupted` gives `"interrupted"` with the reason, attaches the rows to the exception as `.rows`, and raises it again so the whole run stops (`test_input_stopped_mid_dialog_still_stops_the_run_and_keeps_the_rows_so_far`).

### The rows written

`PhotoshopAdapter._record_control_rows` writes each row twice. The full row, with the text read, goes to `control-actions-full.jsonl` beside the captures in the local corpus. The row passed through `publishable` goes to `control-actions.jsonl` in the dataset. Both get `item_id`, `at` and `parity`. A walked number field, as published, looks like this:

```json
{"item_id": "menu:example@controls", "at": "2026-11-10T03:12:44",
	"parity": {"evidence_id": "ev_3f1c...", "pid": 4312, "window_id": 1180742, "launch_time": "..."},
	"dialog": "Filter > Example > Sample", "rect": [212, 64, 268, 84], "source": "keyboard",
	"kind": "number_field", "label": {"chars": 2, "sha256": "9f2c..."}, "name": "Example amount",
	"catalogued_as": "number_field", "probe": ["arrow keys change it", "typing changes it"],
	"actions": [{"keys": ["ctrl+a", "0", "tab", "shift+tab"], "changed": true,
		"change": [212, 64, 268, 84], "opened_popup": false}]}
```

| Field | Meaning |
|---|---|
| `source` | `keyboard` (Tab walk), `catalogue label` (placed), `drawn` (uncatalogued), or `file dialog`. |
| `kind`, `probe` | The kind and the answers that decided it. |
| `name`, `catalogued_as` | The catalogue entry the walked control matched, or the text beside it. |
| `actions` | One `Action` per step. `text_after` is dropped when published. |
| `read` | A passive control's reading, published as its length and hash. |
| `placed` | `false` for a catalogue entry that could not be placed. |
| `skipped` | Why nothing was sent: off limits, never pressed, a command menu. |
| `retried_after`, `put_back` | The hidden-control retry. |
| `closed_dialog`, `window_left_open`, `interrupted`, `focused` | How driving stopped, or that focus never reached the stop. |

`controls_summary` reduces the rows to the kinds driven with an effect, driven with none, read, and not placed. The runner records it as the spec's `controls` observation.

## 4. Safety rules and the mechanisms behind them

The harness runs on the operator's own desktop, in the operator's own copy of the app. Each rule below has a mechanism in code and a test that fails without it.

### Never take the foreground from the operator

The operator's keyboard and mouse always win.

- `idle.RealInputWatcher` installs low-level keyboard and mouse hooks. Windows marks injected events, so the watcher can tell the harness's own input from the operator's. It keeps only the time of the last real event, never which key or where.
- `idle.PersonInput` decides which real events count. Keys, clicks and the wheel always count. A pointer move counts only once it is more than `DRIFT_PX` (4 px) from where the operator left it. An idle mouse reported 1 px moves about once a minute, which kept an unattended run from ever starting (`test_a_mouse_drifting_a_pixel_on_its_own_is_not_the_person_coming_back`).
- `runner_photoshop.away_after_s` sets the idle threshold. An away run waits `--idle-minutes` (default 20). An attended run (`--now`) waits `ATTENDED_QUIET_S`, 10 s. The watcher runs in both cases, so the operator typing in another app stops an attended run at once. An earlier attended run read an idle time of 10^9 s and kept taking the foreground (`test_an_attended_run_stops_its_input_the_moment_the_person_types`).
- `runner.run_session` runs a spec only while the operator is away and hands each spec `should_stop`. A spec stopped because the operator came back is retried later, not recorded. A spec interrupted `max_interruptions` times while nobody came back is recorded as failed, because another program is taking the foreground.
- `win_input.focus` asks `should_stop` before it touches any window (`test_the_foreground_is_never_taken_from_the_person_once_they_are_back`). It then closes a running screensaver by message, refuses a locked workstation, takes the foreground with `AttachThreadInput`, and checks that the target process now owns it.
- `win_input.perform` checks `should_stop` and the foreground process before every event. A missing foreground window gets 0.5 s to return (`test_no_foreground_window_for_a_moment_is_not_the_person_coming_back`). Any other process stops input. However the plan ends, `release_plan` lets go of the mouse button and every held key, so a held Shift never follows the operator into their next action (`test_a_plan_stopped_part_way_lets_go_of_the_shift_it_was_holding`).
- `may_cancel_now` and `escape_due` never send Escape or Enter once the operator is back.
- To stop between specs, create the file `STOP-RUNNER` in the corpus folder. Ctrl+C also works, and clean-up steps still run.

### Never press what outlives Cancel or leaves for another program

Canceling the dialog afterwards undoes its settings. It does not undo a deleted preset, a saved file or a started browser.

- `controls.NEVER_PRESS` joins three lists: OK and Cancel, which end the dialog. `families.NEVER_PRESS`, which spend credits or send content. `_OUTLIVES_CANCEL`, which act at once on presets, files, settings or the account, act on real files in a file dialog, or leave the dialog for another program (web links, help).
- `never_press(label)` compares the label after undoing the OCR misread of O as 0. A label matches when it equals a listed word or phrase, or starts with one followed by a space.
- The rule applies in three places: `probe` before any key, `drive_button`, and placed controls (by label, and by text drawn under the control). Tests: `test_ok_cancel_and_buttons_that_send_or_spend_are_never_pressed`, `test_a_button_whose_effect_outlives_cancel_is_never_pressed`, and `test_a_button_that_opens_another_program_is_never_pressed`. In the last incident a button that opens a web page was clicked twice and a browser started.
- Drawn things no catalogue entry names are recorded, never clicked (`test_a_drawn_thing_nothing_catalogues_is_recorded_but_never_clicked`).
- `cancel_action` presses a real Cancel button where one exists. Closing a floating dialog with `WM_CLOSE` destroyed its window but left the app's scripting stuck in its modal state.
- `win_input.owned_elsewhere` refuses a shortcut another program has registered system-wide, because that program would act instead.
- `new_adobe_windows` and `_close_new_program_windows` close only windows that another image-platform program opened during the probe, by handle.

### Never choose from a menu of commands

Some dropdowns hold commands, not values. Any key that lands on an entry runs it.

- `lists_commands` flags a list whose entries end in an ellipsis (or what OCR makes of one) or start with a word in `COMMAND_WORDS`. The probe reads the list on Alt+Down, before any arrow key, and `_drive` records it as opened and read, never chosen (`test_a_dropdown_listing_commands_is_opened_and_read_but_nothing_is_ever_chosen_from_it`).
- Some command menus run an entry even on Home or Alt+Down. `control_pass.COMMAND_MENUS` lists them as `(dialog, label)` pairs. A walked stop that overlaps such a menu's catalogue `box`, or a placed control with that label, is never keyed, probed or clicked (`test_a_catalogued_command_menu_is_never_keyed_probed_or_clicked`). The walk can only recognise the stop if the catalogue entry has a `box`.

### Stop when a window will not close

Every key sent after an unclosed window goes to that window.

- `DialogSurface.close_popups` closes what the dialog opened without canceling the dialog. A popup that is itself a dialog with real buttons gets its `cancel_action`, which is Cancel, or OK on a notice, never a button that changes a preference. Other popups get Escape only once they are in the foreground. Self-drawn lists do not take focus, so a blind Escape reaches the dialog. When the popup will not come to the front, a click on the dialog's title bar closes it.
- `controls.close_popups` raises `WindowLeftOpen` if anything is still open afterwards. `drive_dialog` then sends nothing more and writes `"window_left_open": true`. In the incident, a notice that ignored Escape took every key for sixteen minutes (`test_a_window_the_dialog_opened_that_will_not_close_stops_the_drive_and_says_so`).

### Drive file dialogs only inside the sandbox

A Windows file dialog opens wherever the operator last was, and lists their own files.

- `families.controls_scenario(item, sandbox=True)` drives such dialogs only over a scratch document saved in the sandbox folder. Its first step, `require_only_harness_documents`, raises `Blocked` if any document other than the harness's own (`observed-truth-*`) is open. A blocked spec waits and touches nothing, not even its clean-up.
- `DialogSurface.go_to_folder` sets the sandbox path into the file name box with `WM_SETTEXT`, presses Enter, and checks that the dialog is still open, the box is empty and the folder's name is on screen. If any check fails, nothing is driven.
- `file_dialog_parts` finds, by window class, the parts that leave the folder: the folder tree, Back, Forward, Up, the breadcrumb and recent places. They become `off_limits` for `drive_dialog` (`test_a_control_in_an_off_limits_area_is_recorded_but_never_touched`).
- `publishable` with `known_labels` keeps a label only if it is a catalogue label or one of the app's own interface strings, so a file name read in the dialog never reaches the dataset (`test_text_read_in_a_dialog_is_published_only_if_it_is_a_known_photoshop_label`).

### Never lose the operator's work

- `_photoshop_hung` asks Windows (`IsHungAppWindow`) and sends the app nothing, because a scripting call to a hung app never returns.
- `runner.run_session` restarts the app after three failures in a row that `looks_stuck`, at most twice in a row. `PhotoshopAdapter.restart` refuses unless `may_force_quit` holds: the last reading of open documents saw only scratch documents and was taken after the operator's last input.
- `_watchdog` force-quits an app frozen for two minutes under the same condition.

### Publish only what is not proprietary

The dataset and the bundle may leave the machine. The app vendor's text and code may not.

- `publishable(row, known)` turns every reading (`read`) into `{"chars", "sha256"}`. It does the same to a `label` or `name` longer than 40 characters or not in `known`, and drops `text_after` from actions. The hash still shows that a control was read and whether its text changed (`test_what_is_published_carries_no_text_read_off_the_dialog_only_short_labels`).
- Full rows, captures, parity observations (which carry a window screenshot), the OCR environment, the interface-string list and the decompiled code stay in the corpus folder (`ADOBE_REA_CORPUS`), outside the repository.
- `control_code.py` and `plugin_params.py` record binary names, setting codes, string keys and function addresses, never code or text.
- `TopWindow` records a window's class and executable name, never its title, which can name a private file. `window_observation` names only the vendor's windows and counts the rest.
- `photoshop.py` reads named descriptor keys only. The application descriptor also carries the license serial, so it is never dumped whole.
- `scripts/adobe_observed_truth/lesson_gate.py`, in the private repository the harness came from, scans this package for personal data, machine paths, vendor interface strings and agent text. Its interface-string rule allows only the made-up form `"$$$/Example/Key=Label"`. Run an equivalent scan on anything you publish.

## 5. Bring up a new self-drawn app

This section is a procedure. It assumes you have read sections 2 and 3.

### Start on the bundled fixture window

Prove the bridge and your surface on a window you control before you touch a real app.

1. Build the helper and the fixture:

	```
	cd scripts/adobe_observed_truth/rea_windows_ui
	npm ci
	dotnet build helper/ReaWindowsUi.sln -c Release
	```

2. Run the live parity proof. It starts `ReaWindowsUi.Fixture`, a WPF window with a button, a slider and a text box, and drives it through the MCP server as an agent would:

	```
	node live/prove_fixture.mjs <bundle.json>
	```

	It prints the tool list, the target's format and hash, and each step. It writes an Evidence bundle that REA's `import_evidence_bundle` accepts.
3. Write a surface over the fixture window: `shot`, `send`, `popups`, `read_text` and `words`, as in `DialogSurface`. Then run `focus_walk` and `probe` on it.
4. Compare what your walk finds with the fixture's UI Automation tree from step 2. The fixture is the one window where the pixel walk has ground truth. WPF moves focus on arrow keys, so the fixture also exercises the probe's arrow-navigation case (`test_an_arrow_key_that_takes_focus_away_is_navigation_and_focus_is_brought_back`).

### Confirm the target needs this technique

Observe the target app's main window and one dialog with the bridge, modelled on `live/observe_photoshop.mjs`. If the dialog's controls appear as elements with names, use REA's scenario tool instead. If the dialog is a pane with no children, continue.

### Replace the app-specific parts

| Part | Photoshop file | What to write for your app |
|---|---|---|
| Identity | `photoshop.Photoshop.identity`, `_main_window` | Executable path, SHA-256, version, process ID and main window handle. Find the window by class and executable, not title. |
| Dialog listing | `photoshop.list_dialogs`, `blocking` | Which top-level windows of the process are modal dialogs. New classes keep appearing, so test each one you meet. |
| Dismissal | `cancel_action`, `accept_action`, `answer` | How each dialog class cancels cleanly. Prefer a real Cancel button. Check that the app's modal state ends, not only the window. |
| Opening a dialog | `PhotoshopAdapter._drive_dialog_controls`, `uxp_bridge.py` | The app's own command route if it has one (scripting, a plug-in, a command ID), else a keyboard shortcut through `_press`. |
| Surface details | `DialogSurface` | `is_popup` (which new windows are not popups), `close_popups`, `flicker_s`, and the OCR polarity in `prepare_for_ocr`. |
| Never-press words | `controls._OUTLIVES_CANCEL`, `families.NEVER_PRESS`, `COMMAND_WORDS`, `COMMAND_MENUS` | The app's own destructive, sending and outward buttons, in the app's language. |
| Held-back commands | `families._NOT_DRIVEN`, `CLOUD` | Commands whose controls must never be driven: generative features, uploads, account actions. |
| Interface strings | `ocr_correct.STRINGS_FILE`, `known_labels` | The app's own labels, extracted locally, for OCR correction and the publish filter. |
| Catalogue | `dialog-controls.jsonl`, `catalogue_positions.py` | Capture each dialog, list its controls with kinds and labels, then add boxes. |
| Evidence wording | `rea_windows_ui/src/harness.js` | The provider, the operation names (`photoshop_*`), `METHOD`, `CONTROL_METHOD` and the limitations. |
| Code map | `plugin_params.py`, `control_code._UI_STRING` | The app's own plug-in metadata and interface-string format, if it has them. |

### Keep the parts that carry over

These modules know nothing about Photoshop. Keep them and their tests:

- `controls.py`: the walk, the probe, the blink mask, `never_press`.
- `control_drivers.py`: the drivers and `act_events`.
- `control_pass.py`: placement, retries, `publishable`. Only `COMMAND_MENUS` is app data.
- `win_input.py`, `idle.py` and `runner.py`: input, the operator guard, and the session loop.
- `capture.py`, `input_plan.py` and `parity.py`.
- `rea_windows_ui/`: the bridge, `linkedBundle` and the helper.

### Turn every incident into a test first

Each surprise on a real dialog is a new rule. Write a fake that reproduces it, in the style of `FakeDialog` or `Widget`, with a docstring that tells what happened. Watch the test fail, then fix the code. The tests named in sections 3 and 4 all follow this pattern.

### Run attended, then away

Run one dialog attended with `--now --only <item id>`, watching it. Read its rows in `control-actions-full.jsonl` before you let it run while you are away.

## 6. Run it

This section covers setup, the commands in order, and the tests. Run every `python -m` command from `code/`, so that the `scripts` package is importable.

### Set up the machine

You need Windows 10 or 11 with a desktop session.

1. Install Python 3.12 (the version the tests were run with), then the packages the harness imports:

	```
	python -m pip install numpy opencv-python Pillow pywin32 psutil pytest
	```

2. Install Node.js 24 or later, then the bridge's locked dependencies:

	```
	cd scripts/adobe_observed_truth/rea_windows_ui
	npm ci
	```

3. Install the .NET 9 SDK, then build the UI Automation helper and its fixture:

	```
	dotnet build helper/ReaWindowsUi.sln -c Release
	```

4. Build one OCR reader. For Windows OCR, run `dotnet build scripts/adobe_observed_truth/win_ocr -c Release`. For RapidOCR, which read more labels, create a virtual environment at `<corpus>/ocr-venv` with `rapidocr` 3.x. `dialog_surface.ocr_command` picks RapidOCR when that environment exists.
5. Choose a folder outside any repository for the local corpus and set `ADOBE_REA_CORPUS` to it. Without it, `corpus.CORPUS` is `adobe-rea-corpus` in the working directory. The corpus holds `captures/`, `sandbox/`, `ocr-venv/`, the interface-string list (`photoshop-ui-strings.txt`), the decompiled binaries and their `manifest.json`, `parity-observations.jsonl`, `control-actions-full.jsonl` and the `STOP-RUNNER` file.
6. For Photoshop only, install the UXP helper plug-in as `uxp_helper/README.md` describes, then check it with `python -m scripts.adobe_observed_truth.uxp_bridge`.
7. For the code map only, REA runs as `npx -y rea-agents@6.8.0`, and Ghidra and a Java runtime are found through `rea_corpus.GHIDRA_ENV`.

The dataset folder holds the app's inventory and catalogue and receives the results: `inventory.jsonl`, `dialog-controls.jsonl`, `control-families.jsonl`, `results.jsonl`, `control-actions.jsonl`, `plugin-parameters.jsonl` and `control-code.jsonl`.

### Run the harness

1. Write one spec per catalogued dialog that may be driven:

	```
	python -m scripts.adobe_observed_truth.control_pass --dataset <dataset>
	```

	It writes `control-families.jsonl` and prints how many dialogs it queued.
2. Run the specs. Without `--now` the runner waits until you have been away for `--idle-minutes`:

	```
	python -m scripts.adobe_observed_truth.runner_photoshop --dataset <dataset> --specs control-families.jsonl
	python -m scripts.adobe_observed_truth.runner_photoshop --dataset <dataset> --specs control-families.jsonl --now --only <item id>
	```

	It prints the parity observation, the number of specs queued, then one line per spec with its status. `--limit N`, `--retry-failed` and `--again` (with `--only`) change what runs. A run resumes after the last result written to `results.jsonl`.
3. To build the code map, run the corpus steps, then the two link steps:

	```
	python -m scripts.adobe_observed_truth.rea_corpus manifest --out <corpus>
	python -m scripts.adobe_observed_truth.rea_corpus inspect --out <corpus>
	python -m scripts.adobe_observed_truth.rea_corpus decompile --out <corpus>
	python -m scripts.adobe_observed_truth.plugin_params build --corpus <corpus>/photoshop --dataset <dataset>
	python -m scripts.adobe_observed_truth.control_code --corpus <corpus> --dataset <dataset>
	```

	`control_code` prints a summary with counts by status and by `via`, and the binaries still waiting.
4. Build the linked bundle:

	```
	node scripts/adobe_observed_truth/rea_windows_ui/src/cli.js bundle --exe <path to Photoshop.exe> \
		--results <dataset>/results.jsonl --observations <corpus>/parity-observations.jsonl \
		--controls <dataset>/control-actions.jsonl --code <dataset>/control-code.jsonl --out <bundle.json>
	```

	It prints `{"records": ..., "linked": ..., "unlinked": ...}`. A high `unlinked` count means rows whose parity observation is not in the observations file.
5. Import the bundle with REA's `import_evidence_bundle` tool. To connect it to what UI Automation could not read, record the gap with REA's `record_unknown` and resolve it with `update_unknown`, citing the harness Evidence.

### Run the tests

The Python tests need nothing outside `code/`. `pyproject.toml` puts the folder on the path, and every test uses fakes in place of Windows, the app and REA:

```
cd code
python -m pytest
```

All 390 tests pass at the time of writing. Run `python -m pytest -q` to count them again.

The bridge has its own tests. Run `npm test` in `rea_windows_ui/` for the Node seams, and `dotnet test helper/ReaWindowsUi.sln` for the helper.
