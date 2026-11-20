"""Side-effect boundaries of the preview verbs and the runtime started from an isolated plugin copy.

* `status` and `inspect` start, signal and write nothing; `needs-install` and every early stop happen before any process,
  launch entry or record exists; `preview` never calls npm itself for an installation.
* The skill is started the way a host starts it: from an extracted copy under a path with spaces, from another working
  directory, `python3 -B`, without PYTHONPATH. Templates and the schema come from the copy; the copy stays byte-identical.
All processes are fake dev servers started by the tests' own fake `npm`, on free 127.0.0.1 ports; cleanup is identity-checked.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.support import preview_helpers as helpers
from tests.support.preview_process import ControlBase, run
import control


def tree(root):
    out = {}
    for current, dirs, files in os.walk(root):
        for name in dirs + files:
            path = Path(current) / name
            rel = path.relative_to(root).as_posix()
            out[rel] = "dir" if path.is_dir() and not path.is_symlink() else hashlib.sha256(path.read_bytes()).hexdigest()
    return out


class NoUnintendedSideEffects(ControlBase):
    def state_exists(self):
        return (self.tmp / "state").exists()

    def test_status_of_a_project_without_instance_starts_and_writes_nothing(self):
        root = self.project()
        before = tree(root)
        code, out = run(root, "status")
        self.assertEqual((code, out["state"], out["started"]), (0, "not-running", False), out)
        self.assertEqual(self.spawned, [])
        self.assertFalse(control.port_bound(self.port))
        self.assertFalse(self.state_exists())
        self.assertFalse((root / ".claude").exists())
        self.assertEqual(tree(root), before)

    def test_stop_without_instance_signals_and_writes_nothing(self):
        root = self.project()
        before = tree(root)
        code, out = run(root, "stop")
        self.assertEqual((code, out["state"]), (0, "not-running"), out)
        self.assertEqual(self.spawned, [])
        self.assertFalse(self.state_exists())
        self.assertEqual(tree(root), before)

    def test_inspect_without_any_server_reports_not_reachable_and_changes_nothing(self):
        root = self.project()
        before = tree(root)
        code, out = run(root, "inspect", "--expect", "Hello")
        self.assertEqual((code, out["state"]), (1, "page-not-reachable"), out)
        self.assertEqual(self.spawned, [])
        self.assertFalse(control.port_bound(self.port))
        self.assertFalse(self.state_exists())
        self.assertFalse((root / ".claude").exists())
        self.assertEqual(tree(root), before)

    def test_inspect_of_our_running_instance_changes_neither_process_nor_record_nor_launch_entry(self):
        root = self.project()
        code, started = run(root, "start", "--timeout", "20")
        self.assertEqual(started["state"], "running-new", started)
        rfile = control.record_file(root, "site.test")
        launch = root / ".claude" / "launch.json"
        before = (rfile.read_bytes(), launch.read_bytes(), tree(root), control.proc_info(started["pid"])["start"], len(self.spawned))
        code, out = run(root, "inspect", "--expect", "Hello")
        # the fake dev server answers "ok" without site identity: the page is not confirmed, and process and page are separate facts
        self.assertEqual((code, out["state"], out["process"]), (1, "page-identity-unknown", "ours"), out)
        after = (rfile.read_bytes(), launch.read_bytes(), tree(root), control.proc_info(started["pid"])["start"], len(self.spawned))
        self.assertEqual(after, before)
        self.assertEqual(len(control.port_listeners(self.port)), 1)
        self.assertEqual(run(root, "stop")[1]["state"], "stopped")

    def test_missing_dependencies_give_needs_install_before_anything_and_never_install(self):
        root = self.project()
        shutil.rmtree(root / "sites" / "site.test" / "node_modules")
        calls = self.tmp / "npm-calls.log"
        recorder = self.bin / "npm"
        recorder.write_text(f'#!/bin/sh\necho "$@" >> "{calls}"\nexit 0\n')
        recorder.chmod(0o755)
        before = tree(root)
        code, out = run(root, "start")
        self.assertEqual((code, out["state"], out["started"]), (1, "needs-install", False), out)
        self.assertIn("npm install", out["message"])
        self.assertFalse(calls.exists(), "npm was called")
        self.assertEqual(self.spawned, [])
        self.assertFalse(self.state_exists())
        self.assertFalse((root / ".claude").exists())
        self.assertEqual(tree(root), before)
        for verb in ("status", "stop"):                  # the other verbs never install either
            run(root, verb)
        self.assertFalse(calls.exists())

    def test_invalid_manifest_stops_every_verb_before_state_launch_or_process(self):
        bad = {"version": 2, "components": [{**helpers._static("site.test", port=self.port), "serve": {"mode": "x"}}]}
        root = helpers.make_repo(bad, ("site.test",))
        (root / "sites" / "site.test" / "node_modules").mkdir()
        self.roots.append(root)
        before = tree(root)
        for verb in ("start", "status", "stop", "inspect"):
            code, out = run(root, verb)
            self.assertEqual(code, 1, (verb, out))
            self.assertTrue(isinstance(out, str) and out.startswith("STOP"), (verb, out))
        self.assertEqual(self.spawned, [])
        self.assertFalse(self.state_exists())
        self.assertEqual(tree(root), before)


class IsolatedPluginCopy(ControlBase):
    """The runtime from an extracted copy: only skills/preview and skills/_shared, under a path with spaces."""

    def setUp(self):
        super().setUp()
        base = Path(tempfile.mkdtemp()).resolve() / "My Plugin Copy" / "skills"
        base.mkdir(parents=True)
        ignore = shutil.ignore_patterns("__pycache__")
        shutil.copytree(helpers.SKILL, base / "preview", ignore=ignore)
        shutil.copytree(helpers.ROOT / "skills" / "_shared", base / "_shared", ignore=ignore)
        self.copy = base.parent
        self.script = base / "preview" / "scripts" / "control.py"
        self.elsewhere = Path(tempfile.mkdtemp()).resolve()
        self.assertIn(" ", str(self.script))

    def env(self, **extra):
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP")}
        env.update(extra)
        return env

    def call(self, *argv, cwd=None, flags=("-I", "-B"), env=None):
        done = subprocess.run([sys.executable, *flags, str(self.script), *argv], capture_output=True, text=True,
                              cwd=cwd or self.elsewhere, env=env or self.env())
        try:
            return done.returncode, json.loads(done.stdout)
        except ValueError:
            return done.returncode, done.stdout + done.stderr

    def test_full_lifecycle_from_the_copy_with_another_cwd_leaves_the_copy_unchanged(self):
        root = self.project()
        copy_before = tree(self.copy)
        code, first = self.call("start", "--root", str(root), "--timeout", "20")
        self.assertEqual((code, first["state"]), (0, "running-new"), first)
        code, again = self.call("start", "--root", str(root), "--timeout", "20")
        self.assertEqual((code, again["state"], again["pid"]), (0, "running-reused", first["pid"]), again)
        self.assertEqual(len(control.port_listeners(self.port)), 1)
        self.assertEqual(self.call("status", "--root", str(root))[1]["state"], "running-reused")
        code, stopped = self.call("stop", "--root", str(root))
        self.assertEqual((code, stopped["state"]), (0, "stopped"), stopped)
        self.assertFalse(control.port_bound(self.port))
        self.assertEqual(tree(self.copy), copy_before)          # no state, no bytecode, no log inside the installed copy
        self.assertEqual(list(self.copy.rglob("__pycache__")), [])

    def test_the_website_project_as_working_directory_works_without_root_argument(self):
        root = self.project()
        code, out = self.call("status", cwd=root)
        self.assertEqual((code, out["state"], out["project_root"]), (0, "not-running", str(root)), out)

    def test_decoy_modules_on_pythonpath_do_not_shadow_the_runtime(self):
        decoy = self.tmp / "decoy"
        decoy.mkdir()
        for name in ("preview.py", "errors.py", "sites.py", "manifest.py", "schema.py"):
            (decoy / name).write_text("raise RuntimeError('decoy imported')\n")
        (decoy / "site_common").mkdir()
        (decoy / "site_common" / "__init__.py").write_text("raise RuntimeError('decoy package imported')\n")
        root = self.project()
        code, out = self.call("status", "--root", str(root), flags=("-B",), env=self.env(PYTHONPATH=str(decoy)))
        self.assertEqual((code, out["state"]), (0, "not-running"), out)

    def test_launch_template_comes_from_the_copy(self):
        root = self.project()
        template = self.copy / "skills" / "preview" / "templates" / "launch" / "astro-static.json.tpl"
        template.write_text(template.read_text().replace('"autoPort": false', '"autoPort": false, "marker": "from-the-copy"'))
        code, out = self.call("start", "--root", str(root), "--timeout", "20")
        self.assertEqual((code, out["state"]), (0, "running-new"), out)
        entry = json.loads((root / ".claude" / "launch.json").read_text())["configurations"][0]
        self.assertEqual(entry["marker"], "from-the-copy")
        self.assertEqual(self.call("stop", "--root", str(root))[1]["state"], "stopped")

    def test_missing_template_in_the_copy_stops_before_launch_entry_record_and_process(self):
        root = self.project()
        (self.copy / "skills" / "preview" / "templates" / "launch" / "astro-static.json.tpl").unlink()
        code, out = self.call("start", "--root", str(root))
        self.assertEqual(code, 1)
        self.assertIn("No preview template for type 'astro-static'", out)
        self.assertFalse((root / ".claude").exists())
        self.assertEqual(list((self.tmp / "state").rglob("*.json")), [])
        self.assertFalse(control.port_bound(self.port))
        self.assertEqual(list(self.tmp.glob("state/*/preview-*.log")), [])

    def test_missing_schema_in_the_copy_stops_with_an_incomplete_installation_message(self):
        root = self.project()
        (self.copy / "skills" / "_shared" / "resources" / "website.schema.json").unlink()
        code, out = self.call("start", "--root", str(root))
        self.assertEqual(code, 1)
        self.assertIn("installation is incomplete", out)
        self.assertFalse((root / ".claude").exists())
        self.assertFalse(control.port_bound(self.port))


if __name__ == "__main__":
    unittest.main()
