"""Helpers for the static setup tests: temporary repositories (no origin), snapshots, fake runner."""
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

from tests.support import setup_paths as helpers
import static_setup  # noqa: E402  (importable after setup_paths)

SCHEMA_FOREIGN = helpers.OLDER_SCHEMA   # a schema copy that is not the plugin schema (older, foreign): never replaced automatically
SITE_GITIGNORE = "dist/\n.astro/\nnode_modules/\n"


def repo() -> Path:
    """Temporary git repository WITHOUT an origin remote."""
    root = Path(tempfile.mkdtemp()).resolve()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    return root


def snapshot(root: Path) -> dict:
    """Everything below root except .git: {relative path: sha256 | 'dir' | 'link:<target>'} plus mode-less content."""
    result = {}
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if not (Path(current) == root and d == ".git")]
        for name in dirs + files:
            path = Path(current) / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                result[rel] = "link:" + os.readlink(path)
            elif path.is_dir():
                result[rel] = "dir"
            else:
                result[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def sub(snap: dict, prefix: str) -> dict:
    return {k: v for k, v in snap.items() if k == prefix or k.startswith(prefix + "/")}


def opts(operation, domain="example.com", root=None, **kw):
    kw.setdefault("site_type", "astro-static" if operation == "create" else None)
    return static_setup.Options(operation=operation, domain=domain, root=str(root), **kw)


def manifest_of(root: Path) -> dict:
    return json.loads((root / ".project" / "specs" / "zyris-website.json").read_text())


def record_of(root: Path) -> dict:
    return json.loads((root / ".project" / "specs" / "zyris-website.managed.json").read_text())


def make_static_site(root: Path, domain="adopted.example", scripts=None, gitignore=SITE_GITIGNORE, extra=None):
    """An existing static Astro folder as a person would have it (no Docker files, not from the template)."""
    site = root / "sites" / domain
    (site / "src" / "pages").mkdir(parents=True)
    scripts = {"build": "astro build", "check": "echo ok"} if scripts is None else scripts
    (site / "package.json").write_text(json.dumps({"name": domain, "version": "1.0.0", "scripts": scripts}, indent=2) + "\n")
    (site / ".gitignore").write_text(gitignore)
    (site / "src" / "pages" / "index.astro").write_text("<h1>Hello</h1>\n")
    (site / "astro.config.mjs").write_text("export default { site: 'https://" + domain + "' };\n")
    for rel, text in (extra or {}).items():
        (site / rel).parent.mkdir(parents=True, exist_ok=True)
        (site / rel).write_text(text)
    return site


class FakeRunner:
    """Replaces npm. results: {'install'|'build'|'check': (ran, exit, output)}. A passing build creates dist/."""
    NAMES = {"npm install": "install", "npm run build": "build", "npm run check": "check"}

    def __init__(self, **results):
        self.results, self.calls = results, []

    def __call__(self, argv, cwd):
        name = self.NAMES[" ".join(argv)]
        self.calls.append((name, Path(cwd)))
        ran, code, out = self.results.get(name, (True, 0, f"{name} ok"))
        if name == "build" and ran and code == 0:
            (Path(cwd) / "dist").mkdir(exist_ok=True)
            (Path(cwd) / "dist" / "index.html").write_text("<html></html>")
        if name == "install" and ran and code == 0:
            (Path(cwd) / "node_modules").mkdir(exist_ok=True)
            (Path(cwd) / "package-lock.json").write_text('{"fake": true}\n')
        return ran, code, out


class NoRun:
    """Runner that fails the test when it is called (plan must never install or build)."""
    def __call__(self, argv, cwd):
        raise AssertionError(f"command must not run: {argv}")
