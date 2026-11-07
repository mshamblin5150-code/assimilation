# Lab verification

The following checks ran on the author's Windows x64 host. The
[fixture hashes](fixtures/SHA256SUMS) identify the supplied files.

| Check | Observed result |
| --- | --- |
| Build | Visual Studio 2022 x64 tools, .NET SDK 9.0.102, Temurin 21.0.13, and Android SDK Build Tools 36.0.0 with platform 36 produced all three artifacts. A second build in a new output directory reproduced all three SHA-256 values. |
| Native dependencies | The build disables default libraries. `dumpbin /dependents quota.exe` listed only `KERNEL32.dll` and `SHELL32.dll`. |
| Native behavior | The [instructor check](instructor/verify-cutoff.py) observed accepted/0 for 36, rejected/3 for 37 and 38, and invalid units/2 on stderr for `abc`. |
| Ghidra 12.1.4 through REA 6.8.0 | `rea decompile quota.exe 0x140001000 --provider ghidra --format json` recovered `return param_1 < 0x25;` from the supplied executable. |
| x64dbg 2026.05.27 | The headless check read 37 at the comparison, stepped over the conditional jump to RVA `0x1018`, and observed exit 3. All three debugger assertions passed. |
| ILSpy 11.2 | The installed decompiler recovered `return value + 7;` from the supplied DLL. Invoking the compiled `Adjust(5)` returned 12. |
| JADX 1.5.6 | The standalone CLI decoded the manifest package `org.assimilation.lab` and recovered `return i < 3 ? 2 : 10;` from the supplied APK. |
| REA headless JADX | The 0.7.1 bridge read the same APK manifest and recovered `org.assimilation.lab` with both Android SDK environment variables unset. |
| Learner copy | All three file hashes matched the manifest after copying the fixtures to a new directory. |

The cutoff check uses the application's observable output and exit status.
The debugger assertions independently check the claimed branch for the
supplied binary. The APK was inspected statically.

These are author-run checks. The complete walkthrough, fresh-host installation,
and Chad's run have yet to be independently verified.
