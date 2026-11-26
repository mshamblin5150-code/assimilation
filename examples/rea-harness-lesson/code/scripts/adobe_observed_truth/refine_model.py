"""Photoshop's Refine Edge (Select and Mask's output, run by its refineSelectionEdge event), from
refined selections over the harness's own disc with a Gaussian-blurred edge (lasso_probe
refine_specs; refine-probe.jsonl, 11 probes, starting from the exact hard circle).

Within the border radius of the selection's edge the selection becomes the image's own matte:
on a two-colour edge, alpha = (I - B) / (F - B) for foreground F and background B; outside the
band it stays as it was. Radius 10 and 20 (over three times the edge blur) reproduce the true matte
within 0.5 level on average; at radius 2 and 5 the band truncates it and its edge is softer than
a step (mean within 1.6 and 2.3 levels). Contrast sharpens the matte back towards a hard edge,
Smooth rounds and hardens it, Feather blurs the result; Shift Edge changed nothing at radius 0.

On images that are not a grey two-tone (lasso_probe.REFINE_IMAGES), the solver works in colour:
red over blue, and red over a green of the same L* and b*, come back as well as grey (within 1.1
levels of the true matte). A closed-form matte (matting_refine: Levin, Lischinski and Weiss's
matting Laplacian over 11 x 11 windows, epsilon 0.01, the band's pixels free and the rest fixed
by the selection) matches Photoshop better than the true matte does on the two-colour, colour and
ramped-background edges (0.7 levels on average, against 0.9 to 1.4), and on a disc of two-tone
stripes at radius 20 (7.0 against 12.9). Window and epsilon were fitted over 3 to 17 px and
1e-7 to 1e-2, not read from Adobe's code.

Not settled: the striped disc at radius 10 (12 levels off, no closer than the true matte), smart
radius (up to 56 levels off on the ramped background), decontaminate, and how contrast, smooth,
feather and shift combine with the band.
"""

from __future__ import annotations

import numpy as np


def refine(image: np.ndarray, selected: np.ndarray, distance: np.ndarray, radius: float,
           foreground: float, background: float) -> np.ndarray:
    """The refined selection (0..255) of a hard selection over a two-colour image: the image's matte
    where the edge distance is within `radius`, the selection elsewhere."""
    matte = np.clip((np.asarray(image, float) - background) / (foreground - background), 0, 1) * 255
    return np.where(np.abs(distance) <= radius, matte, np.where(selected, 255.0, 0.0))


MATTING_WINDOW = 5  # window half-size, px (11 x 11 windows)
MATTING_EPSILON = 1e-2


def _box(a: np.ndarray, r: int) -> np.ndarray:
    """Sums over the (2r + 1)^2 window round each pixel (zero outside the image)."""
    pad = ((r + 1, r), (r + 1, r)) + ((0, 0),) * (a.ndim - 2)
    c = np.cumsum(np.cumsum(np.pad(a, pad), 0), 1)
    return c[2 * r + 1:, 2 * r + 1:] - c[:-2 * r - 1, 2 * r + 1:] - c[2 * r + 1:, :-2 * r - 1] + c[:-2 * r - 1, :-2 * r - 1]


def _laplacian(image: np.ndarray, r: int, eps: float):
    """The matting Laplacian of an RGB image (0..1) as a function on alpha, applied by box sums."""
    count = _box(np.ones(image.shape[:2]), r)
    mean = _box(image, r) / count[..., None]
    cov = _box(image[..., :, None] * image[..., None, :], r) / count[..., None, None] - mean[..., :, None] * mean[..., None, :]
    inverse = np.linalg.inv(cov + eps / count[..., None, None] * np.eye(3))

    def apply(p: np.ndarray) -> np.ndarray:
        mean_p = _box(p, r) / count
        a = np.einsum("hwij,hwj->hwi", inverse, _box(image * p[..., None], r) / count[..., None] - mean * mean_p[..., None])
        b = mean_p - (a * mean).sum(-1)
        return count * p - ((_box(a, r) * image).sum(-1) + _box(b, r))
    return apply


def matting_refine(image: np.ndarray, distance: np.ndarray, radius: float, window: int = MATTING_WINDOW,
                   epsilon: float = MATTING_EPSILON) -> np.ndarray:
    """Refine Edge on a hard selection (inside where `distance` < 0) of an RGB image (0..1): alpha
    (0..1) solved as a closed-form matte where |distance| <= radius, the selection elsewhere."""
    alpha = (np.asarray(distance) < 0).astype(float)
    free_all = np.abs(distance) <= radius
    ys, xs = np.nonzero(free_all)
    margin = 2 * window + 1
    top, left = max(0, ys.min() - margin), max(0, xs.min() - margin)
    bottom, right = min(alpha.shape[0], ys.max() + margin + 1), min(alpha.shape[1], xs.max() + margin + 1)
    crop, free = alpha[top:bottom, left:right].copy(), free_all[top:bottom, left:right]
    laplacian = _laplacian(np.asarray(image, float)[top:bottom, left:right], window, epsilon)

    def lhs(p: np.ndarray) -> np.ndarray:
        q = np.zeros(crop.shape)
        q[free] = p
        return laplacian(q)[free]

    rhs = -laplacian(np.where(free, 0.0, crop))[free]
    x = np.full(rhs.shape, 0.5)
    residual = rhs - lhs(x)
    direction, rr = residual.copy(), residual @ residual
    for _ in range(3000):  # conjugate gradients
        step = lhs(direction)
        s = rr / (direction @ step)
        x += s * direction
        residual -= s * step
        new = residual @ residual
        if new < 1e-12 * len(x):
            break
        direction, rr = residual + new / rr * direction, new
    crop[free] = x
    alpha[top:bottom, left:right] = crop
    return np.clip(alpha, 0.0, 1.0)
