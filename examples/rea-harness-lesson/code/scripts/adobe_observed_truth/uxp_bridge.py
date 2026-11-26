"""Hand commands to the harness's UXP helper plugin inside Photoshop, and wait for its answers.

ExtendScript cannot run a menu command by the number menuBarInfo gives it; UXP's
core.performMenuCommand can. A UXP plugin cannot listen for connections, so the harness
serves a tiny queue on 127.0.0.1 and the plugin polls it: GET /next for a command, POST
/result with the outcome. Only the command kinds below are ever queued.
"""

from __future__ import annotations

import itertools
import json
import threading
import time
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Self

ALLOWED_KINDS = frozenset({"ping", "menu_command", "listen", "recorded_actions"})  # never batch_play
PLUGIN_PORT = 47615  # the only address uxp_helper/manifest.json lets the plugin reach


class Bridge:
    def __init__(self, port: int = 0) -> None:
        self._commands: Queue[dict[str, Any]] = Queue()
        self._results: dict[int, Queue[dict[str, Any]]] = {}
        self._ids = itertools.count(1)
        self._abandoned: set[int] = set()  # timed out before the plugin fetched them
        self._server = ThreadingHTTPServer(("127.0.0.1", port), self._handler())
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address[:2]
        host = host.decode() if isinstance(host, bytes) else host
        return f"http://{host}:{port}"

    def __enter__(self) -> Self:
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._server.shutdown()
        self._server.server_close()

    def call(self, kind: str, payload: dict[str, Any], *, timeout_s: float) -> Any:
        if kind not in ALLOWED_KINDS:
            raise ValueError(f"The bridge never sends {kind!r}; allowed: {sorted(ALLOWED_KINDS)}")
        command_id = next(self._ids)
        answer: Queue[dict[str, Any]] = Queue(maxsize=1)
        self._results[command_id] = answer
        self._commands.put({"id": command_id, "kind": kind, **payload})
        try:
            result = answer.get(timeout=timeout_s)
        except Empty:
            self._results.pop(command_id, None)
            self._abandoned.add(command_id)
            raise TimeoutError(
                f"Photoshop's helper did not answer {kind} within {timeout_s:g} s "
                "(is the plugin loaded, or is a dialog open?)"
            ) from None
        if not result.get("ok"):
            raise RuntimeError(f"{kind} failed in Photoshop: {result.get('error')}")
        return result.get("value")

    def _next_live_command(self) -> dict[str, Any] | None:
        """The next queued command the harness still waits for; timed-out ones are dropped."""
        deadline = time.monotonic() + 1
        while (left := deadline - time.monotonic()) > 0:
            try:
                command = self._commands.get(timeout=left)
            except Empty:
                return None
            if command["id"] not in self._abandoned:
                return command
        return None

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                command = bridge._next_live_command()
                if command is None:
                    self.send_response(204)
                    self.end_headers()
                    return
                body = json.dumps(command).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self) -> None:
                result = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                waiting = bridge._results.pop(result["id"], None)
                if waiting is not None:
                    waiting.put(result)
                self.send_response(204)
                self.end_headers()

            def log_message(self, *_: object) -> None:  # keep the harness output readable
                pass

        return Handler


HELPER_DIR = Path(__file__).parent / "uxp_helper"
HELPER_FILES = ("manifest.json", "index.html", "main.js")
INSTALLER = Path(
    r"C:\Program Files\Common Files\Adobe\Adobe Desktop Common\RemoteComponents\UPI"
    r"\UnifiedPluginInstallerAgent\UnifiedPluginInstallerAgent.exe"
)


def require_photoshop(ping: Any, *, major: str) -> None:
    """The helper is installed for every Photoshop on the machine; only answer from `major`."""
    version = ping.get("version", "?") if isinstance(ping, dict) else "unknown"
    if not version.startswith(f"{major}."):
        raise RuntimeError(
            f"The helper answered from Photoshop {version}, not {major}.x; close the other one."
        )


def package_helper(destination: Path) -> Path:
    """Zip the plugin into a .ccx, the format Creative Cloud installs permanently."""
    destination.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((HELPER_DIR / "manifest.json").read_text(encoding="utf-8"))
    package = destination / f"{manifest['id']}_{manifest['version']}.ccx"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in HELPER_FILES:
            archive.write(HELPER_DIR / name, name)
    return package


def main() -> None:
    """python -m scripts.adobe_observed_truth.uxp_bridge   (check the plugin is loaded)"""
    with Bridge(PLUGIN_PORT) as bridge:
        ping = bridge.call("ping", {}, timeout_s=15)
        require_photoshop(ping, major="27")
        print(ping)


if __name__ == "__main__":
    main()
