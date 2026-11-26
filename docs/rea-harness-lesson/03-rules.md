# Rules and the bugs behind them

This page has three parts. The operator's standing rulings, each with its reason and the incident that produced it. A table of the bugs found live, each with the rule it became and the test that now locks it. And a short guide to steering an agent through work like this.

The story is in [01-story.md](01-story.md) and every operator message is in [02-operator-log.md](02-operator-log.md). Quotes are lightly cleaned of typos, with the operator's wording kept.

## Part A: The operator's standing rulings

### Read the help for the installed versions before decompiling anything

> Before we bring in any binary decompiling, we first need the help files for the versions of the programs we actually have installed, the ones you are going to look at with REA.

- **Why.** Documented behavior has to be pinned to the exact versions under study before code is read. Otherwise you compare code against the wrong release's claims.
- **Incident.** The design studio's notes were pinned to Photoshop 2025 while the help described 2026, and about 20 of their claims were wrong. He then narrowed the scope to the 2026 releases, the ones REA would examine.

### Independent review is how you stop the model lying

> Run an adversarial review against that to ensure that the model doesn't lie to us. Because I know how you are: you like to take the shortest route.

He asked for verification by several subagents that share none of the session's context, and for two readers: a structural extraction plus an independent reader of the rendered page, with the rendered page settling disagreements.

- **Why.** An agent checking its own work passes its own mistakes.
- **Incident.** Reader B, run by independent subagents, found about 26,600 rewritten links, garbled mailto links, missing accordion questions, and dropped videos. The agent's own checks had passed all of them.

### Use the real browser, and stay inside the site's limits

> Through the real Chrome browser.

- **Why.** Headless capture was refused, and disguised capture is evasion.
- **Incident.** The agent disclosed that an earlier crawl had spoofed the browser identity. When the operator later said "I think initially I would try to get around it", the agent declined to use fresh profiles, IP changes, cleared cookies, or spoofing, and measured the limit instead. That line was the agent's, and the operator accepted it.

### Use data, not guessed constants

> Why would the crawler pause for 3 hours? We use data for that.

> Remember, we use data to find out what we are missing.

> n=5 is not enough for a representative sample.

- **Why.** Every constant the agent guessed was wrong in a way the log could show: the 3-hour pause, the step-down rule, and a schedule fitted to five blocks.
- **Incident.** Asked for "an exact figure", the agent re-read its records and retracted a "second block" that had been a Chrome tab freeze. The operator then turned the variable from volume into rate: "Why don't we make that the constant tick of the clock?" He also asked for one change at a time, after a clean test: "Wait for a successful test first before changing that."

### "We watched it happen", not "the help says"

- **Why.** The help contradicts itself. It gives both 20 and 50 for the default history depth, and states a maximum zoom below the 12,800% the harness observed.
- **Incident.** The first harness scenarios. Every behavior claim is now backed by an observation in an Evidence bundle.

### Land everything in one REA ledger

> I would go with the REA-format bundle so everything can land in one ledger.

- **Why.** One store with one identity scheme means observations, decompile findings, and hooks can be cross-referenced and verified by REA itself.
- **Incident.** The agent recommended a simpler side format linked by hashes. The operator overruled it. REA's `import_evidence_bundle` then verified every harness record.

### Map everything first, then choose

> No, because our contracts might be insufficient. We need to know with REA how everything works, then we can choose what we want to implement.

> You shouldn't prioritise what you think [the design studio] needs. You should be able to capture all of them. Remember, that was driven by prose and I couldn't get it right.

- **Why.** He had built an earlier version of the studio by guiding an agent with prose alone, and in his words he couldn't get it right. Choosing what matters is his job, not the agent's. He wants to look at the result and say "yeah, I know this, I've seen this before".
- **Incident.** The agent proposed narrowing the work to the behaviors the studio already relied on, and later wanted to drive only the controls the studio needed. The app's own inventory, not the help, became the denominator.

### Static analysis is a first-class source

> Why are you not running REA's decompiler on everything? Because it provides much more layered data than watching alone.

- **Why.** Code shows defaults, limits, and wiring that watching cannot.
- **Incident.** The agent had framed decompiling as a narrow last resort. It then decompiled all 617 image-platform binaries.

### Drive REA the way REA wants to be driven, with 1:1 parity, and design before building

> Drive this like REA wants to be driven. And the tools we needed to make, i.e. the Photoshop harness, I think need to match what the Mac version does for REA.

> What I want is an equivalent process to what the macOS tools do, so we need to really think about that before we build anything. I want 1:1 parity.

- **Why.** A tool that writes REA's Evidence through REA's own code is checked by REA. A home-grown format is not.
- **Incident.** Asked "Is this how REA should be run?", the agent admitted it had drifted into text search over decompiler output and its own result format. It then read REA's installed source, wrote a design, and built `rea_windows_ui` only after "Go ahead."

### Every control type you have seen must be drivable

> If Windows UI can't drive them because, as you said, the image platform draws its own, the harness should be able to drive every type of control we have seen.

- **Why.** REA cannot see inside self-drawn dialogs. Pixels and real input can.
- **Incident.** The agent admitted the harness could not drive every visible control. The answer was the pixel-driven control pass and a coverage gate that fails for any control type without a live, effective drive.

### Use the TDD and engineering-principle skill sets for all code work

> Always, for any code work, use [the TDD and engineering-principle skill sets].

> Keep going. Just use [them]; that is my one constraint.

- **Why.** Structure, not prose, is what he relies on: test-first loops, a two-axis review (Standards and Spec), and root-cause diagnosis.
- **Incident.** A context compaction dropped the rule, and he restated it. The Spec review then caught dialog text being published, and the code review caught the force-kill risk to his unsaved work.

### A question is not an order

> Don't do anything yet, these are just questions.

> This is just a question for now. Don't start any work yet.

- **Why.** He needs to think with the agent before it changes anything.
- **Incident.** Several design turns, including the 1:1 parity design, were answered and agreed before any code was written.

### Control passes explicitly, both ways

> Force quit, but hold until my order.

> You may. I am done typing on the computer. You have the conn.

> I think you should hold its hand while it runs.

- **Why.** The harness and the operator share one keyboard, mouse, and desktop.
- **Incident.** A live run ended with Photoshop hung. The agent asked before force-quitting, then held until "You may continue."

### Probes run only when the operator is truly away

> If you can set up a watcher for any mouse movement or keyboard clicks, then when I am truly not at the machine the probes can run.

- **Why.** Injected input must never fight a person's input.
- **Incident.** The Windows idle timer counts injected input. The idle gate in `idle.py` reads the "injected" flag instead and records only when real input happened, never what it was.

### Nothing should need the operator after every restart

> I think that needs to be installed permanently, because that will get tedious, especially because I might not be here to help.

- **Why.** A step that needs a human each time is a defect in an unattended tool.
- **Incident.** The UXP helper first took three manual setup steps.

### Consent is per action

- **Why.** One approval does not carry over to the next action.
- **Incident.** He approved each of these one at a time: installing a dependency ("Yes, you may install that dependency"), a factory-preferences reset, a single force-push, deleting duplicates ("Agree, and delete the dups"), stopping a job he had started ("I agree. We can retry that DLL later"), and a force-quit.

### Never publish proprietary code; do publish the learnings

> I agree we should never publish proprietary code, but the learning we gain should be published.

- **Why.** The learnings are what the studio needs. The image platform's code and text are not the operator's to publish.
- **Incident.** The agent extended the rule to dialog text, interface strings, and plug-in internals. Records keep only binary names, codes, string keys, and function addresses. Photoshop's interface strings stay on the machine as an OCR spell-check list.

### Leave other agents' work alone

> WSL is off-limits. My Codex agents are using it as we speak.

> Let it carry on.

- **Why.** Other agents run on the same machine.
- **Incident.** The agent twice offered to stop WSL to free memory. Later it found a parallel session and asked before sending it a note. When another program kept taking the foreground, it left that program alone.

### Run what you can now, and use help where you need it

> Why don't you run what you can run now and then await my return to do the rest.

> If necessary, use subagents, as many as needed.

- **Why.** Not everything waits on the operator.
- **Incident.** The agent asked for an unlocked PC when only the input scenarios needed one.

### Set a measurable target, and accept an honest limit

> Ideally I want a 95% or higher score. I want an A, but I will take the best I can get.

- **Why.** A number turns "good enough" into a test.
- **Incident.** OCR reached 97.5% on a 40-dialog answer key. The agent named the limits itself: the key is small, and the corrections were tuned on it.

### Rules the agent recorded as standing during the work

These grew out of incidents in the session and were saved by the agent as standing rules:

- Cloud and AI features are discover-only: never Generate, Submit, or Share.
- Never sign out.
- Never run a command that sends content to the image platform.
- Never record license data, serial data, or private paths.
- Live tests of new harness code use only the agent's own synthetic fixture window.
- File dialogs are driven only inside a sandbox folder.
- A button whose effect outlives Cancel is never pressed.
- A button that opens another program is never pressed.

### Teach from the REA work, distilled and gated

> We show and teach from that point, not all of the private project's lessons. We're teaching what we learned with REA, showing the harness code we built and the code we built for REA so it could have its own native parity.

- **Why.** The package leaves a private repository.
- **Incident.** The operator first asked for raw transcripts. The agent pushed back, and he agreed to this distilled account behind an automated redaction scanner.

## Part B: Bugs found live

Python tests are in `code/tests/unit/`, in files named `test_adobe_observed_truth_<area>.py`. The last column gives `<area>` and the test name. Bridge tests are in `code/scripts/adobe_observed_truth/rea_windows_ui/test/` and are quoted by their test titles. Where no shipped test locks a rule, the column gives a test idea.

### Setup and capture

| Symptom | Root cause | Rule it became | Test that locks it |
| --- | --- | --- | --- |
| Claude Desktop showed no REA after setup reported success. | A Microsoft Store install reads its settings from outside the package folder that REA's setup wrote to. | "Done" means the consumer read the file. Check where the app reads its config, not where setup wrote. | Test idea: after setup, read the config path that the running Desktop reports and assert the `rea` entry is there. |
| The receiver rejected a correct help page. | An emoji counts as 2 characters in JavaScript (UTF-16) and 1 in Python, so the length check disagreed. | Measure lengths in one unit on both sides. | Test idea: round-trip a page containing an astral-plane character through both ends of the check. (The crawler is not in this package.) |
| Cleaning bugs could not be repaired offline. | Only cleaned text was saved, not raw HTML. | Keep the raw source next to any derived text. | Test idea: assert every saved page has its raw HTML beside the cleaned text. |

### Decompiling

| Symptom | Root cause | Rule it became | Test that locks it |
| --- | --- | --- | --- |
| Overnight, one Ghidra process hung about 9 hours, and every later job failed with a misleading "JDK not found". | REA's per-function decompile timeout was unset. | Always set a per-function limit, in committed code, not only in an environment variable. | Committed as `REA_GHIDRA_DECOMPILE_TIMEOUT_SECONDS` in `rea_corpus.py`. Test idea: assert the decompile environment always carries a finite per-function limit. |
| A Rust library stalled the queue for more than 15 hours, twice. | One oversized binary held the queue. | Stop it and retry it later, alone, with a shorter limit. Ask first when the operator started the job. | Test idea: a queue test that a binary past its time budget is set aside and the rest proceed. |

### Running Photoshop unattended

| Symptom | Root cause | Rule it became | Test that locks it |
| --- | --- | --- | --- |
| The harness could bind an older Photoshop. | Three releases are installed, and the default scripting connection binds whichever registered last. | Refuse unless connected to the 2026 release. | `uxp_bridge`: `test_a_helper_answering_from_the_wrong_photoshop_is_refused`. Test idea for the COM side: a fake app reporting 26.x is refused. |
| Every scripting refusal raised a modal that froze Photoshop. | Script dialogs were on. | Switch script dialogs off for each scenario and restore the setting afterwards. | `dialogs`: `test_a_failed_restore_does_not_hide_the_scenario_error`. |
| A probe changed the operator's brush settings and the restore was not checked. | Tool options and colors are the user's persistent state. | Snapshot tool state, write it back byte for byte, and report whether it reads back identical (`ps_tools.preserved_tool_state()`). | Test idea: a fake whose restore silently fails is reported as not identical. |
| The screensaver could not be closed. | On Windows 11 it runs on its own desktop, one window per monitor. The fake modelled the normal desktop. | Prove operating-system behavior live. Close the screensaver without spending simulated input. | `screensaver`: `test_running_screensaver_is_closed_once_and_awaited_until_gone`, `test_screensaver_without_a_closable_window_is_refused_without_waiting`. |
| Photoshop could not be brought to the front after the screensaver (0 of 5). | The machine's foreground lock was at its maximum. | Join the focused window's input queue (`win_input._take_foreground`), never send a keystroke to get focus. | Proven 5 of 5 live. Test idea: assert focus never sends a key event. |
| Every script failed, even trivial ones. | A hidden image-platform feedback survey sat behind other windows. The dialog check knew only Photoshop's own dialog class. | Pre-flight: decline the survey for good, never Submit, wait until it has closed, refuse to start behind any other dialog, and never click a checkbox whose state cannot be read. | `dialogs`: `test_survey_is_declined_for_good_and_never_submitted`, `test_preflight_waits_until_the_survey_has_closed_before_the_scenario_starts`, `test_preflight_refuses_to_start_behind_another_dialog_and_names_it`, `test_survey_box_with_unreadable_state_is_not_clicked_in_case_it_is_already_ticked`. |
| A clean-up error hid the real error. | The clean-up exception replaced the original one. | The first error wins, and the clean-up failure is attached as a note, in one place. | `dialogs`: `test_a_scenario_failure_is_headlined_by_its_first_error_not_the_cleanup`. `runner`: `test_a_failed_step_still_runs_every_clean_up_step_after_it`. |
| The idle detector could not tell the person from the harness. | The Windows idle timer counts injected input, and it overflowed on a long uptime. | Use low-level hooks with the "injected" flag. Record only when real input happened. Release held keys and buttons when the person returns. | `idle`: `test_a_running_probe_yields_the_moment_the_person_comes_back`, `test_stopping_mid_drag_releases_the_button_then_the_held_keys_in_reverse`, `test_a_mouse_drifting_a_pixel_on_its_own_is_not_the_person_coming_back`. |
| The UXP helper could not reach the harness. | Photoshop's plug-in network permission did not cover the address spelling in use. | Allow both spellings of the local address on one port only. Listen on this machine only. | `uxp_bridge`: `test_the_plugin_is_allowed_to_reach_exactly_the_bridge_port_and_nothing_else`, `test_the_bridge_listens_on_this_machine_only`. |
| Self-drawn modal dialogs were invisible to the dialog check. | Their OK and Cancel are not Windows buttons, and the main window stays enabled. | Recognise each dialog kind and close it the matching way: a close message, a real Cancel press, or Escape. | `dialogs`: `test_a_photoshop_drawn_dialog_blocks_even_without_windows_buttons`, `test_a_real_cancel_button_is_pressed_and_only_self_drawn_dialogs_are_closed`. |
| The About box stopped the whole run. | It scrolls and has no buttons, so it was not a dialog. The runner re-ran it first after each restart, and found the main window by a title that changes. | Any floating Photoshop window is a dialog, dismissed with Escape. The probe that likely caused a hang is recorded as failed and skipped. Find the main window by class. | `dialogs`: `test_a_floating_window_with_no_buttons_still_blocks_and_is_dismissed_with_escape`. `runner`: `test_a_probe_that_hangs_photoshop_is_recorded_and_the_rest_are_retried`. |
| Close commands were recorded as failures. | The recorder read the history of a document that had just closed. | Record "no document open" instead. | `runner_photoshop`: `test_a_command_that_closed_the_document_is_recorded_as_such_not_as_a_failure`. |
| A probe opened the Creative Cloud app, and Bridge. | A menu command launched another image-platform program. | Clean-up closes only new windows from other image-platform programs. With no "before" snapshot it closes nothing. | `runner_photoshop`: `test_only_windows_that_appeared_during_the_probe_from_other_adobe_programs_are_closed`, `test_without_a_window_snapshot_nothing_is_closed`. |
| The runner could force-kill Photoshop with the operator's unsaved work open. Found by code review while the runner was live. | Each probe failed the scratch-only check, each failure counted toward a restart, and the restart force-killed Photoshop. | With the person's documents open, the runner waits and counts nothing. Force-quit only if the last check saw scratch work alone. | `runner`: `test_a_spec_blocked_by_the_persons_own_document_waits_and_never_restarts_photoshop`. `runner_photoshop`: `test_photoshop_is_force_quit_only_if_the_last_check_saw_nothing_but_scratch_work`, `test_the_watchdog_never_kills_photoshop_when_the_persons_work_may_be_open`. |
| The runner restarted into a Photoshop still stuck mid-command and waited forever. | Startup assumed Photoshop would answer. | Startup restarts Photoshop if it does not answer within about 3 minutes. | Test idea: a startup test with a fake that never answers. |
| Photoshop refused scripting with no visible dialog. | The Filter Gallery is a separate top-level window. | A full-window filter dialog blocks, and its Cancel is pressed. | `dialogs`: `test_a_full_window_filter_dialog_blocks_and_its_cancel_button_is_pressed`. |
| Vanishing Point timed out. | Its OK stays grayed out until a plane is drawn, and the harness kept clicking it. | Read whether a button is enabled. If it is not, cancel. Click the plane only on a confident image match. | `dialogs`: `test_a_greyed_out_ok_is_never_pressed_the_dialog_is_cancelled_instead`. `workspace`: `test_the_found_area_looks_like_the_known_image`, `test_a_perspective_plane_is_four_clicks_on_an_inset_rectangle_of_the_image`. |
| A menu command opened a cloud-upload dialog. | The command sends content to the image platform. | Never run a command that sends content, from any menu. | `families`: `test_a_command_that_sends_content_to_adobe_is_never_run_even_from_the_file_menu`, `test_no_spec_anywhere_presses_a_button_that_spends_credits_or_uploads`. |
| Probes on a white canvas showed almost nothing. | Most filters leave white white. | Probe on a chart drawn by code, with a band for each kind of tool. | `test_images`: `test_the_chart_is_pixel_for_pixel_the_same_every_time`, `test_the_named_chart_regions_cover_every_pixel_exactly_once`. |
| Captures filled the disk. | Most dialogs are captured byte for byte the same on every run. | Keep one file per distinct image, with a manifest from every name to the kept copy. | `capture_store`: `test_identical_captures_keep_one_file_and_every_name_still_resolves`. |

### The Windows bridge

| Symptom | Root cause | Rule it became | Test that locks it |
| --- | --- | --- | --- |
| A live parity test read the operator's open Notepad tabs and closed Notepad. | The test aimed at a real app on his desktop. | Live tests of new code use only the agent's own fixture window (`helper/ReaWindowsUi.Fixture`, `live/prove_fixture.mjs`). | Helper: `An_element_owned_by_another_process_is_refused` in `UiTreeTests.cs`. Test idea: the live proof refuses any target that is not the fixture. |
| Canceling never reached a running scenario. | Not recorded in detail. Found by an independent review against REA's own behavior. | Match REA's interruption behavior exactly. | `scenario.test.js`: `a caller cancellation stops the scenario and marks the step cancelled`. `server.test.js`: `a request the client cancelled is reported cancelled, read from the request`. |
| The deadline never stopped a stuck helper. | Not recorded in detail. Found by the same review. | Match REA's deadline behavior. | `helper.test.js`: "a helper still running at the deadline is stopped and reported as ETIMEDOUT". `scenario.test.js`: "the helper call gets a signal that aborts at the deadline". |
| A helper crash lost the partial results. | Not recorded in detail. Found by the same review. | Keep the partial observation, as REA does. | `scenario.test.js`: "a helper that dies mid-scenario fails the step and keeps the partial report". `server.test.js`: "a failed scenario reports a REA-style error with its partial observation". |

### Settings sweeps and OCR

| Symptom | Root cause | Rule it became | Test that locks it |
| --- | --- | --- | --- |
| Unsharp Mask reported its defaults while applying a new value. | A dialog's reported settings are not proof. | The pixel hash proves a value was applied. The defaults run three times to show determinism. | `sweeps`: `test_each_setting_is_swept_alone_and_the_defaults_are_replayed_three_times`. `harness.test.js`: "a setting sweep says the pixels, not Photoshop's reply, prove the value was applied". |
| 25 commands gave a different hash every run. | They are random. | One hash means nothing for these. Sample about 60 runs. | Test idea: a command whose default replays disagree is marked random, not swept. |
| OCR correction damaged correct text. | Each word was snapped to the nearest known label, so "Radius:" became "Radius" and "Calculate" became "Calculator". | Change only words Photoshop never shows, by known confusable characters. Never guess between equal fits. Never lower-case a capital. | `ocr_correct`: `test_a_word_two_labels_fit_equally_well_is_not_guessed`, `test_a_capital_read_is_never_made_lower_case`, `test_punctuation_read_around_a_known_word_is_kept`. |

### Driving self-drawn dialogs by pixels

| Symptom | Root cause | Rule it became | Test that locks it |
| --- | --- | --- | --- |
| The Up key moving focus was read as a value change. | Navigation and value changes look alike in pixels. | An arrow key that takes focus away is navigation, and focus is brought back. | `controls`: `test_an_arrow_key_that_takes_focus_away_is_navigation_and_focus_is_brought_back`. |
| Fields kept test text after driving. | Fields were not emptied. | Empty a text field that started empty. | `control_drivers`: `test_an_empty_text_field_is_emptied_again_afterwards`. |
| Buttons were pressed twice. | Both the probe and the driver pressed them. | Record the probe's press and do not press again. | `control_pass`: `test_a_button_the_probe_pressed_is_recorded_from_that_press_not_pressed_again`. |
| Labels did not match after driving. | Driving had renamed them. | Place controls by their labels as the dialog opened. | `control_pass`: `test_controls_are_placed_by_their_labels_as_the_dialog_opened_not_as_driving_left_them`. |
| Text read in a tight crop came out garbled. | OCR needs context around the text. | Read a region with a margin of the dialog around it. | `dialog_ocr`: `test_a_region_is_read_with_a_margin_of_the_dialog_round_it_kept_inside_the_dialog`. |
| Up to 80 characters of dialog text sat in published rows. Found by the Spec review. | Rows carried text read off the dialog. | Published rows carry no dialog text. Only known labels pass `publishable`. | `control_pass`: `test_what_is_published_carries_no_text_read_off_the_dialog_only_short_labels`, `test_text_read_in_a_dialog_is_published_only_if_it_is_a_known_photoshop_label`. |
| Typing "7" visibly worked, but the field was called a button. Levels found 7 stops in one run and 1 in the next. | A focused field blinks its whole box, and the Tab walk ignored anything that had ever blinked. | A field's own text is its answer. A blink starting or stopping is focus moving. A pulsing default button is not focus. | `controls`: `test_a_field_whose_whole_box_blinks_is_still_told_apart_by_its_text`, `test_controls_whose_only_focus_sign_is_a_blinking_box_are_all_found`, `test_a_default_button_that_pulses_on_every_tab_is_not_taken_for_focus`, `test_another_stop_pulsing_while_a_field_is_probed_is_not_taken_for_focus_moving`. |
| Long dialogs timed out, and a dialog closing mid-drive lost its rows. | Limits were too short for real dialogs: they went from 90 s to 30 minutes to 3 hours. | A dialog that closes mid-drive keeps its rows and names the control that closed it. | `control_pass`: `test_a_dialog_that_closes_while_driven_keeps_the_rows_so_far_and_names_what_closed_it`. |
| Hue/Saturation kept closing. | Tooltips counted as open lists, and a blind Escape reached the dialog. | Ignore tooltips and shadows. Close lists safely. | `dialog_ocr`: `test_a_tooltip_or_a_shadow_is_not_something_the_dialog_opened`. |
| A field at its maximum looked inert, and "100%" was typed wrongly. | Up does nothing at the top of a range, and capitals and symbols were sent as bare keys. | Try Down when Up does nothing. Type characters as themselves. | `controls`: `test_a_field_at_the_top_of_its_range_is_still_a_number_field`. `win_input`: `test_a_capital_or_a_symbol_is_typed_as_that_character_not_its_bare_key`. |
| A file dialog opened on the operator's real documents folder. The agent caught it live. | File dialogs open where the user last was. | Steer to a sandbox folder and confirm it before driving. Fence off the folder tree, Back, Up, breadcrumbs, and recent places. | `families`: `test_a_file_dialog_is_driven_only_in_the_sandbox_on_a_scratch_document_saved_there`. `control_pass`: `test_a_control_in_an_off_limits_area_is_recorded_but_never_touched`. |
| File Info lost the foreground, and later the star rating could not be driven. | First theory, wrong: Photoshop's own helper took focus. Real cause: another desktop program took the foreground. | The interruption names the process that took the foreground. The harness stops and does not touch that program. | `win_input`: `test_an_interruption_names_the_process_that_took_the_foreground`. |
| Curves closed itself during the drive. | Typing a 7 changed pixels inside some buttons, so they were taken for text fields, and a typed space pressed them. | A control is a field only if the typed digit shows in its text. | `controls`: `test_a_button_whose_box_changes_when_a_digit_is_typed_is_not_taken_for_a_field`. |
| Catalogued control kinds were never driven. | When Tab reached a control the catalogue calls another kind, only the probe's guess was driven. | Drive it as the catalogue's kind too. The gate was not loosened. | `control_pass`: `test_a_walked_control_the_catalogue_calls_another_kind_is_driven_as_that_kind_too`. |
| An interruption threw away every row. | Rows were kept only on a clean finish. | Keep the rows. The last row names the control being driven, and the run still stops. | `control_pass`: `test_input_stopped_mid_dialog_still_stops_the_run_and_keeps_the_rows_so_far`. |
| A notice popup inside Liquify could not be closed. | The popup had no Cancel. | Cancel, or OK for a notice, and never "don't show again". If it still will not close, stop driving that dialog, mark the row `window_left_open`, and send no more keys. | `control_pass`: `test_a_window_the_dialog_opened_that_will_not_close_stops_the_drive_and_says_so`. `dialogs`: `test_a_notice_without_cancel_is_acknowledged_with_ok_not_more_info_or_dont_show`. |
| A click on the thumbnail grid "changed nothing", and the run changed the operator's saved layout. | The panel was hidden at open, and a button driven seven controls later revealed it. | Retry a quiet control after a later button changes the dialog. Then press the revealing button again to leave the dialog as the person had it. | `control_pass`: `test_a_control_hidden_until_a_later_button_shows_it_is_driven_then_and_the_panel_put_back`. |
| A dropdown driver pressed Down up to 300 times. | An animation elsewhere in the dialog kept "something changed" true. | Stop when the control itself stops changing or repeats an option. Proven live: Levels went from 255 presses to 4. | `control_drivers`: `test_options_stop_at_the_last_one_while_something_else_in_the_dialog_keeps_moving`. |
| A button in File Info started a web browser. | The button leaves the dialog for another program. | A button that opens another program is never pressed (`NEVER_PRESS` in `controls.py`). | `control_drivers`: `test_a_button_that_opens_another_program_is_never_pressed`. |
| A dropdown in File Info listed commands, not values. | Choosing from it would run a command. | A catalogued command menu is never keyed, probed, or clicked. | `control_pass`: `test_a_catalogued_command_menu_is_never_keyed_probed_or_clicked`. `controls`: `test_a_dropdown_listing_commands_is_found_by_opening_its_list_before_any_arrow_key`. |
| Image Size left a stray window open, at a different control on each run. | Not a window the dialog opened: `PSDragFeedback`, the image platform's transient drag overlay, named by the row's new `left_open` record. Counted as a popup, it could never be closed and blocked refocusing the dialog. | Record the class of any window left open; windows beside a dialog that it did not open (tooltips, shadows, the drag overlay) are not popups. | `test_a_window_the_dialog_opened_that_will_not_close_stops_the_drive_and_says_so`, `test_photoshops_drag_feedback_overlay_is_not_something_the_dialog_opened` |

### Help claims

| Symptom | Root cause | Rule it became | Test that locks it |
| --- | --- | --- | --- |
| 130 claims were wrongly flagged macOS-only. After the fix, 5 were. | Ordinary words matched a macOS-only pattern. | Only real macOS-only wording makes a claim macOS-only. | `claim_map`: `test_ordinary_words_command_and_option_do_not_make_a_claim_macos_only`, `test_claims_that_also_work_on_windows_are_not_called_macos_only`. |
| Two copies of the cloud-feature pattern disagreed, and one was too broad. | The pattern was defined twice. | One shared definition. | `families`: `test_filter_render_clouds_is_a_filter_not_a_cloud_service`, `test_cloud_sharing_panels_are_held_back_like_other_cloud_features`. |

### The gate that ties it together

The coverage gate is an executable test: `test_adobe_observed_truth_control_coverage.py`. It reads the private dataset, so it is not shipped in `code/`. For every control type seen in a captured dialog, it requires a driver or a reader, and a live row in which driving that control changed the dialog. A new control type in a new capture fails it until that type is handled. It went from 0 to 16, 20, 29, 72, 73, and finally 74 of 74. When the catalogue disagreed with the walk, the fix was to drive the control both ways, not to loosen the gate.

## Part C: How to steer an agent like this

These patterns come from what the operator did across the four sessions.

- **Hold the agent until you order it.** Write "just a question" or "do nothing yet" when you want thinking, not action, and expect the agent to answer and stop. Ask for the design before the build: the 1:1 parity bridge was written down and agreed before any code existed.
- **Hand over the conn out loud, and take it back out loud.** "Start it now." "Hold its hand." "You have the conn." "Force quit, but hold until my order." "You may continue." When you share one desktop with an agent, both sides must know who is driving.
- **Ask plain questions that expose blind spots.** "Does the harness need to control all those sliders?" exposed defaults-only filters. "Is this how REA should be run?" exposed drift into home-grown formats. "Can you not use virtual memory?" fixed a stalled plan. "So what all did you run while I was busy?" exposed overstated progress. Re-ask when the agent answers half: "That was my question underneath."
- **Ask for exact figures.** "Give me an exact figure" made the agent re-read its records and retract a block that never happened. Then reject constants that did not come from data.
- **Report the physical world the agent cannot sense.** Error sounds, a scrolling window, a stuck filter you timed, a program that opened. Each one became a diagnosis.
- **Do not let the agent choose scope for you.** Map everything, then choose. An agent narrows scope to finish sooner.
- **Insist on executable gates.** A rule that matters becomes a test that fails today and passes when the thing is real: the coverage gate, the redaction scanner on this package, and REA's own import check on every Evidence bundle. When the agent wants to pass a gate, make it fix the code, not the gate.
- **Make independent reviewers do the checking.** Subagents that share none of the context found what the agent's own checks passed: the cleaning bugs in the help capture, the parity server's three bugs, published dialog text, and the risk to unsaved work.
- **Use the TDD and engineering-principle skill sets on every task, and restate them after compaction.** A compaction can drop a standing rule. The operator noticed and restated it: "That was lost in compaction." Failing test first, then the fix, then a Standards and Spec review.
- **Keep consent per action.** Approve each install, delete, force-push, reset, and job stop on its own. Expect the agent to ask again next time.
- **Guard your own machine.** Set up the screensaver and power plan so the agent is not locked out. Ask for an idle gate so probes run only when you are away. Expect the agent to report, unprompted, anything it touched that was yours.
