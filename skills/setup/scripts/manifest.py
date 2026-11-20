"""Read and check .project/specs/zyris-website.json (setup variant of the shared manifest module: adds the file locations,
validates the type against types.json and derives effective ports). Constants and the schema location come from `site_common`."""
import json
from pathlib import Path

from errors import Stop
from site_common import manifest as shared
from site_common import schema as schemalib
from site_common.sites import BASE_PORT

SPECS, FILE, SCHEMA = shared.SPECS, shared.FILE, shared.SCHEMA
legacy_problem = shared.legacy_problem
is_legacy_reference = shared.is_legacy_reference


def files(root: Path) -> tuple:
    return root / SPECS / FILE, root / SPECS / SCHEMA


def load(file: Path):
    try:
        return json.loads(file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise Stop(f"{file} is not valid JSON: {error}")


PLUGIN_SCHEMA = shared.PLUGIN_SCHEMA


def plugin_schema() -> dict:
    """The binding manifest contract: the plugin's own schema, never the copy a project happens to carry."""
    if not PLUGIN_SCHEMA.is_file():
        raise Stop(f"{PLUGIN_SCHEMA} is missing: the plugin installation is incomplete.")
    return load(PLUGIN_SCHEMA)


def project_schema_copy(file: Path):
    """The project's schema copy must exist and be a JSON object; it is never used to relax the plugin contract."""
    if not file.is_file():
        raise Stop(f"{file} is missing: run the `setup` skill of the Website plugin (it creates the project's schema copy). Nothing was started or written.")
    if not isinstance(load(file), dict):
        raise Stop(f"{file} is not a JSON object. Nothing was started or written.")


def problems(data, schema_file, type_names=None) -> list:
    """Errors against the plugin schema (binding) plus the rules a schema cannot express. schema_file is the project's schema path
    (only checked to exist and be valid JSON) or the already loaded plugin schema dict."""
    if isinstance(schema_file, dict):          # planning: the plugin schema itself
        schema = schema_file
    else:                                      # a project schema path: the plugin schema stays the binding contract
        project_schema_copy(schema_file)
        schema = plugin_schema()
    old = shared.version_problem(data)
    if old:
        raise Stop(old)
    errors = schemalib.validate(data, schema)
    if not errors and type(data["version"]) is not int:       # 2.0 equals 2 in Python; the manifest version is the integer 2
        errors.append("$.version: must be the integer 2 (not a float or boolean)")
    if errors:
        return errors
    seen_domains = {}
    seen_names, seen_ports, keys = set(), {}, {}
    for index, c in enumerate(data["components"]):
        where = f"$.components[{index}]"
        if c["name"] in seen_names:
            errors.append(f"{where}: duplicate name '{c['name']}'")
        seen_names.add(c["name"])
        if "port" in c:
            if c["port"] in seen_ports:
                errors.append(f"{where}: port {c['port']} already used by '{seen_ports[c['port']]}'")
            seen_ports[c["port"]] = c["name"]
        if type_names is not None and c["type"] not in type_names:
            errors.append(f"{where}: unsupported type '{c['type']}' (supported: {', '.join(sorted(type_names))})")
        if "domain" in c:
            owner = seen_domains.setdefault(c["domain"], c["name"])
            if owner != c["name"]:
                errors.append(f"{where}: domain '{c['domain']}' already belongs to '{owner}'")
        for key in [c["name"], *c.get("aliases", [])]:
            owner = keys.setdefault(key.lower(), c["name"])
            if owner != c["name"]:
                errors.append(f"{where}: '{key}' is already a name or alias of '{owner}'")
    return errors


def effective_ports(components) -> list:
    """Ports the resolver really uses: the explicit one, else BASE_PORT + index (same rule as site_common.sites.load)."""
    return [c.get("port", BASE_PORT + index) for index, c in enumerate(components)]


def next_port(components) -> int:
    """Automatic port for a new component: BASE_PORT in an empty project, else the highest effective port + 1.
    Never collides with an effective port; stops instead of leaving the valid range."""
    ports = effective_ports(components)
    port = max(ports) + 1 if ports else BASE_PORT
    if port > 65535:
        raise Stop(f"No automatic port available: the highest effective port is {max(ports)} and the next one would leave the valid range "
                   "(1024-65535). Choose one with --port.")
    return port
