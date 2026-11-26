"""Photoshop's Spot Healing Brush, from single dabs over a black dot on the harness's own smooth
images (heal_probe; heal-probe.jsonl, 15 dabs: a ramp, a bowl and stripes, each type, sizes 21 and
31). The area healed is the dab.

- Proximity Match copies a patch from beside the spot (one tip-width away) and blends it by its
  gradients: the healed area solves Poisson's equation with the patch's Laplacian, the pixels
  round it as its edge (poisson_fill). Within 0.4 levels on the ramp, 0.8 and 1.2 on the bowl,
  exact on the stripes; it keeps the bowl's curve, which a smooth fill flattens (by 6 and 12
  levels at the centre).
- Create Texture comes closest to a smooth harmonic fill from the edge (harmonic_fill): within 0.3
  levels on the ramp and 2.1 on the bowl, 7.8 on the stripes (it does not keep them).
- Content-Aware puts back an image that repeats exactly (the ramp along its columns, the stripes
  by their period): only the blemish's pixels change, each to its true value. Where nothing
  repeats (the bowl's bottom) it is off by 14 and 27 levels on average and neither fill comes
  close: it copies patch values without blending their gradients (patch synthesis, in the
  PatchMatch DLL; not modelled).

Not settled: which patch Proximity Match takes (the best of the four one tip-width away is
used), Create Texture's own synthesis, Content-Aware's search, the Healing Brush (its Alt-click
source cannot be scripted), soft tips and Diffusion.
"""

from __future__ import annotations

import numpy as np


def _neighbours(u: np.ndarray) -> np.ndarray:
    return np.roll(u, 1, 0) + np.roll(u, -1, 0) + np.roll(u, 1, 1) + np.roll(u, -1, 1)


def poisson_fill(image: np.ndarray, region: np.ndarray, guide: np.ndarray, iterations: int = 6000) -> np.ndarray:
    """`image` with `region` replaced by the solution of Laplace(u) = Laplace(guide), the pixels
    round it fixed (Jacobi; `region` must stay clear of the array's border)."""
    laplacian = _neighbours(np.asarray(guide, float)) - 4 * np.asarray(guide, float)
    u = np.asarray(image, float).copy()
    u[region] = u[~region].mean()
    for _ in range(iterations):
        u[region] = ((_neighbours(u) - laplacian) / 4)[region]
    return u


def harmonic_fill(image: np.ndarray, region: np.ndarray, iterations: int = 6000) -> np.ndarray:
    """`image` with `region` filled smoothly from the pixels round it (Laplace(u) = 0)."""
    return poisson_fill(image, region, np.zeros(np.shape(image)), iterations)


def side_patch(full: np.ndarray, centre: tuple[int, int], half: int, offset: tuple[int, int]) -> np.ndarray:
    """The square of `half` round `centre` moved by `offset` (dx, dy): a candidate source patch."""
    x, y = centre[0] + offset[0], centre[1] + offset[1]
    return np.asarray(full, float)[y - half:y + half + 1, x - half:x + half + 1]
