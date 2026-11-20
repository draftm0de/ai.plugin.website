"""The generated plugin package (Claude and Codex payload, built by scripts/plugin.py) carries the skeleton templates, including the
dot-named ones, and `setup` runs from the package alone (fictional project, fake npm, no network, no git)."""
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("website_plugin_tool", ROOT / "scripts/plugin.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

TEMPLATES = ROOT / "skills/setup/templates/astro-static"
DOT_TEMPLATES = {".gitignore.tpl", "public/.gitkeep"}
FAKE_NPM = """#!/bin/sh
case "$1" in
  install) echo '{"fake": true}' > package-lock.json; mkdir -p node_modules ;;
  run) if [ "$2" = build ]; then mkdir -p dist; echo '<html></html>' > dist/index.html; fi ;;
esac
exit 0
"""


def write_package(files, target):
    for name, data in files.items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _version, portable, claude = tool.payload()
        cls.packages = {"claude": claude, "codex": tool.codex_payload(portable)}

    def test_dot_named_template_files_are_in_both_packages(self):
        for host, files in self.packages.items():
            for rel in DOT_TEMPLATES:
                self.assertIn(f"skills/setup/templates/astro-static/{rel}", files, (host, rel))
                self.assertEqual(files[f"skills/setup/templates/astro-static/{rel}"], (TEMPLATES / rel).read_bytes(), (host, rel))

    def test_template_tree_of_the_package_equals_the_source_tree(self):
        source = {p.relative_to(ROOT).as_posix() for p in (ROOT / "skills/setup/templates").rglob("*") if p.is_file()}
        for host, files in self.packages.items():
            packaged = {n for n in files if n.startswith("skills/setup/templates/")}
            self.assertEqual(packaged, source, host)

    def test_private_and_generated_files_stay_out_of_the_package(self):
        for host, files in self.packages.items():
            for name in files:
                parts = Path(name).parts
                self.assertFalse(any(p.startswith(".env") for p in parts), name)
                self.assertNotIn("__pycache__", parts, name)
                self.assertFalse(name.endswith((".pyc", ".pem", ".key")), name)
                if any(p.startswith(".") for p in parts):
                    self.assertIn(parts[0], {".claude-plugin", ".codex-plugin"}.union({"skills"}), name)
                    if parts[0] == "skills":
                        self.assertIn(parts[-1], {".gitignore.tpl", ".gitkeep"}, name)

    def test_setup_runs_from_the_package_and_creates_the_skeleton(self):
        for host, files in self.packages.items():
            with self.subTest(host=host), tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp).resolve()
                package, project, fakebin = tmp / "package with space", tmp / "project", tmp / "bin"
                write_package(files, package)
                project.mkdir()
                fakebin.mkdir()
                npm = fakebin / "npm"
                npm.write_text(FAKE_NPM)
                npm.chmod(npm.stat().st_mode | stat.S_IXUSR)
                env = {"PATH": f"{fakebin}:/usr/bin:/bin", "HOME": str(tmp)}
                script = package / "skills/setup/scripts/site_setup.py"
                done = subprocess.run([sys.executable, "-I", "-B", str(script), "create", "physio-wien", "--type", "astro-static",
                                       "--domain", "demo-a.com", "--root", str(project), "--build", "--json"],
                                      capture_output=True, text=True, env=env, cwd=tmp, timeout=120)
                result = json.loads(done.stdout)
                self.assertEqual((done.returncode, result["state"]), (0, "created"), done.stdout + done.stderr)
                self.assertEqual({k: v["exit"] for k, v in result["verification"].items()}, {"install": 0, "build": 0, "check": 0})
                site = project / "sites/physio-wien"
                self.assertTrue((site / ".gitignore").is_file())
                ignore = (site / ".gitignore").read_text()
                for entry in ("dist", "node_modules", ".astro"):
                    self.assertIn(entry, ignore)
                self.assertTrue((site / "public/.gitkeep").is_file())
                manifest = json.loads((project / ".project/specs/zyris-website.json").read_text())
                self.assertEqual(manifest["version"], 2)
                self.assertEqual(manifest["components"][0]["domain"], "demo-a.com")
                record = json.loads((project / ".project/specs/zyris-website.managed.json").read_text())
                self.assertIn(".gitignore", record["sites"]["physio-wien"]["files"])
                self.assertFalse((project / ".git").exists())                 # local work needs no git
                self.assertEqual(list(package.rglob("__pycache__")), [])        # the package stayed untouched


class PrivateFilesTests(unittest.TestCase):
    def test_private_file_in_a_distributable_source_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            skill = root / "skills/example"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: example\ndescription: Fictional.\n---\n# Example\n")
            (skill / ".env.local").write_text("TOKEN=fictional\n")
            (root / "plugin.json").write_text(json.dumps({"name": "fixture", "description": "Fictional",
                                                          "extensions": {"io.zyris.distribution": {"skillRoot": "skills", "catalogs": False}}}))
            original = tool.ROOT
            tool.ROOT = root
            try:
                with self.assertRaisesRegex(ValueError, "Private file"):
                    tool.payload()
            finally:
                tool.ROOT = original


if __name__ == "__main__":
    unittest.main()
