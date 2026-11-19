"""Fixtures for the tests of the `edit` skill: a temporary git repository with a fictional site created by the real `setup`
(astro-static, fake runner, no install, no real build), a fake `npm` outside the repository that logs every call and refuses
everything but `run`, and process-level calls of `edit.py` from the repository or from an extracted copy.

Importing this module also makes `edit.py` importable in-process (`import edit`). No real website, no real npm, no network."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.support import setup_helpers as h

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT                                          # the repository root is the plugin root
SKILL = ROOT / "skills" / "edit"
PY = SKILL / "scripts"
EDIT = PY / "edit.py"
SHARED = ROOT / "skills" / "_shared"
PREVIEW = ROOT / "skills" / "preview"
SPY = Path(__file__).resolve().parent / "edit_spy.py"
if str(PY) not in sys.path:
    sys.path.insert(0, str(PY))

GOOD = """---
import BaseLayout from '../layouts/BaseLayout.astro';
import { SITE_NAME } from '../lib/site';
---

<BaseLayout title={SITE_NAME} description="Fixture club welcomes new players every week with training, matches and a friendly team." current="home">
  <div class="container">
    <header class="page-header">
      <h1 class="page-header__title">{SITE_NAME}</h1>
      <p class="page-header__lead">Training twice a week.</p>
    </header>
    <section class="prose" id="about"><h2>About</h2><p>We play on Sundays.</p></section>
    <section class="prose" id="contact"><h2>Contact</h2><p>Ask at the front desk.</p></section>
  </div>
</BaseLayout>
"""

FAKE_NPM = """#!/bin/sh
[ "$1" = run ] || { echo "fake npm: refused $*" >> "$FAKE_NPM_LOG"; exit 64; }
echo "$*" >> "$FAKE_NPM_LOG"
f=src/pages/index.astro
case "$2" in
  build) if grep -q BREAK_BUILD "$f"; then echo "build exploded" >&2; exit 3; fi; mkdir -p dist; echo ok > dist/index.html ;;
  check) if grep -q BAD_CHECK "$f"; then echo "Errors (1): index.html: bad" ; exit 1; fi; echo "No errors." ;;
  *) exit 65 ;;
esac
"""


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tree(root: Path, skip=("dist", ".astro", "node_modules", ".git")) -> dict:
    """{relative path: sha256 | 'link:<target>' | 'dir'} below root, symlinks never followed."""
    snap = {}
    for cur, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if d not in skip]
        for name in dirs + files:
            p = Path(cur) / name
            rel = p.relative_to(root).as_posix()
            if p.is_symlink():
                snap[rel] = "link:" + os.readlink(p)
            elif p.is_dir():
                snap[rel] = "dir"
            else:
                snap[rel] = sha(p)
    return snap


def delta(a: dict, b: dict) -> set:
    return {k for k in set(a) | set(b) if a.get(k) != b.get(k)}


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout


def clean_env(**extra):
    """Environment without PYTHONPATH and friends."""
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP")}
    env.update(extra)
    return env


class EditCase(unittest.TestCase):
    DOMAIN = "club.test"
    SCRIPT = EDIT                                      # overridden by tests that run an extracted copy

    def setUp(self):
        self.root = h.repo()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()      # TMPDIR of the helper: the backup area lives here
        self.addCleanup(shutil.rmtree, self.tmpdir, True)
        self.env = clean_env(TMPDIR=str(self.tmpdir), FAKE_NPM_LOG=str(self.tmpdir / "npm.log"))
        bin_dir = self.tmpdir / "bin"
        bin_dir.mkdir()
        self.npm = bin_dir / "npm"
        self.npm.write_text(FAKE_NPM)
        self.npm.chmod(0o755)
        self.make_site(self.DOMAIN)
        self.site = self.root / "sites" / self.DOMAIN
        self.index = self.site / "src" / "pages" / "index.astro"
        self.index.write_text(GOOD)
        git(self.root, "config", "user.email", "t@example.invalid")
        git(self.root, "config", "user.name", "t")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "fixture")
        self.rel = f"sites/{self.DOMAIN}"

    def make_site(self, domain):
        r = h.static_setup.execute(h.opts("create", domain, self.root), h.FakeRunner())
        assert r["exit"] == 0, r
        site = self.root / "sites" / domain
        (site / "node_modules").mkdir(exist_ok=True)
        (site / "package-lock.json").write_text('{"lockfileVersion": 3}\n')

    # --- process-level calls (the way a host starts the helper)
    def run_edit(self, *args, flags=("-I", "-B"), cwd=None, env=None, script=None):
        return subprocess.run([sys.executable, *flags, str(script or self.SCRIPT), *args], capture_output=True, text=True,
                              env=env or self.env, cwd=cwd)

    def edit(self, *args, check=False, **kw):
        p = self.run_edit(*args, **kw)
        try:
            data = json.loads(p.stdout)
        except ValueError:
            data = {"raw": p.stdout + p.stderr}
        if check:
            assert p.returncode == 0, (p.stdout, p.stderr)
        return p.returncode, data

    def preflight(self, *args):
        return self.edit("preflight", "--root", str(self.root), *args)

    def begin(self):
        code, d = self.edit("begin", "--root", str(self.root), "--site", self.DOMAIN, check=True)
        return d["state_folder"]

    def write(self, state, text):
        f = self.tmpdir / "content.astro"
        f.write_bytes(text if isinstance(text, bytes) else text.encode())
        return self.edit("write", "--state", state, "--content-file", str(f))

    def replace(self, state, find, new):
        return self.edit("replace", "--state", state, "--find", find, "--replace", new)

    def check(self, state, npm=None):
        return self.edit("check", "--state", state, "--npm", str(npm or self.npm))

    def finish(self, state, visual=False):
        return self.edit("finish", "--state", state, *(["--visual-done"] if visual else []))

    def npm_calls(self):
        p = Path(self.env["FAKE_NPM_LOG"])
        return p.read_text().splitlines() if p.exists() else []

    def snap(self):
        return tree(self.root)

    def state_files(self):
        """Everything below <TMPDIR>/zyris-website (the backup area); empty when it was never created."""
        area = self.tmpdir / "zyris-website"
        return tree(area) if area.exists() else {}
