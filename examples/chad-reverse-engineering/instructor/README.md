# Instructor key

Start with the [learner walkthrough](../../../docs/CHAD-REVERSE-ENGINEERING.md).
The fixtures were written for this lab. Give learners the
[fixture directory](../fixtures/) first. Reveal the source and the expected
results after they have recorded their own prediction.

## Expected results

| Input to `quota.exe` | Output | Exit code |
| --- | --- | --- |
| `36` | `accepted` on stdout | 0 |
| `37` | `rejected` on stdout | 3 |
| `38` | `rejected` on stdout | 3 |
| `abc` | `invalid units` on stderr | 2 |

The accepted range ends at 36. The program validates the input before it
calls the comparison function. In the supplied x64 binary, Ghidra loads at
image base `0x140000000`. The comparison function starts at
`0x140001000`. The comparison is at RVA `0x1008` and compares the value
with `0x25` (37). The signed jump at RVA `0x100D` takes input 37 to
RVA `0x1018`, which returns false to the caller. A build with a different
compiler or settings may put these instructions at other addresses.

The [scripted instructor check](verify-cutoff.py) verifies the supplied
binary's hash before using those RVAs. From the repository root, pass the x64
headless executable from the verified x64dbg release.

```powershell
$debugger = "$env:LOCALAPPDATA/Programs/ReverseEngineering/x64dbg-2026.05.27/release/x64/headless.exe"
python examples/chad-reverse-engineering/instructor/verify-cutoff.py $debugger
```

The managed fixture's `Adjust(5)` returns 12. The APK declares package
`org.assimilation.lab`. Its `RetryPolicy.delaySeconds` returns 2 for
attempts below 3 and 10 for attempts of 3 or more. The APK is unsigned and
contains no launch activity. It is supplied for static inspection.

## Rebuild the fixtures

Use PowerShell 7.3 or newer from an x64 Visual Studio Native Tools Command Prompt with
the MSVC C/C++ workload and Windows SDK. The full build also needs the .NET 9
SDK, a full JDK 21, Android SDK Build Tools 36.0.0, and Android platform 36.
These are authoring prerequisites. The learner can use the supplied files.

```powershell
./build-fixtures.ps1 -AndroidSdk 'C:/path/to/android-sdk' -JavaHome 'C:/path/to/jdk-21' -OutputDirectory './rebuilt'
```

Run this from the instructor directory. Use a new output directory. The script
prints the new SHA-256 values. The checked-in manifest identifies the supplied
files. Compare behavior on rebuilds and re-discover addresses if the native
hash differs. The source is in [native](native/), [managed](managed/), and
[android](android/).
