import ctypes
import json
import os
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from scripts.adobe_observed_truth.function_index import FunctionIndex
from scripts.adobe_observed_truth.stack_sampler import (
    Loaded,
    after_call,
    functions_on_stack,
    sample,
    to_batches,
)


@pytest.mark.parametrize("code", [
    bytes.fromhex("e8 10 20 30 40"),  # call rel32
    bytes.fromhex("ff 15 10 20 30 40"),  # call [rip+disp32] (also how a guarded indirect call is made)
    bytes.fromhex("48 ff 15 10 20 30 40"),  # the same with REX.W
    bytes.fromhex("ff d0"),  # call rax
    bytes.fromhex("41 ff d2"),  # call r10
    bytes.fromhex("ff 50 08"),  # call [rax+8]
    bytes.fromhex("ff 54 24 08"),  # call [rsp+8]
    bytes.fromhex("ff 90 10 20 30 40"),  # call [rax+disp32]
])
def test_a_return_address_follows_a_call_instruction(code):
    assert after_call(b"\x90" * 8 + code)


@pytest.mark.parametrize("code", [
    bytes.fromhex("90 90 90 90 90 90 90 90"),
    bytes.fromhex("90 90 90 90 ff 25 10 20 30 40"),  # jmp [rip+disp32]: not a call
    bytes.fromhex("90 90 90 90 90 48 89 c3"),  # mov rbx, rax
])
def test_other_code_is_not_after_a_call(code):
    assert not after_call(code)


BASE, IMAGE = 0x7FF700000000, 0x140000000
INDEX = FunctionIndex([
    ("0x140001000", "A", [(0x140001000, 0x1400010FF)]),
    ("0x140002000", "B", [(0x140002000, 0x1400020FF)]),
    ("0x140003000", "C", [(0x140003000, 0x1400030FF)]),
])
# The binary's code: a direct call ends at A+0x20, an indirect one at B+0x40, plain code elsewhere.
CODE = {0x1020: bytes.fromhex("90 90 90 e8 00 00 00 00"), 0x2040: bytes.fromhex("90 90 ff 15 00 00 00 00")}


def _code_at(module, rva, length):
    assert module == "Photoshop.exe"
    return CODE.get(rva, b"\x90" * length)[-length:]


def test_the_stack_holds_the_functions_its_return_addresses_return_into_and_the_one_running():
    stack = b"".join(struct.pack("<Q", v) for v in (
        BASE + 0x1020,  # returns into A after a call
        BASE + 0x1050,  # points into A, but not after a call: a stale pointer, not a frame
        0x00007FFA12345678,  # outside the watched binaries
        BASE + 0x2040,  # returns into B after an indirect call
        BASE + 0x9000,  # in the binary but in no decompiled function
    ))
    loaded = [Loaded("Photoshop.exe", BASE, BASE + 0x100000, IMAGE)]
    found = functions_on_stack(stack, BASE + 0x3010, loaded, _code_at, {"Photoshop.exe": INDEX})
    assert found == {"Photoshop.exe!0x140001000", "Photoshop.exe!0x140002000", "Photoshop.exe!0x140003000"}


def test_samples_become_batches_counting_the_samples_each_function_was_on_the_stack_in():
    samples = [(1000, {"m!a", "m!b"}), (1100, {"m!a"}), (1240, {"m!a"}), (1260, {"m!c"}), (1900, {"m!c"})]
    assert to_batches(samples, window_ms=250) == [
        {"kind": "hits", "t0": 1000, "t1": 1250, "counts": {"m!a": 3, "m!b": 1}},
        {"kind": "hits", "t0": 1250, "t1": 1500, "counts": {"m!c": 1}},
        {"kind": "hits", "t0": 1750, "t1": 2000, "counts": {"m!c": 1}},
    ]


def _pdata_index(path: Path) -> tuple[FunctionIndex, int]:
    """A binary's functions from its x64 unwind table (.pdata), and its preferred image base."""
    data = path.read_bytes()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    count, optional = struct.unpack_from("<H", data, pe + 6)[0], struct.unpack_from("<H", data, pe + 20)[0]
    image_base = struct.unpack_from("<Q", data, pe + 48)[0]
    table_rva, table_size = struct.unpack_from("<II", data, pe + 24 + 112 + 3 * 8)
    sections = [struct.unpack_from("<IIII", data, pe + 24 + optional + 40 * i + 8) for i in range(count)]
    at = next(raw + table_rva - va for size, va, _, raw in sections if va <= table_rva < va + size)
    rows = []
    for i in range(table_size // 12):
        begin, end, _ = struct.unpack_from("<III", data, at + 12 * i)
        rows.append((hex(image_base + begin), f"f{i}", [(image_base + begin, image_base + end - 1)]))
    return FunctionIndex(rows), image_base


def _main_thread(pid: int) -> int:
    class Entry(ctypes.Structure):
        _fields_ = [("size", ctypes.c_uint32), ("usage", ctypes.c_uint32), ("tid", ctypes.c_uint32),
                    ("pid", ctypes.c_uint32), ("base", ctypes.c_long), ("delta", ctypes.c_long), ("flags", ctypes.c_uint32)]
    k32 = ctypes.windll.kernel32
    k32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    snap = k32.CreateToolhelp32Snapshot(4, 0)  # threads
    entry = Entry(ctypes.sizeof(Entry))
    ok = k32.Thread32First(ctypes.c_void_p(snap), ctypes.byref(entry))
    try:
        while ok:
            if entry.pid == pid:
                return entry.tid
            ok = k32.Thread32Next(ctypes.c_void_p(snap), ctypes.byref(entry))
    finally:
        k32.CloseHandle(ctypes.c_void_p(snap))
    raise LookupError(pid)


@pytest.mark.skipif(os.name != "nt", reason="samples a live Windows thread")
def test_a_sleeping_process_is_sampled_in_the_wait_it_sleeps_in(tmp_path):
    kernelbase = Path(os.environ["SystemRoot"]) / "System32" / "KernelBase.dll"
    index, image_base = _pdata_index(kernelbase)
    k32 = ctypes.windll.kernel32
    k32.GetModuleHandleW.restype = k32.GetProcAddress.restype = ctypes.c_void_p
    k32.GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    here = k32.GetModuleHandleW("KernelBase.dll")  # loaded at the same address in every process this boot
    waits = {index.containing(image_base + k32.GetProcAddress(here, name) - here)
             for name in (b"WaitForMultipleObjectsEx", b"WaitForSingleObjectEx", b"SleepEx")}
    child = subprocess.Popen([sys.executable, "-c", "import time\nwhile True: time.sleep(0.05)"])
    try:
        time.sleep(1)
        out, stop = tmp_path / "batches.jsonl", threading.Event()
        result = {}
        worker = threading.Thread(target=lambda: result.update(sample(
            child.pid, _main_thread(child.pid), {"KernelBase.dll": kernelbase}, {"KernelBase.dll": index}, out, stop)))
        worker.start()
        time.sleep(1.5)
        stop.set()
        worker.join(10)
        assert child.poll() is None  # sampling left it running
    finally:
        child.kill()
    batches = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert result["samples"] > 200
    assert result["median_pause_us"] < 2000
    on_stack = sum(n for b in batches for fn, n in b["counts"].items() if fn.split("!")[1] in waits)
    assert on_stack > result["samples"] / 2  # nearly every sample finds it waiting


def test_the_busiest_background_thread_is_the_one_whose_cpu_time_grew_most_besides_the_ui_thread() -> None:
    # Importing a video and saving a copy, 2026-11-24: the UI thread did 25% of Photoshop's work;
    # one other thread (UXP's engine, where every menu command enters) did more than it.
    from scripts.adobe_observed_truth.stack_sampler import busy_threads

    before = {51960: 1000.0, 33684: 500.0, 9992: 40.0}
    after = {51960: 3000.0, 33684: 1700.0, 9992: 60.0, 41088: 30.0}  # 41088 started meanwhile

    assert busy_threads(before, after, ui=51960)[0] == 33684


def test_each_period_samples_whichever_background_thread_was_busiest_just_before_it(tmp_path) -> None:
    from scripts.adobe_observed_truth.stack_sampler import sample_busy

    readings = iter([
        {1: 0.0, 7: 0.0, 8: 0.0}, {1: 500.0, 7: 80.0, 8: 5.0},  # 7 busy
        {1: 500.0, 7: 80.0, 8: 5.0}, {1: 600.0, 7: 81.0, 8: 2.0 + 95},  # then 8
        {1: 600.0, 7: 81.0, 8: 97.0}, {1: 900.0, 7: 81.0, 8: 97.0},  # then only the UI thread
    ])
    stop, sampled = threading.Event(), []

    def cpu(pid: int) -> dict[int, float]:
        reading = next(readings, None)
        if reading is None:
            stop.set()
            return {}
        return reading

    def fake_sample(pid, tid, watch, indexes, out, until, rate_hz):
        sampled.append((tid, rate_hz))
        return {"samples": 0}

    sample_busy(42, 1, {}, {}, tmp_path / "b.jsonl", stop, cpu=cpu, sample_fn=fake_sample, measure_s=0.0)

    assert sampled == [(7, 200), (8, 200)]


def test_every_busy_background_thread_is_picked_busiest_first_up_to_a_cap() -> None:
    # A filter's pixel work spreads over a pool of workers beside UXP's engine and any render
    # thread; the busiest alone misses the rest of them (operator's point, 2026-11-24).
    from scripts.adobe_observed_truth.stack_sampler import busy_threads

    before = {1: 0.0, 10: 0.0, 11: 0.0, 12: 0.0, 13: 0.0}
    after = {1: 900.0, 10: 50.0, 11: 300.0, 12: 120.0, 13: 4.0}

    assert busy_threads(before, after, ui=1) == [11, 12, 10]  # 13 below the threshold, 1 is the UI
    assert busy_threads(before, after, ui=1, cap=2) == [11, 12]


def test_every_busy_thread_is_sampled_the_busiest_alone_in_the_base_file_at_the_full_rate(tmp_path) -> None:
    # The base file is what busiest-only sampling records, so one run compares the two.
    from scripts.adobe_observed_truth.stack_sampler import sample_busy

    readings = iter([
        {1: 0.0, 7: 0.0, 8: 0.0, 9: 0.0}, {1: 500.0, 7: 300.0, 8: 90.0, 9: 40.0},  # 7, 8, 9 busy
        {1: 500.0, 7: 300.0, 8: 90.0, 9: 40.0}, {1: 600.0, 7: 301.0, 8: 190.0, 9: 41.0},  # only 8
    ])
    stop, sampled, lock = threading.Event(), [], threading.Lock()

    def cpu(pid: int) -> dict[int, float]:
        reading = next(readings, None)
        if reading is None:
            stop.set()
            return {}
        return reading

    def fake_sample(pid, tid, watch, indexes, out, until, rate_hz):
        with lock:
            sampled.append((tid, out.name, rate_hz))
        return {"samples": 0}

    sample_busy(42, 1, {}, {}, tmp_path / "b.jsonl", stop, cpu=cpu, sample_fn=fake_sample, measure_s=0.0)

    assert sorted(sampled) == sorted([
        (7, "b.jsonl", 200), (8, "b-1.jsonl", 100), (9, "b-2.jsonl", 100),  # first period
        (8, "b.jsonl", 200),  # second: 8 alone is now the busiest
    ])


def test_no_thread_is_busiest_when_nothing_but_the_ui_thread_did_real_work() -> None:
    from scripts.adobe_observed_truth.stack_sampler import busy_threads

    assert busy_threads({1: 0.0, 2: 0.0}, {1: 900.0, 2: 3.0}, ui=1) == []
