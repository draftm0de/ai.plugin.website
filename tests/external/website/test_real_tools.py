"""REAL npm/Node/Astro end-to-end run of setup -> optimize -> edit -> preview on a fictional site (demo.example).

NOT part of any default layer; NOT RUN unless started through `python3 -B scripts/run_external_tests.py --approved`
(module flag `tests.external.ENABLED`, never an environment variable). Network: the npm registry (site dependencies).
Everything lives in a temporary folder with a space in its path: a copy of the shipped payload (skills/ only), a fictional git
repository and a private TMPDIR for process/backup state. The preview dev server binds 127.0.0.1 on a free port and is checked and
stopped only through the preview controller (ownership proof); nothing is signalled by port or guessed PID. Cleanup is registered
before the first call: the fixture is deleted only after a passed test and a confirmed end of the own processes, otherwise it is
kept and its path printed (rules: tests/support/external_cleanup.py, regression: tests/unit/external_cleanup/). Evidence only: a
passing HTTP check is no browser check.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import tests.external as external
from tests.support import external_cleanup as cleanup

ROOT = Path(__file__).resolve().parents[3]
DOMAIN = "demo.example"
MARK = "EDITMARKER7431"
DUP = '<h1 class="page-header__lead">Fixture duplicate heading</h1>'
LEAD = '<p class="page-header__lead">demo.example</p>'


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@unittest.skipUnless(external.ENABLED, "external real-tool tests: only via scripts/run_external_tests.py --approved")
class RealToolchainTests(unittest.TestCase):
    def setUp(self):
        cls = type(self)
        cls.base = Path(tempfile.mkdtemp(prefix="website real tools ")).resolve()
        self.completed = False
        self.addCleanup(self._cleanup)                      # registered before anything can start or fail
        cls.plugin = cls.base / "plugin copy"
        shutil.copytree(ROOT / "skills", cls.plugin / "skills", ignore=shutil.ignore_patterns("__pycache__"))
        cls.site = cls.base / "fictional site"
        cls.site.mkdir()
        cls.state = cls.base / "state tmp"
        cls.state.mkdir()
        cls.env = {**os.environ, "TMPDIR": str(cls.state), "PYTHONDONTWRITEBYTECODE": "1"}
        for name in ("PYTHONPATH", "WEBSITE_MANAGER_STATE_DIR"):
            cls.env.pop(name, None)
        cls.port = free_port()
        cls.git("init", "-q", "-b", "main")
        (cls.site / "README.md").write_text("# fictional demo.example repository\n")
        cls.git("add", "README.md")
        cls.commit("fixture: initial commit")

    def _control(self, verb):
        rc, data, _ = self.run_py("preview", "control.py", verb, DOMAIN, "--root", str(self.site), timeout=120)
        return rc, data

    def _cleanup(self):
        ended, note = cleanup.ensure_preview_stopped(self._control)
        deleted = cleanup.finalize_fixture(self.base, self.completed, ended, note)
        if self.completed and not deleted:
            raise AssertionError("own preview process not confirmed ended; fixture kept at %s (%s)" % (self.base, note))

    @classmethod
    def git(cls, *args):
        return subprocess.run(["git", *args], cwd=cls.site, env=cls.env, check=True, capture_output=True, text=True).stdout

    @classmethod
    def commit(cls, message):
        cls.git("-c", "user.name=Fixture", "-c", "user.email=fixture@demo.example", "commit", "-qam", message)

    @classmethod
    def run_py(cls, skill, script, *args, timeout=600):
        argv = [sys.executable, "-B", str(cls.plugin / "skills" / skill / "scripts" / script), *args]
        done = subprocess.run(argv, cwd=cls.site, env=cls.env, capture_output=True, text=True, timeout=timeout)
        try:
            data = json.loads(done.stdout)
        except ValueError:
            data = None
        return done.returncode, data, done

    def test_end_to_end(self):
        page = self.site / "sites" / DOMAIN / "src" / "pages" / "index.astro"
        # setup: real install/build/check, then verify
        rc, data, done = self.run_py("setup", "site_setup.py", "create", DOMAIN, "--type", "astro-static", "--title", "Demo Example",
                                     "--port", str(self.port), "--build", "--json")
        self.assertEqual((rc, data["state"]), (0, "created"), done.stdout + done.stderr)
        self.assertEqual({k: (v["ran"], v["exit"]) for k, v in data["verification"].items()},
                         {"install": (True, 0), "build": (True, 0), "check": (True, 0)})
        self.assertEqual(data["lockfile"], "created")
        self.assertTrue((self.site / "sites" / DOMAIN / "dist" / "index.html").is_file())
        self.assertTrue((self.site / ".project" / "specs" / "website.schema.json").is_file())
        rc, data, done = self.run_py("setup", "site_setup.py", "verify", DOMAIN, "--json")
        self.assertEqual((rc, data["state"], data["lockfile"]), (0, "verified", "unchanged"), done.stdout + done.stderr)
        self.git("add", "-A")
        self.commit("fixture: setup create")

        # optimize: controlled SEO error (test setup: duplicate h1), real audit, approve exactly that finding, apply, recheck
        original = page.read_text()
        self.assertEqual(original.count(LEAD), 1)
        page.write_text(original.replace(LEAD, DUP))
        self.commit("fixture TEST SETUP: duplicate h1")
        rc, data, done = self.run_py("optimize", "audit.py", "audit", "--site", DOMAIN)
        self.assertEqual((rc, data["status"]), (1, "errors"), done.stdout + done.stderr)
        self.assertEqual((data["build_exit"], data["checks"]["seo"]["exit"], data["checks"]["a11y"]["exit"]), (0, 1, 0))
        self.assertEqual(data["readonly_violations"], [])
        proposals = self.base / "proposals.json"
        worklist = (self.site / data["worklist"]).read_text()
        blocks = worklist.split("\n### ")
        finding = next(b.split(" ")[0] for b in blocks if "`seo.h1-count`" in b)   # only the h1 finding is approved
        self.assertIn(finding, data["changes"]["new"])
        proposals.write_text(json.dumps({finding: {"summary": "Keep exactly one h1", "kind": "rule", "current": DUP, "proposed": LEAD,
                                                   "edit": {"file": f"sites/{DOMAIN}/src/pages/index.astro", "find": DUP, "replace": LEAD}}}))
        self.assertEqual(self.run_py("optimize", "audit.py", "propose", "--site", DOMAIN, "--proposals", str(proposals))[0], 0)
        self.assertEqual(self.run_py("optimize", "audit.py", "decide", finding, "--status", "approved", "--reason", "fixture", "--site", DOMAIN)[0], 0)
        rc, data, done = self.run_py("optimize", "audit.py", "apply", finding, "--site", DOMAIN)
        self.assertEqual((rc, data["changes"].get("resolved")), (0, [finding]), done.stdout + done.stderr)
        self.assertEqual(page.read_text(), original)
        self.assertEqual(data["checks"]["seo"]["exit"], 0)
        changed = [l[3:] for l in self.git("status", "--porcelain").splitlines()]
        self.assertEqual([c for c in changed if not c.startswith(".project/reports/")], [f"sites/{DOMAIN}/src/pages/index.astro"])
        self.git("add", "-A")
        self.commit("fixture: optimize apply")

        # edit: one fictional text, real check, finish without --visual-done leaves the visual check open
        rc, data, done = self.run_py("edit", "edit.py", "begin", "--root", str(self.site), "--site", DOMAIN)
        self.assertEqual((rc, data["state"]), (0, "begun"), done.stdout + done.stderr)
        state = data["state_folder"]
        self.assertEqual(self.run_py("edit", "edit.py", "replace", "--state", state, "--find", LEAD,
                                     "--replace", f'<p class="page-header__lead">Edited fictional lead {MARK} for demo.example</p>')[0], 0)
        rc, data, done = self.run_py("edit", "edit.py", "check", "--state", state)
        self.assertEqual((rc, data["state"], data["build"]["exit"], data["check"]["exit"]), (0, "checked", 0, 0), done.stdout + done.stderr)
        rc, data, done = self.run_py("edit", "edit.py", "finish", "--state", state)
        self.assertEqual((rc, data["technical"], data["visual"]), (0, "passed", "open"), done.stdout + done.stderr)
        self.assertEqual(data["outcome"], "technically checked, visual check open")
        self.assertEqual(self.git("show", "HEAD:" + f"sites/{DOMAIN}/src/pages/index.astro"), original)

        # preview: real Astro dev server on 127.0.0.1 through the preview runtime only (cleanup in _cleanup via the controller)
        rc, data, done = self.run_py("preview", "control.py", "start", DOMAIN, "--root", str(self.site), "--timeout", "120", timeout=180)
        self.assertIsNotNone(data, "unreadable start output: " + done.stdout + done.stderr)
        self.assertEqual((rc, data["state"]), (0, "running-new"), done.stdout + done.stderr)
        rc, data, done = self.run_py("preview", "control.py", "inspect", DOMAIN, "--root", str(self.site), "--expect", MARK)
        self.assertEqual((rc, data["state"], data["process"]), (0, "page-confirmed", "ours"), done.stdout + done.stderr)
        self.assertFalse(data["visibility_checked"])
        rc, data, done = self.run_py("preview", "control.py", "inspect", DOMAIN, "--root", str(self.site), "--expect", "NOT-ON-THE-PAGE-9999")
        self.assertEqual((rc, data["state"]), (1, "page-stale"))
        rc, data, done = self.run_py("preview", "control.py", "stop", DOMAIN, "--root", str(self.site))
        self.assertEqual((rc, data["state"]), (0, "stopped"), done.stdout + done.stderr)
        rc, data, done = self.run_py("preview", "control.py", "status", DOMAIN, "--root", str(self.site))
        self.assertEqual(data["state"], "not-running")
        with socket.socket() as s:
            self.assertNotEqual(s.connect_ex(("127.0.0.1", self.port)), 0)
        self.completed = True                               # only now may _cleanup delete the fixture

if __name__ == "__main__":
    unittest.main()
