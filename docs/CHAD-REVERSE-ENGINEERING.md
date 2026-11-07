# Assimilation Living Up to Its Name

**An advanced Windows lab for Chad.** Take a compiled program, explain one
decision it makes, and leave enough evidence for someone else to repeat your
investigation. You can stop after any checkpoint and pick up from your notes.

This lesson follows the [five-minute orientation](../README.md#for-chad-five-minute-orientation).
You need a Windows x64 computer, a local coding agent or PowerShell, and permission
to install tools under your account. Work in a copy of the
[lab fixtures](../examples/chad-reverse-engineering/fixtures/). The lab's
synthetic APK is ready to inspect with JADX. You can do that exercise without
Android Studio, the Android SDK, a phone, or an emulator.

## 1. Give your agent the method

Ask your agent to read [START_HERE](../START_HERE.md) and the original skill
files below. The files are already in the checkout.

- **Matt Pocock's** [Teach](../upstream/matt-pocock/skills/productivity/teach/SKILL.md)
  informs the short checkpoints. Ask your agent to teach you explicitly if you
  want its teaching workflow. [Diagnosing Bugs](../upstream/matt-pocock/skills/engineering/diagnosing-bugs/SKILL.md)
  supplies the repeatable input-and-output check you build before decompiling.
- **P-Stack's** [Prove It Works](../upstream/pstack/skills/principle-prove-it-works/SKILL.md)
  and [Test Behavior, Not Implementation](../upstream/pstack/skills/principle-test-behavior-not-implementation/SKILL.md)
  supply the evidence standard. Ask for those principles explicitly. Record
  the actual output and exit code, then use the debugger to explain them.

Use the checked-in originals for this Windows lab. If you want your agent to
discover installed skills by name, follow the [upstream installation walkthrough](CHAD-BLANK-PROJECT.md#4-choose-one-scope-and-install-the-upstream-skills).
It covers choosing repository or personal scope, previewing Matt's skills,
and choosing the P-Stack material your host can support. Then
[verify discovery in your agent](CHAD-BLANK-PROJECT.md#5-verify-that-the-agent-can-find-and-use-the-right-skill).

Assimilation's own optional `python3 scripts/skills.py install --locked` route
runs from a fresh checkout in a qualified POSIX environment with Git and Python
3.10 or newer. It refuses native Windows source operations. Both skill sources
are separate from REA's bundled investigation skill.

## 2. Install REA and qualify the tools

### Connect REA to Codex

We ran the official npm package's setup preview for Codex and approved the plan
before applying it. First run `node --version`, `npm --version`, and
`npm view rea-agents@latest version engines --json`. We verified REA setup and its
provider checks with REA 6.8.0 and Node.js 24.22.1. That release declares Node 22.23.4 or later
in the 22 series, 24.22.1 or later in the 24 series, or 26.12.1 or later.
Use a supported Node on the PATH that starts Codex. On our host the default
shell's Node was older, so we used Codex's existing supported Node for setup.

```powershell
npx.cmd rea-agents@6.8.0 setup --client codex --dry-run --json
```

Read the preview. It should identify your user-level Codex config, the backup
path when a config already exists, and the destination for REA's
`reverse-engineer-anything` skill and references. That scope applies to other
Codex sessions under your account. If you approve the displayed plan, run the
same setup with `--yes` in place of `--dry-run`. npm may separately ask to fetch
the package. If you intend to use the latest release, the original command is
`npx.cmd rea-agents@latest setup`. Preview and apply the same resolved version.

```powershell
npx.cmd rea-agents@6.8.0 doctor --client codex --skill --json
codex mcp get rea
```

Restart Codex to load the registration. Ask it to call REA's `binary_session`
with an empty argument object and show the result. A healthy doctor report
checks the saved setup. The tool call checks the live connection.
[REA installation guide](https://github.com/morluto/rea/blob/rea-agents-6.8.0/docs/installation.md)

### Install the representative programs

We downloaded the upstream Windows archives, checked their SHA-256 values, and
extracted each under its own folder in
`%LOCALAPPDATA%\Programs\ReverseEngineering`. Choose a directory you control
and compare `Get-FileHash -Algorithm SHA256 <archive>` with the published digest
before extracting. Keep the archive's DLLs and other files beside its launcher.
The versions below match the lab's verified toolchain.

| Tool | What to install and how to check it |
| --- | --- |
| Ghidra 12.1.4 | Extract the public archive. Keep the directory containing `ghidraRun.bat` and `support\analyzeHeadless.bat`. Extract the Temurin 21 x64 JDK and run its `bin\java.exe -version` and `bin\javac.exe -version`. [Ghidra release](https://github.com/NationalSecurityAgency/ghidra/releases/tag/Ghidra_12.1.4_build) · [Temurin releases](https://github.com/adoptium/temurin21-binaries/releases) |
| x64dbg 2026.05.27 | Extract the snapshot. Use `release\x64\x64dbg.exe` for the native exercise. Its sibling `headless.exe` supports scripted checks. [x64dbg release](https://github.com/x64dbg/x64dbg/releases/tag/2026.05.27) |
| ILSpy 11.2 | Extract the Windows x64 archive and open `ILSpy.exe`. Use the self-contained archive if the regular archive needs a .NET Desktop Runtime you lack. [ILSpy release](https://github.com/icsharpcode/ILSpy/releases/tag/v11.2) |
| JADX 1.5.6 | Extract the standalone archive. Set `JAVA_HOME` to the full JDK folder in your shell. Run `bin\jadx.bat --version` or open `bin\jadx-gui.bat`. [JADX release](https://github.com/skylot/jadx/releases/tag/v1.5.6) |

To make Ghidra and JADX available through REA as well, set the following in
PowerShell using your actual extraction paths. The standalone JADX download and
the headless bridge are separate. Obtain the exact 0.7.1 bridge linked by REA.
[REA Windows Ghidra setup](https://github.com/morluto/rea/blob/rea-agents-6.8.0/docs/windows-ghidra-p0.md) · [REA Android setup](https://github.com/morluto/rea/blob/rea-agents-6.8.0/docs/android-analysis.md)

```powershell
$toolRoot = Join-Path $env:LOCALAPPDATA 'Programs\ReverseEngineering'
$env:JAVA_HOME = Join-Path $toolRoot 'Temurin-21.0.13'
$env:GHIDRA_INSTALL_DIR = Join-Path $toolRoot 'Ghidra-12.1.4'
$env:REA_JADX_MCP_JAR = Join-Path $toolRoot 'JADX-bridge-0.7.1\jadx-headless-mcp-0.7.1-all.jar'

npx.cmd rea-agents@6.8.0 doctor --provider ghidra --json
npx.cmd rea-agents@6.8.0 doctor --provider jadx --json
npx.cmd rea-agents@6.8.0 setup --client codex --skill=false --dry-run --json
```

The final preview should show the provider paths on the existing Codex entry.
If you approve, apply the preview with `--yes` in place of `--dry-run`, restart
Codex, and check `binary_session` again. The hands-on exercises also work with
the standalone tools. Use x64dbg and ILSpy directly in the exercises below.

## 3. Investigate the native program

1. Check your copy against the [fixture hashes](../examples/chad-reverse-engineering/fixtures/SHA256SUMS).
   In PowerShell, change into the copied fixture folder. Run the following and
   record both output lines and exit codes. Describe the difference in your own words.

   ```powershell
   .\quota.exe 36
   $LASTEXITCODE
   .\quota.exe 38
   $LASTEXITCODE
   ```

2. Import `quota.exe` into Ghidra and let it analyze the binary. Search for the
   `accepted` and `rejected` strings. Follow a reference from either string into
   the caller, then trace the condition that chooses between them. Write down
   the suspected cutoff and the comparison that makes equality matter.
3. Predict the output and exit code for the cutoff value **before** running it.
   In x64dbg's command bar, use `init "C:\path\to\quota.exe", "<cutoff>"`,
   substituting your copy's path and your predicted cutoff. Subtract Ghidra's
   image base from the comparison address to get its relative virtual address
   (RVA). In x64dbg, `bp mod.main()+<RVA>` sets the breakpoint at that offset
   from the loaded base. Enter the RVA in hex. Resume past any earlier stops
   until your breakpoint fires. Inspect the compared value and step through
   the comparison and conditional jump. Record which address executes next.
4. Run the cutoff directly and compare the output and exit code with your
   prediction. Try a nonnumeric input. It tests whether the program reaches
   the same decision for malformed input. Revise your explanation if an
   observation disagrees with it.

## 4. Apply the method to two other formats

- **Managed .NET DLL.** Open `LabArithmetic.dll` in ILSpy, expand
  `AssimilationLab.LabArithmetic`, and inspect `Adjust`. Predict the return
  value for input `5`. If you have a PowerShell host running .NET 9 or newer,
  run `Add-Type -Path (Resolve-Path .\LabArithmetic.dll).Path`, then
  `[AssimilationLab.LabArithmetic]::Adjust(5)`. Compare the observed return
  value with your prediction.
- **Synthetic Android APK.** Open `assimilation-lab.apk` in JADX GUI, or run
  `jadx.bat -d <new-output-folder> assimilation-lab.apk`. Find
  `org.assimilation.lab.RetryPolicy`. Use the decompiled code to explain how
  the delay changes at the boundary. Open the manifest and record the package
  name. This exercise is static. Its result is evidence about the APK contents.

In the optional worked example, we used the Android SDK Build Tools 36.0.0
native x64 `aapt2.exe` with the `version` argument. Our first x64dbg assertion expected to stop at
the program entry point after one resume. The log showed a TLS callback first.
We advanced past three callbacks, reached the entry-point breakpoint, and
observed exit code 0. The first failure was useful evidence about how the
debugger and executable start up.

## 5. Hand back evidence

Give Vox a short record of the fixture hash, tool versions, commands, outputs
and exit codes, your prediction, and the breakpoint or decompiled code that
supports your explanation. Separate direct observations from conclusions
drawn from them. A second reader should be able to use a new input to check
whether the rule you described holds.

Open the [instructor key and build instructions](../examples/chad-reverse-engineering/instructor/README.md)
after your run. The [author's results](../examples/chad-reverse-engineering/RESULTS.md)
record the checks performed on the supplied fixtures.
