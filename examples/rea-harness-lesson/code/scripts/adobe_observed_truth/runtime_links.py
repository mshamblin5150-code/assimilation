"""Upgrade a control's code link (control_code.py: a name match) to an observation.

REA attaches Frida to the running app (start_frida_session, load_frida_script) with the script
hook_script() writes: each mapped function is hooked at its offset in the loaded module, and
call counts go back as timestamped batches. Meanwhile the harness drives the dialog, logging
the time window of every action. attribute() then says, per function, which control it fired
for. A function that fires while the dialog sits idle is background work; one that fires for
several controls is shared code; only one firing for a single control, and never idle, is
observed for that control. Function addresses are Ghidra's (the binary's image base plus the
offset), so they hold wherever Windows loads the module.

A control the name match could not place has no functions to hook. For it, stack_sampler
samples the app's interface thread while the harness drives the dialog, and discoveries() keeps,
per control, the functions observed for it alone (runtime-discovery.jsonl, via sampled). What
sampling missed, quicker than its interval, is called by what it caught: hook_candidates() names
those callees from the decomp, this module's hook script hooks them while the dialog is driven
again, and discoveries() keeps the ones observed for one control (via runtime).
"""

from __future__ import annotations

import bisect
import json
from collections.abc import Callable, Iterable
from typing import Any

from .function_index import FunctionIndex

BATCH_MS = 250  # how often the script reports its counts


def hook_script(module: str, image_base: str, functions: list[str]) -> str:
    """The Frida script hooking `functions` (Ghidra addresses) in the loaded `module`."""
    return f"""const MODULE = {json.dumps(module)};
const IMAGE_BASE = ptr({json.dumps(image_base)});
const FUNCS = {json.dumps(list(functions))};
const counts = {{}};
let windowStart = Date.now();
let hookedBase = null;
function hookModule(mod) {{
  if (hookedBase !== null && mod.base.equals(hookedBase)) return;
  hookedBase = mod.base;
  const hooked = [];
  for (const f of FUNCS) {{
    try {{
      Interceptor.attach(mod.base.add(ptr(f).sub(IMAGE_BASE)), {{ onEnter() {{ counts[f] = (counts[f] || 0) + 1; }} }});
      hooked.push(f);
    }} catch (e) {{ send({{ kind: "hook_failed", fn: f, error: String(e) }}); }}
  }}
  send({{ kind: "loaded", module: MODULE, base: mod.base.toString(), hooked, t: Date.now() }});
}}
// A filter plug-in loads when its filter runs, at a new address each time: hook it on load.
const present = Process.findModuleByName(MODULE);
if (present !== null) hookModule(present);
if (typeof Process.attachModuleObserver === "function") {{
  Process.attachModuleObserver({{
    onAdded(mod) {{ if (mod.name.toLowerCase() === MODULE.toLowerCase()) hookModule(mod); }},
    onRemoved(mod) {{ if (mod.name.toLowerCase() === MODULE.toLowerCase()) {{ hookedBase = null; send({{ kind: "unloaded", t: Date.now() }}); }} }},
  }});
}} else {{
  setInterval(() => {{ const m = Process.findModuleByName(MODULE); if (m !== null) hookModule(m); }}, 20);
}}
setInterval(() => {{
  const now = Date.now();
  const keys = Object.keys(counts);
  if (keys.length) {{
    const snapshot = {{}};
    for (const k of keys) {{ snapshot[k] = counts[k]; delete counts[k]; }}
    send({{ kind: "hits", t0: windowStart, t1: now, counts: snapshot }});
  }}
  windowStart = now;
}}, {BATCH_MS});
"""


def _overlaps(a0: int, a1: int, b0: int, b1: int) -> bool:
    return a0 <= b1 and b0 <= a1


Window = tuple[int, int]


def _control(action: dict[str, Any]) -> str:
    """An action's control: "kind label", with its dialog first when a sweep names one."""
    named = f"{action['kind']} {action['label']}"
    return f"{action['dialog']}: {named}" if action.get("dialog") else named


def _innermost(overlapping: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The overlapping actions that hold no narrower one: a control acted on inside a menu
    command's window is what runs then, not the command."""
    return [a for a in overlapping
            if not any(b is not a and a["t0"] <= b["t0"] and b["t1"] <= a["t1"] and (b["t0"], b["t1"]) != (a["t0"], a["t1"])
                       for b in overlapping)]


def _windows_at(windows: list[dict[str, Any]], starts: list[int], reach: int, t0: int, t1: int) -> list[dict[str, Any]]:
    """The windows (sorted by start) overlapping t0..t1; none is longer than `reach`."""
    upper = bisect.bisect_right(starts, t1)
    lower = bisect.bisect_left(starts, t0 - reach)
    return [w for w in windows[lower:upper] if _overlaps(t0, t1, w["t0"], w["t1"])]


def attribute(
    batches: Iterable[dict[str, Any]], baseline: Window | list[Window], actions: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Per hooked function: status (observed, several controls, fires while idle,
    unattributed), the controls it fired for ("kind label", or "dialog: kind label" in a sweep),
    and its total calls. `baseline` is the idle window, or a sweep's many."""
    idle_windows = [baseline] if baseline and isinstance(baseline[0], int) else list(baseline)
    ordered = sorted(actions, key=lambda a: a["t0"])
    starts = [a["t0"] for a in ordered]
    reach = max((a["t1"] - a["t0"] for a in ordered), default=0)
    calls: dict[str, int] = {}
    idle: set[str] = set()
    fired_for: dict[str, set[str]] = {}
    for b in batches:
        if b.get("kind") != "hits":
            continue
        during = {_control(a) for a in _innermost(_windows_at(ordered, starts, reach, b["t0"], b["t1"]))}
        quiet = not during and any(_overlaps(b["t0"], b["t1"], *w) for w in idle_windows)
        for fn, n in b["counts"].items():
            calls[fn] = calls.get(fn, 0) + n
            fired_for.setdefault(fn, set()).update(during)
            if quiet:  # a batch running into an action is that action's
                idle.add(fn)
    links = {}
    for fn, n in calls.items():
        controls = sorted(fired_for[fn])
        if fn in idle:
            status = "fires while idle"
        elif not controls:
            status = "unattributed"
        elif len(controls) == 1:
            status = "observed"
        else:
            status = "several controls"
        links[fn] = {"status": status, "controls": controls, "calls": n}
    return links


def discoveries(
    batches: Iterable[dict[str, Any]],
    baseline: tuple[int, int],
    actions: list[dict[str, Any]],
    dialog: str,
    via: str,
    anchor: str,
    binary: str | None = None,
) -> list[dict[str, Any]]:
    """Per control driven in `dialog` and per binary, the functions observed for that control
    alone (attribute() status observed), with their calls, how they were seen (`via` sampled:
    stack_sampler; runtime: the hook script) and its `anchor` (the sample file's digest, or the
    REA Frida observation). Sampled functions carry their binary ("name!address"); hooked ones
    are plain addresses in `binary`. A control nothing was observed for alone has no row."""
    links = attribute(batches, baseline, actions)
    places: dict[tuple[str, str], dict[str, int]] = {}  # (control, binary) -> address -> calls
    for fn, link in links.items():
        if link["status"] == "observed":
            where, address = fn.split("!", 1) if "!" in fn else (binary, fn)
            places.setdefault((link["controls"][0], where), {})[address] = link["calls"]
    driven = {(a.get("dialog") or dialog, a["label"], a["kind"]): _control(a) for a in actions}
    return [
        {"dialog": in_dialog, "label": label, "kind": kind, "binary": where,
         "functions": sorted(here), "calls": sum(here.values()), "via": via, "anchor": anchor}
        for (in_dialog, label, kind), name in sorted(driven.items())
        for (control, where), here in sorted(places.items())
        if control == name
    ]


HOOK_DEPTH = 2
HOOK_CAP = 4000  # hooks one drive of a dialog carries


def hook_candidates(
    sampled: dict[str, dict[str, Any]],
    binary: str,
    index: FunctionIndex,
    pseudocode: Callable[[str], str],
    depth: int = HOOK_DEPTH,
    cap: int = HOOK_CAP,
) -> list[str]:
    """The functions of `binary` to hook after sampling (`sampled`: attribute() of the sampled
    batches): the decomp's callees of control code (observed for one control, or shared by
    several), up to `depth` calls deep, that sampling never saw; nearest first, at most `cap`.
    The idle loop calls everything and seeds nothing."""
    prefix = f"{binary}!"
    seen = {fn[len(prefix):] for fn in sampled if fn.startswith(prefix)}
    frontier = sorted(
        (fn[len(prefix):] for fn, link in sampled.items()
         if fn.startswith(prefix) and link["status"] in ("observed", "several controls")),
        key=lambda a: int(a, 16),
    )
    reached, chosen = set(frontier), []
    for _ in range(depth):
        found = sorted({c for fn in frontier for c in index.callees(pseudocode(fn))} - reached, key=lambda a: int(a, 16))
        reached.update(found)
        chosen.extend(c for c in found if c not in seen)
        frontier = found
    return chosen[:cap]
