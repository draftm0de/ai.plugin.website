"""Paths and imports for the tests of the `setup` skill. Importing this module makes the skill's flat script modules and the
shared package `site_common` importable in-process (same sys.path layout as site_setup.py builds for itself)."""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT                                        # the repository root is the plugin root
SKILL = ROOT / "skills" / "setup"
PY = SKILL / "scripts"
RES = SKILL / "templates"
SHARED_SCRIPTS = ROOT / "skills" / "_shared" / "scripts"
SCHEMA_FILE = ROOT / "skills" / "_shared" / "resources" / "website.schema.json"
OLDER_SCHEMA = ROOT / "tests" / "fixtures" / "setup" / "schema-foreign-older.json"
SITE_SCRIPT = PY / "site_setup.py"
for _p in (str(SHARED_SCRIPTS), str(PY)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def make_repo(remote="https://github.com/Acme/Sites.git") -> Path:
    root = Path(tempfile.mkdtemp())
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "remote", "add", "origin", remote], cwd=root, check=True)
    return root
