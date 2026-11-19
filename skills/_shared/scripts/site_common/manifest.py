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
    project_schema_copy(project_schema_file)
    errors = schemalib.validate(data, plugin_schema())
    if errors:
        return errors
    names, ports, keys = set(), {}, {}
    for index, c in enumerate(data["components"]):
        where = f"$.components[{index}]"
        if c["name"] in names:
            errors.append(f"{where}: duplicate name '{c['name']}'")
        names.add(c["name"])
        if "port" in c:
            if c["port"] in ports:
                errors.append(f"{where}: port {c['port']} already used by '{ports[c['port']]}'")
            ports[c["port"]] = c["name"]
        for key in [c["name"], *c.get("aliases", [])]:
            owner = keys.setdefault(key.lower(), c["name"])
            if owner != c["name"]:
                errors.append(f"{where}: '{key}' is already a name or alias of '{owner}'")
    return errors
