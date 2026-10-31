"""Fault-injection controls for a pure in-memory model, not actual recovery tests."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from windows_view_transaction_model import SimulatedTransaction, Refused


class TransactionModelTests(unittest.TestCase):
    def test_happy_path_is_model_only(self):
        t = SimulatedTransaction().advance("verify", digest="source")
        t = t.advance("stage", digest="source", identity="dest")
        self.assertEqual(t.advance("commit", digest="source", identity="dest").state, "committed")

    def test_mismatched_staged_bytes_refused(self):
        t = SimulatedTransaction().advance("verify", digest="source")
        with self.assertRaises(Refused):
            t.advance("stage", digest="substituted", identity="dest")

    def test_destination_identity_change_refused(self):
        t = SimulatedTransaction().advance("verify", digest="source").advance("stage", digest="source", identity="dest")
        with self.assertRaises(Refused):
            t.advance("commit", digest="source", identity="swapped")

    def test_fault_aborts_at_each_precommit_state(self):
        t = SimulatedTransaction()
        for state in (t, t.advance("verify", digest="source"),
                      t.advance("verify", digest="source").advance("stage", digest="source", identity="dest")):
            self.assertEqual(state.advance("ignored", fault=True).state, "aborted")

    def test_terminal_state_cannot_restart(self):
        with self.assertRaises(Refused):
            SimulatedTransaction("aborted").advance("verify", digest="source")

    def test_out_of_order_commit_refused(self):
        with self.assertRaises(Refused):
            SimulatedTransaction().advance("commit", digest="source", identity="dest")


if __name__ == "__main__":
    unittest.main()
