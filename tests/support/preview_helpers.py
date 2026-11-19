"""Paths, imports and fictional project fixtures for the tests of the `preview` skill.

Importing this module makes the skill's flat script modules (`control`, `preview`) and the shared package `site_common`
importable in-process (the same sys.path layout the scripts build for themselves). Only fictional sites; no real site
names, contents or manifests.
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT                                         # the repository root is the plugin root
SKILL = ROOT / "skills" / "preview"
PY = SKILL / "scripts"
RES = SKILL / "templates"
SHARED_SCRIPTS = ROOT / "skills" / "_shared" / "scripts"
SCHEMA_FILE = ROOT / "skills" / "_shared" / "resources" / "website.schema.json"
CONTROL = PY / "control.py"
PREVIEW = PY / "preview.py"
for _p in (str(SHARED_SCRIPTS), str(PY)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _site(name, **extra):
    return {"name": name, "path": f"sites/{name}", "type": "astro-static", **extra}


_static = _site


def _removed_type_site(name, **extra):
    """A component of the removed Docker/Caddy type: every skill must reject it, none translates it."""
    return {"name": name, "path": f"sites/{name}", "type": "astro", "serve": {"mode": "behind-proxy", "network": "public"}, **extra}


TWO_SITES = {"version": 1, "components": [
    _site("alpha.example", title="Alpha Example", aliases=["first", "alpha"], port=4321),
    _site("beta.example"),
]}
ONE_SITE = {**TWO_SITES, "components": TWO_SITES["components"][:1]}
MIXED = {"version": 1, "components": [
    _site("alpha.example", title="Alpha Example", aliases=["first"], port=4321),
    _static("static.example", title="Static Example", aliases=["stat"], port=4322),
]}
STATIC_ONLY = {"version": 1, "components": [_static("static.example", port=4322)]}


def make_repo(manifest=TWO_SITES, sites=("alpha.example", "beta.example"), schema_text=None) -> Path:
    """Temp website project: manifest, the project's copy of the current schema and empty site folders."""
    root = Path(tempfile.mkdtemp()).resolve()
    specs = root / ".project" / "specs"
    specs.mkdir(parents=True)
    (specs / "zyris-website.json").write_text(json.dumps(manifest))
    (specs / "website.schema.json").write_text(SCHEMA_FILE.read_text() if schema_text is None else schema_text)
    for s in sites:
        (root / "sites" / s).mkdir(parents=True)
    return root
