"""Photoshop's pixel kernels hooked: which kernels each spec ran, and with what buffers.

Photoshop keeps its per-pixel maths (brush and stamp tips, blend modes, dodge and burn by tonal
range, resampling, a PDE solver, morphology) as Halide pipelines in one plug-in,
HalideBottlenecks.8bx. Each pipeline is registered once, statically, under a name of the form
HalideProcFunctor::<name>, by a small registrar function that stores the pipeline's entry
functions beside the name. kernel_table() reads those registrars out of the plug-in's decompile,
so every kernel's entry addresses are known without running anything.

Sampling misses these kernels (they are sub-second and run on worker threads); Interceptor hooks
on their entries see every call on every thread. The hook run writes batches in runtime_links'
format to a file, so runtime_links.attribute() over a sampled sweep's timeline says which kernels
ran for which spec.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_REGISTRATION = re.compile(r'"HalideProcFunctor::(\w+)";(.*?)_Init_thread_footer', re.S)
_ENTRY = re.compile(r"= FUN_([0-9a-f]+);")


def kernel_table(pseudocode: Path) -> list[dict[str, Any]]:
    """Every kernel registered in a decompile's function files (`<address>.c`), by name: its
    entry functions (Ghidra addresses, in the order the registrar stores them) and its registrar."""
    rows = []
    for path in pseudocode.glob("*.c"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "HalideProcFunctor::" not in text:
            continue
        for match in _REGISTRATION.finditer(text):
            rows.append({"name": match.group(1),
                         "entries": [f"0x{a}" for a in _ENTRY.findall(match.group(2))],
                         "registrar": path.stem})
    return sorted(rows, key=lambda r: r["name"])


def kernels_by_spec(
    batches: list[dict[str, Any]], idle: list[list[int]], specs: list[dict[str, Any]], table: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Kernel calls by name: per spec (each batch counts for every spec window it overlaps),
    while idle (nothing run: compositing and other background work), and between windows."""
    name_of = {entry: row["name"] for row in table for entry in row["entries"]}
    out: dict[str, Any] = {"specs": {}, "idle": {}, "between": {}}

    def add(into: dict[str, int], counts: dict[str, int]) -> None:
        for entry, n in counts.items():
            name = name_of.get(entry, entry)
            into[name] = into.get(name, 0) + n

    for batch in batches:
        if batch.get("kind") != "hits":
            continue
        t0, t1 = batch["t0"], batch["t1"]
        during = [s["label"] for s in specs if t0 <= s["t1"] and s["t0"] <= t1]
        for label in during:
            add(out["specs"].setdefault(label, {}), batch["counts"])
        if not during:
            quiet = any(t0 <= w[1] and w[0] <= t1 for w in idle)
            add(out["idle" if quiet else "between"], batch["counts"])
    return out


ARG_SLOTS = 10  # leading arguments read on each sampled call
SIGNATURES_PER_ENTRY = 40  # distinct argument shapes kept per entry


def hook_script(module: str, image_base: str, entries: list[str], out_path: str, batch_ms: int = 250) -> str:
    """The Frida script hooking every kernel entry (Ghidra addresses) in the loaded `module`.

    It appends JSON lines to `out_path`: runtime_links-format batches ({"kind": "hits", t0, t1,
    counts}) and, per entry, each new argument shape ({"kind": "args", fn, t, args}) up to
    SIGNATURES_PER_ENTRY. An argument that reads as a Halide buffer (type code, bits, 1 to 4
    dimensions) is kept as its type and per-dimension min/extent/stride; any other is kept as its
    raw 64-bit value (a float scalar passed on the stack shows as its bits)."""
    return f"""const MODULE = {json.dumps(module)};
const IMAGE_BASE = ptr({json.dumps(image_base)});
const FUNCS = {json.dumps(list(entries))};
const OUT = new File({json.dumps(out_path)}, "a");
const counts = {{}};
const shapes = {{}};
let windowStart = Date.now();
let hookedBase = null;
function write(row) {{ OUT.write(JSON.stringify(row) + "\\n"); }}
function buffer(p) {{
  try {{
    const code = p.add(0x20).readU8(), bits = p.add(0x21).readU8(), dims = p.add(0x24).readS32();
    if (code > 3 || [8, 16, 32, 64].indexOf(bits) < 0 || dims < 1 || dims > 4) return null;
    const d = p.add(0x28).readPointer();
    const out = {{ code, bits, dims: [] }};
    for (let i = 0; i < dims; i++) {{
      const q = d.add(16 * i);
      out.dims.push([q.readS32(), q.add(4).readS32(), q.add(8).readS32()]);
    }}
    return out;
  }} catch (e) {{ return null; }}
}}
function hookModule(mod) {{
  if (hookedBase !== null && mod.base.equals(hookedBase)) return;
  hookedBase = mod.base;
  let hooked = 0;
  for (const f of FUNCS) {{
    try {{
      Interceptor.attach(mod.base.add(ptr(f).sub(IMAGE_BASE)), {{ onEnter(args) {{
        counts[f] = (counts[f] || 0) + 1;
        const seen = shapes[f] || (shapes[f] = {{}});
        if (Object.keys(seen).length >= {SIGNATURES_PER_ENTRY}) return;
        const row = [];
        for (let i = 0; i < {ARG_SLOTS}; i++) {{
          const a = args[i];
          const b = a.isNull() ? null : buffer(a);
          row.push(b === null ? a.toString() : b);
        }}
        const key = JSON.stringify(row.map(x => typeof x === "string" ? x : [x.code, x.bits, x.dims.map(d => d[1])]));
        if (seen[key]) return;
        seen[key] = 1;
        write({{ kind: "args", fn: f, t: Date.now(), tid: Process.getCurrentThreadId(), args: row }});
      }} }});
      hooked++;
    }} catch (e) {{ write({{ kind: "hook_failed", fn: f, error: String(e) }}); }}
  }}
  write({{ kind: "loaded", module: MODULE, base: mod.base.toString(), hooked, t: Date.now() }});
  send({{ kind: "loaded", hooked }});
}}
const present = Process.findModuleByName(MODULE);
if (present !== null) hookModule(present);
else send({{ kind: "module_absent", module: MODULE }});
setInterval(() => {{
  const now = Date.now();
  const keys = Object.keys(counts);
  if (keys.length) {{
    const snapshot = {{}};
    for (const k of keys) {{ snapshot[k] = counts[k]; delete counts[k]; }}
    write({{ kind: "hits", t0: windowStart, t1: now, counts: snapshot }});
  }}
  OUT.flush();
  windowStart = now;
}}, {batch_ms});
"""


def capture_script(
    module: str, image_base: str, entries: list[str], out_path: str,
    per_window: int = 3, window_ms: int = 5000, max_span: int = 1 << 20,
    bytes_of: list[int] | None = None,
) -> str:
    """The Frida script copying kernel buffers: for at most `per_window` calls of each entry in
    every `window_ms` (so captures spread over the specs of a run), every argument that reads as
    a Halide buffer is copied on entry and again on return, with the scalar arguments, as one
    JSON line ({"kind": "buffers", fn, t, scalars, before, after}; a buffer is its type, dims and
    the hex bytes from its first element to its last, at most `max_span` bytes, and its host
    address: dabs into one stroke buffer differ by their offset in it). With `bytes_of`, only
    those argument positions keep their bytes; the others keep type, dims and address."""
    return f"""const MODULE = {json.dumps(module)};
const IMAGE_BASE = ptr({json.dumps(image_base)});
const FUNCS = {json.dumps(list(entries))};
const OUT = new File({json.dumps(out_path)}, "a");
const BYTES_OF = {json.dumps(bytes_of)};
const taken = {{}};
let window = Date.now();
function hex(bytes) {{ return Array.from(new Uint8Array(bytes), b => (b < 16 ? "0" : "") + b.toString(16)).join(""); }}
function buffer(p, withBytes) {{
  try {{
    const code = p.add(0x20).readU8(), bits = p.add(0x21).readU8(), dims = p.add(0x24).readS32();
    if (code > 3 || [8, 16, 32, 64].indexOf(bits) < 0 || dims < 1 || dims > 4) return null;
    const d = p.add(0x28).readPointer(), host = p.add(0x10).readPointer();
    const out = {{ code, bits, host: host.toString(), dims: [] }};
    let span = 1;
    for (let i = 0; i < dims; i++) {{
      const q = d.add(16 * i);
      const dim = [q.readS32(), q.add(4).readS32(), q.add(8).readS32()];
      out.dims.push(dim);
      span += (dim[1] - 1) * Math.abs(dim[2]);
    }}
    const bytes = span * bits / 8;
    if (withBytes && !host.isNull() && bytes > 0 && bytes <= {max_span}) out.hex = hex(host.readByteArray(bytes));
    return out;
  }} catch (e) {{ return null; }}
}}
function hookModule(mod) {{
  let hooked = 0;
  for (const f of FUNCS) {{
    try {{
      Interceptor.attach(mod.base.add(ptr(f).sub(IMAGE_BASE)), {{
        onEnter(args) {{
          const now = Date.now();
          if (now - window > {window_ms}) {{ window = now; for (const k in taken) delete taken[k]; }}
          if ((taken[f] || 0) >= {per_window}) {{ this.skip = true; return; }}
          taken[f] = (taken[f] || 0) + 1;
          this.ptrs = []; this.scalars = []; this.before = [];
          for (let i = 0; i < 10; i++) {{
            const a = args[i];
            const b = a.isNull() ? null : buffer(a, BYTES_OF === null || BYTES_OF.indexOf(i) >= 0);
            if (b === null) {{ this.scalars.push(a.toString()); this.ptrs.push(null); this.before.push(null); }}
            else {{ this.scalars.push(null); this.ptrs.push(a); this.before.push(b); }}
          }}
        }},
        onLeave(retval) {{
          if (this.skip) return;
          const after = this.ptrs.map((p, i) => p === null ? null : buffer(p, BYTES_OF === null || BYTES_OF.indexOf(i) >= 0));
          OUT.write(JSON.stringify({{ kind: "buffers", fn: f, t: Date.now(), ret: retval.toInt32(), scalars: this.scalars, before: this.before, after }}) + "\\n");
          OUT.flush();
        }},
      }});
      hooked++;
    }} catch (e) {{ OUT.write(JSON.stringify({{ kind: "hook_failed", fn: f, error: String(e) }}) + "\\n"); }}
  }}
  send({{ kind: "loaded", hooked }});
}}
const present = Process.findModuleByName(MODULE);
if (present !== null) hookModule(present); else send({{ kind: "module_absent", module: MODULE }});
"""


_DTYPES = {(0, 8): "int8", (0, 16): "int16", (0, 32): "int32", (1, 8): "uint8", (1, 16): "uint16",
           (1, 32): "uint32", (2, 32): "float32", (2, 64): "float64"}


def buffer_array(buffer: dict[str, Any]) -> Any:
    """A captured buffer's bytes as an array indexed [last dim, ..., first dim] (rows, columns
    for an image), honouring each dimension's stride."""
    import numpy as np

    flat = np.frombuffer(bytes.fromhex(buffer["hex"]), dtype=_DTYPES[(buffer["code"], buffer["bits"])])
    dims = buffer["dims"]
    grids = np.meshgrid(*[np.arange(d[1]) * d[2] for d in reversed(dims)], indexing="ij")
    return flat[sum(grids)]


def tip_shape(tip: Any) -> dict[str, float]:
    """A dab's tip mask measured from its second moments, as a filled ellipse: length and width
    (4 standard deviations along each principal axis), roundness (width / length), the long
    axis's angle in degrees (counter-clockwise from the x axis, 0 to 180) and its mass in
    full-coverage pixels."""
    import numpy as np

    a = tip.astype(float) / 255.0
    mass = float(a.sum())
    ys, xs = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    cx, cy = (a * xs).sum() / mass, (a * ys).sum() / mass
    cxx, cyy = (a * (xs - cx) ** 2).sum() / mass, (a * (ys - cy) ** 2).sum() / mass
    cxy = (a * (xs - cx) * (ys - cy)).sum() / mass
    values, vectors = np.linalg.eigh([[cxx, cxy], [cxy, cyy]])
    length, width = 4 * float(np.sqrt(values[1])), 4 * float(np.sqrt(max(values[0], 0.0)))
    angle = float(np.degrees(np.arctan2(-vectors[1, 1], vectors[0, 1])) % 180.0)
    return {"length": length, "width": width, "roundness": width / length if length else 1.0,
            "angle": angle, "mass": mass}


# Where each tip kernel takes its per-dab bytes (argument positions): the airbrush (flow under
# 100) takes a per-dab seed, then opacity and flow; the others opacity, then the seed.
_TIP_BYTES = {"Airbrush": {"opacity_byte": 4, "flow_byte": 5}, "": {"opacity_byte": 3}}


def dab_rows(
    captures: list[dict[str, Any]], specs: list[dict[str, Any]], table: list[dict[str, Any]], masks: bool = False
) -> list[dict[str, Any]]:
    """Per spec, every dab a tip kernel drew in its window (capture_script rows with the tip
    mask's bytes, argument 2): kernel counts, and per dab its tip shape (tip_shape), opacity and
    flow bytes, and where it landed in the stroke buffer (row and column from the stroke
    buffer's address, relative to the spec's first dab). With `masks`, each dab's tip mask too."""
    name_of = {entry: row["name"] for row in table for entry in row["entries"]}
    rows: dict[str, dict[str, Any]] = {}
    for capture in sorted((c for c in captures if c.get("kind") == "buffers"), key=lambda c: c["t"]):
        spec = next((s for s in specs if s["t0"] <= capture["t"] <= s["t1"]), None)
        tip = capture["before"][2]
        if spec is None or tip is None or "hex" not in tip:
            continue
        name = name_of.get(capture["fn"], capture["fn"])
        layout = next(v for k, v in _TIP_BYTES.items() if k in name)
        row = rows.setdefault(spec["label"], {"item_id": spec["label"], "kernels": {}, "dabs": 0, "origin": None,
                                              "length": [], "width": [], "roundness": [], "angle": [],
                                              "opacity_byte": [], "flow_byte": [], "row": [], "column": []})
        row["kernels"][name] = row["kernels"].get(name, 0) + 1
        row["dabs"] += 1
        mask = buffer_array(tip)
        if masks:
            row.setdefault("tip", []).append(mask.tolist())
        shape = tip_shape(mask)
        for key in ("length", "width", "roundness", "angle"):
            row[key].append(round(shape[key], 2 if key != "roundness" else 3))
        for key in ("opacity_byte", "flow_byte"):
            if key in layout:
                row[key].append(int(capture["scalars"][layout[key]], 16) & 0xFF)
        stroke = capture["before"][1]
        address, stride = int(stroke["host"], 16), stroke["dims"][1][2]
        row["origin"] = address if row["origin"] is None else row["origin"]
        down, across = divmod(address - row["origin"], stride)
        if across > stride // 2:  # a dab left of the first one, on the next row's address
            down, across = down + 1, across - stride
        row["row"].append(down)
        row["column"].append(across)
    for row in rows.values():
        del row["origin"]
        if not row["flow_byte"]:
            del row["flow_byte"]
    return list(rows.values())


def main() -> None:
    """python -m scripts.adobe_observed_truth.kernel_hooks <sweep folder> --table <kernel table> --out <file>

    Write one row per spec of a sweep run under capture_script (dabs.jsonl beside timeline.jsonl):
    the dabs each spec drew, measured (dab_rows)."""
    import argparse

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("sweep", type=Path)
    parser.add_argument("--table", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--masks", action="store_true", help="keep each dab's tip mask")
    args = parser.parse_args()

    def lines(path: Path) -> list[dict[str, Any]]:
        return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

    specs = [r for r in lines(args.sweep / "timeline.jsonl") if "label" in r and "dialog" not in r]
    rows = dab_rows(lines(args.sweep / "dabs.jsonl"), specs, lines(args.table), masks=args.masks)
    with args.out.open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(r, sort_keys=True) + "\n" for r in rows)
    print(f"{len(rows)} specs, {sum(r['dabs'] for r in rows)} dabs written to {args.out.name}")


if __name__ == "__main__":
    main()
