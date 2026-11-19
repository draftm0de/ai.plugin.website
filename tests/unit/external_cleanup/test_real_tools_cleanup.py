"""Deterministic regression tests for the cleanup of tests/external/website/test_real_tools.py (fake controller, no npm, no network,
no process is started). They prove the error paths: start timeout with a leftover own server, TimeoutExpired / unreadable output,
failing inspect/stop, unclear ownership (nothing is signalled) and that the fixture survives anything but a clean, confirmed end."""
import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tests.support import external_cleanup as cleanup
from tests.external.website import test_real_tools as real

SOURCE = Path(real.__file__).read_text(encoding="utf-8")


class FakeControl:
    """Scripted `control.py` stand-in: replies per verb in order; an Exception instance is raised, None means unreadable output."""

    def __init__(self, **replies):
        self.replies = {k: list(v) for k, v in replies.items()}
        self.calls = []

    def __call__(self, verb):
        self.calls.append(verb)
        reply = self.replies[verb].pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def state(name):
    return (0, {"state": name})


class EnsurePreviewStopped(unittest.TestCase):
    def test_no_own_process_is_a_confirmed_end_without_any_signal(self):
        control = FakeControl(status=[state("not-running")])
        self.assertTrue(cleanup.ensure_preview_stopped(control)[0])
        self.assertEqual(control.calls, ["status"])

    def test_start_timeout_with_leftover_own_server_is_stopped_through_the_controller(self):
        control = FakeControl(status=[state("starting"), state("not-running")], stop=[state("stopped")])
        ended, note = cleanup.ensure_preview_stopped(control)
        self.assertTrue(ended, note)
        self.assertEqual(control.calls, ["status", "stop", "status"])

    def test_running_server_after_a_failed_inspect_is_stopped(self):
        control = FakeControl(status=[state("running-reused"), state("not-running")], stop=[state("stopped")])
        self.assertTrue(cleanup.ensure_preview_stopped(control)[0])

    def test_status_timeout_or_unreadable_output_signals_nothing_and_is_unresolved(self):
        for reply in (subprocess.TimeoutExpired("control.py", 120), None, (1, {"no": "state"}), RuntimeError("boom")):
            with self.subTest(reply=repr(reply)):
                control = FakeControl(status=[reply])
                ended, note = cleanup.ensure_preview_stopped(control)
                self.assertFalse(ended)
                self.assertEqual(control.calls, ["status"])
                self.assertTrue(note)

    def test_unclear_ownership_signals_nothing(self):
        for name in ("unknown-owner", "insufficient-evidence", "something-new"):
            with self.subTest(state=name):
                control = FakeControl(status=[state(name)])
                ended, note = cleanup.ensure_preview_stopped(control)
                self.assertFalse(ended)
                self.assertEqual(control.calls, ["status"])
                self.assertIn("nothing was signalled", note)

    def test_failing_or_timing_out_stop_is_unresolved(self):
        for stop in ([state("failed")], [subprocess.TimeoutExpired("control.py", 120)], [None]):
            with self.subTest(stop=repr(stop)):
                control = FakeControl(status=[state("running-reused"), state("running-reused")], stop=stop)
                self.assertFalse(cleanup.ensure_preview_stopped(control)[0])

    def test_stop_that_leaves_the_server_running_is_unresolved(self):
        control = FakeControl(status=[state("running-reused"), state("running-reused")], stop=[state("stopped")])
        ended, note = cleanup.ensure_preview_stopped(control)
        self.assertFalse(ended)
        self.assertIn("still reports", note)

    def test_final_status_failure_is_unresolved(self):
        control = FakeControl(status=[state("running-reused"), subprocess.TimeoutExpired("c", 1)], stop=[state("stopped")])
        self.assertFalse(cleanup.ensure_preview_stopped(control)[0])


class FinalizeFixture(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="cleanup test "))
        (self.base / "marker").write_text("x")
        self.addCleanup(lambda: __import__("shutil").rmtree(self.base, ignore_errors=True))

    def run_finalize(self, passed, ended, **kw):
        out = io.StringIO()
        with redirect_stdout(out):
            deleted = cleanup.finalize_fixture(self.base, passed, ended, "note", **kw)
        return deleted, out.getvalue()

    def test_deleted_only_after_a_passed_test_with_confirmed_end(self):
        deleted, out = self.run_finalize(True, True)
        self.assertTrue(deleted)
        self.assertFalse(self.base.exists())
        self.assertEqual(out, "")

    def test_kept_and_path_printed_for_failure_or_unconfirmed_processes(self):
        for passed, ended in ((False, True), (True, False), (False, False)):
            with self.subTest(passed=passed, ended=ended):
                deleted, out = self.run_finalize(passed, ended)
                self.assertFalse(deleted)
                self.assertTrue((self.base / "marker").exists())
                self.assertIn(str(self.base), out)

    def test_a_deletion_error_is_not_hidden(self):
        def failing(path):
            raise OSError("cannot delete")
        with self.assertRaises(OSError):
            cleanup.finalize_fixture(self.base, True, True, rmtree=failing)


class ExternalTestWiring(unittest.TestCase):
    """The cleanup hook of the real external test, driven with a fake controller."""

    def make(self, completed, **replies):
        test = real.RealToolchainTests("test_end_to_end")
        test.base = Path(tempfile.mkdtemp(prefix="wiring test "))
        (test.base / "marker").write_text("x")
        self.addCleanup(lambda: __import__("shutil").rmtree(test.base, ignore_errors=True))
        test.completed = completed
        test.control = FakeControl(**replies)
        test._control = test.control
        return test

    def run_cleanup(self, test):
        out = io.StringIO()
        with redirect_stdout(out):
            try:
                test._cleanup()
            except AssertionError as exc:
                return exc, out.getvalue()
        return None, out.getvalue()

    def test_failed_test_with_leftover_server_stops_it_but_keeps_the_fixture(self):
        test = self.make(False, status=[state("starting"), state("not-running")], stop=[state("stopped")])
        error, out = self.run_cleanup(test)
        self.assertIsNone(error)
        self.assertEqual(test.control.calls, ["status", "stop", "status"])
        self.assertTrue(test.base.exists())
        self.assertIn(str(test.base), out)

    def test_failed_test_with_unclear_state_does_not_displace_the_original_failure(self):
        test = self.make(False, status=[subprocess.TimeoutExpired("control.py", 120)])
        error, out = self.run_cleanup(test)
        self.assertIsNone(error)
        self.assertEqual(test.control.calls, ["status"])
        self.assertTrue(test.base.exists())
        self.assertIn(str(test.base), out)

    def test_passed_test_with_unconfirmed_end_fails_and_keeps_the_fixture(self):
        test = self.make(True, status=[state("unknown-owner")])
        error, out = self.run_cleanup(test)
        self.assertIsNotNone(error)
        self.assertIn(str(test.base), str(error))
        self.assertTrue(test.base.exists())

    def test_passed_test_with_confirmed_end_deletes_the_fixture(self):
        test = self.make(True, status=[state("not-running")])
        error, _ = self.run_cleanup(test)
        self.assertIsNone(error)
        self.assertFalse(test.base.exists())

    def test_cleanup_is_registered_before_any_call_and_the_test_never_signals_by_port_or_pid(self):
        setup = SOURCE.split("def setUp(self):")[1].split("def _control")[0]
        self.assertLess(setup.index("self.addCleanup(self._cleanup)"), setup.index("cls.plugin"))
        self.assertLess(setup.index("self.addCleanup(self._cleanup)"), setup.index("free_port()"))
        for forbidden in ("ignore_errors", "os.kill", "killpg", "pkill", "lsof", "signal."):
            self.assertNotIn(forbidden, SOURCE, forbidden)
        self.assertIn("self.completed = True", SOURCE)
        self.assertLess(SOURCE.index("running-new"), SOURCE.index("self.completed = True"))


if __name__ == "__main__":
    unittest.main()
