#!/usr/bin/env python3
"""Resolve which site of the repository is meant and print its paths as JSON.

Exit codes: 0 resolved, 1 STOP, 2 ASK (ambiguous; options in the JSON).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from site_common import manifest, sites  # noqa: E402
from site_common.errors import EXIT_ASK, EXIT_OK, EXIT_STOP, Ask, Stop  # noqa: E402

RULES_DIR = "rules"
BRAND_DIR = ".project/brand"   # rules of the brand, valid for every channel


def parse(argv):
    p = argparse.ArgumentParser(prog="which_site.py")
    p.add_argument("site", nargs="?", help="domain, folder, title or alias")
    p.add_argument("--cwd", help="working directory of the conversation")
    p.add_argument("--last", help="site used last in this conversation")
    p.add_argument("--root", help="repository root (default: current directory)")
    return p.parse_args(argv)


def run(args) -> dict:
    root = Path(args.root).resolve() if args.root else Path.cwd().resolve()
    result = sites.resolve(sites.load(root), root, args.site, args.cwd, args.last)
    component = result["component"]
    site_dir = root / component["path"]
    if not site_dir.is_dir():
        raise Stop(f"Site folder missing: {site_dir}")
    notes = manifest.require_consistent(root, component)   # contradictions stop here, before anything is written or started
    rules = site_dir / RULES_DIR
    brand = root / BRAND_DIR
    return {
        "site": component["name"], "title": component["title"], "reason": result["reason"],
        "confirm": result["confirm"], "path": component["path"], "type": component["type"],
        "rules": f"{component['path']}/{RULES_DIR}",
        "rule_files": sorted(f.name for f in rules.glob("*.md")) if rules.is_dir() else [],
        "brand": BRAND_DIR,
        "brand_files": sorted(f.name for f in brand.glob("*.md")) if brand.is_dir() else [],
        "has_node_modules": (site_dir / "node_modules").is_dir(),
        "domain": component.get("domain"), "consistency_unverifiable": notes,
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
