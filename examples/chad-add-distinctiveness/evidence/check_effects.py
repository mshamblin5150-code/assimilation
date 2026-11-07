"""Bounded integration check of the pure fixture, not a general sandbox."""
from pathlib import Path
import io
import socket
import subprocess
import sys
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "instructor"))
import test_readiness

suite = unittest.defaultTestLoader.loadTestsFromModule(test_readiness)


def forbidden(*args, **kwargs):
    raise AssertionError("unexpected external effect")


def audit(event, args):
    if event.startswith("socket.") or event in ("os.system", "subprocess.Popen"):
        forbidden()
    if event == "open":
        mode, flags = args[1:3]
        if (isinstance(mode, str) and any(letter in mode for letter in "wax+")) or (
                isinstance(flags, int) and flags & 3):
            forbidden()


time.sleep = forbidden
socket.socket = forbidden
socket.create_connection = forbidden
subprocess.Popen = forbidden
sys.addaudithook(audit)
output = io.StringIO()
result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
print(output.getvalue())
raise SystemExit(0 if result.wasSuccessful() and result.testsRun == 15 else 1)
