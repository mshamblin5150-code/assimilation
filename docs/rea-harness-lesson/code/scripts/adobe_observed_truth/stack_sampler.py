"""Which decompiled functions an app's threads are running, by sampling their stacks.

The interface thread is sampled throughout; beside it, the busiest other thread of each moment
(sample_process: UXP's engine thread, where menu commands enter Photoshop, did more work than the
interface thread while a video was imported, 2026-11-24).

From outside the app, hundreds of times a second: suspend the thread, read its instruction and
stack pointers, copy its live stack (stack pointer to stack base) in one read, resume it. Nothing
is injected and no code is rewritten. The copy is scanned after the thread runs again: every
value pointing into a watched binary just past a call instruction (checked against the binary's
file) is a return address, and the decompiled function holding it is on the stack, as is the one
holding the instruction pointer. Samples are counted in time windows as hits batches like
runtime_links' hook script's, so attribute() reads them: a count is the number of samples a
function was on the stack in. A function that starts and ends between two samples is missed;
runtime_links hooks the decompiled callees of what was found to catch those.
"""

from __future__ import annotations

import ctypes
import json
import mmap
import struct
import threading
import time
from collections import Counter
from collections.abc import Callable, Iterable
from ctypes import wintypes
from dataclasses import dataclass
from functools import cache, lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from .function_index import FunctionIndex

WINDOW_MS = 250
RATE_HZ = 500
STACK_CAP = 256 * 1024  # bytes of stack copied per sample, from the stack pointer up


@dataclass(frozen=True)
class Loaded:
    name: str
    base: int  # where Windows loaded it
    end: int
    image_base: int  # where Ghidra placed it (the file's preferred base)


CodeAt = Callable[[str, int, int], bytes]  # (binary, rva, length) -> the bytes just before rva


def _modrm_length(code: bytes, at: int) -> int:
    """Bytes taken by the ModRM byte at `at` with its SIB and displacement."""
    modrm = code[at]
    mod, rm = modrm >> 6, modrm & 7
    size = 1
    if mod != 3 and rm == 4:
        size += 1
        if mod == 0 and code[at + 1] & 7 == 5:
            size += 4
    if mod == 0 and rm == 5:
        size += 4
    elif mod == 1:
        size += 1
    elif mod == 2:
        size += 4
    return size


def after_call(code: bytes) -> bool:
    """Whether `code` (the bytes just before an address) ends in a call instruction: a direct call,
    or an indirect one (FF /2) with any ModRM form, with or without a REX prefix."""
    if len(code) >= 5 and code[-5] == 0xE8:
        return True
    for length in range(2, min(len(code), 8) + 1):
        at = len(code) - length
        if 0x40 <= code[at] <= 0x4F:
            at += 1
        if at + 1 >= len(code) or code[at] != 0xFF or (code[at + 1] >> 3) & 7 != 2:
            continue
        try:
            if at + 1 + _modrm_length(code, at + 1) == len(code):
                return True
        except IndexError:
            continue
    return False


def functions_on_stack(
    stack: bytes, ip: int, loaded: list[Loaded], code_at: CodeAt, indexes: dict[str, FunctionIndex]
) -> set[str]:
    """The decompiled functions ("binary!address") a stack copy returns into, and the one `ip` is in."""
    watched = sorted((m for m in loaded if m.name in indexes), key=lambda m: m.base)
    if not watched:
        return set()
    bases = np.array([m.base for m in watched], dtype=np.uint64)
    ends = np.array([m.end for m in watched], dtype=np.uint64)
    values = np.unique(np.frombuffer(stack[: len(stack) // 8 * 8], dtype="<u8"))
    at = np.searchsorted(bases, values, side="right") - 1  # the module starting at or below
    inside = (at >= 0) & (values < ends[np.clip(at, 0, None)])
    found = set()
    for value, which in zip(values[inside].tolist(), at[inside].tolist(), strict=True):
        module = watched[which]
        rva = value - module.base
        if after_call(code_at(module.name, rva, 8)) and (fn := indexes[module.name].containing(module.image_base + rva)):
            found.add(f"{module.name}!{fn}")
    for module in watched:  # the function running now
        if module.base <= ip < module.end and (fn := indexes[module.name].containing(module.image_base + ip - module.base)):
            found.add(f"{module.name}!{fn}")
    return found


class _Windows:
    """Samples counted per window of `window_ms`, windows aligned on the first sample."""

    def __init__(self, window_ms: int):
        self.window_ms, self.origin, self.at, self.counts = window_ms, None, None, Counter()

    def add(self, t: int, functions: Iterable[str]) -> dict[str, Any] | None:
        if self.origin is None:
            self.origin, self.at = t, 0
        at = (t - self.origin) // self.window_ms
        done = self.close() if at != self.at else None
        self.at = at
        self.counts.update(functions)
        return done

    def close(self) -> dict[str, Any] | None:
        if self.origin is None or not self.counts:
            return None
        t0 = self.origin + self.at * self.window_ms
        batch = {"kind": "hits", "t0": t0, "t1": t0 + self.window_ms, "counts": dict(sorted(self.counts.items()))}
        self.counts = Counter()
        return batch


def to_batches(samples: Iterable[tuple[int, set[str]]], window_ms: int = WINDOW_MS) -> list[dict[str, Any]]:
    """Samples (time in ms, functions on the stack) as hits batches: per window, the number of
    samples each function was on the stack in. Windows with no samples are left out."""
    windows, batches = _Windows(window_ms), []
    for t, functions in samples:
        if done := windows.add(t, functions):
            batches.append(done)
    if last := windows.close():
        batches.append(last)
    return batches


# --- live: Windows only -----------------------------------------------------------------------

_CONTEXT_SIZE, _FLAGS_AT, _RSP_AT, _RIP_AT = 0x4D0, 0x30, 0x98, 0xF8
_CONTEXT_CONTROL = 0x100001


class PeFile:
    """A binary's file, read by relative virtual address, and its preferred image base."""

    def __init__(self, path: Path):
        self._file = open(path, "rb")  # noqa: SIM115 - kept open for the map
        self._map = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)
        pe = struct.unpack_from("<I", self._map, 0x3C)[0]
        sections, optional_size = struct.unpack_from("<H", self._map, pe + 6)[0], struct.unpack_from("<H", self._map, pe + 20)[0]
        self.image_base = struct.unpack_from("<Q", self._map, pe + 24 + 24)[0]
        table = pe + 24 + optional_size
        self._sections = [struct.unpack_from("<IIII", self._map, table + 40 * i + 8) for i in range(sections)]

    def read(self, rva: int, length: int) -> bytes:
        """The `length` bytes ending at `rva` (b"" outside the file's sections)."""
        start = rva - length
        for size, address, raw_size, raw_at in self._sections:
            if address <= start and rva <= address + min(size, raw_size):
                return self._map[raw_at + start - address: raw_at + rva - address]
        return b""


def ui_thread(pid: int, window_class: str) -> int | None:
    """The thread owning `pid`'s top-level window of `window_class`."""
    user32 = ctypes.windll.user32
    hwnd, owner = None, wintypes.DWORD()
    while hwnd := user32.FindWindowExW(None, hwnd, window_class, None):
        tid = user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid:
            return tid
    return None


BUSY_MS = 10  # CPU a thread must use in a period to be worth sampling


BUSY_CAP = 8  # background threads sampled at once, at most


def busy_threads(before: dict[int, float], after: dict[int, float], ui: int | None, cap: int = BUSY_CAP) -> list[int]:
    """The threads other than `ui` whose CPU time (ms) grew by BUSY_MS or more between two
    readings, busiest first, at most `cap`. Importing a video and saving a copy (2026-11-24),
    the UI thread did a quarter of Photoshop's work; a filter's pixel work spreads over a pool."""
    grown = {tid: ms - before.get(tid, 0.0) for tid, ms in after.items() if tid != ui}
    busy = sorted((tid for tid, ms in grown.items() if ms >= BUSY_MS), key=grown.__getitem__, reverse=True)
    return busy[:cap]


class _Target:
    def __init__(self, pid: int, tid: int):
        k32 = self.k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenProcess.restype = k32.OpenThread.restype = wintypes.HANDLE
        k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
        k32.GetThreadContext.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
        k32.SuspendThread.argtypes = k32.ResumeThread.argtypes = [wintypes.HANDLE]
        k32.SuspendThread.restype = k32.ResumeThread.restype = wintypes.DWORD
        self.process = k32.OpenProcess(0x0410, False, pid)  # query information, read memory
        self.thread = k32.OpenThread(0x004A, False, tid)  # suspend/resume, get context, query information
        if not self.process or not self.thread:
            raise OSError(ctypes.get_last_error(), f"cannot open process {pid} thread {tid}")
        raw = ctypes.create_string_buffer(_CONTEXT_SIZE + 16)
        self.context = ctypes.addressof(raw) + (-ctypes.addressof(raw)) % 16
        self._raw = raw
        self.stack_base = self._stack_base()
        self.copy = ctypes.create_string_buffer(STACK_CAP)

    def _read(self, address: int, length: int, into: Any = None) -> bytes:
        buffer = into if into is not None else ctypes.create_string_buffer(length)
        done = ctypes.c_size_t()
        self.k32.ReadProcessMemory(self.process, ctypes.c_void_p(address), buffer, length, ctypes.byref(done))
        return buffer.raw[: done.value]

    def _stack_base(self) -> int:
        info = ctypes.create_string_buffer(48)  # THREAD_BASIC_INFORMATION: TEB at offset 8
        ntdll = ctypes.WinDLL("ntdll")
        ntdll.NtQueryInformationThread(self.thread, 0, info, 48, None)
        teb = struct.unpack_from("<Q", info.raw, 8)[0]
        return struct.unpack("<Q", self._read(teb + 8, 8))[0]  # NT_TIB StackBase

    def sample(self) -> tuple[int, bytes, int]:
        """(instruction pointer, the live stack copy, microseconds the thread was suspended)."""
        k32 = self.k32
        ctypes.c_uint32.from_address(self.context + _FLAGS_AT).value = _CONTEXT_CONTROL
        start = time.perf_counter()
        if k32.SuspendThread(self.thread) == 0xFFFFFFFF:
            raise OSError(ctypes.get_last_error(), "thread gone")
        try:
            k32.GetThreadContext(self.thread, ctypes.c_void_p(self.context))
            rsp = ctypes.c_uint64.from_address(self.context + _RSP_AT).value
            rip = ctypes.c_uint64.from_address(self.context + _RIP_AT).value
            length = max(0, min(STACK_CAP, self.stack_base - rsp))
            done = ctypes.c_size_t()
            k32.ReadProcessMemory(self.process, ctypes.c_void_p(rsp), self.copy, length, ctypes.byref(done))
        finally:
            k32.ResumeThread(self.thread)
        paused = int((time.perf_counter() - start) * 1e6)
        return rip, self.copy.raw[: done.value], paused

    def modules(self, watch: dict[str, Path]) -> list[Loaded]:
        """The watched binaries loaded now, by file name (case-insensitive)."""
        k32, handles, needed = self.k32, (ctypes.c_void_p * 4096)(), wintypes.DWORD()
        k32.K32EnumProcessModulesEx(self.process, handles, ctypes.sizeof(handles), ctypes.byref(needed), 3)
        wanted = {name.lower(): name for name in watch}
        name, info, loaded = ctypes.create_unicode_buffer(260), (ctypes.c_uint64 * 3)(), []
        for handle in handles[: needed.value // ctypes.sizeof(ctypes.c_void_p)]:
            k32.K32GetModuleBaseNameW(self.process, ctypes.c_void_p(handle), name, 260)
            if key := wanted.get(name.value.lower()):
                k32.K32GetModuleInformation(self.process, ctypes.c_void_p(handle), info, ctypes.sizeof(info))
                loaded.append(Loaded(key, info[0], info[0] + (info[1] & 0xFFFFFFFF), _pe(watch[key]).image_base))
        return loaded

    def close(self) -> None:
        self.k32.CloseHandle(self.thread)
        self.k32.CloseHandle(self.process)


@cache
def _pe(path: Path) -> PeFile:
    return PeFile(path)


def sample(
    pid: int,
    tid: int,
    watch: dict[str, Path],
    indexes: dict[str, FunctionIndex],
    out: Path,
    stop: threading.Event,
    rate_hz: int = RATE_HZ,
    window_ms: int = WINDOW_MS,
) -> dict[str, Any]:
    """Sample thread `tid` of `pid` until `stop` is set (or the thread ends), appending a hits
    batch per window to `out` as JSON lines. `watch`: binary name -> its file (for call checks
    and its image base); `indexes`: binary name -> its decomp. Returns sample and pause stats."""
    target = _Target(pid, tid)

    @lru_cache(maxsize=1 << 20)
    def code_at(module: str, rva: int, length: int) -> bytes:
        return _pe(watch[module]).read(rva, length)

    windows, loaded, refreshed = _Windows(window_ms), [], 0.0
    pauses: list[int] = []
    interval = 1.0 / rate_hz
    try:
        with out.open("a", encoding="utf-8", newline="\n") as sink:
            next_at = time.perf_counter()
            while not stop.is_set():
                if time.perf_counter() - refreshed > 2:  # plug-ins load while dialogs open
                    loaded, refreshed = target.modules(watch), time.perf_counter()
                try:
                    ip, stack, paused = target.sample()
                except OSError:
                    break
                pauses.append(paused)
                if done := windows.add(int(time.time() * 1000), functions_on_stack(stack, ip, loaded, code_at, indexes)):
                    sink.write(json.dumps(done) + "\n")
                    sink.flush()
                next_at += interval
                if (wait := next_at - time.perf_counter()) > 0:
                    time.sleep(wait)
                else:
                    next_at = time.perf_counter()
            if last := windows.close():
                sink.write(json.dumps(last) + "\n")
    finally:
        target.close()
    ordered = sorted(pauses) or [0]
    return {"samples": len(pauses), "median_pause_us": ordered[len(ordered) // 2], "max_pause_us": ordered[-1]}


class _Until:
    """Stops a sample() at a deadline or when the whole run stops, whichever comes first."""

    def __init__(self, stop: threading.Event, seconds: float):
        self.stop, self.deadline = stop, time.monotonic() + seconds

    def is_set(self) -> bool:
        return self.stop.is_set() or time.monotonic() >= self.deadline


BACKGROUND_HZ = 200  # the busiest background thread: below the UI thread's rate
OTHERS_HZ = 200  # shared by the other busy threads, so more busy threads do not mean more load


def sample_busy(
    pid: int,
    ui: int | None,
    watch: dict[str, Path],
    indexes: dict[str, FunctionIndex],
    out: Path,
    stop: threading.Event,
    *,
    cpu: Callable[[int], dict[int, float]] | None = None,
    sample_fn: Callable[..., dict[str, Any]] | None = None,
    measure_s: float = 0.5,
    period_s: float = 2.0,
) -> None:
    """Until `stop`: measure every thread's CPU for `measure_s`, then for `period_s` sample
    every busy thread other than `ui` (busy_threads) at once: the busiest at BACKGROUND_HZ into
    `out`, the others sharing OTHERS_HZ into `<out stem>-<rank>.jsonl`. `out` alone is what
    busiest-only sampling records, so one run compares the two. Nothing busy: measure again."""
    cpu = cpu or thread_cpu_ms
    sample_fn = sample_fn or sample

    def run(tid: int, path: Path, rate: int) -> None:
        try:
            sample_fn(pid, tid, watch, indexes, path, _Until(stop, period_s), rate_hz=rate)
        except (OSError, struct.error):  # the thread or process ended under the sampler
            pass

    while not stop.is_set():
        before = cpu(pid)
        if stop.wait(measure_s):
            return
        after = cpu(pid)
        if stop.is_set():
            return
        busy = busy_threads(before, after, ui)
        share = max(25, OTHERS_HZ // max(1, len(busy) - 1))
        workers = [
            threading.Thread(target=run, args=(tid, out if rank == 0 else out.with_name(f"{out.stem}-{rank}{out.suffix}"),
                                               BACKGROUND_HZ if rank == 0 else share), daemon=True)
            for rank, tid in enumerate(busy)
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(period_s + 10)


def sample_process(
    pid: int,
    ui: int,
    watch: dict[str, Path],
    indexes: dict[str, FunctionIndex],
    out: Path,
    stop: threading.Event,
    *,
    sample_fn: Callable[..., dict[str, Any]] | None = None,
    busiest_fn: Callable[..., None] | None = None,
) -> dict[str, Any]:
    """Sample the UI thread into `out` and, beside it, the busy other threads (sample_busy)
    into `<out stem>-background*.jsonl` (read with the rest of the sweep's batch files), until
    `stop`. Returns the UI sampler's stats."""
    background = out.with_name(f"{out.stem}-background{out.suffix}")
    helper = threading.Thread(
        target=busiest_fn or sample_busy, args=(pid, ui, watch, indexes, background, stop), daemon=True
    )
    helper.start()
    try:
        return (sample_fn or sample)(pid, ui, watch, indexes, out, stop)
    finally:
        helper.join(10)


def thread_cpu_ms(pid: int) -> dict[int, float]:
    """Every thread of `pid` and the CPU time (kernel + user, ms) it has used so far."""
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class THREADENTRY32(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ThreadID", wintypes.DWORD),
                    ("th32OwnerProcessID", wintypes.DWORD), ("tpBasePri", ctypes.c_long),
                    ("tpDeltaPri", ctypes.c_long), ("dwFlags", wintypes.DWORD)]

    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    snapshot = k32.CreateToolhelp32Snapshot(0x4, 0)  # TH32CS_SNAPTHREAD
    entry = THREADENTRY32()
    entry.dwSize = ctypes.sizeof(entry)
    tids = []
    try:
        ok = k32.Thread32First(snapshot, ctypes.byref(entry))
        while ok:
            if entry.th32OwnerProcessID == pid:
                tids.append(entry.th32ThreadID)
            ok = k32.Thread32Next(snapshot, ctypes.byref(entry))
    finally:
        k32.CloseHandle(snapshot)
    used: dict[int, float] = {}
    for tid in tids:
        handle = k32.OpenThread(0x0800, False, tid)  # THREAD_QUERY_LIMITED_INFORMATION
        if not handle:
            continue
        times = [wintypes.FILETIME() for _ in range(4)]
        if k32.GetThreadTimes(handle, *(ctypes.byref(t) for t in times)):
            used[tid] = sum((t.dwHighDateTime << 32 | t.dwLowDateTime) / 10_000 for t in times[2:])
        k32.CloseHandle(handle)
    return used
