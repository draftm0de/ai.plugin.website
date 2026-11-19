#!/usr/bin/env python3
"""Website plugin, skill `setup`: static Astro sites: create | adopt | plan | verify.

    site_setup.py create <domain> --type astro-static [options]
    site_setup.py adopt  <domain> [options]
    site_setup.py plan create|adopt <domain> [options]      # writes, installs and builds nothing
    site_setup.py verify <domain> [--root R] [--json]       # install + build + check of the current content

Exit codes: 0 ok (created, adopted, verified, unchanged, planned), 1 refused or failed, 2 input missing (needs-input).
Only the type `astro-static` exists. `update`, `--add-missing`, `--regenerate`, `--adopt-edits` and `plan` without an
operation are NOT available; any other option (including the options of the removed Docker/Caddy path) is an argument error.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "_shared" / "scripts"))   # shared package `site_common` (schema validator, legacy-format check)

import static_setup  # noqa: E402

NOT_AVAILABLE = {
    "update": "setup update is not available (not implemented; the registered site stays as it is)",
    "--add-missing": "--add-missing is not available (not implemented)",
    "--regenerate": "--regenerate is not available (not implemented)",
    "--adopt-edits": "--adopt-edits is not available (not implemented)",
}


def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--type", dest="site_type")
    common.add_argument("--path", dest="sites_dir", help="sites folder, relative to the repository root (default: sites)")
    common.add_argument("--title")
    common.add_argument("--alias", action="append", default=[], help="repeatable")
    common.add_argument("--port", type=int)
    common.add_argument("--environment")
    common.add_argument("--root", help="repository root (default: from git)")
    common.add_argument("--json", action="store_true")
    common.add_argument("--build", action="store_true", help="npm install, npm run build, npm run check; real exit codes are reported")
    p = argparse.ArgumentParser(prog="site_setup.py")
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("create", "adopt"):
        s = sub.add_parser(name, parents=[common])
        s.add_argument("domain", nargs="?")
    s = sub.add_parser("plan", parents=[common])
    s.add_argument("target", nargs="?", help="create | adopt")
    s.add_argument("domain", nargs="?")
    s = sub.add_parser("verify")
    s.add_argument("domain", nargs="?")
    s.add_argument("--root")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("update")
    s.add_argument("rest", nargs="*")
    return p


def options_from(args, operation) -> static_setup.Options:
    return static_setup.Options(operation=operation, domain=args.domain, root=args.root, site_type=getattr(args, "site_type", None),
                                sites_dir=getattr(args, "sites_dir", None), title=getattr(args, "title", None),
                                aliases=tuple(getattr(args, "alias", []) or ()), port=getattr(args, "port", None),
                                environment=getattr(args, "environment", None), build=getattr(args, "build", False))


def refuse(message, as_json):
    if as_json:
        print(json.dumps({"state": "not-available", "exit": 1, "problems": [message]}, indent=2))
    else:
        print(f"STOP: {message}")
    return 1


def main(argv=None, runner=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    for flag, message in NOT_AVAILABLE.items():
        if flag in argv:
            return refuse(message, "--json" in argv)
    args = build_parser().parse_args(argv)
    if args.command == "update":
        return refuse(NOT_AVAILABLE["update"], False)
    if args.command == "plan":
        if args.target not in ("create", "adopt"):
            return refuse("`setup plan` needs the operation: `plan create <domain>` or `plan adopt <domain>` "
                          "(automatic detection of the operation is not available)", args.json)
        result = static_setup.plan_only(options_from(args, args.target))
    elif args.command == "verify":
        result = static_setup.verify(static_setup.Options("verify", args.domain, root=args.root), runner)
    else:
        result = static_setup.execute(options_from(args, args.command), runner)
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else static_setup.render_text(result))
    return result["exit"]


if __name__ == "__main__":
    sys.exit(main())
