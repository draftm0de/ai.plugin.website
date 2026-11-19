"""Fixtures for the manifest-contract tests of the skill entry points (setup now; preview/optimize/edit in later stages).

The plugin's own schema (skills/_shared/resources/website.schema.json) is the binding contract. These helpers
build temporary projects whose manifest and *project schema copy* try to relax it, and run the real entry points on them.
"""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPTS = PLUGIN / "skills"
CURRENT_SCHEMA = PLUGIN / "skills" / "_shared" / "resources" / "website.schema.json"
OLDER_SCHEMA = PLUGIN / "tests" / "fixtures" / "setup" / "schema-foreign-older.json"     # an older foreign schema (type astro, serve required)
SITE = "site.example"

_spec = importlib.util.spec_from_file_location("zw_schema_for_tests", PLUGIN / "skills" / "_shared" / "scripts" / "site_common" / "schema.py")
schemalib = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(schemalib)


def good_manifest(**component):
    return {"version": 1, "components": [{"name": SITE, "path": f"sites/{SITE}", "type": "astro-static", "port": 4500, **component}]}


def old_manifest():
    """What HEAD 810e48c held for draftmode.io: the removed type with serve, plus registry and retention."""
    return {"version": 1, "registry": "ghcr.io", "retention": {"registry": 5, "server": 2}, "components": [
        {"name": SITE, "path": f"sites/{SITE}", "type": "astro", "port": 4500, "environment": "production",
         "serve": {"mode": "behind-proxy", "network": "public"}}]}


def loosened_schema_text():
    """The current schema made permissive: accepts astro and hugo and the removed fields."""
    schema = json.loads(CURRENT_SCHEMA.read_text())
    schema["properties"]["registry"] = {"type": "string"}
    schema["properties"]["retention"] = {"type": "object"}
    component = schema["$defs"]["component"]["properties"]
    component["type"] = {"enum": ["astro", "astro-static", "hugo"]}
    component["serve"] = {"type": "object"}
    component["dockerfile"] = {"type": "string"}
    return json.dumps(schema, indent=2) + "\n"


def accepted_by(schema_text, manifest):
    """True when the (relaxed) schema alone would let the manifest through: proves a test is not vacuous."""
    return schemalib.validate(manifest, json.loads(schema_text)) == []


def rejected_by_plugin_contract(manifest):
    return schemalib.validate(manifest, json.loads(CURRENT_SCHEMA.read_text())) != []


def with_top(manifest, **top):
    return {**manifest, **top}


# (label, manifest, project schema text): every one must be refused by every consumer.
def refusal_cases():
    loose = loosened_schema_text()
    cases = [
        ("old manifest + old project schema", old_manifest(), OLDER_SCHEMA.read_text()),
        ("old manifest + current schema", old_manifest(), CURRENT_SCHEMA.read_text()),
        ("type astro + loosened schema", good_manifest(type="astro"), loose),
        ("type hugo + loosened schema", good_manifest(type="hugo"), loose),
        ("removed field serve + loosened schema", good_manifest(serve={"mode": "behind-proxy", "network": "public"}), loose),
        ("removed field dockerfile + loosened schema", good_manifest(dockerfile="Dockerfile"), loose),
        ("removed field registry + loosened schema", with_top(good_manifest(), registry="ghcr.io"), loose),
        ("removed field retention + loosened schema", with_top(good_manifest(), retention={"registry": 5}), loose),
    ]
    for label, manifest, schema_text in cases:
        assert rejected_by_plugin_contract(manifest), label
        if "loosened" in label:
            assert accepted_by(schema_text, manifest), label        # the relaxed project schema alone would have accepted it
    return cases


def make_project(manifest, schema_text, with_site=True, package_scripts=None):
    root = Path(tempfile.mkdtemp()).resolve()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    specs = root / ".project" / "specs"
    specs.mkdir(parents=True)
    (specs / "zyris-website.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if schema_text is not None:
        (specs / "website.schema.json").write_text(schema_text)
    if with_site:
        site = root / "sites" / SITE
        (site / "src" / "pages").mkdir(parents=True)
        scripts = {"build": "astro build", "check": "echo ok"} if package_scripts is None else package_scripts
        (site / "package.json").write_text(json.dumps({"name": SITE, "version": "1.0.0", "scripts": scripts}) + "\n")
        (site / ".gitignore").write_text("dist/\n.astro/\nnode_modules/\n")
        (site / "node_modules").mkdir()
        (site / "package-lock.json").write_text("{}\n")
    git = ["git", "-c", "user.email=t@example.invalid", "-c", "user.name=t"]
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(git + ["commit", "-q", "-m", "fixture"], cwd=root, check=True)       # audits need a committed tree
    return root


def snapshot(root):
    result = {}
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in dirs + files:
            path = Path(current) / name
            rel = path.relative_to(root).as_posix()
            result[rel] = "dir" if path.is_dir() else hashlib.sha256(path.read_bytes()).hexdigest()
    return result


class Sandbox:
    """A fake npm that only records its calls, a private state dir and an environment for the real entry points."""

    def __init__(self):
        self.dir = Path(tempfile.mkdtemp()).resolve()
        self.bin = self.dir / "bin"
        self.bin.mkdir()
        self.log = self.dir / "npm-calls.log"
        npm = self.bin / "npm"
        npm.write_text('#!/bin/sh\necho "$@" >> "%s"\ncase "$*" in *build*) mkdir -p dist ;; esac\nexit 0\n' % self.log)
        npm.chmod(0o755)
        self.state = self.dir / "state"
        self.state.mkdir()
        self.env = {**os.environ, "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}", "ZYRIS_WEBSITE_STATE_DIR": str(self.state)}

    def run(self, script, *argv, cwd=None):
        result = subprocess.run([sys.executable, str(SCRIPTS / script), *argv], cwd=cwd, env=self.env, capture_output=True, text=True)
        return result.returncode, result.stdout + result.stderr

    def npm_calls(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def state_files(self):
        return sorted(p.name for p in self.state.rglob("*"))
