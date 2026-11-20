"""Paths, imports and deterministic fixtures for the tests of the `optimize` skill.

Importing this module makes the skill's flat script modules (`audit`, `findings`, `store`, `worklist`) and the shared package
`site_common` importable in-process (the same sys.path layout `audit.py` builds for itself).

`AuditCase` creates a throw-away git repository with a fictional site whose `build`, `seo:check` and `a11y:check` are tiny shell
scripts. They mimic the *output format* of the check scripts that `setup` ships (`skills/setup/templates/astro-static/scripts/`;
see `tests/contracts/test_optimize_contract.py` for the comparison with those templates) and read `src/content.json`, so defects and
fixes are injected by editing that file. A fake `npm` (outside the repository) runs `fx/<script>.sh` and logs every call; it refuses
`install`, `ci` and everything else but `run`. No real website, no real npm, no network.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT                                          # the repository root is the plugin root
SKILL = ROOT / "skills" / "optimize"
PY = SKILL / "scripts"
AUDIT = PY / "audit.py"
SHARED = ROOT / "skills" / "_shared"
SHARED_SCRIPTS = SHARED / "scripts"
SCHEMA_FILE = SHARED / "resources" / "website.schema.json"
for _p in (str(SHARED_SCRIPTS), str(PY)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

LONG = "A concrete description of the home page that is long enough to satisfy the guideline of one hundred twenty characters."
SHORT_A = "Short one."
SHORT_B = "Also short text here."
GOOD_A = "Metrics for service A: exposes runtime state so monitoring systems can collect it and dashboards can chart it over time."
TZ = timezone(timedelta(hours=1))
COMPONENT = {"name": "fx.test", "path": "sites/fx.test", "type": "astro-static", "title": "fx.test", "aliases": []}

FILES = {
    "fx/build.sh": 'if [ -f src/MUTATE ]; then echo x >> src/touched.txt; fi\n'
                   'if [ -f src/CREATE ]; then echo x > src/created-by-build.txt; fi\n'
                   'if [ -f src/BREAK ]; then echo "build exploded" >&2; exit 3; fi\n'
                   'if [ -f src/LEAK ]; then echo "TOKEN=abc123secret"; fi\n'
                   'mkdir -p dist && cp src/content.json dist/content.json && echo built\n',
    "fx/seo-check.sh": "exec python3 fx/seo.py\n",
    "fx/a11y-check.sh": "exec python3 fx/a11y.py\n",
    "fx/seo.py": '''import json, os, sys
pages = json.load(open("dist/content.json"))
if os.path.exists("src/GARBLE_SEO"):
    print("something else entirely"); sys.exit(0)
errs, warns = [], []
for p in pages:
    d = p.get("description")
    if not d: errs.append(f"{p['url']}: missing meta description")
    elif len(d) > 160: warns.append(f"{p['url']}: description is {len(d)} chars (max 160)")
    elif len(d) < 70: warns.append(f"{p['url']}: description is short ({len(d)}, aim for 120 to 160)")
print(f"Checked {len(pages)} pages.")
if warns: print(f"\\nWarnings ({len(warns)}):\\n- " + "\\n- ".join(warns))
if errs:
    print(f"\\nErrors ({len(errs)}):\\n- " + "\\n- ".join(errs)); sys.exit(1)
print("\\nNo errors.")
''',
    "fx/a11y.py": '''import json, sys
pages = json.load(open("dist/content.json"))
errs = [f"{p['url']}: image without alt: <img src=\\"x.png\\">" for p in pages if p.get("alt_missing")]
print(f"Checked {len(pages)} pages for accessibility.")
if errs:
    print(f"\\nErrors ({len(errs)}):\\n- " + "\\n- ".join(errs)); sys.exit(1)
print("\\nNo errors. (Contrast, keyboard use and screen reader output still need a manual check.)")
''',
}


def content(**overrides):
    pages = [{"url": "/", "description": LONG}, {"url": "/a.html", "description": SHORT_A}, {"url": "/b.html", "description": SHORT_B}]
    pages = overrides.get("pages", pages)
    return json.dumps(pages, indent=1) + "\n"


def sh(cwd, *args):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout


def clean_env(**extra):
    """Environment without PYTHONPATH (and without any checkout hint)."""
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP")}
    env.update(extra)
    return env


class AuditCase(unittest.TestCase):
    """Creates the fixture repo and a fake npm; gives helpers for reading state."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = self.tmp / "repo"
        self.root.mkdir()
        site = self.root / "sites" / "fx.test"
        for rel, text in FILES.items():
            (site / rel).parent.mkdir(parents=True, exist_ok=True)
            (site / rel).write_text(text)
        (site / "src").mkdir(exist_ok=True)
        (site / "src" / "content.json").write_text(content())
        (site / "src" / "touched.txt").write_text("")
        (site / "package.json").write_text(json.dumps({"name": "fx", "scripts": {"build": "x", "seo:check": "x", "a11y:check": "x"}}))
        (site / "package-lock.json").write_text("{}\n")
        (site / ".gitignore").write_text("dist/\nnode_modules/\n.astro/\n")
        (site / "node_modules").mkdir()
        specs = self.root / ".project" / "specs"
        specs.mkdir(parents=True)
        (specs / "website.json").write_text(json.dumps({"version": 2, "components": [{"name": "fx.test", "path": "sites/fx.test", "type": "astro-static"}]}))
        (specs / "website.schema.json").write_text(SCHEMA_FILE.read_text())
        sh(self.root, "git", "init", "-q", "-b", "main")
        sh(self.root, "git", "config", "user.email", "t@example.invalid")
        sh(self.root, "git", "config", "user.name", "t")
        sh(self.root, "git", "add", "-A")
        sh(self.root, "git", "commit", "-q", "-m", "fixture")
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        self.log = self.tmp / "npm.log"
        self.npm = bin_dir / "npm"
        self.npm.write_text('#!/bin/sh\n[ "$1" = run ] || { echo "fake npm: refused $*" >> "$FAKE_NPM_LOG"; echo "fake npm: refused $*" >&2; exit 64; }\n'
                            'echo "$*" >> "$FAKE_NPM_LOG"\ns=$(echo "$2" | tr : -)\nexec sh "./fx/$s.sh"\n')
        self.npm.chmod(0o755)
        patcher = mock.patch.dict(os.environ, {"FAKE_NPM_LOG": str(self.log)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.site = site
        self.t = datetime(2026, 11, 17, 14, 44, 0, tzinfo=TZ)

    # --- helpers
    def now(self, minutes=0):
        return self.t + timedelta(minutes=minutes)

    def audit(self, minutes=0, **kw):
        import audit
        return audit.do_audit(self.root, COMPONENT, npm=str(self.npm), now=self.now(minutes), **kw)

    def decide(self, ids, status, minutes=0, **kw):
        import audit
        return audit.do_decide(self.root, COMPONENT, ids, status, now=self.now(minutes), **kw)

    def apply(self, ids, minutes=0, **kw):
        import audit
        return audit.do_apply(self.root, COMPONENT, ids, npm=str(self.npm), now=self.now(minutes), **kw)

    def state(self):
        import store
        import worklist
        text, _ = store.read_worklist(self.root, "fx.test")
        return worklist.parse(text, "fx.test")

    def finding(self, fid):
        return next(f for f in self.state()["findings"] if f["id"] == fid)

    def npm_calls(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def set_content(self, pages, commit=False):
        (self.site / "src" / "content.json").write_text(json.dumps(pages, indent=1) + "\n")
        if commit:
            sh(self.root, "git", "commit", "-qam", "content")

    def tracked_hashes(self):
        import audit
        return audit.source_state(self.root, ".project/reports/")["hashes"]

    def reports(self):
        d = self.root / ".project" / "reports" / "fx.test" / "optimize"
        return sorted(p.name for p in d.glob("*.md")) if d.is_dir() else []

    def proposal_for(self, text_new, old=SHORT_A):
        return {"summary": "Rewrite the description", "kind": "draft", "current": old, "proposed": text_new,
                "edit": {"file": "sites/fx.test/src/content.json", "find": f'"description": "{old}"', "replace": f'"description": "{text_new}"'}}

    def cli(self, *args, cwd=None, env=None):
        """Run the real entry point `audit.py` as a process against the fixture repository."""
        done = subprocess.run([sys.executable, "-B", str(AUDIT), "--root", str(self.root), *args], capture_output=True, text=True,
                              cwd=cwd or self.tmp, env=env or os.environ.copy())
        return done.returncode, done.stdout + done.stderr
