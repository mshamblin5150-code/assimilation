# Giving REA reach into Windows apps that draw their own UI

This is the story of one ticket, from installing REA to a working answer for something REA could not see. It runs over four days, 2026-11-08 to 2026-11-11, and four overlapping Claude sessions. One operator drove all of them.

REA ("reverse-engineer-anything", npm package `rea-agents`) is an open-source MCP toolkit for reverse engineering. It decompiles native and managed code, hooks running processes, and records every result as Evidence in a ledger that it can import, export, and verify. On macOS it can also watch a running app's interface through the accessibility tree, with `observe_native_ui` and `capture_native_ui_scenario`. On Windows those two tools refuse to run.

The operator builds a design studio that is drawn in Photoshop and Illustrator. He wanted to know exactly how those two programs behave, so the studio could copy what matters. Photoshop and Illustrator draw most of their own interface. Even Windows UI Automation sees only their window frames and panel tabs. The dialogs, sliders, curves, and swatches inside are pixels.

By the end, REA's ledger held three linked kinds of Evidence:

- An observation of each Photoshop process, taken by a Windows bridge that gives REA's two macOS UI tools 1:1 parity.
- A result for every probe, setting sweep, and dialog control that a harness drove by pixels and real input, linked to that observation.
- For each driven control, the binary and the candidate functions that carry its code.

The code is in the [`code`](code) folder: the harness in `code/scripts/adobe_observed_truth`, the bridge in `code/scripts/adobe_observed_truth/rea_windows_ui`. Every message the operator sent is in [02-operator-log.md](02-operator-log.md). The rules and the bugs behind them are in [03-rules.md](03-rules.md). All times are UTC. Operator quotes are lightly cleaned of typos, with his wording kept.

## Phase 1: Set REA up for every Claude surface

**What the operator wanted.** REA installed for Claude Code, then for more: "It needs to be set up for all that Claude can do, including Desktop."

**What the agent did.** It registered `rea-agents` 6.8.0 for Claude Code. REA's health check reported healthy, with Ghidra 12.1.4 and JADX available, and setup backed up the client config before changing it. It reported two deviations from the approved plan. Node was too old: REA needs 24.22.1 or newer, so the operator chose a newer release. The package manager refused to upgrade Node while Node processes ran, so the agent turned on "ignore running processes" for that one upgrade and then turned it off again.

REA still said `environment_healthy: false`. The operator asked whether he needed the missing back-ends: "I thought I might need one to look at exe files, so I'm hearing that I do not." The agent confirmed it. Ghidra decompiles ordinary Windows `.exe` and `.dll` files, and REA reads .NET and Electron apps with its own tools. IDA and Kuna were the only missing pieces, and Kuna does not run on Windows. It also passed on REA's own caveats: Ghidra on Windows is marked experimental and read-only in REA, and targets must sit on a local NTFS drive.

**What went wrong.** REA refused to write the Claude Desktop config from inside a running Desktop, because Desktop could overwrite the file from memory. That guard was right. The agent gave the operator a quit-then-run procedure, checked the config file REA had written, and called the setup done. It did flag that it could not see Desktop's logs. The operator came back with: "I could find nothing. This is the Desktop config JSON file."

The cause: this Claude Desktop was a Microsoft Store install, which keeps its settings outside its package folder. REA's setup wrote to the package folder. Desktop read a different file, and that file had no MCP section. The agent had checked the file it wrote, not the file Desktop reads.

**What changed.** The agent owned the error and the fix was a hand edit of the real file: back it up, quit Desktop, add an `mcpServers.rea` block with the command and environment that worked for Claude Code, then check Settings > Developer. Two habits came out of this phase. "Done" means the consumer read it. And REA's tools appear only in a new client session, never in the session that ran setup.

## Phase 2: Read the help before the binaries

**What the operator wanted.** He had opened Claude in his project "for a very good reason": the design studio. "I don't think we went into the depth that REA can bring us." His first order was an adversarial review of the Photoshop and Illustrator help that the studio's design notes were built from. After the first verdict he set the order of work:

> Before we bring in any binary decompiling, we first need the help files for the versions of the programs we actually have installed, the ones you are going to look at with REA. So first find what versions of Photoshop and Illustrator we have access to, then get the full corpus of each program's help. And run an adversarial review against that to ensure that the model doesn't lie to us. Because I know how you are: you like to take the shortest route.

**What the agent did.** The first review found the notes were neither thorough nor accurate. Most rows recorded the studio's own implementation choices rather than what Photoshop does, and about 20 claims were wrong. The agent checked shortcut claims against Photoshop's shipped `Default Keyboard Shortcuts.kys`: Ctrl+Y was recorded as Redo but is bound to Proof Colors. Citations were topic labels with no file behind them, and the checker compared labels against a list the same author wrote. The notes were pinned to the 2025 release while the help described 2026. The agent concluded that a shipped config file outranks help prose for shortcuts.

It then listed the installs: Photoshop 2024, 2025, and 2026 (27.11.0), and Illustrator 2024, 2025, and 2026 (30.8.2). The operator narrowed the scope to the 2026 releases, the ones REA would examine. The agent built the page list from the image platform's sitemap, cross-checked it against the table of contents, and read `robots.txt`: articles allowed, PDFs not.

**What went wrong.** Headless Chrome got HTTP 403. The agent's own safety checks stopped an automated visible browser as bot-check circumvention, and it did not work around them. It also disclosed that an earlier crawl had succeeded only by spoofing the browser identity, "the shortcut I won't repeat". The operator chose "Through the real Chrome browser."

Chrome then blocked the hand-off from the tab to a local receiver behind a local-network permission prompt that the browser extension could not click. The operator planned to have Codex click it with computer control, but the machine was locked:

> Codex cannot do that because the computer is locked, so your objective is to find another way. I think reading the page and then doing an adversarial review is the only way we can move forward. The adversarial review prevents you from lying.

So the agent built "Reader A". It fetched each page inside the tab, extracted the article, and emitted it through the browser tool's output in small pieces, each with a checksum (FNV-1a over UTF-16 code units). An assembler rebuilt pages from the saved tool results, so the model never retyped page text. The operator also asked for verification "with multiple subagents" that do not share the session's context, reusing a two-reader method from earlier work: a structural extraction, plus an independent reader of the rendered page, with the rendered page settling disagreements. (These two rulings survive only in the agent's compaction summary.)

The site's bot manager blocked the crawl again and again. The operator's first instinct was "I think initially I would try to get around it." The agent declined: fresh profiles, a different IP address, cleared cookies, or a spoofed identity would all evade a limit the site set on purpose. It proposed staying under the limit.

The rate-limit work is where the operator taught the agent to stop guessing. He asked for "an exact figure" of pages collected before each block. Re-reading its records, the agent retracted its claim of a second block: that run had ended when Chrome froze, with no recorded failure. The operator then reframed the variable:

> We were accessing 44 pages a minute and the image platform blocked that. Then we accessed 7 pages a minute and the image platform had no concerns. So why don't we make that the constant tick of the clock?

He rejected each guessed constant in turn. A 3-hour pause: "Why would the crawler pause for 3 hours? We use data for that." A step-down rule: "Do not step it down, because 10 was working for quite some time, until it didn't. Remember, we use data to find out what we are missing." A crawl-and-rest schedule from five blocks: "n=5 is not enough for a representative sample." The agent added a per-request log that survives tab freezes, then passive recording of response headers and cookie names, never values. It said this was "only to understand the rules and stay inside them, not to get around them."

**What changed.** The log produced a model of the block instead of a guess. The connection was cut at the network edge within 0.1 to 0.4 s. The block followed a session cookie, not the IP address. It behaved like a suspicion score that decays with rest, with runs of about 18 to 25 minutes, and throughput averaged over the block cycle came to about 2 to 2.6 pages a minute. The crawl finished at 1,807 of 1,807 pages (954 Photoshop, 853 Illustrator), every checksum verified.

The operator then said "Then make it so" to "Reader B": an offline audit plus a live side-by-side check, run by subagents that shared none of the conversation. It confirmed every page was captured once and intact. It also found real bugs in the agent's cleaning step, such as placeholder `#` links rewritten to the site root (about 26,600 links), garbled mailto links, missing accordion questions, and silently dropped videos. The agent admitted it had saved only cleaned text, not raw HTML, so nothing could be repaired offline. The operator ruled that the meaning was intact and no fix was needed, so the agent listed the known artifacts in a README.

The agent's own checks had passed those cleaning bugs. Independent readers caught them. That is the operator's anti-lying mechanism working as he intended.

## Phase 3: Find out what REA cannot see

This phase ran in a second session, alongside the crawl.

**What the operator wanted.** To turn about 20 behaviours his review had flagged as wrong or unsupported into watched facts. His examples included Shift pressed before or after starting a marquee drag, whether Free Transform scales proportionally by default, eraser opacity, the default history depth (the help says both 20 and 50), and Ctrl+Y against Shift+Ctrl+Z.

> Use REA's native-UI tools (capture_native_ui_scenario, trace_native_ui_action, observe_native_ui) on the roughly 20 behaviours my review flagged. Each produces an evidence bundle, so a behaviour stops being "the help says" and becomes "we watched it happen".

**What the agent did.** It launched Photoshop 2026 and read the three tools' descriptions before planning around them. They spoke of Mach-O targets, macOS accessibility values, and Objective-C handlers. The agent flagged that the tools were probably macOS-only and proposed one cheap test call first. The operator agreed: "Sure, run that test first. It may mean that we need another decompilation program in addition to Ghidra."

Both observation tools refused with an unsupported-host error that named macOS. The agent argued against a second decompiler. The gap was watching the screen, not reading code, and `trace_native_ui_action` is static analysis centred on Objective-C. It proposed a small home-built harness instead: exact input through Windows `SendInput`, so Shift timing relative to a drag is controlled; before-and-after window captures; and Photoshop's own state read back through its scripting interface.

**What the operator said.** "Besides the harness, would it still be able to use REA after we got done building it? That's the question."

**What changed.** The agent confirmed that the harness replaces only REA's macOS screen-watching. Ghidra decompiling, Frida hooking, version comparison across the three installed releases, static-to-runtime correlation, and Evidence import and export all work on Windows. That answer shaped everything after it: build only the part REA lacks, and keep REA as the system of record.

## Phase 4: One ledger, and decompile everything

**What the operator wanted.** The agent had offered two formats: write REA-format bundles, or start with a simpler side format linked by hashes. It recommended the side format. The operator overruled it:

> Then let's build the harness for that, and I would go with the REA-format bundle so everything can land in one ledger.

**What the agent did.** It designed the harness around kinds of interaction, not features, so a new behaviour is a new scenario file rather than a rebuild. With the operator's licence ("If necessary, use subagents, as many as needed"), it fanned a coverage pass out to subagents and merged a map of about 40 capabilities across input, view, state, observation, and setup, each marked built, partial, or missing.

The pieces are all in the code folder:

- `rea_evidence.py` writes Evidence records and bundles that REA 6.8.0's `import_evidence_bundle` accepts. It mirrors REA's own `evidence.js` and `evidenceBundle.js`. The test fixtures `rea_evidence_bundle_reference.json` and `rea_accepted_harness_bundle.json` come from real REA output. `test_observation_record_rebuilds_every_record_rea_accepted_from_its_inputs` rebuilds them byte for byte, and `test_observation_record_rejects_floats_whose_text_differs_between_python_and_js` stops a record that Python and JavaScript would serialise differently.
- `input_plan.py` and `win_input.py` turn a gesture into exact `SendInput` events. `test_modifier_held_after_drag_starts_goes_down_mid_drag_and_holds_through_release` pins the Shift-timing case the operator cared about. Input stops if any other process takes the foreground, so keys cannot land in a terminal.
- `capture.py` asks a window to render itself with `PrintWindow`, so overlapping windows do not spoil the capture.
- `photoshop.py` and `illustrator.py` read state over COM by exact keys only. Photoshop's application descriptor also carries the licence serial, so it is never dumped whole. With three releases installed, the default scripting connection could bind an older one, so both adapters refuse unless they are talking to 2026.
- `canvas.py` maps document pixels to screen pixels from Photoshop's own view state.

**What went wrong, and what the operator said.** The agent asked for the operator to unlock the PC. He asked back: "If Photoshop is already open, why do you need me to be there to unlock the PC? That seems to be an asynchronous event that can happen without me." The agent split the work. Script-only probes run while the machine is locked. Real input cannot be injected into a locked session, so input scenarios wait in a queue and fire at the next login. The operator agreed: "Run what you can run now and then await my return to do the rest."

The first results landed in REA's ledger and REA verified every record. History kept exactly 50 states after 61 edits. The canvas mapping matched on-screen positions within 1 px at four zoom levels. The Illustrator adapter read anchors and handles exactly.

Two side effects came with them. Photoshop began refusing scripted calls, and each refusal raised a modal that froze the app. The agent pressed OK three times before it fixed the cause: `photoshop.py` now switches script dialogs off for each scenario and puts the setting back afterwards. It also disclosed that an early probe had changed and restored the operator's brush settings without checking the restore. `ps_tools.preserved_tool_state()` now writes tool state back byte for byte and reports whether each value reads back identical.

Then came two scope corrections in a row. The operator asked, "So what all did you run while I was busy?" The agent admitted it had run four observations, not everything. It proposed narrowing the goal to the behaviours the design studio already relied on. The operator refused:

> No, because our contracts might be insufficient. We need to know with REA how everything works, then we can choose what we want to implement.

The agent's new plan still treated decompiling as a last resort. The operator corrected that too: "Bingo, you got it right now. Why are you not running REA's decompiler on everything? Because it provides much more layered data than watching alone."

**What changed.** `rea_corpus.py` lists every native binary of both installs with its SHA-256, runs REA's PE inspections on each one, decompiles all 617 image-platform binaries with REA and Ghidra (smallest first, several at once, every step resumable), and wraps every REA Evidence record into one importable bundle. The agent built a first static inventory from REA records only. Each fact names an REA Evidence ID, and each resource was checked against REA's SHA-256 before decoding.

The run brought its own lessons. The agent's ETA moved from "8 to 13 hours" to "about a day" ("I was wrong about the parallelism"). It had overstated Photoshop's memory use as 7 GB when about 0.7 GB was resident. When it offered to stop WSL to free memory, the operator ruled: "WSL is off-limits. My Codex agents are using it as we speak."

The operator asked whether a full decompile would explain how the programs work. The agent answered "mostly yes, but not by itself". Function names are stripped, so features are found through anchors such as interface text, command IDs, and plug-in registrations. Code also shows what can happen, not what does, so it pairs with observation. When the operator pointed out that the help corpus was useful too, the agent built a three-way comparison: help claim, decompiled code, and harness observation, each row linked to REA Evidence. The first rows already disagreed. The help gives both 20 and 50 for history depth, and states a maximum zoom lower than the 12,800% the harness observed.

## Phase 5: Let the harness run while the operator is away

The next morning a third session took over the harness. The operator had to point it at the right session first: "Nope, that is not it... I want you to take over that session; that is why I gave you that specific URL."

**What went wrong overnight.** One Ghidra process hung for about 9 hours on a single function and used up memory. Every job after it failed with a misleading "JDK not found" error. REA's per-function decompile timeout had been unset. The agent re-ran only the 72 failed binaries with a 5-minute limit per function. The operator asked, "Can you not use virtual memory? Use disk space to account for the memory need." So the oversized binaries ran one at a time afterwards and spilled to the page file. The limit at first lived only in an environment variable. It is now committed in `rea_corpus.py` as `REA_GHIDRA_DECOMPILE_TIMEOUT_SECONDS`.

**What the operator wanted.** For the harness to run without him, and to test everything. He changed his own machine so the agent would never be locked out: a power plan that never turns the display off, and a screensaver to protect the monitors. He also set the method: "Bingo. Use [the TDD and engineering-principle skill sets] for the harness." When the agent said lint and type-check tools were missing, he said "Then install them."

Then he explained why he wanted everything:

> Testing everything Photoshop does is the right way, because I built [the design studio] before I knew how to structure it with engineering skills, which is why you are using them. I was trying to guide that original tool with prose alone and it still had issues. The point is being able to understand everything both programs do and assimilate what we need.

**What the agent did.** Every step of this phase met the physical machine and broke on it:

- **The screensaver.** It runs on its own desktop on Windows 11, with one window per monitor, which the unit-test fake could not show. The live test failed until the agent fixed it. `test_screensaver_without_a_closable_window_is_refused_without_waiting` now covers the case.
- **Focus.** Photoshop would not come to the front after the screensaver (0 of 5), because the machine's foreground lock was at its maximum. `win_input._take_foreground` joins the input queue of the window that has focus instead of sending a keystroke (5 of 5).
- **A hidden survey.** An image-platform feedback survey sat behind other windows and blocked all scripting. The pre-flight in `run.py`, with `photoshop.dismiss_surveys`, now finds it, declines it for good, and refuses to start behind any other dialog (`test_survey_is_declined_for_good_and_never_submitted`, `test_preflight_refuses_to_start_behind_another_dialog_and_names_it`).
- **The idle gate.** The operator asked for probes that run only when he is truly away. The Windows idle timer counts the harness's own injected input, so it cannot tell the person from the probes. `idle.py` uses low-level hooks, reads each event's "injected" flag, and keeps only the time of the last real event, never the key or the position. When real input arrives mid-probe, held keys and buttons are released (`test_stopping_mid_drag_releases_the_button_then_the_held_keys_in_reverse`).
- **The inventory.** `inventory.py` lists what the app reports it can do (menus, tools, panels, preferences, shortcut sets). That list, not the help, is the denominator for "test it all". `families.py` drafts one probe per item, each saying how it is undone and whether it is safe to run unattended.
- **The 125 menu commands that scripting could not run.** ExtendScript cannot run a menu command by number, but UXP can. A UXP plug-in cannot listen for connections, so `uxp_bridge.py` serves a tiny queue on 127.0.0.1 and the plug-in in `uxp_helper/` polls it. The first setup took three manual steps. The operator ruled: "I think that needs to be installed permanently, because that will get tedious, especially because I might not be here to help."
- **The overnight runner.** `runner.py` plans the queue, runs each probe with clean-up that always runs, and writes each result as it finishes. `runner_photoshop.py` carries the steps out on the real Photoshop.

The operator watched the first unattended run from another machine: "I'm coming at you through the back door so I don't disturb the harness. What the fuck is it doing? It's got some sort of scrolling thing up." It was the About box. It scrolls and has no buttons, so it did not count as a dialog. The runner had restarted Photoshop twice, re-running About first each time, and found the main window by a title that changes when a document is open. Then he asked the agent to "hold its hand while it runs", and kept reporting what only he could see: "No, but it did open Bridge. I'm looking at it right now."

The agent's code review found the worst bug of the phase while the runner was live. With one of the operator's own documents open, every probe failed the scratch-only check, each failure counted toward a restart, and the restart force-killed Photoshop. Unsaved work would have been lost. The fix went in test-first: `test_a_spec_blocked_by_the_persons_own_document_waits_and_never_restarts_photoshop` and `test_photoshop_is_force_quit_only_if_the_last_check_saw_nothing_but_scratch_work`.

The operator also noticed that probes were running on a blank canvas: "I don't think you can get much data from a white canvas." The agent put a real image under the probes. `test_images.py` now draws its own chart, with saturated hues, a grey ramp, hard edges, noise, and a transparent strip, so a command's effect shows in the pixels and no private image is needed. For full-window workspaces such as Vanishing Point, which the operator asked about ("Can the harness not already do that?"), `workspace.py` finds the known chart in a screenshot and clicks a perspective plane onto it.

**What changed.** The first full pass ran 1,441 probes: 1,410 succeeded, 25 were refused by Photoshop, and 6 failed.

## Phase 6: Drive it the way REA wants to be driven

**What the operator wanted.** He asked, as a question only, whether enough was decompiled to match a deeper run to the code. The answer was yes for the 78 plug-in filters and no for the built-in commands, which live in `Photoshop.exe`. He chose the 78 filters. Then he asked a second question: "Is this how REA should be run? Just a question."

**What went wrong.** The agent stopped and admitted it had drifted outside REA. It was matching code by text search over decompiler output and keeping results in its own format, not as REA Evidence and not in REA's unknowns ledger. The operator answered:

> Yes, that should be it. Drive this like REA wants to be driven. And the tools we needed to make, i.e. the Photoshop harness, I think need to match what the Mac version does for REA. The question is, can we make that happen?

Then he set the bar and the order:

> I would create that local MCP server. What I want is an equivalent process to what the macOS tools do, so we need to really think about that before we build anything. I want 1:1 parity.

**What the agent did.** It read REA's own skill and the installed source of the macOS tools, not just their descriptions, and wrote a design document. It built nothing until the operator said "Go ahead."

The bridge, `rea_windows_ui`, is a local MCP server with REA's tool names: `open_binary`, `observe_native_ui`, `capture_native_ui_scenario`, `export_evidence_bundle`, and `close_binary`. It imports REA's own input schemas, output budget, deadlines, error classes, and `createEvidence`, so REA's checks are the parity checks. `src/scenario.js` mirrors REA's step sequencing and interruption control. The helper in `helper/ReaWindowsUi` is a C# program on Microsoft UI Automation, the counterpart of REA's macOS helper: one JSON request in, one snapshot out. A small WPF window in `helper/ReaWindowsUi.Fixture` has a known tree for live proofs. Like REA, the bridge binds only to an executable ("a DLL is refused: REA binds native UI observation to an executable").

An independent review found three real bugs. Cancelling never reached a running scenario, the deadline never stopped a stuck helper, and a helper crash lost the partial results. Tests now cover all three: "a caller cancellation stops the scenario and marks the step cancelled", "a helper still running at the deadline is stopped and reported as ETIMEDOUT", and "a helper that dies mid-scenario fails the step and keeps the partial report".

The agent also reported, unprompted, that an early live test had read the operator's open Notepad tabs and closed Notepad. From then on, live tests of new code used only the agent's own fixture window.

**What the operator said next.**

> Link the harness evidence, register the MCP client, and make sure REA's longer remediation text is included, because I want the harness to be able to communicate what REA needs. Do we need some sort of API for that, or can we modify the harness?

**What changed.** No API was needed. `parity.py` takes one parity observation of each Photoshop process when the runner connects, through the bridge's own tool handlers (`cli.js observe`). Every result row records that observation's Evidence ID, or REA's projected error with its remediation text when the observation failed. `cli.js bundle` and `src/harness.js` turn the rows into REA Evidence from provider `adobe-observed-truth`, marked as a controlled replay, each linked to its observation. Questions that UI Automation cannot answer go through REA's own `record_unknown` and `update_unknown`, and REA verified one resolution as true.

The parity observation also proved the problem on Windows. UI Automation saw Photoshop's window frame and docked panel tabs. Everything Photoshop draws itself appeared as panes with no children.

## Phase 7: Drive every control by pixels

**What the operator wanted.** He asked a question that exposed a blind spot: "Does the harness need to be able to control all those sliders as well? I don't think it does that yet, so it can match what REA needs." The filters had only ever run at their defaults. Then he widened it:

> Can the harness control all of the visible laid-out controls, no matter what they are?

The agent's honest answer was no, with a list of what it could and could not drive. The operator replied:

> But if Windows UI can't drive them because, as you said, the image platform draws its own, the harness should be able to drive every type of control we have seen.

> And you shouldn't prioritise what you think [the design studio] needs. You should be able to capture all of them. Remember, that was driven by prose and I couldn't get it right. Now I'm not driving by prose.

**What the agent did.** First, setting sweeps. `action_settings.py` reads a command's settings from the descriptor Photoshop reports when the command runs at its defaults, and `plugin_params.py` reads each filter's own settings from its plug-in file. `sweeps.py` replays each command with one setting changed: a quarter, half, double, and four times a number; every other choice; each switch flipped. The defaults run three times to show the command is deterministic. Proof that a value was applied is the pixel hash, not what Photoshop reports, because Unsharp Mask reported its defaults while applying the new value. The sweeps finished at 982 of 982, and 475 changed the result. Another 25 commands were random and need about 60 runs each before one hash means anything.

Second, a driver that works the way a person does. `controls.py` treats a dialog as a `Surface`: a picture of the dialog, plus key presses and clicks sent to it. `focus_walk` finds keyboard controls by pressing Tab and watching what changes. `probe` tells kinds apart by how they answer keys. `control_drivers.py` holds one driver for each kind, including number fields, sliders, dropdowns, curves, angle dials, swatches, eyedroppers, and resize grips. Controls the keyboard cannot reach are placed from a catalogue of every captured dialog (`control_catalogue.py`): the drawn thing of the right shape nearest its label, as OCR reads the label. `dialog_surface.py` joins it to a real dialog. It captures with `PrintWindow`, sends input with `SendInput` only while the dialog is in the foreground, and reads the light-on-dark text inverted and enlarged. `control_pass.py` drives every control of one open dialog and writes one row for each.

Third, OCR good enough to find labels. The operator suggested trying PyMuPDF and approved installing Tesseract. The agent scored several engines on 142 dialogs, and RapidOCR won. He set the target: "Ideally I want a 95% or higher score. I want an A, but I will take the best I can get." The agent built an exact answer key of 40 dialogs and reached 97.5%. It named the catch itself: the key is small, and the corrections were tuned on that same set. `ocr_correct.py` corrects only words that Photoshop never shows, and only into a word it does show that differs by characters OCR confuses. The list of Photoshop's interface strings (entries shaped like `$$$/Example/Key=Label`) stays on the machine and is never published.

Fourth, placing every catalogued control. The operator chose "Re-catalogue." Nine annotator subagents placed 95% of 3,408 catalogued controls (`catalogue_positions.py`). Each batch hid a copy of one reference dialog as a check, and all nine agreed with the reference.

**What went wrong.** Driving self-drawn dialogs by pixels broke in ways no fake predicted. Focused fields blink their whole box. A pulsing default button looks like focus moving. Tooltips look like open lists. Typing a 7 changed pixels inside some buttons, so Curves took them for text fields and later pressed them. An animation elsewhere in a dialog kept a dropdown driver pressing Down up to 300 times. Each became a failing test first, then a fix. [03-rules.md](03-rules.md) lists them all.

Some failures touched the operator's own things. A file dialog opened on his real documents folder. The agent caught it live, stopped, confirmed nothing had changed, and fenced file dialogs into a sandbox folder. The Spec review found that up to 80 characters of dialog text were being published, so `publishable` now passes only known labels. A run changed the operator's saved layout preference, and the agent set it back. A button that opened another program was later added to the never-press list in `controls.py`.

The operator also had to restate his method after a context compaction dropped it: "That was lost in compaction. Always, for any code work, use [the TDD and engineering-principle skill sets]." Later: "Keep going. Just use [them]; that is my one constraint." The agent loaded the bug-diagnosis skill and the bug-fix playbook, which commits the failing test before the fix.

Control of the machine passed back and forth explicitly. A live run ended with Photoshop hung. The agent asked before force-quitting, and the operator answered: "Force quit, but hold until my order." The agent held until "You may continue." Later the operator heard what the agent could not: "I hear a bunch of error sounds at this time." Focus sat on a bare window, so arrow keys had nothing to change. The agent judged that harmless and let the run go on. When the star-rating control kept failing, the agent traced it to another desktop program taking the foreground right after File Info came forward. Codex computer-use helpers had started around then. The agent left those programs alone, and the interruption message now names the process that took the foreground (`test_an_interruption_names_the_process_that_took_the_foreground`).

**What changed.** The coverage gate is an executable test, `test_adobe_observed_truth_control_coverage.py`. It reads the private dataset, so it is not shipped in the code folder. For every control type seen in a captured dialog, it requires a driver, and a live row in which driving that control changed the dialog. It went from 0 to 16, 20, 29, 72, and 73. Then the operator stepped away: "You may. I am done typing on the computer. You have the conn." The gate reached 74 of 74.

## Phase 8: Link each control to the decompiled code

**What the operator wanted.** "Can you map the decompiled files so the harness can expose what they need to REA?"

**What the agent did.** `control_code.py` finds each driven control in the binaries. A control row names its dialog by menu path and its label. The dialog's binary is the filter plug-in that adds that menu item, or Photoshop itself. Inside a plug-in, a control is a setting with a four-letter code, and the plug-in's functions compare against that code as a 32-bit number. `plugin_params.py` searches the decompiled functions for those numbers. A control with no setting is found through the interface string its drawing code carries. Only binary names, codes, string keys, and function addresses are recorded, never the image platform's code or text. A control whose binary is not decompiled yet waits (`test_a_dialog_no_plugin_adds_is_the_apps_own_and_waits_while_the_app_is_decompiled`). In the bridge, "a control carries where its code is in the decompiled binaries, so REA can open it there" proves the link reaches REA's Evidence.

**What went wrong.** A large Rust library stalled the decompile queue twice, once for more than 15 hours. Because the operator had started that job, the agent recommended stopping the library and asked before acting. "I agree. We can retry that DLL later."

**What changed.** Each control's Evidence now names its binary and its candidate functions, so REA can open the code behind a control the harness drove.

## Phase 9: The result

REA on Windows now reaches what it could not see natively. For each Photoshop process, REA holds:

1. A parity observation from `rea_windows_ui`, in the same Evidence shape as REA's macOS observations, with a Windows provider. It shows the window frame and the drawn panes.
2. Harness Evidence for every probe, setting sweep, and driven control, each linked to that observation. Each record states its method and its limits: what was scripted, what was typed, and that a pixel hash, not Photoshop's own report, proves a setting.
3. For driven controls, the binary and the candidate functions to open in REA.
4. Open questions in REA's own unknowns ledger, resolved against harness Evidence where possible.

| Measure | Result |
| --- | --- |
| Help pages captured, checksum-verified | 1,807 of 1,807 |
| Image-platform binaries in the decompile | 617; 598 decompiled by the end, `Photoshop.exe` and five others over the run's 50 MB cap never queued |
| Probes in the first full pass | 1,441: 1,410 succeeded, 25 refused, 6 failed |
| Setting sweeps | 982 of 982; 475 changed the pixels |
| OCR on the exact answer key | 97.5% on 40 dialogs |
| Catalogued controls placed | 95% of 3,408 |
| Control coverage gate | 74 of 74 |

Some items are still open. (One that closed at the end: Image Size left a stray window at a different control each run. The harness began recording the class of any window left open; the next run named it, `PSDragFeedback`, the image platform's transient drag overlay, which it now ignores like a tooltip, and the following run drove all 23 of Image Size's controls cleanly.) The built-in commands wait on the decompile of `Photoshop.exe`. The 25 random commands need repeated sampling. The OCR answer key needs to grow beyond the set it was tuned on.

At the end the operator asked whether the harness was ready "to teach someone else how to build a fix for what REA cannot natively read". He first proposed publishing the raw transcripts. The agent pushed back: transcripts carry personal data, image-platform text, and system text, and they teach poorly. It proposed a distilled log behind an executable redaction check. The operator agreed and set the scope: "We show and teach from that point, not all of the private project's lessons. We're teaching what we learned with REA, showing the harness code we built and the code we built for REA so it could have its own native parity." That is this package. An automated scanner gates it before it leaves the private repository. The plan was for Vox, another agent, to carry it out; the operator later had the agent publish it directly instead.

## Phase 10: Package the lesson

**What the operator wanted.** A lesson that could leave the private repository: the story from REA's setup on, the code, and nothing that was not his to publish. "Just make sure it includes this entire branch, this entire transcript on the machine, because we did most of the work here. You can have it include the real app icon image file."

**What the agent did.** It inventoried every transcript that mentioned REA and kept the four that hold this work, condensed them to the operator's messages and its own closing replies with no tool output, and had separate readers extract each session under the same exclusions. Then it made the exclusions executable before writing a word of the lesson: `lesson_gate.py` scans every file of the package for personal identifiers, this machine's paths, the private repository's name and subjects, image-platform interface strings and agent system text, and the gate test fails on any finding. The code ships as a copy of what git tracks (`lesson_package.py`), and a second test fails if any copy differs from the live harness.

**What went wrong.** The gate found the harness itself was not clean. Eleven corpus paths were hard-coded to this machine, the Evidence provider, scenario predicate, mutex and helper plug-in carried the private repository's name, the icon test image was read from that repository's assets, docstrings and tests carried real image-platform interface keys, and the survey check matched the image platform's full question text. Two REA reference fixtures were edited by hand at first, which broke the tests that compare the harness's Evidence ids with the ones REA computed.

**What changed.** One corpus setting (`ADOBE_REA_CORPUS`); neutral names everywhere; example interface keys (`$$$/Example/...`); the survey recognised by the SHA-256 of its question; the operator's real app icon shipped beside the harness, approved in the gate by its own SHA-256 so no other binary can pass. The fixtures were regenerated with REA's own canonical digest and bundle builder and checked by its strict parser, and REA's recomputed id matched the one the harness computes. The shipped code was copied to an empty folder outside the repository, and its 390 tests passed there with nothing from the private repository on the path.

