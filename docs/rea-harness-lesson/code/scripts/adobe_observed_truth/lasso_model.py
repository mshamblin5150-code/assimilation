"""Photoshop's Magnetic Lasso, from outlines it made round the harness's own disc (lasso_probe;
lasso-probe.jsonl: 16 probes clicking every 10 degrees on a circle offset from the edge, and 19
clicking once and then moving the mouse round, so the tool lays its own anchors).

Clicks:

- Reach: the outline between clicks moves onto the edge when the drawn path lies within the
  detection width (MgWd, default 10 px) of it: with width 10, clicks 4 and 8 px out snapped and
  12 and 16 did not; width 3 and 5 did not snap at 8, width 20 and 40 did. Snapped outlines lie
  on average within 1.7 px of the outline drawn on the edge itself.
- The clicked points themselves stay where they were clicked (the outline's farthest point is
  the click, 8 px out); only the segments between them follow the edge.
- With seeded noise (sd 20 grey levels) the outline still snapped, less cleanly.
- The contrast setting (MgEd, 1 to 20%) changed nothing on an edge of 20 grey levels (7.8%).

Moves (anchors laid by the tool):
- The whole outline snaps, anchors included, while the mouse runs within 0.9 of the detection
  width of the edge; beyond that it is pulled part of the way (moves_residual, a two-parameter
  fit to three partly snapped probes: 12 and 16 px out at width 10, 8 px out at width 5). Moving
  pulls further than clicking: 12 px out at width 10 and 8 px out at width 5 did not snap at all
  with clicks.
- Contrast 1 to 80% changed nothing on the 7.8% edge: not an absolute threshold on the edge's
  own contrast. With a weak edge (40 levels) and a strong one (160) 12 px apart and the mouse
  between them, the outline took the strong edge at every contrast from 1 to 90%: the tool
  follows the strongest edge within the width, and no probe has shown the setting doing anything.
- Enter closes an open outline along the edge, not straight across: stopped three quarters of
  the way round, the closing segment followed the edge to within 3 px at width 20 and partly at
  width 10.

Not settled: the edge-cost kernel and path search (the code is Photoshop.exe's own; no pixel
kernel runs for the tool), what the contrast and frequency settings are measured against, and
where exactly the tool lays its anchors.

A first moves sweep came back empty every second run. The cause was the harness: a trace that
began where the last one ended sent its press with no mouse move, and Photoshop ignored the
press (runner_photoshop lasso_trace now brings the pointer in from beside the first point).
"""

from __future__ import annotations

RADIUS = 80.0  # the probe disc's
DEFAULT_WIDTH = 10
SNAPPED_MEAN_PX = 1.7  # a snapped outline's mean distance beyond the on-edge outline
UNSNAPPED_SLACK_PX = 1.0  # an unsnapped outline lies where it was drawn, within this


def snaps(offset_px: float, width_px: int = DEFAULT_WIDTH) -> bool:
    """Whether the outline drawn `offset_px` from an edge moves onto it."""
    return abs(offset_px) <= width_px


MOVES_FULL_RATIO = 0.905  # offset / width up to which a moved outline snaps fully
MOVES_RATIO_SPAN = 1.31  # how much further the remaining fraction takes to reach 1
MOVES_SLACK_PX = 0.6


def moves_residual(offset_px: float, width_px: int = DEFAULT_WIDTH) -> float:
    """How far (mean px) an outline the mouse moved along `offset_px` from an edge stays from
    it: 0 within MOVES_FULL_RATIO of the width, then a growing part of the offset."""
    ratio = abs(offset_px) / width_px
    return abs(offset_px) * min(1.0, max(0.0, (ratio - MOVES_FULL_RATIO) / MOVES_RATIO_SPAN))


# Where the tool's own code is (Photoshop.exe, functions seen only for it in the sweep): a cluster
# at 0x141234c10-0x141238f30; 0x141237b30 smooths the traced polyline (segment lengths from
# neighbouring points, then a weight 1 / (2ab^2 + 2c + 1)); the edge cost and path search are
# among its neighbours and not yet read.
ENGINE_FUNCTIONS = ("0x141234c10", "0x141235030", "0x141235300", "0x141235800", "0x141237b30", "0x141238200", "0x141238f30")
