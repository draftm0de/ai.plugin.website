#!/usr/bin/env python3
"""Website plugin, skill `preview`: pick the site, write its dev-server entry into `.claude/launch.json`, print a JSON result.

`.claude/launch.json` is a Claude-desktop-specific artifact (see references/preview.md); it is not a Codex integration.
Exit codes: 0 resolved, 1 STOP, 2 ASK (ambiguous; options in the JSON).
The caller starts the server with the returned launch name and opens the url. The skill's own start path is `control.py`.
"""
import argparse
import json
import os
import stat
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "_shared" / "scripts"))   # shared package `site_common` (resolver, manifest validator, errors)

from site_common import manifest, sites  # noqa: E402
from site_common.errors import EXIT_ASK, EXIT_OK, EXIT_STOP, Ask, Stop  # noqa: E402

SKILL_DIR = HERE.parent
RES = SKILL_DIR / "templates"   # templates of this skill, inside the plugin (never a developer path, never written to)
LAUNCH_NAME = "zyris-{name}"


def parse(argv):
    p = argparse.ArgumentParser(prog="preview.py")
    p.add_argument("site", nargs="?", help="domain, folder, title or alias")
    p.add_argument("--page", default="/", help="path to open, e.g. /about.html")
    p.add_argument("--cwd", help="working directory of the conversation")
    p.add_argument("--last", help="site used last in this conversation")
    p.add_argument("--root", help="repository root (default: current directory)")
    return p.parse_args(argv)


def render(text: str, values: dict) -> str:
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def launch_entry(component: dict) -> dict:
    """The dev-server entry of a component, rendered from the type's template."""
    template = RES / "launch" / f"{component['type']}.json.tpl"
    if not template.is_file():
        raise Stop(f"No preview template for type '{component['type']}' ({template.name} missing).")
    name = LAUNCH_NAME.format(name=component["name"])
    return json.loads(render(template.read_text(encoding="utf-8"),
                             {"launch_name": name, "path": component["path"], "port": component["port"]}))


def _checked_launch_file(root: Path) -> Path:
    """`.claude/launch.json` of the project, after a metadata-only check (lstat, no content access): `.claude` must be absent or a real
    directory (not a symlink, not a broken one either), `launch.json` absent or a regular file (not a symlink, not a broken one,
    not a directory or special file). Nothing behind a link is ever read, overwritten or removed."""
    directory = root / ".claude"
    file = directory / "launch.json"
    for path, what, ok in ((directory, "directory", stat.S_ISDIR), (file, "regular file", stat.S_ISREG)):
        try:
            mode = os.lstat(path).st_mode
        except FileNotFoundError:
            continue
        except OSError as error:
            raise Stop(f"{path} cannot be inspected ({error}); left untouched.")
        if stat.S_ISLNK(mode):
            raise Stop(f"{path} is a symbolic link (also a broken one counts); the launch configuration is neither read nor written through "
                       "links and nothing was started. Replace it by a real file or directory yourself.")
        if not ok(mode):
            raise Stop(f"{path} is not a {what}; left untouched and nothing was started. Remove or repair it yourself.")
    return file


def write_launch(root: Path, component: dict) -> str:
    entry = launch_entry(component)
    name = entry["name"]
    file = _checked_launch_file(root)
    if os.path.lexists(file):
        try:
            fd = os.open(file, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, "r", encoding="utf-8") as handle:
                data = json.loads(handle.read())
            configs = data["configurations"]
            if not isinstance(configs, list):
                raise TypeError
        except (ValueError, KeyError, TypeError):
            raise Stop(f"{file} is not valid launch JSON (object with a 'configurations' list); left untouched. Repair or remove it.")
        except OSError as error:
            raise Stop(f"{file} cannot be read safely ({error}); left untouched.")
    else:
        data, configs = {"version": "0.0.1", "configurations": []}, []
    if entry in configs:      # identical own entry present: write nothing (contract D2)
        return name
    data["configurations"] = [c for c in configs if c.get("name") != name] + [entry]
    file.parent.mkdir(parents=True, exist_ok=True)
    _checked_launch_file(root)                      # again right before the write (the directory may just have been created)
    try:
        fd = os.open(file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o666)
    except OSError as error:
        raise Stop(f"{file} cannot be written safely ({error}); left untouched.")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(data, indent=2) + "\n")
    return name


def run(args) -> dict:
    root = Path(args.root).resolve() if args.root else Path.cwd().resolve()
    components = sites.load(root)
    result = sites.resolve(components, root, args.site, args.cwd, args.last)
    component = result["component"]
    site_dir = root / component["path"]
    if not site_dir.is_dir():
        raise Stop(f"Site folder missing: {site_dir}")
    notes = manifest.require_consistent(root, component)   # contradictions stop here, before anything is written or started
    page = args.page if args.page.startswith("/") else "/" + args.page
    return {
        "site": component["name"], "title": component["title"], "reason": result["reason"],
        "confirm": result["confirm"], "launch_name": write_launch(root, component),
        "port": component["port"], "url": f"http://localhost:{component['port']}{page}",
        "needs_install": not (site_dir / "node_modules").is_dir(), "path": component["path"],
    }


def main(argv=None) -> int:
    try:
        print(sites.as_json(run(parse(argv))))
        return EXIT_OK
    except Ask as q:
        print(sites.as_json({"ask": str(q), "options": q.options}))
        return EXIT_ASK
    except Stop as s:
        print(f"STOP: {s}")
        return EXIT_STOP


if __name__ == "__main__":
    sys.exit(main())
