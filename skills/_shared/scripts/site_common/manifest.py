"""Read and check .project/specs/website.json against the plugin's own schema (shared by preview, optimize and edit)."""
import json
from pathlib import Path

from . import schema as schemalib
from .errors import Stop

SPECS = Path(".project") / "specs"
FILE = "website.json"
SCHEMA = "website.schema.json"


def load(file: Path):
    try:
        return json.loads(file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise Stop(f"{file} is not valid JSON: {error}")


PLUGIN_SCHEMA = Path(__file__).resolve().parents[2] / "resources" / "website.schema.json"


def plugin_schema() -> dict:
    """The binding manifest contract: the plugin's own schema, never the copy a project happens to carry."""
    if not PLUGIN_SCHEMA.is_file():
        raise Stop(f"{PLUGIN_SCHEMA} is missing: the plugin installation is incomplete.")
    return load(PLUGIN_SCHEMA)


def consistency_problems(root: Path, component: dict) -> dict:
    """Version 2: manifest `domain` vs. the domain-dependent configuration (see site_common/consistency.py).
    Returns {"conflicts": [...], "unverifiable": [...]}; only reports, never repairs."""
    from . import consistency
    return consistency.check(root, component)


def require_consistent(root: Path, component: dict) -> list:
    """Stop with concrete conflicts before any change, build or process; returns the unverifiable notes for the caller to report."""
    found = consistency_problems(root, component)
    if found["conflicts"]:
        raise Stop(f"site '{component['name']}': the manifest and the site configuration contradict each other (nothing was started or written, "
                   "nothing is repaired automatically):\n  " + "\n  ".join(found["conflicts"]))
    return found["unverifiable"]


def project_schema_copy(file: Path):
    """The project's schema copy must exist and be a JSON object; it is never used to relax the plugin contract."""
    if not file.is_file():
        raise Stop(f"{file} is missing: run the `setup` skill of the Website plugin (it creates the project's schema copy). Nothing was started or written.")
    if not isinstance(load(file), dict):
        raise Stop(f"{file} is not a JSON object. Nothing was started or written.")


def problems(data, project_schema_file: Path) -> list:
    """Errors against the plugin schema (binding). The project's schema copy only has to exist and be valid JSON."""
    project_schema_copy(project_schema_file)
    errors = schemalib.validate(data, plugin_schema())
    if not errors and type(data["version"]) is not int:       # 2.0 equals 2 in Python; the manifest version is the integer 2
        errors.append("$.version: must be the integer 2 (not a float or boolean)")
    if errors:
        return errors
    names, ports, keys, domains = set(), {}, {}, {}
    for index, c in enumerate(data["components"]):
        where = f"$.components[{index}]"
        if c["name"] in names:
            errors.append(f"{where}: duplicate name '{c['name']}'")
        names.add(c["name"])
        if "port" in c:
            if c["port"] in ports:
                errors.append(f"{where}: port {c['port']} already used by '{ports[c['port']]}'")
            ports[c["port"]] = c["name"]
        if "domain" in c:
            owner = domains.setdefault(c["domain"], c["name"])
            if owner != c["name"]:
                errors.append(f"{where}: domain '{c['domain']}' already belongs to '{owner}'")
        for key in [c["name"], *c.get("aliases", [])]:
            owner = keys.setdefault(key.lower(), c["name"])
            if owner != c["name"]:
                errors.append(f"{where}: '{key}' is already a name or alias of '{owner}'")
    return errors
