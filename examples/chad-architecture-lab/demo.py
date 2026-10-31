"""Show a named stage using only a fresh, fixed synthetic fixture."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
from checks import STAGES, load_stage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=STAGES, default="05-casefold")
    parser.add_argument("--scenario", choices=("baseline", "uppercase", "repeat"),
                        default="baseline")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="architecture-demo-") as temp:
        folder = Path(temp)
        files = {"garden.txt": b"Plant basil Saturday\n",
                 "photo.jpg": b"invented image", "unknown.bin": b"synthetic\x00"}
        if args.scenario == "uppercase":
            files["NOTES.TXT"] = b"Synthetic uppercase note"
        for name, data in files.items():
            (folder / name).write_bytes(data)
        preview = load_stage(args.stage).preview
        first = preview(folder)
        initial_json = json.dumps(first, sort_keys=True)
        if args.scenario == "repeat":
            other = folder / "other"
            other.mkdir()
            (other / "drawing.jpg").write_bytes(b"Different synthetic image")
            preview(other)
            files["other/drawing.jpg"] = b"Different synthetic image"
        actual = {p.relative_to(folder).as_posix(): p.read_bytes()
                  for p in folder.rglob("*") if p.is_file()}
        if actual != files:
            raise RuntimeError("Synthetic input changed during preview")
        print(json.dumps({"stage": args.stage, "scenario": args.scenario,
                          "plan": first, "input_files_preserved": True,
                          "earlier_plan_stable": initial_json == json.dumps(first, sort_keys=True)},
                         indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
