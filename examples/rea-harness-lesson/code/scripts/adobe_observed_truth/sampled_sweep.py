"""A whole-app sweep with the app's interface thread stack-sampled throughout.

The sweep runner (runner_photoshop --sample) runs every spec: menu commands, tools, panels,
image effects pressed through OK, dialogs whose controls are driven. SampledSweep keeps a
sampler (stack_sampler) on the app's current process, restarting it with the app; times every
spec and, inside it, every control action (control_drivers.timed), each control tagged with the
dialog it belongs to; and keeps idle windows (nothing run) at the start, after each restart and
every so many specs. Each process's samples go to their own batch file and the windows to
timeline.jsonl, so a sweep interrupted at any point is still read whole by read_sweep(), and
runtime_links.discoveries() gives each spec and each control the code that ran only for it.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .control_drivers import Control
from .function_index import FunctionIndex, load_index
from .rea_corpus import is_decompiled
from .runtime_links import attribute, discoveries

StartSampler = Callable[[int, threading.Event, Path], None]  # (pid, stop, batch file): blocks until stopped
IDLE_S = 5
IDLE_EVERY = 50


class SampledSweep:
    def __init__(
        self,
        out_dir: Path,
        start_sampler: StartSampler,
        pids: Callable[[], list[int]],
        dialog_of: Callable[[], str | None] = lambda: None,
        clock: Callable[[], int] = lambda: int(time.time() * 1000),
        sleep: Callable[[float], None] = time.sleep,
        idle_s: float = IDLE_S,
        idle_every: int = IDLE_EVERY,
    ):
        out_dir.mkdir(parents=True, exist_ok=True)
        self.out_dir, self._start, self._pids, self._dialog_of = out_dir, start_sampler, pids, dialog_of
        self._clock, self._sleep, self._idle_s, self._idle_every = clock, sleep, idle_s, idle_every
        self._timeline = (out_dir / "timeline.jsonl").open("a", encoding="utf-8", newline="\n")
        self._pid: int | None = None
        self._stop: threading.Event | None = None
        self._thread: threading.Thread | None = None
        self._specs = 0

    def _write(self, row: dict[str, Any]) -> None:
        self._timeline.write(json.dumps(row) + "\n")
        self._timeline.flush()

    def _idle(self) -> None:
        t0 = self._clock()
        self._sleep(self._idle_s)
        self._write({"idle": [t0, self._clock()]})

    def _follow(self) -> None:
        """A sampler on the app's current process: started first, restarted with the app."""
        pids = self._pids()
        pid = pids[0] if pids else None
        if pid is None or pid == self._pid:
            return
        self._stop_sampler()
        self._pid, self._stop = pid, threading.Event()
        out = self.out_dir / f"batches-{pid}.jsonl"
        self._thread = threading.Thread(target=self._start, args=(pid, self._stop, out), daemon=True)
        self._thread.start()
        self._idle()

    def _stop_sampler(self) -> None:
        if self._stop is not None:
            self._stop.set()
            self._thread.join(30)
        self._stop = self._thread = None

    @contextmanager
    def spec(self, item_id: str, kind: str) -> Iterator[None]:
        """Time one spec (its window holds the control actions inside it)."""
        self._follow()
        t0 = self._clock()
        try:
            yield
        finally:
            self._write({"t0": t0, "t1": self._clock(), "kind": kind, "label": item_id})
            self._specs += 1
            if self._idle_every and self._specs % self._idle_every == 0:
                self._idle()

    def control_acted(self, control: Control, t0: int, t1: int) -> None:
        """control_drivers.timed's listener: one control action's window, in its dialog."""
        row = {"t0": t0, "t1": t1, "kind": control.kind, "label": control.label or str(list(control.rect))}
        if dialog := self._dialog_of():
            row["dialog"] = dialog
        self._write(row)

    def close(self) -> None:
        self._stop_sampler()
        self._timeline.close()


def watched_binaries(corpus: Path, app: str) -> tuple[dict[str, Path], dict[str, FunctionIndex]]:
    """Every binary of `app` whose pseudocode is all on disk, by file name: its installed file
    (for the sampler's call checks and image base) and its decomp index. A filter's dialog runs
    in its plug-in, so the sweep watches them all."""
    manifest = json.loads((corpus / "manifest.json").read_text(encoding="utf-8"))
    watch, indexes = {}, {}
    for entry in manifest:
        work = Path(entry["work_dir"])
        name = Path(entry["relative"].replace("\\", "/")).name
        if entry["app"] == app and name not in watch and is_decompiled(work):
            watch[name], indexes[name] = Path(entry["path"]), load_index(work)
    return watch, indexes


def feature_of(item_id: str) -> str:
    """The feature a spec exercises: its item id without variants ("menu:1802@chart@mask" is
    Levels applied on a masked layer, a variant of menu:1802)."""
    return item_id.split("@", 1)[0]


def build_maps(out_dir: Path, dataset: Path, *, known: set[str]) -> dict[str, int]:
    """Map a sweep: feature-code.jsonl, per feature (menu command, tool, panel; feature_of) and
    binary, the functions observed for it alone in any of its variants (on the chart, in each
    document state, its effect applied, its dialog's controls driven), with the variants that ran:
    counted per spec, code a feature ran in every state belonged to none of them (2026-11-25).
    And in runtime-discovery.jsonl the functions observed for each control
    of each dialog driven, replacing earlier sampled rows of those dialogs (rows found another
    way, such as hooks, are kept). The anchor is the SHA-256 of the sweep's timeline and batch
    files: the samples themselves stay local.

    A control's label is published only if it is in `known` (Photoshop's own labels, as for
    control-actions.jsonl; anything else becomes its length and hash): timeline labels are raw
    OCR, and a file dialog's walk read the operator's own file names (2026-11-24). Dialogs whose
    control pass recorded a Windows file dialog get no control rows: they are the work pass's."""
    from .control_pass import publishable

    batches, idle, actions = read_sweep(out_dir)
    file_dialogs = _file_dialogs(out_dir / "control-actions.jsonl")
    digest = hashlib.sha256()
    for path in [out_dir / "timeline.jsonl", *sorted(out_dir.glob("batches-*.jsonl"))]:
        digest.update(path.read_bytes())
    anchor = f"sha256:{digest.hexdigest()}"
    variants: dict[str, set[str]] = {}
    for a in actions:
        if not a.get("dialog"):
            variants.setdefault(feature_of(a["label"]), set()).add(a["label"])
    as_features = [{"t0": a["t0"], "t1": a["t1"], "kind": "feature", "label": feature_of(a["label"])}
                   for a in actions if not a.get("dialog")]
    features = [{"item_id": r["label"], "variants": sorted(variants[r["label"]]), "binary": r["binary"],
                 "functions": r["functions"], "calls": r["calls"], "via": r["via"], "anchor": r["anchor"]}
                for r in discoveries(batches, idle, as_features, dialog="", via="sampled", anchor=anchor)]
    rows = discoveries(batches, idle, actions, dialog="", via="sampled", anchor=anchor)
    controls = [publishable(r, known) for r in rows if r["dialog"] and r["dialog"] not in file_dialogs]
    with (dataset / "feature-code.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(f) + "\n" for f in features)
    found = dataset / "runtime-discovery.jsonl"
    earlier = [json.loads(l) for l in found.read_text(encoding="utf-8").splitlines() if l.strip()] if found.exists() else []
    # An earlier sampled row is replaced only for a control this sweep drove again: a short rerun
    # touching one Curves control had dropped all 28 earlier Curves rows (2026-11-24). A file
    # dialog's rows all go: it is not control-mapped.
    driven = {(a["dialog"], a["kind"], json.dumps(publishable(a, known).get("label")))
              for a in actions if a.get("dialog")}
    kept = [r for r in earlier
            if r["dialog"] not in file_dialogs
            and not (r["via"] == "sampled" and (r["dialog"], r["kind"], json.dumps(r["label"])) in driven)]
    with found.open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(r) + "\n" for r in kept + controls)
    observed = {f for f, link in attribute(batches, idle, actions).items() if link["status"] == "observed"}
    return {
        "specs": len({a["label"] for a in actions if not a.get("dialog")}),
        "features_with_code": len({f["item_id"] for f in features}),
        "controls": len({(a["dialog"], a["kind"], a["label"]) for a in actions if a.get("dialog")}),
        "controls_with_code": len({(r["dialog"], r["kind"], json.dumps(r["label"])) for r in controls}),
        "functions_observed": len(observed),
    }


def _file_dialogs(control_actions: Path) -> set[str]:
    """Dialogs a control pass recorded as Windows file dialogs (left to the work pass)."""
    if not control_actions.exists():
        return set()
    rows = (json.loads(l) for l in control_actions.read_text(encoding="utf-8").splitlines() if l.strip())
    return {r["dialog"] for r in rows if r.get("kind") == "file_dialog" and r.get("dialog")}


def read_sweep(out_dir: Path) -> tuple[list[dict[str, Any]], list[list[int]], list[dict[str, Any]]]:
    """A sweep's samples (every process's batches), idle windows and actions (by start)."""
    batches = [json.loads(line) for path in sorted(out_dir.glob("batches-*.jsonl"))
               for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    idle, actions = [], []
    for line in (out_dir / "timeline.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if "idle" in row:
                idle.append(row["idle"])
            else:
                actions.append(row)
    return batches, idle, sorted(actions, key=lambda a: a["t0"])


def main() -> None:
    """python -m scripts.adobe_observed_truth.sampled_sweep <sweep folder> --dataset <dir>

    Map a sweep run with runner_photoshop --sample (it may still be running: what is there so far)."""
    import argparse

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("sweep", type=Path)
    parser.add_argument("--dataset", type=Path, required=True)
    args = parser.parse_args()
    from .control_catalogue import load
    from .control_pass import known_labels
    from .ocr_correct import STRINGS_FILE

    strings = STRINGS_FILE.read_text(encoding="utf-8").splitlines() if STRINGS_FILE.exists() else []
    known = known_labels(load(args.dataset / "dialog-controls.jsonl"), strings)
    print(json.dumps(build_maps(args.sweep, args.dataset, known=known), indent=2))


if __name__ == "__main__":
    main()
