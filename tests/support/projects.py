"""Fictional website-project fixtures for the shared-module tests. No real site names or contents."""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "skills" / "_shared"
SCHEMA_FILE = SHARED / "resources" / "website.schema.json"
OLDER_SCHEMA = ROOT / "tests" / "fixtures" / "shared" / "schema-foreign-older.json"
SITE = "alpha.example"


def use_shared_scripts():
    """Make `site_common` importable from the repository's shared runtime (in-process tests only)."""
    path = str(SHARED / "scripts")
    if path not in sys.path:
        sys.path.insert(0, path)


def component(name, **extra):
    return {"name": name, "path": f"sites/{name}", "type": "astro-static", **extra}


TWO_SITES = {"version": 2, "components": [
    component("alpha.example", title="Alpha Example", aliases=["first", "alpha"], port=4321),
    component("beta.example"),
]}
ONE_SITE = {"version": 2, "components": TWO_SITES["components"][:1]}


def make_project(manifest=TWO_SITES, sites=("alpha.example", "beta.example"), schema_text="current"):
    """Temp project with manifest, project schema copy (current by default, None = absent) and site folders."""
    root = Path(tempfile.mkdtemp()).resolve()
    specs = root / ".project" / "specs"
    specs.mkdir(parents=True)
    (specs / "zyris-website.json").write_text(json.dumps(manifest))
    if schema_text == "current":
        schema_text = SCHEMA_FILE.read_text()
    if schema_text is not None:
        (specs / "website.schema.json").write_text(schema_text)
    for name in sites:
        (root / "sites" / name).mkdir(parents=True)
    return root


def loosened_schema_text():
    """The plugin schema made permissive: accepts astro/hugo and the removed fields."""
    schema = json.loads(SCHEMA_FILE.read_text())
    schema["properties"]["registry"] = {"type": "string"}
    schema["properties"]["retention"] = {"type": "object"}
    props = schema["$defs"]["component"]["properties"]
    props["type"] = {"enum": ["astro", "astro-static", "hugo"]}
    props["serve"] = {"type": "object"}
    props["dockerfile"] = {"type": "string"}
    return json.dumps(schema, indent=2) + "\n"


def tree_snapshot(root):
    import hashlib
    result = {}
    for current, dirs, files in os.walk(root):
        for name in dirs + files:
            path = Path(current) / name
            rel = path.relative_to(root).as_posix()
            result[rel] = "dir" if path.is_dir() else hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def copy_shared_to_spaced_dir():
    """Extracted-copy stand-in: only skills/_shared, under a path with spaces. Returns (copy_root, shared_dir)."""
    base = Path(tempfile.mkdtemp()).resolve() / "My Plugin Copy" / "skills"
    base.mkdir(parents=True)
    shutil.copytree(SHARED, base / "_shared", ignore=shutil.ignore_patterns("__pycache__"))
    return base.parent, base / "_shared"


def clean_env(**extra):
    """Environment without PYTHONPATH (and without any checkout hint)."""
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP")}
    env.update(extra)
    return env
