"""Run observed-truth scenarios against the running Adobe apps and write one REA Evidence bundle.

python -m scripts.adobe_observed_truth.run history_depth redo_shortcuts --out <dir>
python -m scripts.adobe_observed_truth.run --all --out <dir>

Input scenarios are skipped, and reported as queued, while the workstation is locked.
"""

from __future__ import annotations

import argparse
import functools
import importlib
import json
import math
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import photoshop, win_input
from .idle import ATTENDED_QUIET_S, RealInputWatcher
from .rea_evidence import evidence_bundle, observation_record
from .scenarios import Spec

# Each module exposes SCENARIOS: dict[str, Spec] for one app; keeping them separate
# lets scenario families grow without editing a shared registry.
SCENARIO_MODULES = (
    ("scenarios", "photoshop"),
    ("scenarios_input", "photoshop"),
    ("scenarios_canvas", "photoshop"),
    ("scenarios_painting", "photoshop"),
    ("scenarios_illustrator", "illustrator"),
)


PREFLIGHT_POLL_S = 0.1


def registry() -> dict[str, tuple[Spec, str]]:
    merged: dict[str, tuple[Spec, str]] = {}
    for module_name, app in SCENARIO_MODULES:
        module = importlib.import_module(f"{__package__}.{module_name}")
        for key, spec in module.SCENARIOS.items():
            if key in merged:
                raise ValueError(f"Scenario {key!r} is registered twice")
            merged[key] = (spec, app)
    return merged


def preflight(
    name: str,
    look: Callable[[], list[photoshop.Dialog]],
    click: Callable[[photoshop.Control], None],
    *,
    sleep: Callable[[float], None] = time.sleep,
    timeout_s: float = 5.0,
) -> None:
    """Clear Adobe's survey, then refuse to start a scenario behind any other modal dialog.

    Clicks are posted, not sent, so wait until the survey has really gone: scripting
    stays refused while it is open.
    """
    dismissal = photoshop.dismiss_surveys(look(), click)
    if dismissal.remaining:
        texts = "; ".join(dialog.text for dialog in dismissal.remaining)
        raise RuntimeError(f"{name} not started: Photoshop has a dialog open: {texts}")
    for _ in range(max(1, math.ceil(timeout_s / PREFLIGHT_POLL_S))):
        if not (still_open := photoshop.blocking(look())):
            for survey in dismissal.declined:
                # Evidence for the first real survey: only a replica's control classes are proven.
                classes = sorted({control.class_name for control in survey.controls})
                print(f"{name}: declined Adobe's feedback survey (control classes {classes})")
            return
        sleep(PREFLIGHT_POLL_S)
    texts = "; ".join(dialog.text for dialog in still_open)
    raise RuntimeError(
        f"{name} not started: a dialog did not close within {timeout_s:g} s: {texts}"
    )


def explain_failure(name: str, error: BaseException) -> RuntimeError | None:
    """Headline the error a scenario first raised when another was raised while handling it.

    Scenario `finally` blocks talk to Photoshop, which refuses them behind a modal, so the
    error that surfaces is often the clean-up's, with the real one as its implicit context.
    Context Python suppresses and deliberate `raise ... from` translations are left alone.
    Returns None when there is nothing to re-headline.
    """
    first = error
    while (
        first.__context__ is not None and first.__cause__ is None and not first.__suppress_context__
    ):
        first = first.__context__
    if first is error:
        return None
    return RuntimeError(f"{name} failed: {first!r}; then, while handling it: {error!r}")


def _observe(name: str, spec: Spec, app: str, adapter: Any, identity: Any, out: Path) -> Any:
    if app != "photoshop":
        return spec.run(adapter, identity, out)
    with photoshop.dialogs_off(adapter):
        observation = spec.run(adapter, identity, out)
    if dialogs := photoshop.blocking_dialogs(identity.pid):
        raise RuntimeError(f"{name} left Photoshop blocked by a dialog: {dialogs}")
    return observation


def connect(app: str) -> Any:
    if app == "photoshop":
        return photoshop.Photoshop()
    from .illustrator import Illustrator

    return Illustrator()


def main() -> None:
    scenarios = registry()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenarios", nargs="*", choices=sorted(scenarios))
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    selected = sorted(scenarios) if args.all else args.scenarios
    if not selected:
        parser.error("name scenarios or pass --all")

    win_input.make_dpi_aware()
    # The person's own keyboard or mouse stops every scenario's input at once: attended runs
    # obey the same guard as the runner (idle.PersonInput ignores a drifting mouse).
    watcher = RealInputWatcher().start()
    win_input.set_session_guard(lambda: watcher.idle_s() < ATTENDED_QUIET_S)
    environment = photoshop.environment()
    locked = win_input.workstation_locked()
    sessions: dict[str, tuple[Any, Any]] = {}

    records, queued = [], []
    for name in selected:
        spec, app = scenarios[name]
        if spec.needs_input and locked:
            queued.append(name)
            continue
        with photoshop.exclusive(app):
            if app == "photoshop":
                for pid in photoshop.main_window_pids():
                    look = functools.partial(photoshop.list_dialogs, pid)
                    preflight(name, look, photoshop.click)
            if app not in sessions:
                adapter = connect(app)
                sessions[app] = (adapter, adapter.identity())
                if getattr(adapter, "launched", False):
                    print(f"started {app}; it is left running")
            adapter, identity = sessions[app]
            try:
                observation = _observe(name, spec, app, adapter, identity, args.out)
            except Exception as error:
                if explained := explain_failure(name, error):
                    raise explained from error
                raise
        observation["parameters"][app] = {"version": identity.version, "build": identity.build}
        subject = {"path": identity.executable_path, "sha256": identity.executable_sha256}
        records.append(observation_record(subject=subject, environment=environment, **observation))
        print(f"{name}: {json.dumps(observation['observed'])}")

    if queued:
        print(f"queued until unlocked: {', '.join(queued)}")
    if not records:
        return
    args.out.mkdir(parents=True, exist_ok=True)
    bundle_path = args.out / "rea-evidence-bundle.json"
    bundle_path.write_text(
        json.dumps(evidence_bundle(records), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {bundle_path} ({len(records)} records)")


if __name__ == "__main__":
    main()
