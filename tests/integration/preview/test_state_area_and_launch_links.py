"""Protection of the state area (ownership records and logs) and of `.claude/launch.json` for every controller verb.

A symlink in a PARENT of a state file (the base directory or the project's state directory) must not be followed: no verb reads,
changes or removes anything behind it, none treats it as evidence of ownership, `status`/`stop` end as `unsafe-state` without a
signal, `inspect` continues with the page check and reports the process as `unknown`. A missing state area stays a normal case and is
not created by status/stop/inspect. Only fictional data; the "external" area, the processes and signals are the tests' own: signals are
intercepted by a spy (never delivered), the process behind the planted record is a bystander started by the test itself.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from tests.integration.preview.test_inspect import SITE_TS, Serve
from tests.support import preview_helpers as helpers
from tests.support.preview_process import AccessSpy, ControlBase, run
from tests.unit.preview.test_launch_links import CASES, LaunchLinkCases, tree
import control


class StateAreaBase(ControlBase):
    def setUp(self):
        super().setUp()
        self.external = Path(tempfile.mkdtemp()).resolve() / "external"
        self.external.mkdir()
        self.state = self.tmp / "state"

    def bystander(self):
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)  # preview-test-bystander"], start_new_session=True)
        self.addCleanup(proc.wait)
        self.addCleanup(proc.terminate)
        time.sleep(0.2)
        return proc

    def record(self, root, pid, info, log):
        return {"start_id": "fictional", "project_root": str(root.resolve()), "site": "site.test",
                "working_dir": str((root / "sites" / "site.test").resolve()), "launch_name": "zyris-site.test", "port": self.port,
                "host_server_id": None, "pid": pid, "pgid": info["pgid"], "process_start_time": info["start"],
                "command_line_at_start": info["command"], "started_at": "2026-01-01T00:00:00+00:00", "surface": "terminal", "log": str(log)}

    def plant(self, root, kind, live):
        """Put a record and a log into the EXTERNAL area and make the controller's state path lead there through a symlink.
        live=True: the record names a real bystander process (it would be 'ours' if the area were trusted);
        live=False: a stale record (its process is gone) and a log that cleanup would normally remove."""
        project_hash = control.project_hash(root)
        if kind == "base-link":
            area = self.external / project_hash
            area.mkdir()
            self.state.symlink_to(self.external, target_is_directory=True)
        else:                                    # project-link
            self.state.mkdir(mode=0o700)
            area = self.external
            (self.state / project_hash).symlink_to(area, target_is_directory=True)
        if live:
            proc = self.bystander()
            pid, info = proc.pid, control.proc_info(proc.pid)
        else:
            gone = subprocess.Popen([sys.executable, "-c", "pass"])
            gone.wait()
            pid, info = gone.pid, {"pgid": gone.pid, "start": "Thu Jan  1 00:00:00 2026", "command": "x"}
        log_name = "preview-site.test-fictional.log"
        (area / log_name).write_text("log line from the external area\n")
        (area / "preview-site.test.json").write_text(json.dumps(self.record(root, pid, info, self.state / project_hash / log_name)))
        return pid, info


class StateAreaLinkTests(StateAreaBase):
    KINDS = ("base-link", "project-link")

    def check_untouched(self, spy, before, pid=None, info=None):
        self.assertEqual(spy.hits, [], "something behind the link was opened, changed or removed")
        self.assertEqual(spy.signals, [], "a signal was sent")
        self.assertEqual(tree_files(self.external), before)
        self.assertEqual(self.spawned, [])
        if pid is not None:
            now = control.proc_info(pid)
            self.assertTrue(now and now["start"] == info["start"], "the bystander is gone or replaced")

    def test_status_stop_and_start_end_as_unsafe_state_for_every_link_and_record_kind(self):
        for kind in self.KINDS:
            for live in (True, False):
                for verb in ("status", "stop", "start"):
                    with self.subTest(kind=kind, live=live, verb=verb):
                        self.tearDownStateArea()
                        root = self.project()
                        pid, info = self.plant(root, kind, live)
                        before = tree_files(self.external)
                        with AccessSpy(self.external) as spy:
                            code, out = run(root, verb, "--timeout", "3")
                        self.assertEqual((code, out["state"]), (1, "unsafe-state"), out)
                        self.assertIn("symlink", out["message"])
                        self.check_untouched(spy, before, pid if live else None, info)
                        self.assertFalse(control.port_bound(self.port))

    def test_inspect_continues_with_the_page_but_reads_no_state_and_reports_the_process_unknown(self):
        for kind in self.KINDS:
            for live in (True, False):
                with self.subTest(kind=kind, live=live):
                    self.tearDownStateArea()
                    root = self.project()
                    lib = root / "sites" / "site.test" / "src" / "lib"
                    lib.mkdir(parents=True, exist_ok=True)
                    (lib / "site.ts").write_text(SITE_TS)
                    pid, info = self.plant(root, kind, live)
                    before = tree_files(self.external)
                    server = Serve(self.port, body="Hello visitors")
                    try:
                        with AccessSpy(self.external) as spy:
                            code, out = run(root, "inspect", "--expect", "Hello visitors")
                    finally:
                        server.close()
                    self.assertEqual((code, out["state"], out["process"]), (0, "page-confirmed", "unknown"), out)
                    self.check_untouched(spy, before, pid if live else None, info)

    def test_inspect_without_a_page_reports_not_reachable_and_still_touches_nothing(self):
        root = self.project()
        pid, info = self.plant(root, "base-link", True)
        before = tree_files(self.external)
        with AccessSpy(self.external) as spy:
            code, out = run(root, "inspect", "--expect", "x")
        self.assertEqual((code, out["state"], out["process"]), (1, "page-not-reachable", "unknown"), out)
        self.check_untouched(spy, before, pid, info)

    def test_a_stale_record_behind_a_link_is_not_cleaned_up_and_its_log_is_not_read(self):
        root = self.project()
        self.plant(root, "project-link", False)
        before = tree_files(self.external)
        with AccessSpy(self.external) as spy:
            for verb in ("status", "stop"):
                self.assertEqual(run(root, verb)[1]["state"], "unsafe-state")
        self.assertEqual(spy.hits, [])
        self.assertEqual(tree_files(self.external), before)
        self.assertTrue((self.external / "preview-site.test-fictional.log").is_file())

    def test_helpers_refuse_to_touch_files_in_an_unsafe_area_directly(self):
        root = self.project()
        self.plant(root, "project-link", False)
        rfile = control.record_file(root, "site.test")
        log = rfile.parent / "preview-site.test-fictional.log"
        with AccessSpy(self.external) as spy:
            with self.assertRaises(control.UnsafeState):
                control.read_record(rfile)
            with self.assertRaises(control.UnsafeState):
                control.write_record(rfile, {"x": 1})
            self.assertFalse(control.remove_own(log))
            self.assertFalse(control.remove_own(rfile))
            self.assertEqual(control.log_tail(log), [])
            self.assertIsNone(control.own_log_path(root, {"log": str(log)}))
        self.assertEqual(spy.hits, [])

    def tearDownStateArea(self):
        """Fresh state area for the next sub-case."""
        import shutil
        if self.state.is_symlink() or self.state.is_file():
            self.state.unlink()
        elif self.state.exists():
            shutil.rmtree(self.state)
        shutil.rmtree(self.external)
        self.external.mkdir()


class MissingStateAreaTests(StateAreaBase):
    def test_a_missing_state_area_is_normal_and_is_not_created_by_status_stop_or_inspect(self):
        root = self.project()
        with AccessSpy(self.external) as spy:
            self.assertEqual(run(root, "status")[1]["state"], "not-running")
            self.assertEqual(run(root, "stop")[1]["state"], "not-running")
            code, out = run(root, "inspect", "--expect", "x")
        self.assertEqual((out["state"], out["process"]), ("page-not-reachable", "not-managed-by-this-skill"))
        self.assertFalse(self.state.exists(), "status/stop/inspect must not create the state directory")
        self.assertEqual(spy.signals, [])
        self.assertEqual(self.spawned, [])

    def test_an_existing_base_without_the_project_directory_stays_without_it(self):
        root = self.project()
        self.state.mkdir(mode=0o700)
        for verb in ("status", "stop"):
            self.assertEqual(run(root, verb)[1]["state"], "not-running")
        run(root, "inspect", "--expect", "x")
        self.assertEqual(list(self.state.iterdir()), [])

    def test_the_safe_regular_case_still_works_after_the_new_checks(self):
        root = self.project()
        code, started = run(root, "start", "--timeout", "20")
        self.assertEqual(started["state"], "running-new", started)
        self.assertEqual(run(root, "status")[1]["state"], "running-reused")
        self.assertEqual(run(root, "stop")[1]["state"], "stopped")


class LaunchLinksThroughTheControllerTests(ControlBase):
    """`control.py start` shares the generator's protection: a refusal stops before any state, process or log exists."""

    def test_start_refuses_unsafe_launch_locations_and_starts_no_dev_server(self):
        import signal
        signal.alarm(60)
        self.addCleanup(signal.alarm, 0)
        for name in CASES:
            with self.subTest(case=name):
                root, external = getattr(LaunchLinkCases, name)()
                site = root / "sites" / "alpha.example"
                (site / "node_modules").mkdir()
                (site / ".fake").write_text("ok")
                # use the controller's fixed test port: alpha.example has port 4321 in ONE_SITE, so write a manifest with our free port
                spec = root / ".project" / "specs" / "website.json"
                spec.write_text(json.dumps({"version": 2, "components": [helpers._static("alpha.example", port=self.port)]}))
                before_project, before_external = tree(root), tree(external)
                with AccessSpy(external) as spy:
                    code, out = run(root, "start", "--timeout", "3")
                self.assertEqual(code, 1, out)
                self.assertTrue(isinstance(out, str) and out.startswith("STOP:"), out)
                self.assertNotIn("Traceback", out)
                self.assertEqual(spy.hits, [])
                self.assertEqual(self.spawned, [], "a dev server was started")
                self.assertFalse(control.port_bound(self.port))
                self.assertEqual(tree(external), before_external)
                self.assertEqual(tree(root), before_project)
                self.assertEqual(list(self.tmp.glob("state/*/preview-*")), [], "record or log written")

    def test_start_with_a_normal_launch_file_keeps_independent_entries(self):
        root = self.project()
        launch = root / ".claude" / "launch.json"
        launch.parent.mkdir()
        launch.write_text(json.dumps({"version": "0.0.1", "configurations": [{"name": "other", "port": 1}]}))
        code, out = run(root, "start", "--timeout", "20")
        self.assertEqual(out["state"], "running-new", out)
        names = [c["name"] for c in json.loads(launch.read_text())["configurations"]]
        self.assertEqual(names, ["other", "zyris-site.test"])
        self.assertEqual(run(root, "stop")[1]["state"], "stopped")


def tree_files(root):
    """Names and content hashes of the files below root, links not followed, special files not opened."""
    import hashlib
    result = {}
    for current, dirs, files in os.walk(root):
        for name in dirs + files:
            path = Path(current) / name
            rel = path.relative_to(root).as_posix()
            result[rel] = "dir" if path.is_dir() and not path.is_symlink() else "link" if path.is_symlink() else \
                hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "special"
    return result


if __name__ == "__main__":
    unittest.main()
