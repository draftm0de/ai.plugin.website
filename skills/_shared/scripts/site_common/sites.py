"""Load the manifest and resolve which site is meant. Deterministic, no guessing."""
import json
from pathlib import Path

from . import manifest
from .errors import Ask, Stop

MANIFEST = manifest.SPECS / manifest.FILE
BASE_PORT = 4321


def load(root: Path) -> list:
    file = root / MANIFEST
    if not file.is_file():
        raise Stop(f"{MANIFEST} not found - run the `setup` skill of the Website plugin first.")
    data = manifest.load(file)
    errors = manifest.problems(data, root / manifest.SPECS / manifest.SCHEMA)
    if errors:
        raise Stop(f"{MANIFEST} is invalid:\n  " + "\n  ".join(errors))
    components = data["components"]
    if not components:
        raise Stop(f"{MANIFEST} has no components - run the `setup` skill of the Website plugin first.")
    for index, component in enumerate(components):
        component.setdefault("title", component["name"])
        component.setdefault("aliases", [])
        component.setdefault("port", BASE_PORT + index)
    return components


def _keys(component: dict) -> list:
    path_name = Path(component["path"]).name
    return [str(k).lower() for k in [component["name"], path_name, component["title"], *component["aliases"]]]


def _match(components: list, query: str) -> list:
    q = query.strip().lower()
    exact = [c for c in components if q in _keys(c)]
    if exact:
        return exact
    return [c for c in components if any(k.startswith(q) or q in k for k in _keys(c))]


def _label(component: dict) -> dict:
    return {"name": component["name"], "title": component["title"], "path": component["path"]}


def resolve(components: list, root: Path, query=None, cwd=None, last=None) -> dict:
    """Order: explicit query, working directory, single site, last used (needs confirmation), else ask."""
    if query:
        found = _match(components, query)
        if len(found) == 1:
            return {"component": found[0], "reason": "named", "confirm": False}
        if not found:
            raise Stop(f"No site matches '{query}'. Sites: {', '.join(c['name'] for c in components)}.")
        raise Ask(f"'{query}' matches several sites. Which one?", [_label(c) for c in found])
    if cwd:
        here = Path(cwd).resolve()
        for c in components:
            site = (root / c["path"]).resolve()
            if here == site or site in here.parents:
                return {"component": c, "reason": "working directory", "confirm": False}
    if len(components) == 1:
        return {"component": components[0], "reason": "only site", "confirm": False}
    if last:
        found = [c for c in components if c["name"] == last]
        if found:
            return {"component": found[0], "reason": "last used in this conversation", "confirm": True}
    raise Ask("Which site?", [_label(c) for c in components])


def as_json(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)
