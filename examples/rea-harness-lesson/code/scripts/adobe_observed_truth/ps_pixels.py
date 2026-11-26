"""True pixels out of Photoshop, and the analysis that turns them into integers.

Exports save a PNG copy of the active document to a fresh temporary folder, read
it, and delete it. Only 8-bit RGB documents are supported.

Arrays are indexed [y, x]. Coordinates are pixel indices; a centre (x, y) means
the pixel whose document-space centre is (x + 0.5, y + 0.5).
"""

from __future__ import annotations

import json
import math
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import numpy as np

from .photoshop import Photoshop


def radial_profile(channel: np.ndarray, centre: tuple[int, int], radii: Sequence[int]) -> list[int]:
    """Mean of the right, left, down and up samples at each radius; samples off the array are skipped."""
    height, width = channel.shape
    cx, cy = centre
    profile = []
    for radius in radii:
        samples = [
            int(channel[y, x])
            for x, y in ((cx + radius, cy), (cx - radius, cy), (cx, cy + radius), (cx, cy - radius))
            if 0 <= x < width and 0 <= y < height
        ]
        profile.append(round(sum(samples) / len(samples)) if samples else 0)
    return profile


def zero_radius(channel: np.ndarray, centre: tuple[int, int]) -> int:
    """Smallest whole radius beyond every non-zero pixel; 0 when nothing is covered."""
    ys, xs = np.nonzero(channel)
    if len(xs) == 0:
        return 0
    cx, cy = centre
    farthest_squared = int(((xs - cx) ** 2 + (ys - cy) ** 2).max())
    return math.isqrt(farthest_squared) + 1


def nonzero_bounds(mask: np.ndarray) -> list[int] | None:
    """[left, top, right, bottom] of non-zero pixels, right and bottom exclusive as Photoshop reports bounds."""
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def mask_difference(before: np.ndarray, after: np.ndarray) -> dict[str, int]:
    difference = np.abs(before.astype(np.int16) - after.astype(np.int16))
    return {
        "differing_pixels": int(np.count_nonzero(difference)),
        "max_abs_difference": int(difference.max(initial=0)),
    }


def changed_mask(before: np.ndarray, after: np.ndarray) -> np.ndarray:
    """[y, x] booleans: True where any channel of two same-sized RGBA arrays differs."""
    return np.any(before != after, axis=-1)


Region = tuple[int, int, int, int]  # y0, y1, x0, x1 (end exclusive)


def pixels_sha256(image: np.ndarray) -> str:
    """The exact identity of an image's pixels: its shape and bytes."""
    import hashlib

    digest = hashlib.sha256(repr(image.shape).encode("ascii"))
    digest.update(np.ascontiguousarray(image).tobytes())
    return digest.hexdigest()


def canvas_change(
    before: np.ndarray, after: np.ndarray, regions: dict[str, Region] | None = None
) -> dict[str, Any]:
    """What a command did to an RGBA canvas: how much changed, where, and by how much per
    channel; with `regions`, the fraction changed in each (which band of the probe chart)."""
    if before.shape != after.shape:
        return {
            "size_before": [before.shape[1], before.shape[0]],
            "size_after": [after.shape[1], after.shape[0]],
        }
    changed = changed_mask(before, after)
    delta = np.abs(before.astype(np.int16) - after.astype(np.int16))
    ys, xs = np.nonzero(changed)
    out: dict[str, Any] = {
        "changed_fraction": round(float(changed.mean()), 4),
        "changed_box": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
        if len(xs)
        else None,
        "mean_delta": {
            name: round(float(delta[..., index].mean()), 2) for index, name in enumerate("rgba")
        },
    }
    if regions is not None:
        out["regions"] = {
            name: round(float(changed[y0:y1, x0:x1].mean()), 4)
            for name, (y0, y1, x0, x1) in regions.items()
        }
    return out


def edges_touched(mask: np.ndarray) -> list[str]:
    """Canvas edges, in left, top, right, bottom order, that hold at least one non-zero pixel."""
    edges = {"left": mask[:, 0], "top": mask[0, :], "right": mask[:, -1], "bottom": mask[-1, :]}
    return [name for name, line in edges.items() if line.any()]


def region_stats(channel: np.ndarray, box: Sequence[int]) -> dict[str, int]:
    """Pixel count, min, max and rounded mean inside [left, top, right, bottom)."""
    left, top, right, bottom = box
    region = channel[top:bottom, left:right]
    return {
        "pixels": int(region.size),
        "min": int(region.min()),
        "max": int(region.max()),
        "mean": round(float(region.mean())),
    }


def dab_shape(coverage: np.ndarray) -> str:
    """'square' when coverage fills its bounding box at full strength, 'aliased-round' when it is
    only full or none but not square, 'soft' when any pixel is partly covered, 'empty' when none is."""
    bounds = nonzero_bounds(coverage)
    if bounds is None:
        return "empty"
    left, top, right, bottom = bounds
    covered = coverage[coverage > 0]
    if (covered < 255).any():
        return "soft"
    return "square" if covered.size == (right - left) * (bottom - top) else "aliased-round"


# --- Live exports. Each acts on the active document. ---

# showOnly() hides every top-level layer except the one named (null shows them as
# they are) and returns the previous visibility; visibility is not a History step here.
_EXPORT_JS = r"""
function showOnly(doc,only){var vis=[],found=0;for(var i=0;i<doc.layers.length;i++){var l=doc.layers[i];
 vis.push(l.visible);if(only!==null){var want=(l.name==only);if(want)found++;if(l.visible!=want)l.visible=want;}}
 if(only!==null&&found!=1){restoreVisibility(doc,vis);throw new Error("expected one layer named "+only+", found "+found);}
 return vis;}
function restoreVisibility(doc,vis){for(var i=0;i<vis.length;i++){var l=doc.layers[i];if(l.visible!=vis[i])l.visible=vis[i];}}
function savePngCopy(doc,path){doc.saveAs(new File(path),new PNGSaveOptions(),true,Extension.LOWERCASE);}
"""


def document_facts(ps: Photoshop) -> dict[str, Any]:
    """Mode, bit depth, colour profile and size of the active document, as Photoshop reports them."""
    return ps.js(
        'var d=app.activeDocument,p;try{p=d.colorProfileName;}catch(e){p="(none)";}'
        "'{\"mode\":'+q(d.mode)+',\"bits_per_channel\":'+q(d.bitsPerChannel)"
        "+',\"colour_profile_type\":'+q(d.colorProfileType)+',\"colour_profile\":'+q(p)"
        "+',\"resolution_ppi\":'+Math.round(d.resolution)+',\"width_px\":'+Math.round(d.width.as('px'))"
        "+',\"height_px\":'+Math.round(d.height.as('px'))+'}';"
    )


def export_composite(ps: Photoshop) -> np.ndarray:
    """RGBA of the visible layers' composite. Alpha is 255 everywhere when there is a Background layer."""
    return _export(ps, None)


def export_layer(ps: Photoshop, name: str) -> np.ndarray:
    """RGBA of one top-level layer alone (the others are hidden for the save, then shown as before)."""
    return _export(ps, name)


def export_selection_mask(ps: Photoshop) -> tuple[np.ndarray, dict[str, Any]]:
    """The selection as 8-bit coverage, and what exporting it did to History.

    Fills the selection with opaque white on a temporary layer, exports that layer's
    alpha, then makes the previously active History state current again, which also
    restores the selection and active layer. The added steps remain in History as
    redo states until the next edit. No selection gives an all-zero mask.
    """
    with _temporary_png("observed-truth-mask-") as path:
        report = ps.js(
            _EXPORT_JS + "var doc=app.activeDocument,saved=doc.activeHistoryState,"
            "before=doc.historyStates.length,active=doc.activeLayer.name,has=true;"
            "try{doc.selection.bounds;}catch(e){has=false;}"
            "if(has){var lay=doc.artLayers.add();lay.name='observed-truth-mask';"
            "var c=new SolidColor();c.rgb.red=255;c.rgb.green=255;c.rgb.blue=255;"
            "doc.selection.fill(c,ColorBlendMode.NORMAL,100,false);"
            "var vis=showOnly(doc,'observed-truth-mask');"
            f"try{{savePngCopy(doc,{json.dumps(path.as_posix())});}}finally{{restoreVisibility(doc,vis);}}}}"
            "var added=doc.historyStates.length-before;doc.activeHistoryState=saved;"
            "'{\"had_selection\":'+has+',\"history_states_added\":'+added"
            "+',\"history_reverted\":'+(doc.activeHistoryState==saved)"
            "+',\"active_layer_restored\":'+(doc.activeLayer.name==active)+'}';"
        )
        if not report["had_selection"]:
            facts = document_facts(ps)
            return np.zeros((facts["height_px"], facts["width_px"]), dtype=np.uint8), report
        return _read_png(path)[..., 3].copy(), report


def _export(ps: Photoshop, only: str | None) -> np.ndarray:
    with _temporary_png("observed-truth-pixels-") as path:
        ps.js(
            _EXPORT_JS + f"var doc=app.activeDocument,vis=showOnly(doc,{json.dumps(only)});"
            f"try{{savePngCopy(doc,{json.dumps(path.as_posix())});}}finally{{restoreVisibility(doc,vis);}}'null';"
        )
        return _read_png(path)


@contextmanager
def _temporary_png(prefix: str) -> Iterator[Path]:
    directory = Path(tempfile.mkdtemp(prefix=prefix))
    path = directory / "copy.png"
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)
        directory.rmdir()


def _read_png(path: Path) -> np.ndarray:
    from PIL import Image

    with Image.open(path) as image:
        if image.mode not in ("RGB", "RGBA"):
            raise ValueError(f"expected an 8-bit RGB(A) PNG, got mode {image.mode}")
        return np.asarray(image.convert("RGBA")).copy()
