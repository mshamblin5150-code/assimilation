"""Images for probes to work on, so a command's effect shows in the pixels.

A blank white canvas shows almost nothing: most filters and adjustments leave white white.
The chart is drawn by code (identical every run, owned by no one, safe to publish), with a
band for each kind of tool: saturated hues for colour adjustments, a smooth grey ramp for
tone, hard edges and fixed noise for blur/sharpen/noise filters, mid and skin tones, and a
transparent strip for layer and alpha tools.
"""

from __future__ import annotations

import colorsys
from pathlib import Path

import numpy as np
from PIL import Image

WIDTH, HEIGHT = 600, 400
_HUES = 24
_TONES_END = (WIDTH * 3 // 4) // 5 * 5  # five tone patches, then the transparent strip
# Each band of the chart (y0, y1, x0, x1), so a result says which kinds of content changed.
CHART_REGIONS = {
    "hues": (0, 100, 0, WIDTH),
    "grey_ramp": (100, 200, 0, WIDTH),
    "hard_edges": (200, 300, 0, WIDTH // 2),
    "noise": (200, 300, WIDTH // 2, WIDTH),
    "tones": (300, 400, 0, _TONES_END),
    "transparent": (300, 400, _TONES_END, WIDTH),
}


def chart() -> Image.Image:
    """The probe chart: 600 x 400 RGBA, four bands of 100 rows."""
    rgba = np.zeros((HEIGHT, WIDTH, 4), dtype=np.uint8)
    rgba[..., 3] = 255
    columns = np.arange(WIDTH)

    # Band 1: saturated hues, one column block each.
    for x in columns:
        hue = (x * _HUES // WIDTH) / _HUES
        rgba[0:100, x, :3] = [round(c * 255) for c in colorsys.hsv_to_rgb(hue, 1.0, 1.0)]

    # Band 2: a smooth grey ramp from black to white.
    rgba[100:200, :, :3] = np.round(np.linspace(0, 255, WIDTH)).astype(np.uint8)[None, :, None]

    # Band 3: hard black/white stripes (left), fixed-seed noise (right).
    stripes = np.where((columns[: WIDTH // 2] // 8) % 2 == 0, 0, 255).astype(np.uint8)
    rgba[200:300, : WIDTH // 2, :3] = stripes[None, :, None]
    noise = np.random.default_rng(20261109).integers(0, 256, (100, WIDTH // 2, 3), dtype=np.uint8)
    rgba[200:300, WIDTH // 2 :, :3] = noise

    # Band 4: mid and skin tones, then a transparent strip.
    tones = [(128, 128, 128), (224, 172, 105), (198, 134, 66), (141, 85, 36), (90, 120, 160)]
    width = _TONES_END // len(tones)
    for index, tone in enumerate(tones):
        rgba[300:400, index * width : (index + 1) * width, :3] = tone
    rgba[300:400, _TONES_END:, 3] = 0

    return Image.fromarray(rgba, "RGBA")


ICON = Path(__file__).parent / "test_icon.png"  # shipped with the harness, by the operator's leave


def icon() -> Image.Image:
    """The operator's app icon, scaled to fit 600 px: fine texture, hard edges, a face and a
    transparent background; nearly greyscale, which is why the chart carries the colour."""
    image = Image.open(ICON).convert("RGBA")
    image.thumbnail((600, 600), Image.Resampling.LANCZOS)
    return image
