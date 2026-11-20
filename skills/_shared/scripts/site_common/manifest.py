"""Read and check .project/specs/zyris-website.json against the plugin's own schema (shared by preview, optimize and edit)."""
import json
import posixpath
from pathlib import Path

from . import schema as schemalib
from .errors import Stop

SPECS = Path(".project") / "specs"
FILE = "zyris-website.json"
SCHEMA = "website.schema.json"
LEGACY_SCHEMA = "zyris-website.schema.json"   # former name; only recognised to reject the old format, never read or used


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


def is_legacy_reference(value) -> bool:
    """True if `$schema` is a local relative spelling of the former schema file in the manifest's own folder:
    `zyris-website.schema.json`, `./zyris-website.schema.json`, `././x`, `.//x`, `a/../x`. Purely textual: nothing is fetched or read.
    Not matched: URLs (anything with a scheme), absolute paths, paths into other folders (`../x`, `sub/x`), other file names."""
    if not isinstance(value, str) or "://" in value or value.startswith(("/", "\\")) or ":" in value.split("/")[0]:
        return False
    return posixpath.normpath(value) == LEGACY_SCHEMA


def legacy_problem(specs_dir: Path, data=None):
    """Concrete diagnosis if the project is in the former format (schema file `zyris-website.schema.json`), else None.
    Recognised: the manifest still references the former schema file, or only the former schema copy exists next to a manifest
    without the current copy. There is no fallback, alias or migration; nothing is read from, written to or removed from the old file."""
    if isinstance(data, dict) and is_legacy_reference(data.get("$schema")):
        return (f"the manifest references the former schema file '{data['$schema']}' (old project format). "
                f"This plugin uses './{SCHEMA}'; there is no automatic migration and no fallback. Nothing was started or written. "
                "Convert the project yourself (schema copy and `$schema` reference) or keep using the old tooling.")
    if (specs_dir / LEGACY_SCHEMA).exists() and not (specs_dir / SCHEMA).exists():
        return (f"{specs_dir / LEGACY_SCHEMA} exists but {specs_dir / SCHEMA} does not (old project format). "
                "There is no automatic migration and no fallback to the old file. Nothing was started or written; "
                "the old file was left as it is. Convert the project yourself.")
    return None


def version_problem(data):
    """Version 1 manifests (name = domain, no `domain` field) are refused with a diagnosis; nothing is migrated or inferred."""
    if isinstance(data, dict) and data.get("version") == 1:
        return ("the manifest has version 1 (former project format). This plugin uses version 2: `name` is the stable site ID and "
                "the optional `domain` is the public domain (missing = not decided yet). Version 1 is not migrated, `domain` is never "
                "taken from `name`, `site.ts` or `astro.config.mjs`. Nothing was started or written; existing files were left as they are. "
                "Update the manifest explicitly (version 2, add `domain` only if it is decided) or order that change.")
    return None


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
    legacy = legacy_problem(project_schema_file.parent, data)
    if legacy:
        raise Stop(legacy)
    old = version_problem(data)
    if old:
        raise Stop(old)
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
