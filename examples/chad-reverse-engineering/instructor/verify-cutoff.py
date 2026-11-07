"""Check the supplied quota.exe with the x64 x64dbg headless executable."""

import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile


def check_behavior(target):
    for value, expected in (
        ("36", ("accepted", "", 0)),
        ("37", ("rejected", "", 3)),
        ("38", ("rejected", "", 3)),
        ("abc", ("", "invalid units", 2)),
    ):
        result = subprocess.run(
            [str(target), value], capture_output=True, text=True, timeout=10
        )
        observed = (result.stdout.strip(), result.stderr.strip(), result.returncode)
        if observed != expected:
            raise SystemExit(f"{value}: expected {expected}, observed {observed}")
        print(f"{value}: {observed}", flush=True)


def check_branch(debugger, target):
    # These addresses are relative to the image base of the supplied build.
    commands = f"""init "{target}", "37"
bp mod.main()+1008
run
again:
cmp cip, mod.main()+1008
je atcheck
run
jmp again
atcheck:
testassert dword:[rsp+20] == .37
sti
testassert cip == mod.main()+100d
sti
testassert cip == mod.main()+1018
log "Cutoff branch reached at RVA {{x:cip-mod.main()}}"
run
ret
"""
    with tempfile.TemporaryDirectory(prefix="assimilation-debug-") as stage:
        script = Path(stage) / "check.txt"
        script.write_text(commands, encoding="utf-8")
        result = subprocess.run(
            [str(debugger), "-userdir", stage, "-testing", "-cf", str(script)],
            cwd=stage,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=35,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    expected = (
        "Cutoff branch reached at RVA 1018",
        "Process stopped with exit code 0x3 (3)",
        "[x64dbg-test] FINAL status=pass asserts=3",
    )
    if result.returncode or any(line not in result.stdout for line in expected):
        raise SystemExit(result.stdout[-4500:] + result.stderr[-1000:])
    for line in expected:
        print(line)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("debugger", type=Path, help="Path to release/x64/headless.exe")
    args = parser.parse_args()
    fixtures = Path(__file__).resolve().parent.parent / "fixtures"
    target = fixtures / "quota.exe"
    expected_hashes = {
        name: digest
        for digest, name in (
            line.split() for line in (fixtures / "SHA256SUMS").read_text().splitlines()
        )
    }
    if hashlib.sha256(target.read_bytes()).hexdigest() != expected_hashes[target.name]:
        raise SystemExit("quota.exe differs from the supplied build")
    check_behavior(target)
    check_branch(args.debugger.resolve(strict=True), target)


if __name__ == "__main__":
    main()
