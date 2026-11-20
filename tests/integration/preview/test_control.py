"""Runtime tests for skills/preview/scripts/control.py: real local processes, real 127.0.0.1 ports, a fake `npm` on PATH.

Every test uses a temporary fictional project and a temporary state dir; no real site is touched. Process base class:
tests/support/preview_process.py."""
import io
import json
import os
import shutil
import signal
import socket
import stat
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from tests.support import preview_helpers as helpers
from tests.support.preview_process import ControlBase, FAKE_NPM, free_port, manifest, run
import control


class StartStatusStopTests(ControlBase):
    def test_P1_P2_start_ready_record_reuse_status_stop(self):
        root = self.project()
        code, first = run(root, "start", "--timeout", "20")
        self.assertEqual((code, first["state"]), (0, "running-new"), first)
        self.assertTrue(control.http_ready(self.port))
        rec = control.read_record(control.record_file(root, "site.test"))
        self.assertEqual((rec["project_root"], rec["site"], rec["port"], rec["start_id"]),
                         (str(root.resolve()), "site.test", self.port, first["start_id"]))
        self.assertIn("pgid", first["matched_on"])
        launch = json.loads((root / ".claude" / "launch.json").read_text())
        self.assertEqual(launch["configurations"][0]["name"], "zyris-site.test")
        # P3 reuse: same pid, same start id, no second server
        code, again = run(root, "start", "--timeout", "20")
        self.assertEqual((code, again["state"], again["pid"], again["start_id"]), (0, "running-reused", first["pid"], first["start_id"]))
        self.assertEqual(len(control.port_listeners(self.port)), 1)
        code, st = run(root, "status")
        self.assertEqual((code, st["state"], st["pid"]), (0, "running-reused", first["pid"]))
        # P8 stop
        code, stopped = run(root, "stop")
        self.assertEqual((code, stopped["state"]), (0, "stopped"), stopped)
        self.assertFalse(control.port_bound(self.port))
        self.assertFalse(control.group_alive(rec["pgid"]))
        self.assertFalse(control.record_file(root, "site.test").exists())
        code, st = run(root, "status")
        self.assertEqual((code, st["state"]), (0, "not-running"))

    def test_P2_slow_server_is_not_ready_before_it_answers(self):
        root = self.project(mode="slow")
        t0 = time.monotonic()
        code, out = run(root, "start", "--timeout", "20")
        self.assertEqual(out["state"], "running-new", out)
        self.assertGreaterEqual(time.monotonic() - t0, 1.4)   # reported only after the probe succeeded

    def test_P5_early_exit_reports_log_tail_and_leaves_nothing(self):
        root = self.project(mode="crash")
        code, out = run(root, "start", "--timeout", "10")
        self.assertEqual((code, out["state"]), (1, "failed-early-exit"), out)
        self.assertIn("boom", "\n".join(out["log_tail"]))
        self.assertFalse(control.record_file(root, "site.test").exists())
        self.assertFalse(control.port_bound(self.port))

    def test_detached_dev_server_is_reported_not_adopted(self):
        root = self.project(mode="detach")
        pidfile = root / "sites/site.test/.pid"
        code, out = run(root, "start", "--timeout", "10")
        if pidfile.exists():
            self.extra_pids.append((int(pidfile.read_text()), str(pidfile)))     # identity: its command line carries our pidfile path
        self.assertEqual((code, out["state"]), (1, "failed-early-exit"), out)
        self.assertIn("NOT adopted", out["message"])
        self.assertFalse(control.record_file(root, "site.test").exists())
        self.assertTrue(control.port_bound(self.port))                  # left alone

    def test_start_passes_ignore_lock_to_the_dev_command(self):
        root = self.project()
        with mock.patch.object(control.subprocess, "Popen", wraps=control.subprocess.Popen) as popen:
            run(root, "start", "--timeout", "20")
        dev = [c.args[0] for c in popen.call_args_list if c.args and c.args[0][0] == "npm"]
        self.assertEqual(len(dev), 1)
        self.assertEqual(dev[0][-1], "--ignore-lock")

    def test_P6_timeout_is_bounded_and_reports_instance_left_running(self):
        root = self.project(mode="hang")
        t0 = time.monotonic()
        code, out = run(root, "start", "--timeout", "1.5")
        self.assertLess(time.monotonic() - t0, 10)
        self.assertEqual((code, out["state"], out["left_running"]), (1, "timeout", True), out)
        code, st = run(root, "status")
        self.assertEqual((code, st["state"]), (1, "starting"))          # ours, alive, not answering: never "running"
        code, stopped = run(root, "stop")
        self.assertEqual(stopped["state"], "stopped", stopped)

    def test_missing_node_modules_needs_install_and_starts_nothing(self):
        root = self.project()
        (root / "sites" / "site.test" / "node_modules").rmdir()
        code, out = run(root, "start")
        self.assertEqual((code, out["state"]), (1, "needs-install"))
        self.assertFalse(control.record_file(root, "site.test").exists())

    def test_missing_dev_command_is_failed_not_traceback(self):
        root = self.project()
        with mock.patch.dict(os.environ, {"PATH": str(self.tools)}):           # ps and lsof present, npm absent
            code, out = run(root, "start")
        self.assertEqual((code, out["state"]), (1, "failed"), out)


class ConflictAndIsolationTests(ControlBase):
    def test_P4_foreign_listener_is_a_conflict_and_untouched(self):
        root = self.project()
        s = self.foreign_listener()
        code, out = run(root, "start")
        self.assertEqual((code, out["state"]), (1, "port-conflict"), out)
        self.assertEqual(out["foreign"][0]["pid"], os.getpid())
        self.assertTrue(control.port_bound(self.port))                  # listener unchanged
        self.assertFalse(control.record_file(root, "site.test").exists())
        code, st = run(root, "status")
        self.assertEqual((code, st["state"]), (0, "not-running"))
        self.assertEqual(st["foreign_candidate"][0]["pid"], os.getpid())
        code, sp = run(root, "stop")
        self.assertEqual((code, sp["state"]), (0, "not-running"))       # nothing of ours; nothing signalled
        self.assertTrue(control.port_bound(self.port))

    def test_P7_stale_record_dead_process_is_dropped_and_start_succeeds(self):
        root = self.project()
        run(root, "start", "--timeout", "20")
        rec = control.read_record(control.record_file(root, "site.test"))
        os.killpg(rec["pgid"], signal.SIGKILL)
        for _ in range(50):
            if not control.port_bound(self.port):
                break
            time.sleep(0.1)
        code, st = run(root, "status")
        self.assertEqual((code, st["state"], st["stale_record"]), (0, "not-running", True))
        code, new = run(root, "start", "--timeout", "20")
        self.assertEqual(new["state"], "running-new", new)
        self.assertNotEqual(new["start_id"], rec["start_id"])

    def test_P7_recycled_pid_is_never_signalled(self):
        root = self.project()
        bystander = __import__("subprocess").Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
        self.addCleanup(bystander.kill)
        info = control.proc_info(bystander.pid)
        self.put_record(root, {
            "start_id": "x", "project_root": str(root.resolve()), "site": "site.test",
            "working_dir": str((root / "sites" / "site.test").resolve()), "port": self.port, "pid": bystander.pid,
            "pgid": info["pgid"], "process_start_time": "Mon Jan  1 00:00:00 2001"})
        code, out = run(root, "stop")
        self.assertEqual((code, out["state"]), (0, "not-running"), out)
        self.assertIsNone(bystander.poll())                              # still alive, received no signal
        self.assertIsNotNone(control.proc_info(bystander.pid))

    def test_P9_matching_record_fields_but_foreign_process_group_is_refused(self):
        root = self.project()
        run(root, "start", "--timeout", "20")
        rec = control.read_record(control.record_file(root, "site.test"))
        original = dict(rec)
        rec["pgid"] += 1                                                 # evidence now contradicts the record
        control.write_record(control.record_file(root, "site.test"), rec)
        try:
            code, out = run(root, "stop")
            self.assertNotEqual(out["state"], "stopped")
            self.assertTrue(control.http_ready(self.port))               # real server untouched
        finally:
            control.write_record(control.record_file(root, "site.test"), original)

    def test_P13_two_projects_same_site_same_port(self):
        a, b = self.project(), self.project()
        code, started = run(a, "start", "--timeout", "20")
        self.assertEqual(started["state"], "running-new", started)
        before = (started["pid"], control.proc_info(started["pid"])["start"])
        launch_a = (a / ".claude" / "launch.json").read_text()
        code, conflict = run(b, "start")
        self.assertEqual((code, conflict["state"]), (1, "port-conflict"), conflict)
        code, st = run(b, "status")
        self.assertEqual((code, st["state"]), (0, "not-running"))
        self.assertEqual(st["foreign_candidate"][0]["pid"], control.port_listeners(self.port)[0])
        code, sp = run(b, "stop")
        self.assertEqual((code, sp["state"]), (0, "not-running"))
        # variant: A's record copied into B's record location is still refused
        self.put_record(b, control.read_record(control.record_file(a, "site.test")))
        code, st = run(b, "status")
        self.assertEqual((code, st["state"]), (1, "unknown-owner"), st)
        code, sp = run(b, "stop")
        self.assertEqual((code, sp["state"]), (1, "unknown-owner"), sp)
        code, cf = run(b, "start")
        self.assertEqual(cf["state"], "port-conflict")
        # A is unchanged
        self.assertEqual((started["pid"], control.proc_info(started["pid"])["start"]), before)
        code, sa = run(a, "status")
        self.assertEqual((code, sa["state"], sa["start_id"]), (0, "running-reused", started["start_id"]))
        self.assertEqual((a / ".claude" / "launch.json").read_text(), launch_a)
        # B stopping its own record does not exist; A stops its own
        self.assertEqual(run(a, "stop")[1]["state"], "stopped")

    def test_P8_other_site_in_same_project_is_unaffected(self):
        port2 = free_port()
        root = helpers.make_repo({"version": 2, "components": [helpers._static("site.test", port=self.port), helpers._static("other.test", port=port2)]},
                                 ("site.test", "other.test"))
        for n in ("site.test", "other.test"):
            (root / "sites" / n / "node_modules").mkdir()
        self.roots.append(root)
        self.assertEqual(run(root, "start", "site.test", "--timeout", "20")[1]["state"], "running-new")
        self.assertEqual(run(root, "start", "other.test", "--timeout", "20")[1]["state"], "running-new")
        self.assertEqual(run(root, "stop", "site.test")[1]["state"], "stopped")
        self.assertFalse(control.port_bound(self.port))
        self.assertTrue(control.http_ready(port2))
        self.assertEqual(run(root, "stop", "other.test")[1]["state"], "stopped")

    def test_stop_never_uses_last_used_without_confirmation(self):
        root = helpers.make_repo(helpers.MIXED, ("alpha.example", "static.example"))
        code, out = run(root, "stop", "--last", "static.example")
        self.assertEqual(code, 2)
        self.assertIn("ask", out)


class LaunchJsonTests(ControlBase):
    def test_D1_invalid_launch_json_stops_and_is_untouched(self):
        root = self.project()
        f = root / ".claude" / "launch.json"
        f.parent.mkdir()
        f.write_text("{ not json")
        code, out = run(root, "start")
        self.assertEqual(code, 1)
        self.assertIn("STOP", out)
        self.assertEqual(f.read_text(), "{ not json")
        self.assertFalse(control.port_bound(self.port))

    def test_D2_identical_entry_is_not_rewritten(self):
        import preview
        root = self.project()
        preview.write_launch(root, {"name": "site.test", "type": "astro-static", "path": "sites/site.test", "port": self.port})
        f = root / ".claude" / "launch.json"
        f.write_text(f.read_text().replace('"version": "0.0.1"', '"version":   "0.0.1"'))   # odd formatting survives
        before = f.read_text()
        preview.write_launch(root, {"name": "site.test", "type": "astro-static", "path": "sites/site.test", "port": self.port})
        self.assertEqual(f.read_text(), before)


class SafeStateTests(ControlBase):
    """Review finding 1: symlinks and foreign files in the state area are never followed, overwritten or cleaned."""

    def setUp(self):
        super().setUp()
        self.outside = self.tmp / "outside"          # not inside the temporary project
        self.outside.mkdir()
        self.victim = self.outside / "victim.txt"
        self.victim.write_text("precious")

    def assert_nothing_started_and_victim_intact(self):
        self.assertEqual(self.victim.read_text(), "precious")
        self.assertEqual(sorted(p.name for p in self.outside.iterdir()), ["victim.txt"])
        self.assertFalse(control.port_bound(self.port))
        self.assertEqual(self.spawned, [])

    def test_symlink_as_record_path_is_not_followed_or_replaced(self):
        root = self.project()
        directory = control.ensure_state_dir(root)
        link = directory / "preview-site.test.json"
        link.symlink_to(self.victim)
        for verb in ("start", "status", "stop"):
            code, out = run(root, verb)
            self.assertEqual((code, out["state"]), (1, "unsafe-state"), (verb, out))
        self.assertTrue(link.is_symlink())
        self.assertEqual(os.readlink(link), str(self.victim))
        self.assert_nothing_started_and_victim_intact()

    def test_directory_or_fifo_as_record_path_is_left_alone(self):
        root = self.project()
        directory = control.ensure_state_dir(root)
        (directory / "preview-site.test.json").mkdir()
        self.assertEqual(run(root, "start")[1]["state"], "unsafe-state")
        self.assertTrue((directory / "preview-site.test.json").is_dir())
        (directory / "preview-site.test.json").rmdir()
        os.mkfifo(directory / "preview-site.test.json")
        self.assertEqual(run(root, "status")[1]["state"], "unsafe-state")
        self.assertTrue(stat.S_ISFIFO(os.lstat(directory / "preview-site.test.json").st_mode))
        self.assertEqual(self.spawned, [])

    def test_symlinked_state_directory_is_refused(self):
        root = self.project()
        base = self.tmp / "state"
        base.mkdir(mode=0o700)
        (base / control.project_hash(root)).symlink_to(self.outside)
        code, out = run(root, "start")
        self.assertEqual((code, out["state"]), (1, "unsafe-state"), out)
        self.assert_nothing_started_and_victim_intact()

    def test_symlinked_or_writable_base_directory_is_refused(self):
        root = self.project()
        (self.tmp / "state").symlink_to(self.outside)
        self.assertEqual(run(root, "start")[1]["state"], "unsafe-state")
        self.assert_nothing_started_and_victim_intact()
        (self.tmp / "state").unlink()
        (self.tmp / "state").mkdir()
        os.chmod(self.tmp / "state", 0o777)
        self.assertEqual(run(root, "start")[1]["state"], "unsafe-state")
        self.assertEqual(self.spawned, [])

    def test_stale_record_with_symlinked_log_removes_neither_link_nor_target(self):
        root = self.project()
        directory = control.ensure_state_dir(root)
        log = directory / "preview-site.test-deadbeef.log"
        log.symlink_to(self.victim)
        self.put_record(root, {"start_id": "x", "project_root": str(root.resolve()), "site": "site.test",
                               "working_dir": str((root / "sites" / "site.test").resolve()), "port": self.port,
                               "pid": 2 ** 22 - 3, "pgid": 1, "process_start_time": "Mon Jan  1 00:00:00 2001", "log": str(log)})
        code, out = run(root, "start", "--timeout", "20")
        self.assertEqual(out["state"], "running-new", out)
        self.assertTrue(log.is_symlink())                      # not removed
        self.assertEqual(self.victim.read_text(), "precious")  # not written through
        self.assertEqual(control.own_log_path(root, {"log": str(log)}), None)
        self.assertEqual(control.log_tail(log), [])

    def test_rename_failure_cleans_only_own_staging_and_stops_the_instance(self):
        root = self.project()
        directory = control.ensure_state_dir(root)
        planted = directory / ".preview-site.test.json.planted.tmp"      # foreign file with a staging-like name
        planted.write_text("not ours")
        with mock.patch.object(control.os, "replace", side_effect=OSError("disk says no")):
            code, out = run(root, "start", "--timeout", "10")
        self.assertEqual((code, out["state"], out["started"]), (1, "failed-after-start", True), out)
        self.assertEqual(out["cleanup"]["result"], "stopped")
        self.assertIn("disk says no", out["message"])
        self.assertEqual(planted.read_text(), "not ours")
        self.assertFalse(control.record_file(root, "site.test").exists())
        self.assertEqual([p.name for p in directory.iterdir() if p.name.endswith(".tmp")], [planted.name])
        self.assertFalse(control.port_bound(self.port))                  # the instance just started was stopped
        self.assertEqual([p.name for p in directory.iterdir() if p.name.endswith(".log")], [])

    def test_staging_write_failure_cleans_own_staging_only(self):
        root = self.project()
        directory = control.ensure_state_dir(root)
        planted = directory / ".preview-site.test.json.planted.tmp"
        planted.write_text("not ours")
        with mock.patch.object(control.os, "fsync", side_effect=OSError("no sync")):
            with self.assertRaises(OSError):
                control.write_record(control.record_file(root, "site.test"), {"a": 1})
        self.assertEqual(sorted(p.name for p in directory.iterdir()), [planted.name])
        self.assertEqual(planted.read_text(), "not ours")

    def test_record_swapped_for_symlink_between_check_and_rename_is_replaced_not_followed(self):
        root = self.project()
        directory = control.ensure_state_dir(root)
        target = control.record_file(root, "site.test")
        real_replace = os.replace

        def swap_then_replace(src, dst):
            Path(dst).symlink_to(self.victim)       # an attacker plants a link after the checks
            return real_replace(src, dst)           # rename replaces the link itself, never writes through it
        with mock.patch.object(control.os, "replace", swap_then_replace):
            control.write_record(target, {"a": 1})
        self.assertFalse(target.is_symlink())
        self.assertEqual(self.victim.read_text(), "precious")

    def test_exclusive_staging_refuses_existing_name(self):
        root = self.project()
        directory = control.ensure_state_dir(root)
        fixed = mock.Mock(hex="0" * 32)
        planted = directory / f".preview-site.test.json.{'0' * 32}.tmp"
        planted.symlink_to(self.victim)
        with mock.patch.object(control.uuid, "uuid4", return_value=fixed):
            with self.assertRaises(FileExistsError):
                control.write_record(control.record_file(root, "site.test"), {"a": 1})
        self.assertTrue(planted.is_symlink())
        self.assertEqual(self.victim.read_text(), "precious")

    def test_remove_own_never_removes_links_or_foreign_kinds(self):
        link = self.tmp / "link"
        link.symlink_to(self.victim)
        self.assertFalse(control.remove_own(link))
        self.assertTrue(link.is_symlink())
        self.assertEqual(self.victim.read_text(), "precious")
        self.assertFalse(control.remove_own(self.outside))
        self.assertTrue(control.remove_own(self.victim))


class EvidenceTests(ControlBase):
    """Review finding 2 (and P11 for the terminal path): ps/lsof missing, denied, failing; HTTP without attribution."""

    def fake_tool(self, directory, name, body, executable=True):
        directory.mkdir(exist_ok=True)
        path = directory / name
        path.write_text("#!/bin/sh\n" + body + "\n")
        path.chmod(0o755 if executable else 0o644)
        return path

    def with_path(self, *dirs):
        return mock.patch.dict(os.environ, {"PATH": os.pathsep.join(str(d) for d in dirs)})

    def assert_refused_before_anything(self, root, tool, kind):
        with self.subTest(tool=tool, kind=kind):
            code, out = run(root, "start", "--timeout", "5")
        self.assertEqual((code, out["state"], out["tool"], out["kind"]), (1, "insufficient-evidence", tool, kind), out)
        self.assertEqual(self.spawned, [])
        self.assertFalse((root / ".claude" / "launch.json").exists())      # no write before the capability check
        self.assertFalse((self.tmp / "state").exists())
        self.assertFalse(control.port_bound(self.port))

    def test_missing_ps(self):
        root = self.project()
        only_lsof = self.tmp / "only-lsof"
        only_lsof.mkdir()
        (only_lsof / "lsof").symlink_to(shutil.which("lsof"))
        with self.with_path(self.bin, only_lsof):
            self.assert_refused_before_anything(root, "ps", "missing")

    def test_missing_lsof(self):
        root = self.project()
        only_ps = self.tmp / "only-ps"
        only_ps.mkdir()
        (only_ps / "ps").symlink_to(shutil.which("ps"))
        with self.with_path(self.bin, only_ps):
            self.assert_refused_before_anything(root, "lsof", "missing")

    def test_denied_lsof_not_executable(self):
        root = self.project()
        d = self.tmp / "denied"
        (d).mkdir()
        (d / "ps").symlink_to(shutil.which("ps"))
        self.fake_tool(d, "lsof", "exit 0", executable=False)
        with self.with_path(self.bin, d):
            self.assert_refused_before_anything(root, "lsof", "denied")

    def test_denied_lsof_reports_permission_error_text(self):
        root = self.project()
        d = self.tmp / "denied2"
        d.mkdir()
        (d / "ps").symlink_to(shutil.which("ps"))
        self.fake_tool(d, "lsof", "echo 'lsof: Operation not permitted' >&2; exit 1")
        with self.with_path(self.bin, d):
            self.assert_refused_before_anything(root, "lsof", "denied")

    def test_failing_lsof_exit_code(self):
        root = self.project()
        d = self.tmp / "failing"
        d.mkdir()
        (d / "ps").symlink_to(shutil.which("ps"))
        self.fake_tool(d, "lsof", "echo boom >&2; exit 7")
        with self.with_path(self.bin, d):
            self.assert_refused_before_anything(root, "lsof", "failed")

    def test_blind_lsof_that_cannot_see_own_socket_is_insufficient(self):
        root = self.project()
        d = self.tmp / "blind"
        d.mkdir()
        (d / "ps").symlink_to(shutil.which("ps"))
        self.fake_tool(d, "lsof", "exit 1")                 # looks like "no listener", is in fact blind
        with self.with_path(self.bin, d):
            self.assert_refused_before_anything(root, "lsof", "failed")

    def test_blind_ps_that_cannot_see_own_process_is_insufficient(self):
        root = self.project()
        d = self.tmp / "blindps"
        d.mkdir()
        (d / "lsof").symlink_to(shutil.which("lsof"))
        self.fake_tool(d, "ps", "exit 1")
        with self.with_path(self.bin, d):
            self.assert_refused_before_anything(root, "ps", "failed")

    def test_status_and_stop_refuse_without_evidence_and_signal_nothing(self):
        root = self.project()
        self.assertEqual(run(root, "start", "--timeout", "20")[1]["state"], "running-new")
        only_ps = self.tmp / "only-ps"
        only_ps.mkdir()
        (only_ps / "ps").symlink_to(shutil.which("ps"))
        with self.with_path(self.bin, only_ps):
            for verb in ("status", "stop"):
                code, out = run(root, verb)
                self.assertEqual((code, out["state"], out["tool"]), (1, "insufficient-evidence", "lsof"), (verb, out))
        self.assertTrue(control.http_ready(self.port))                   # still running, untouched
        self.assertEqual(run(root, "stop")[1]["state"], "stopped")

    def test_http_responder_without_attributed_listener_is_never_ready(self):
        root = self.project()
        with mock.patch.object(control, "probe_os_evidence"), mock.patch.object(control, "port_listeners", return_value=[]):
            code, out = run(root, "start", "--timeout", "2")
        self.assertEqual((code, out["state"], out["kind"]), (1, "insufficient-evidence", "not-attributed"), out)
        self.assertFalse(control.port_bound(self.port))                  # our group was stopped; nothing reported as running
        self.assertFalse(control.record_file(root, "site.test").exists())

    def test_status_and_reuse_need_attribution_too(self):
        root = self.project()
        self.assertEqual(run(root, "start", "--timeout", "20")[1]["state"], "running-new")
        with mock.patch.object(control, "probe_os_evidence"), mock.patch.object(control, "port_listeners", return_value=[]):
            code, st = run(root, "status")
            self.assertEqual((code, st["state"]), (1, "insufficient-evidence"), st)
            code, again = run(root, "start", "--timeout", "1.5")
            self.assertEqual((code, again["state"]), (1, "insufficient-evidence"), again)
        self.assertEqual(run(root, "status")[1]["state"], "running-reused")      # with evidence it is reported again
        self.assertEqual(run(root, "stop")[1]["state"], "stopped")

    def test_listener_outside_our_group_is_a_conflict_not_ready(self):
        root = self.project()
        self.assertEqual(run(root, "start", "--timeout", "20")[1]["state"], "running-new")
        rec = control.read_record(control.record_file(root, "site.test"))
        with mock.patch.object(control, "port_listeners", return_value=[os.getpid()]):
            code, st = run(root, "status")
        self.assertEqual((code, st["state"]), (1, "unknown-owner"), st)
        self.assertEqual(control.proc_info(rec["pid"])["start"], rec["process_start_time"])


class TimeoutTests(ControlBase):
    """Review finding 3: only finite, positive, bounded timeouts; rejected before any start or write."""

    def test_invalid_values_are_rejected_before_start_or_write(self):
        root = self.project()
        for value in ("nan", "NaN", "inf", "-inf", "Infinity", "0", "-1", "-0.5", "0.0", "600.0001", "601", "1e999", "1e400", "abc", ""):
            with self.subTest(value=value):
                code, out = run(root, "start", f"--timeout={value}")
                self.assertEqual(code, 1, out)
                self.assertTrue(out.startswith("STOP: --timeout"), out)
        self.assertEqual(self.spawned, [])
        self.assertFalse((root / ".claude").exists())
        self.assertFalse((self.tmp / "state").exists())
        self.assertFalse(control.port_bound(self.port))

    def test_verbs_other_than_start_validate_too(self):
        root = self.project()
        for verb in ("status", "stop"):
            self.assertEqual(run(root, verb, "--timeout", "nan")[0], 1)
        self.assertFalse((self.tmp / "state").exists())

    def test_documented_bounds_are_accepted(self):
        self.assertEqual(control.parse_timeout("0.001"), 0.001)
        self.assertEqual(control.parse_timeout("600"), control.MAX_TIMEOUT)
        self.assertEqual(control.parse_timeout("60"), 60.0)
        root = self.project()
        code, out = run(root, "status", "--timeout", "600")
        self.assertEqual((code, out["state"]), (0, "not-running"))

    def test_default_is_finite_and_inside_the_bound(self):
        self.assertTrue(0 < control.READY_TIMEOUT <= control.MAX_TIMEOUT)
        self.assertEqual(control.parse_timeout(control.parse(["start"]).timeout), control.READY_TIMEOUT)


class PostStartFailureTests(ControlBase):
    """Review finding: any failure after a successful Popen must end or truthfully report the started instance."""

    def evidence_error(self):
        return control.EvidenceError("ps", "failed", "injected")

    def injected_proc_info(self, when):
        """proc_info that behaves normally until `when(self)` is true, then raises."""
        real = control.proc_info

        def patched(pid):
            if when():
                raise self.evidence_error()
            return real(pid)
        return patched

    def assert_ended(self, root, out, step):
        self.assertEqual((out["state"], out["started"], out["failed_step"]), ("failed-after-start", True, step), out)
        self.assertEqual(out["cleanup"]["result"], "stopped", out)
        self.assertIn("WAS started", out["message"])
        self.assertIn("no process of this start remains", out["message"])
        self.assertNotIn("nothing was started", out["message"])
        pid = out["pid"]
        self.assertEqual(self.spawned, [pid])
        with self.assertRaises(ProcessLookupError):
            os.killpg(pid, 0)                                   # no member of the group is left
        self.assertFalse(control.port_bound(self.port))
        state = self.tmp / "state"
        leftovers = [p.name for p in state.glob("*/*")] if state.exists() else []
        self.assertEqual(leftovers, [], "record and log of an ended instance are removed")

    def test_evidence_error_immediately_after_popen(self):
        root = self.project()
        with mock.patch.object(control, "proc_info", self.injected_proc_info(lambda: bool(self.spawned))):
            code, out = run(root, "start", "--timeout", "10")
        self.assertEqual(code, 1)
        self.assert_ended(root, out, "identify the started process")
        self.assertEqual(out["cause"]["tool"], "ps")
        self.assertIn("injected", out["message"])

    def test_live_child_that_cannot_be_identified_is_ended(self):
        root = self.project(mode="hang")
        real = control.proc_info
        with mock.patch.object(control, "proc_info", lambda pid: None if self.spawned and pid == self.spawned[0] else real(pid)):
            code, out = run(root, "start", "--timeout", "10")
        self.assertEqual(code, 1)
        self.assert_ended(root, out, "identify the started process")
        self.assertIn("could not be identified", out["message"])

    def test_evidence_error_during_readiness(self):
        root = self.project(mode="hang")
        record = lambda: control.record_file(root, "site.test").exists()
        with mock.patch.object(control, "proc_info", self.injected_proc_info(record)):
            code, out = run(root, "start", "--timeout", "10")
        self.assertEqual(code, 1)
        self.assert_ended(root, out, "wait for readiness")

    def test_failure_in_final_verification(self):
        root = self.project()
        real, calls = control.verify, []

        def verify(*a, **kw):
            calls.append(1)
            if len(calls) >= 3:                              # 1: reuse check, 2: readiness, 3: final verification
                raise self.evidence_error()
            return real(*a, **kw)
        with mock.patch.object(control, "verify", verify):
            code, out = run(root, "start", "--timeout", "20")
        self.assertEqual(code, 1)
        self.assert_ended(root, out, "final verification")

    def test_final_verification_that_does_not_confirm_is_a_failure_too(self):
        root = self.project()
        real, calls = control.verify, []

        def verify(*a, **kw):
            calls.append(1)
            result = real(*a, **kw)
            return {**result, "attributed": False} if len(calls) == 3 else result
        with mock.patch.object(control, "verify", verify):
            code, out = run(root, "start", "--timeout", "20")
        self.assertEqual(code, 1)
        self.assert_ended(root, out, "final verification")

    def test_timeout_final_verification_failure_is_reported_not_swallowed(self):
        root = self.project(mode="hang")
        real, calls = control.verify, []

        def verify(*a, **kw):
            calls.append(1)
            if len(calls) >= 2:
                raise self.evidence_error()
            return real(*a, **kw)
        with mock.patch.object(control, "verify", verify):
            code, out = run(root, "start", "--timeout", "1")
        self.assertEqual(code, 1)
        self.assert_ended(root, out, "final verification")

    def test_failed_cleanup_is_reported_truthfully_and_start_facts_are_kept(self):
        root = self.project(mode="hang")
        real_killpg = os.killpg

        def killpg(pgid, sig):
            if sig in (signal.SIGTERM, signal.SIGKILL):
                raise PermissionError(1, "Operation not permitted")
            return real_killpg(pgid, sig)
        record = lambda: control.record_file(root, "site.test").exists()
        with mock.patch.object(control, "proc_info", self.injected_proc_info(record)), \
                mock.patch.object(control.os, "killpg", killpg), mock.patch.object(control, "STOP_GRACE", 0.3):
            code, out = run(root, "start", "--timeout", "10")
        self.assertEqual((code, out["state"], out["started"]), (1, "failed-after-start", True), out)
        self.assertEqual(out["cleanup"]["result"], "incomplete", out)
        self.assertIn("SIGTERM", " ".join(out["cleanup"]["detail"]))
        self.assertIn("INCOMPLETE", out["message"])
        self.assertIn("may still be running", out["message"])
        self.assertNotIn("no process of this start remains", out["message"])
        self.assertNotIn("nothing was started", out["message"])
        # the facts needed to find it again are kept
        pid = out["pid"]
        self.assertTrue(pid and out["pgid"] == pid and out["process_start_time"] and out["start_id"])
        self.assertTrue(Path(out["kept"]["log"]).is_file())
        rec = control.read_record(control.record_file(root, "site.test"))
        self.assertEqual((rec["pid"], rec["start_id"]), (pid, out["start_id"]))
        # and the process really is still there (the report is true); the test cleanup ends it by identity
        info = control.proc_info(pid)
        self.assertIsNotNone(info)
        self.assertEqual(info["start"], out["process_start_time"])

    def test_failed_cleanup_before_a_record_exists_reports_ids_and_keeps_the_log(self):
        root = self.project(mode="hang")
        real_killpg = os.killpg

        def killpg(pgid, sig):
            if sig in (signal.SIGTERM, signal.SIGKILL):
                raise PermissionError(1, "Operation not permitted")
            return real_killpg(pgid, sig)
        with mock.patch.object(control, "proc_info", self.injected_proc_info(lambda: bool(self.spawned))), \
                mock.patch.object(control.os, "killpg", killpg), mock.patch.object(control, "STOP_GRACE", 0.3):
            code, out = run(root, "start", "--timeout", "10")
        self.assertEqual((out["state"], out["cleanup"]["result"], out["kept"]["record"]), ("failed-after-start", "incomplete", None), out)
        self.assertTrue(Path(out["kept"]["log"]).is_file())
        self.assertIsNone(out["process_start_time"])                       # identification was what failed; said so, not invented
        self.assertIn("unknown", out["message"])
        self.assertIsNotNone(control.proc_info(out["pid"]))

    def test_terminate_own_never_signals_a_reaped_and_empty_group(self):
        proc = control.subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
        proc.wait()
        with mock.patch.object(control.os, "killpg", wraps=os.killpg) as spy:
            result = control.terminate_own(proc)
        self.assertEqual(result["result"], "stopped")
        sigs = [c.args[1] for c in spy.call_args_list]
        self.assertNotIn(signal.SIGTERM, sigs)
        self.assertNotIn(signal.SIGKILL, sigs)

    def test_pre_start_failures_still_say_nothing_was_started(self):
        root = self.project()
        with mock.patch.dict(os.environ, {"PATH": str(self.tools)}):
            code, out = run(root, "start")
        self.assertEqual((out["state"], out["started"]), ("failed", False))
        self.assertIn("nothing was started", out["message"])
        s = self.foreign_listener()
        code, out = run(root, "start")
        self.assertEqual((out["state"], out["started"]), ("port-conflict", False))
        self.assertEqual(self.spawned, [])


if __name__ == "__main__":
    unittest.main()
