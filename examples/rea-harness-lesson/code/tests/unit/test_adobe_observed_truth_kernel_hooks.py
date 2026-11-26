"""Kernel hooks: the pixel-kernel table read from a decompile, and which kernels each spec ran.

The registrar texts below are invented in the decompiler's style (names and addresses made up);
no Adobe code is carried here."""

from __future__ import annotations

from pathlib import Path

from scripts.adobe_observed_truth.kernel_hooks import kernel_table, kernels_by_spec

ONE_ENTRY = """void FUN_180000100(void)
{
  if (guard < DAT_180900010) {
    init(&DAT_180900010);
    if (DAT_180900010 == -1) {
      _DAT_180900000 = 0x20;
      _DAT_180900008 = "HalideProcFunctor::HalideBNSampleTip_avx2";
      _DAT_180900018 = FUN_180200000;
      _Init_thread_footer(&DAT_180900010);
    }
  }
  return;
}
"""

SEVERAL_ENTRIES = """void FUN_180000200(void)
{
  if (guard < DAT_180900110) {
    init(&DAT_180900110);
    if (DAT_180900110 == -1) {
      _DAT_180900100 = 0x22;
      _DAT_180900108 = "HalideProcFunctor::HalideBNSampleBlend_avx512";
      _DAT_180900120 = 0;
      _DAT_180900128 = &DAT_180800000;
      _DAT_180900130 = FUN_180300000;
      _DAT_180900138 = FUN_180300400;
      _Init_thread_footer(&DAT_180900110);
    }
  }
  DAT_180900140 = FUN_180000999;
  return;
}
"""


def test_each_registered_kernel_gets_every_entry_its_registrar_assigns(tmp_path: Path) -> None:
    (tmp_path / "0x180000100.c").write_text(ONE_ENTRY, encoding="utf-8")
    (tmp_path / "0x180000200.c").write_text(SEVERAL_ENTRIES, encoding="utf-8")
    (tmp_path / "0x180000300.c").write_text("void FUN_180000300(void) { return; }\n", encoding="utf-8")

    assert kernel_table(tmp_path) == [
        {"name": "HalideBNSampleBlend_avx512", "entries": ["0x180300000", "0x180300400"], "registrar": "0x180000200"},
        {"name": "HalideBNSampleTip_avx2", "entries": ["0x180200000"], "registrar": "0x180000100"},
    ]


TABLE = [
    {"name": "HalideBNSampleTip_avx2", "entries": ["0x180200000"], "registrar": "0x180000100"},
    {"name": "HalideBNSampleBlend_avx512", "entries": ["0x180300000", "0x180300400"], "registrar": "0x180000200"},
]


def test_kernel_calls_are_summed_by_name_for_each_spec_whose_window_they_fall_in_and_while_idle() -> None:
    specs = [{"t0": 1000, "t1": 2000, "label": "tool:a@use"}, {"t0": 3000, "t1": 4000, "label": "tool:b@use"}]
    idle = [[0, 900]]
    batches = [
        {"kind": "loaded", "t": 10},
        {"kind": "hits", "t0": 100, "t1": 350, "counts": {"0x180300000": 4}},
        {"kind": "hits", "t0": 1100, "t1": 1350, "counts": {"0x180200000": 2, "0x180300000": 1}},
        {"kind": "hits", "t0": 1350, "t1": 1600, "counts": {"0x180300400": 3}},
        {"kind": "hits", "t0": 2500, "t1": 2750, "counts": {"0x180200000": 9}},
        {"kind": "hits", "t0": 3100, "t1": 3350, "counts": {"0x180200000": 5}},
    ]

    assert kernels_by_spec(batches, idle, specs, TABLE) == {
        "specs": {"tool:a@use": {"HalideBNSampleBlend_avx512": 4, "HalideBNSampleTip_avx2": 2},
                  "tool:b@use": {"HalideBNSampleTip_avx2": 5}},
        "idle": {"HalideBNSampleBlend_avx512": 4},
        "between": {"HalideBNSampleTip_avx2": 9},
    }


def test_a_captured_buffer_reads_back_by_its_strides_and_a_tip_is_measured_as_an_ellipse() -> None:
    import numpy as np

    from scripts.adobe_observed_truth.kernel_hooks import buffer_array, tip_shape

    # A 3x2 image stored with a row stride of 4 (one padding byte per row).
    padded = bytes([1, 2, 3, 0, 4, 5, 6])
    assert buffer_array({"code": 1, "bits": 8, "dims": [[0, 3, 1], [0, 2, 4]], "hex": padded.hex()}).tolist() == [[1, 2, 3], [4, 5, 6]]

    ys, xs = np.mgrid[0:41, 0:41]
    ellipse = (((xs - 20) / 16.0) ** 2 + ((ys - 20) / 8.0) ** 2 <= 1).astype(np.uint8) * 255
    shape = tip_shape(ellipse)
    assert abs(shape["length"] - 32) < 0.5 and abs(shape["width"] - 16) < 0.5
    assert abs(shape["roundness"] - 0.5) < 0.02 and min(shape["angle"], 180 - shape["angle"]) < 0.5
    assert abs(tip_shape(ellipse.T)["angle"] - 90) < 0.5


def test_each_dab_captured_in_a_spec_window_becomes_one_measured_dab_of_that_spec() -> None:
    import numpy as np

    from scripts.adobe_observed_truth.kernel_hooks import dab_rows

    tip = np.zeros((4, 3), dtype=np.uint8)
    tip[1:3, :] = 255  # 3 wide, 2 high
    def dab(t: int, host: int, flow: str) -> dict:
        stroke = {"code": 1, "bits": 8, "dims": [[0, 3, 1], [0, 4, 400]], "host": hex(host)}
        mask = {"code": 1, "bits": 8, "dims": [[0, 3, 1], [0, 4, 3]], "host": "0x1", "hex": tip.tobytes().hex()}
        return {"kind": "buffers", "fn": "0x180200000", "t": t, "ret": 0,
                "scalars": ["0x0", None, None, "0x1a2b", "0xff", flow, None, "0x0", "0x0", "0x0"],
                "before": [None, stroke, mask, None, None, None, stroke, None, None, None], "after": []}

    captures = [dab(1100, 0x10000, "0xd"), dab(1200, 0x10000 + 400 * 5 + 2, "0x80"), dab(2500, 0x20000, "0x1")]
    airbrush = [{"name": "HalideBNAirbrushTip_avx2", "entries": ["0x180200000"], "registrar": "0x180000100"}]
    rows = dab_rows(captures, [{"t0": 1000, "t1": 2000, "label": "brush:dyn:a"}], airbrush)

    assert [r["item_id"] for r in rows] == ["brush:dyn:a"]
    [row] = rows
    assert row["kernels"] == {"HalideBNAirbrushTip_avx2": 2}
    assert row["dabs"] == 2
    assert row["opacity_byte"] == [255, 255] and row["flow_byte"] == [13, 128]
    assert row["row"] == [0, 5] and row["column"] == [0, 2]
    assert row["length"] == [round(row["length"][0], 2)] * 2 and row["roundness"][0] < 1


def test_with_masks_each_dab_keeps_its_tip_mask() -> None:
    import numpy as np

    from scripts.adobe_observed_truth.kernel_hooks import dab_rows

    tip = np.arange(12, dtype=np.uint8).reshape(4, 3)
    stroke = {"code": 1, "bits": 8, "dims": [[0, 3, 1], [0, 4, 400]], "host": "0x10000"}
    mask = {"code": 1, "bits": 8, "dims": [[0, 3, 1], [0, 4, 3]], "host": "0x1", "hex": tip.tobytes().hex()}
    capture = {"kind": "buffers", "fn": "0x180200000", "t": 1100, "ret": 0,
               "scalars": ["0x0", None, None, "0xff", "0x1a2b", None, "0x0", "0x0", "0x0", "0x0"],
               "before": [None, stroke, mask, None, None, stroke, None, None, None, None], "after": []}
    [row] = dab_rows([capture], [{"t0": 1000, "t1": 2000, "label": "brush:tip:a"}], TABLE, masks=True)
    assert row["tip"] == [tip.tolist()]
    assert "tip" not in dab_rows([capture], [{"t0": 1000, "t1": 2000, "label": "brush:tip:a"}], TABLE)[0]
