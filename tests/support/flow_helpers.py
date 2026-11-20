"""Fictional projects and documents for the guided-flow tests."""
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from tests.support import setup_paths as sp
from tests.support import setup_helpers as h
import static_setup
from site_common import flowstate

FLOW = sp.ROOT / "skills/_shared/scripts/flow.py"
SITE = "physio-wien"


def project(domain="demo-a.com", create=True):
    root = Path(tempfile.mkdtemp()).resolve()
    if create:
        result = static_setup.execute(h.opts("create", SITE, root, domain=domain), h.FakeRunner())
        assert result["state"] == "created", result
    return root


def field(value, status="confirmed"):
    return {"value": value, "status": status}


def brief(**override):
    fields = {
        "purpose": field("Praxis-Website mit Terminanfrage"), "audience": field("Berufstätige mit Rückenschmerzen in Wien"),
        "offer": field("Physiotherapie und Rückenkurse"), "message": field("Beweglich bleiben, im eigenen Tempo"),
        "visitor_action": field("Termin anfragen"), "tone": field("ruhig, klar, persönlich"), "site_language": field("de"),
        "design_direction": field("hell, großzügig, medizinisch-freundlich"),
        "palette": field({"name": "Salbei", "colors": {"primary": "#2f6f5e", "background": "#f6f8f5", "accent": "#d98c3f"},
                          "rationale": "Ruhe und Vertrauen, guter Kontrast"}),
    }
    fields.update(override)
    return {"schema_version": 1, "fields": fields,
            "palette_proposals": [{"name": "Salbei", "colors": {"primary": "#2f6f5e", "background": "#f6f8f5"}, "rationale": "ruhig"}]}


def page_a(extra="", lang="de", primary="#2f6f5e"):
    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><title>Entwurf A</title>
<style>:root{{--primary:{primary};--bg:#f6f8f5}}body{{background:var(--bg);font-family:system-ui}}header{{display:flex}}</style></head>
<body><header><nav><a href="#kontakt">Kontakt</a></nav></header>
<main><section><h1>Beweglich bleiben, im eigenen Tempo</h1><p>Physiotherapie und Rückenkurse in Wien.</p>
<p><a href="#kontakt">Termin anfragen</a></p></section>
<section><h2>Angebot</h2><ul><li>Physiotherapie</li><li>Rückenkurse</li></ul></section>
<section id="kontakt"><h2>Kontakt</h2><p data-open-fact>Adresse und Telefon: offene Angabe</p></section>{extra}</main>
<footer><p>Praxis in Wien</p></footer></body></html>
"""


def page_b(extra="", lang="de", primary="#2f6f5e"):
    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><title>Entwurf B</title>
<style>:root{{--primary:{primary}}}body{{display:grid;grid-template-columns:18rem 1fr}}aside{{background:var(--primary);color:#fff}}</style></head>
<body><aside><nav><ul><li>Start</li><li>Angebot</li><li>Kontakt</li></ul></nav></aside>
<main><article><h1>Rückenkurse und Physiotherapie in Wien</h1><blockquote>Im eigenen Tempo.</blockquote></article>
<article><h2>Termin</h2><form><p>Terminanfrage folgt</p></form></article>
<article><h2>Über die Praxis</h2><p data-open-fact>Qualifikationen der Therapeutin: offene Angabe</p></article>
<figure><p>Bild folgt</p></figure>{extra}</main></body></html>
"""


def write_variants(root, revision, a=None, b=None, names=("A", "B")):
    folder = root / ".project/website" / SITE / "design" / f"r{revision:03d}"
    folder.mkdir(parents=True, exist_ok=True)
    pages = {"A": a if a is not None else page_a(), "B": b if b is not None else page_b()}
    for name in names:
        (folder / f"{name}.html").write_text(pages.get(name, page_a()), encoding="utf-8")
    return folder


def confirmed_project(domain="demo-a.com"):
    root = project(domain)
    flowstate.brief_save(root, SITE, brief())
    flowstate.brief_confirm(root, SITE, "Ja, das Briefing passt so.")
    return root


def with_variants(domain="demo-a.com"):
    root = confirmed_project(domain)
    flowstate.design_new(root, SITE)
    write_variants(root, 1)
    flowstate.design_register(root, SITE, 1)
    return root


def approved_project():
    root = with_variants()
    flowstate.design_approve(root, SITE, 1, "B", "Ja, Revision 1 Variante B setzen wir so um.")
    return root


def index_path(root):
    return root / "sites" / SITE / "src/pages/index.astro"


def cli(root, *args, tmp=None):
    import os
    env = {**os.environ, "TMPDIR": str(tmp)} if tmp else None
    done = subprocess.run([sys.executable, "-I", "-B", str(FLOW), *args, "--root", str(root)], capture_output=True, text=True, timeout=60, env=env)
    return done.returncode, done.stdout + done.stderr


def use_edit_tmp(case):
    """Give the test its own TMPDIR, as the edit skill keeps its sessions below it; the process and the edit subprocesses agree on it."""
    import os
    import shutil
    import tempfile as tf
    if getattr(case, "_edit_tmp", None):
        return case._edit_tmp
    tmp = Path(tf.mkdtemp()).resolve()
    old = tf.tempdir
    tf.tempdir = str(tmp)
    case._edit_tmp = tmp

    def restore():
        tf.tempdir = old
        shutil.rmtree(tmp, True)
    case.addCleanup(restore)
    return tmp


def edit_session(case, root, append=None, write=True, check=False):
    """A REAL edit session: `edit.py begin`, then (optionally) `edit.py write` of the current page plus `append`. Returns the state folder."""
    import json as js
    import os
    tmp = use_edit_tmp(case)
    site = root / "sites" / SITE
    (site / "node_modules").mkdir(exist_ok=True)
    if not (site / "package-lock.json").exists():
        (site / "package-lock.json").write_text('{"lockfileVersion": 3}\n')
    env = {"PATH": "/usr/bin:/bin", "TMPDIR": str(tmp)}
    script = sp.ROOT / "skills/edit/scripts/edit.py"

    def call(*args):
        done = subprocess.run([sys.executable, "-I", "-B", str(script), *args], capture_output=True, text=True, env=env, timeout=60)
        assert done.returncode == 0, (args, done.stdout, done.stderr)
        return js.loads(done.stdout)
    folder = call("begin", "--root", str(root), "--site", SITE)["state_folder"]
    if write:
        content = tmp / "content.astro"
        content.write_text(index_path(root).read_text() + (append or "\n<!-- design implemented -->\n"))
        call("write", "--state", folder, "--content-file", str(content))
    if check:        # a check-only session: the fake npm stands in for build and check
        from tests.support.edit_helpers import FAKE_NPM
        npm = tmp / "bin" / "npm"
        npm.parent.mkdir(exist_ok=True)
        npm.write_text(FAKE_NPM)
        npm.chmod(0o755)
        env["FAKE_NPM_LOG"] = str(tmp / "npm.log")
        call("check", "--state", folder, "--npm", str(npm))
    return folder
