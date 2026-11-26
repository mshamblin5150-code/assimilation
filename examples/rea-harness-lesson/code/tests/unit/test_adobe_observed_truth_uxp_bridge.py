from __future__ import annotations

import json
import threading
import urllib.request
import zipfile
from pathlib import Path

import pytest

from scripts.adobe_observed_truth import uxp_bridge
from scripts.adobe_observed_truth.uxp_bridge import Bridge


def fake_plugin(base: str, answer: object) -> threading.Thread:
    """What the Photoshop plugin does: fetch the next command, post its result."""

    def run() -> None:
        while True:
            with urllib.request.urlopen(f"{base}/next", timeout=5) as response:
                if response.status == 200:
                    command = json.loads(response.read())
                    break
        body = json.dumps({"id": command["id"], "ok": True, "value": answer}).encode()
        request = urllib.request.Request(f"{base}/result", data=body, method="POST")
        urllib.request.urlopen(request, timeout=5).close()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


def test_a_command_goes_to_the_plugin_and_its_result_comes_back() -> None:
    with Bridge() as bridge:
        fake_plugin(bridge.base_url, answer=True)

        assert bridge.call("menu_command", {"command": 1134}, timeout_s=5) is True


def test_a_photoshop_that_never_answers_times_out_instead_of_hanging() -> None:
    with Bridge() as bridge, pytest.raises(TimeoutError, match="menu_command"):
        bridge.call("menu_command", {"command": 1134}, timeout_s=0.3)


def test_a_command_that_timed_out_is_never_handed_to_the_plugin_afterwards() -> None:
    with Bridge() as bridge:
        with pytest.raises(TimeoutError):
            bridge.call("menu_command", {"command": 1134}, timeout_s=0.3)

        with urllib.request.urlopen(f"{bridge.base_url}/next", timeout=5) as response:
            assert response.status == 204


def test_a_failure_reported_by_the_plugin_is_raised() -> None:
    with Bridge() as bridge:
        fake_plugin_failing(bridge.base_url, "The command is not currently available.")

        with pytest.raises(RuntimeError, match="not currently available"):
            bridge.call("menu_command", {"command": 1134}, timeout_s=5)


def test_only_allowed_command_kinds_are_ever_queued() -> None:
    with Bridge() as bridge, pytest.raises(ValueError, match="batch_play"):
        bridge.call("batch_play", {"descriptors": []}, timeout_s=1)


def test_the_plugin_is_allowed_to_reach_exactly_the_bridge_port_and_nothing_else() -> None:
    manifest = json.loads(
        (Path(uxp_bridge.__file__).parent / "uxp_helper" / "manifest.json").read_text()
    )

    assert manifest["requiredPermissions"]["network"]["domains"] == [
        f"http://127.0.0.1:{uxp_bridge.PLUGIN_PORT}",
        f"http://localhost:{uxp_bridge.PLUGIN_PORT}",
    ]


def test_the_installable_package_holds_just_the_plugin_and_loads_at_photoshop_startup(
    tmp_path: Path,
) -> None:
    package = uxp_bridge.package_helper(tmp_path)

    with zipfile.ZipFile(package) as archive:
        assert sorted(archive.namelist()) == ["index.html", "main.js", "manifest.json"]
        manifest = json.loads(archive.read("manifest.json"))
    assert package.suffix == ".ccx"
    assert manifest["host"]["data"]["loadEvent"] == "startup"


def test_a_helper_answering_from_the_wrong_photoshop_is_refused() -> None:
    uxp_bridge.require_photoshop({"reply": "pong", "version": "27.11.0"}, major="27")

    with pytest.raises(RuntimeError, match="26.11.8"):
        uxp_bridge.require_photoshop({"reply": "pong", "version": "26.11.8"}, major="27")


def test_the_bridge_listens_on_this_machine_only() -> None:
    with Bridge() as bridge:
        assert bridge.base_url.startswith("http://127.0.0.1:")


def fake_plugin_failing(base: str, error: str) -> None:
    def run() -> None:
        while True:
            with urllib.request.urlopen(f"{base}/next", timeout=5) as response:
                if response.status == 200:
                    command = json.loads(response.read())
                    break
        body = json.dumps({"id": command["id"], "ok": False, "error": error}).encode()
        request = urllib.request.Request(f"{base}/result", data=body, method="POST")
        urllib.request.urlopen(request, timeout=5).close()

    threading.Thread(target=run, daemon=True).start()


def test_the_actions_photoshop_reported_can_be_asked_for_but_never_played() -> None:
    recorded = [{"event": "gaussianBlur", "descriptor": {"radius": {"_unit": "pixelsUnit", "_value": 1}}}]
    with Bridge() as bridge:
        fake_plugin(bridge.base_url, answer=recorded)

        assert bridge.call("recorded_actions", {}, timeout_s=5) == recorded


def test_the_helper_can_be_told_which_actions_to_listen_for() -> None:
    # Photoshop refuses a listener for "all" (2026-11-09): the names come from its own dictionary.
    with Bridge() as bridge:
        fake_plugin(bridge.base_url, answer={"listening": 2, "refused": []})

        assert bridge.call("listen", {"names": ["gaussianBlur", "hueSaturation"]}, timeout_s=5) == {
            "listening": 2,
            "refused": [],
        }