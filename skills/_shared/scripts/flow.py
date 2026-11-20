#!/usr/bin/env python3
"""Website plugin: state of the guided flow (brief -> design -> implementation -> checks) for one site of the selected project.

    flow.py status        [--site S] [--root R]            read-only; derived state and the next step
    flow.py brief-save    --site S --file F [--root R]     save a brief revision (strict schema; earlier revisions are kept)
    flow.py brief-confirm --site S --statement T           the person's explicit confirmation of the current brief revision
    flow.py design-new    --site S [--feedback T]          create/resume the next design revision folder
    flow.py design-register --site S --revision N          validate and register the variants of that revision
    flow.py design-feedback --site S --text T              append feedback to the latest revision
    flow.py design-approve  --site S --revision N --variant V --statement T
    flow.py implement-start  --site S [--accept-current-page]
    flow.py implement-finish --site S --edit-state DIR  (state folder of the edit session that wrote the page)
    flow.py record-checks    --site S [--technical-evidence F] [--visual open|passed|failed] [--visual-note T]

Exit codes: 0 ok, 1 STOP (message starts with `STOP:`), 2 ASK. Output: one JSON object. Format and rules: docs/development/guided-flow.md.
Nothing here writes into the site folder; the page itself is written only by the `edit` skill.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from site_common import flowstate, sites  # noqa: E402
from site_common.errors import EXIT_ASK, EXIT_OK, EXIT_STOP, Ask, Stop  # noqa: E402


def parse(argv):
    p = argparse.ArgumentParser(prog="flow.py")
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("status", "brief-save", "brief-confirm", "design-new", "design-register", "design-feedback", "design-approve",
                 "implement-start", "implement-finish", "record-checks"):
        s = sub.add_parser(name)
        s.add_argument("--root")
        s.add_argument("--site")
        if name == "brief-save":
            s.add_argument("--file", required=True)
        if name in ("brief-confirm", "design-approve"):
            s.add_argument("--statement", default="")
        if name in ("design-register", "design-approve"):
            s.add_argument("--revision", type=int, required=True)
        if name == "design-approve":
            s.add_argument("--variant", required=True)
        if name == "design-new":
            s.add_argument("--feedback")
        if name == "design-feedback":
            s.add_argument("--text", default="")
        if name == "implement-start":
            s.add_argument("--accept-current-page", action="store_true")
        if name == "implement-finish":
            s.add_argument("--edit-state", required=True, help="the state folder that `edit.py begin` returned for this implementation")
        if name == "record-checks":
            s.add_argument("--technical-evidence")
            s.add_argument("--visual", default="open")
            s.add_argument("--visual-note", default="")
    return p.parse_args(argv)


def site_id(root: Path, query, allow_missing=False):
    manifest_file = root / ".project" / "specs" / "website.json"
    if not manifest_file.is_file():
        if allow_missing:
            return None
        raise Stop("no website project is set up here (no .project/specs/website.json); run setup first.")
    return sites.resolve(sites.load(root), root, query, None, None)["component"]["name"]


def _read_json_object(name) -> dict:
    path = Path(name)
    if path.is_symlink() or not path.is_file():
        raise Stop(f"{path} is not a regular file")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise Stop(f"{path} cannot be read as JSON: {error}")
    if not isinstance(data, dict):
        raise Stop(f"{path} is not a JSON object")
    return data


def run(args) -> dict:
    root = Path(args.root).resolve() if args.root else Path.cwd().resolve()
    if args.command == "status":
        site = site_id(root, args.site, allow_missing=True)
        if site is None:
            candidate = args.site if args.site and flowstate.SITE_ID_RE.match(args.site) else None
            if candidate:
                return flowstate.derive(root, candidate)
            leftovers = flowstate.existing_artifacts(root)
            if leftovers:       # not a new project: never routed into a new setup
                return {"site": None, "state": "problems", "next_step": "resolve-setup", "stale": [],
                        "setup": {"state": "contradictory", "problems": [
                            "website or flow artifacts exist (" + "; ".join(leftovers) + ") but .project/specs/website.json is missing; "
                            "no new setup is started and nothing was changed."]}}
            return {"site": None, "setup": {"state": "missing", "problems": []}, "next_step": "setup", "state": "ok"}
        return flowstate.derive(root, site)
    site = site_id(root, args.site)
    if args.command == "brief-save":
        path = Path(args.file)
        if path.is_symlink() or not path.is_file():
            raise Stop(f"{path} is not a regular file")
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError) as error:
            raise Stop(f"{path} cannot be read as JSON: {error}")
        return flowstate.brief_save(root, site, document)
    if args.command == "brief-confirm":
        return flowstate.brief_confirm(root, site, args.statement)
    if args.command == "design-new":
        return flowstate.design_new(root, site, args.feedback)
    if args.command == "design-register":
        return flowstate.design_register(root, site, args.revision)
    if args.command == "design-feedback":
        return flowstate.design_feedback(root, site, args.text)
    if args.command == "design-approve":
        return flowstate.design_approve(root, site, args.revision, args.variant, args.statement)
    if args.command == "implement-start":
        return flowstate.implement_start(root, site, args.accept_current_page)
    if args.command == "implement-finish":
        return flowstate.implement_finish(root, site, args.edit_state)
    evidence = None
    if args.technical_evidence:
        path = Path(args.technical_evidence)
        if path.is_symlink() or not path.is_file():
            raise Stop(f"{path} is not a regular file")
        try:
            evidence = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError) as error:
            raise Stop(f"{path} cannot be read as JSON: {error}")
        if not isinstance(evidence, dict):
            raise Stop(f"{path} is not a check result object")
    return flowstate.record_checks(root, site, evidence, args.visual, args.visual_note)


def main(argv=None) -> int:
    try:
        print(json.dumps(run(parse(argv)), indent=2, ensure_ascii=False))
        return EXIT_OK
    except Ask as question:
        print(json.dumps({"state": "ask", "question": str(question), "options": question.options}, indent=2, ensure_ascii=False))
        return EXIT_ASK
    except Stop as stop:
        print(json.dumps({"state": "stop", "message": f"STOP: {stop}"}, indent=2, ensure_ascii=False))
        return EXIT_STOP
    except OSError as error:
        print(json.dumps({"state": "stop", "message": f"STOP: a file operation failed ({error}); nothing is reported as done."}, indent=2))
        return EXIT_STOP


if __name__ == "__main__":
    sys.exit(main())
