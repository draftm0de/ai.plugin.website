#!/usr/bin/env python3
"""Website plugin, skill `optimize`: audit, decisions, bounded apply. Driver; prints JSON.

  audit.py audit  [--site S] [--proposals FILE] [--editorial FILE] [--applied ID ...] [--npm PATH]
  audit.py propose --proposals FILE      (store drafts for existing findings; no audit run)
  audit.py decide ID [ID ...] --status proposed|approved|deferred|wont-do [--reason TEXT] [--change]
  audit.py apply  ID [ID ...]            (only approved findings whose proposal carries a mechanical edit)
  audit.py show                          (validate and summarise the work list; changes nothing)

Exit codes: 0 clean / clean-with-warnings / done, 1 errors / incomplete / readonly-violated / STOP, 2 ASK (site).

An audit builds into the git-ignored dist/, runs the site's `seo:check` and `a11y:check` independently,
reads their real exit codes, writes an immutable snapshot report and reconciles the work list. It never
edits site content, never installs dependencies and never runs git write commands.
"""
import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "_shared" / "scripts"))   # shared package `site_common` (resolver, manifest validator, errors)

import findings as fx  # noqa: E402
import store  # noqa: E402
import worklist as wl  # noqa: E402
from site_common import manifest, sites, project_files  # noqa: E402
from site_common.errors import EXIT_ASK, EXIT_OK, EXIT_STOP, Ask, Stop  # noqa: E402

CHECKS = (("seo", "seo:check"), ("a11y", "a11y:check"))
NODE_MIN = (22, 23, 4)
SECRET_RE = re.compile(r"(?i)\b([A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|PASSWD|API[_-]?KEY|AUTH)[A-Z0-9_]*)\s*[=:]\s*\S+")
MANUAL = ("colour contrast", "keyboard path and visible focus", "zoom/reflow at 200 %", "screen-reader reading of headings and links",
          "truthfulness of every claim on the page", "hero-image alt decisions", "legal pages (imprint, privacy): only the owner can do these",
          "redirects, HTTPS/HSTS, headers and the 404 status at the live server (not tested here; the site's requirement note is <site>/rules/serving.md where present)", "Search Console / Bing Webmaster registration, DNS")
NOT_COVERED = ("No Lighthouse run, no live crawling, no ranking or traffic measurement, no GEO criteria (not implemented). "
               "The checks are static checks of the built HTML/CSS; editorial suggestions are judgement, not test results.")


# ------------------------------------------------------------------ helpers

def redact(text: str) -> str:
    return SECRET_RE.sub(lambda m: f"{m.group(1)}=<redacted>", text)


def tail(text: str, lines: int = 40, chars: int = 4000) -> str:
    out = "\n".join(text.strip().splitlines()[-lines:])
    return redact(out[-chars:])


def source_state(root: Path, exclude: str) -> dict:
    """Current project files, independent of Git, excluding local/private output."""
    import hashlib
    hashes = project_files.snapshot(root, exclude=(exclude,))
    digest = hashlib.sha256("\n".join(f"{k}\0{v}" for k, v in sorted(hashes.items())).encode()).hexdigest()
    return {"digest": digest, "hashes": hashes}


def state_diff(a: dict, b: dict) -> list:
    return project_files.changed(a["hashes"], b["hashes"])


def run_cmd(argv, cwd: Path, timeout: int) -> dict:
    started = time.monotonic()
    rec = {"argv": argv, "exit": None, "error": None, "stdout": "", "stderr": "", "seconds": 0.0}
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=timeout, env={**os.environ, "NO_COLOR": "1", "FORCE_COLOR": "0"})
        rec.update(exit=p.returncode, stdout=p.stdout.decode("utf-8", "replace"), stderr=p.stderr.decode("utf-8", "replace"))
    except FileNotFoundError as error:
        rec["error"] = f"cannot start: {error.filename or argv[0]}"
    except subprocess.TimeoutExpired:
        rec["error"] = f"timed out after {timeout} s"
    rec["seconds"] = round(time.monotonic() - started, 1)
    return rec


def display(argv) -> str:
    return " ".join(Path(argv[0]).name if i == 0 else a for i, a in enumerate(argv))


def prerequisites(root: Path, site_path: str, npm) -> tuple:
    """Return (problems, npm_argv0). Nothing is installed; every gap is reported."""
    problems = []
    site = root / site_path
    npm_path = npm or shutil.which("npm")
    if not npm_path:
        problems.append("npm not found on PATH")
    elif not npm:
        node = shutil.which("node")
        if not node:
            problems.append("node not found on PATH")
        else:
            out = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip()
            m = re.match(r"v(\d+)\.(\d+)\.(\d+)", out)
            if not m or tuple(int(x) for x in m.groups()) < NODE_MIN:
                problems.append(f"Node {out or 'unknown'} is older than {'.'.join(map(str, NODE_MIN))} (package.json engines)")
    pkg = site / "package.json"
    scripts = {}
    if not pkg.is_file():
        problems.append(f"{site_path}/package.json missing")
    else:
        try:
            scripts = json.loads(pkg.read_text(encoding="utf-8")).get("scripts", {})
        except json.JSONDecodeError:
            problems.append(f"{site_path}/package.json is not valid JSON")
    if "build" not in scripts:
        problems.append("package.json has no 'build' script")
    if not (site / "node_modules").is_dir():
        problems.append(f"dependencies missing: {site_path}/node_modules does not exist. This audit never installs; run `npm ci` in {site_path} yourself, then audit again")
    if not (site / "package-lock.json").is_file():
        problems.append("no package-lock.json: dependencies cannot be installed reproducibly")
    for folder in ("dist", "node_modules", ".astro"):
        if not project_files.is_ignored(root, f"{site_path}/{folder}/x"):
            problems.append(f"{site_path}/{folder}/ is not git-ignored: declare build output in the project-local .gitignore")
    return problems, npm_path


# ------------------------------------------------------------------ execution of one audit

def execute(root: Path, component: dict, npm, hooks) -> dict:
    site, site_path = component["name"], component["path"]
    exclude = f"{store.REPORTS.as_posix()}/{site}/"
    before = source_state(root, exclude)
    problems, npm_path = prerequisites(root, site_path, npm)
    scripts = {}
    pkg = root / site_path / "package.json"
    if pkg.is_file():
        try:
            scripts = json.loads(pkg.read_text(encoding="utf-8")).get("scripts", {})
        except json.JSONDecodeError:
            pass
    run = {"build": None, "checks": {}, "families": {}, "prereq": problems, "before": before, "after": None, "changed": []}
    cwd = root / site_path
    build_ok = False
    if not problems:
        run["build"] = run_cmd([npm_path, "run", "build"], cwd, 900)
        build_ok = run["build"]["exit"] == 0 and (cwd / "dist").is_dir()
    for family, script in CHECKS:
        fam = {"complete": False, "reason": "", "raw": [], "exit": None, "pages": None}
        run["families"][family] = fam
        if problems:
            fam["reason"] = "prerequisites missing: " + "; ".join(problems)
        elif not build_ok:
            fam["reason"] = "build failed or produced no dist/; not checking, a stale dist/ from an earlier build must not count"
        elif script not in scripts:
            fam["reason"] = f"site has no '{script}' script: no machine audit available for {family}"
        else:
            rec = run_cmd([npm_path, "run", script], cwd, 600)
            run["checks"][family] = rec
            fam["exit"] = rec["exit"]
            if rec["error"]:
                fam["reason"] = rec["error"]
                continue
            parsed = fx.parse_output(rec["stdout"], rec["exit"])
            fam["pages"] = parsed["pages"]
            if parsed["status"] != "ok":
                fam["reason"] = "output not evaluable: " + parsed["reason"]
                continue
            fam["complete"] = True
            fam["raw"] = fx.collect(family, parsed)
    if hooks and hooks.get("after_checks"):
        hooks["after_checks"]()
    after = source_state(root, exclude)
    run["after"] = after
    run["changed"] = state_diff(before, after)
    if run["changed"]:
        for fam in run["families"].values():
            if fam["complete"]:
                fam["complete"] = False
                fam["reason"] = "read-only guard violated during the run; results are not trusted for closing findings"
        run["status"] = "readonly-violated"
    elif any(not f["complete"] for f in run["families"].values()):
        run["status"] = "incomplete"
    elif any(r["class"] == fx.ERROR for f in run["families"].values() for r in f["raw"]):
        run["status"] = "errors"
    elif any(f["raw"] for f in run["families"].values()):
        run["status"] = "clean-with-warnings"
    else:
        run["status"] = "clean"
    return run


# ------------------------------------------------------------------ report text

def stamp_of(now) -> str:
    return now.strftime("%Y%m%d-%H%M%S")


def render_report(*, component, run, mode, now, report_name, state, changes, prev, applied_info, rebased) -> str:
    site = component["name"]
    utc = now.astimezone(timezone.utc)
    b = run["before"]
    L = [f"# Optimize report: {site} - {now.strftime('%Y-%m-%d %H:%M:%S %z')}", "",
         f"<!-- zyris-optimize:report v1 site={site} -->",
         f"Immutable snapshot of one run. The authoritative status of all findings is the work list [../optimize.md](../optimize.md); this file is never edited afterwards.", "",
         "## Run", "",
         "| Item | Value |", "|---|---|",
         f"| Site | `{site}` (`{component['path']}`) |",
         f"| Time | {now.isoformat(timespec='seconds')} (local, offset included); UTC {utc.strftime('%Y-%m-%dT%H:%M:%SZ')} |",
         f"| Mode | `{mode}` |",
         f"| Result | `{run['status']}` |",
         f"| Source state | project files audited as they were; source-files digest `{b['digest'][:16]}` |",
         f"| Read-only guard | " + ("passed: no project source file changed (ignored/private files and report area excluded)" if not run["changed"] else "**VIOLATED**: " + ", ".join(f"`{c}`" for c in run["changed"][:20])) + " |",
         f"| Previous run | {prev or 'none (first run)'} |", ""]
    if rebased:
        L += ["The work list was changed by someone else while this run was working; its content was kept and this run was merged onto it (no decision overwritten).", ""]
    L += ["## Checks", "", "| Check | Command | Exit code | Result |", "|---|---|---|---|"]
    if run["build"]:
        bd = run["build"]
        L.append(f"| build | `{display(bd['argv'])}` | {bd['exit'] if bd['exit'] is not None else '-'} | {'ok' if bd['exit'] == 0 else 'FAILED' + (' (' + bd['error'] + ')' if bd['error'] else '')} |")
    else:
        L.append("| build | not run | - | skipped: prerequisites missing |")
    for family, script in CHECKS:
        fam = run["families"][family]
        rec = run["checks"].get(family)
        cmd = f"`npm run {script}`" if rec else f"`npm run {script}` (not run)"
        res = (f"complete, {fam['pages']} pages, {len(fam['raw'])} finding(s)" if fam["complete"] else f"INCOMPLETE - {fam['reason']}")
        L.append(f"| {family} | {cmd} | {fam['exit'] if fam['exit'] is not None else '-'} | {res} |")
    L += ["", "Exit codes are the process exit codes, read directly; the text of the output was not used to decide pass or fail. Results are never reported as clean when a check was incomplete.", ""]
    if run["prereq"]:
        L += ["### Skipped because of missing prerequisites", ""] + [f"- {p}" for p in run["prereq"]] + [""]
    L += ["### Output (tail, secrets redacted)", ""]
    if run["build"]:
        L += ["build:", "```", tail(run["build"]["stdout"] + ("\n" + run["build"]["stderr"] if run["build"]["exit"] else "")) or "(no output)", "```"]
    for family, rec in run["checks"].items():
        L += [f"{family}:", "```", tail(rec["stdout"] + ("\n" + rec["stderr"] if rec["exit"] else "")) or "(no output)", "```"]
    L += ["", "## Changes since the previous run", ""]
    labels = [("new", "New findings"), ("reappeared", "Reappeared (were done before; decide again)"), ("resolved", "Done in this run (recheck evidence below)"),
              ("approval_void", "Approval void (starting point or proposal changed; decide again)"), ("proposal_changed", "Proposal changed"),
              ("evidence_changed", "Evidence changed"), ("recheck_failed", "Applied but still reported"), ("recheck_incomplete", "Applied but recheck incomplete"),
              ("not_observed", "Deferred/rejected and not reported any more (decision kept)"), ("kept", "Kept open without new evidence (check incomplete)"),
              ("unchanged", "Unchanged")]
    any_change = False
    for key, label in labels:
        if changes.get(key):
            any_change = True
            L.append(f"- {label}: " + ", ".join(sorted(changes[key])))
    if not any_change:
        L.append("- No findings in this run and none changed.")
    L.append("")
    if applied_info:
        L += ["## Applied changes (only the approved proposals named below)", ""]
        L += [f"- Findings: {', '.join(applied_info['ids'])}", f"- Changed files: {', '.join('`' + f + '`' for f in applied_info['files'])}", "", "```diff", applied_info["diff"].rstrip() or "(no diff)", "```", ""]
    touched = set(sum((changes.get(k, []) for k in ("new", "reappeared", "resolved", "approval_void", "proposal_changed", "evidence_changed", "recheck_failed", "recheck_incomplete", "unchanged", "not_observed")), []))
    L += ["## Findings in this run", ""]
    shown = [f for f in sorted(state["findings"], key=lambda x: x["id"]) if f["id"] in touched]
    if not shown:
        L += ["None.", ""]
    for f in shown:
        L += [wl.render_finding(f).replace("[optimize/", "[").replace("](optimize/", "]("), ""]
    L += ["## Limits of this run", "", NOT_COVERED, "",
          "Manual check points that no script marks as passed:", ""] + [f"- {m}" for m in MANUAL] + [""]
    return "\n".join(L)


# ------------------------------------------------------------------ commit

def load_state(root, site, now):
    text, sha = store.read_worklist(root, site)
    if text is None:
        return wl.new_state(site, now), None
    return wl.parse(text, site), sha


def make_verify(root: Path):
    def verify(spec):
        path = (root / spec["file"]).resolve()
        if root.resolve() not in path.parents or not path.is_file():
            return False, f"{spec['file']} not readable"
        content = path.read_text(encoding="utf-8")
        if "present" in spec:
            return spec["present"] in content, f"{spec['file']} contains the proposed text"
        if "absent" in spec:
            return spec["absent"] not in content, f"{spec['file']} no longer contains the old text"
        return False, "no verify condition"
    return verify


def do_audit(root: Path, component: dict, *, npm=None, now=None, proposals=None, editorial=None, applied=(), mode="audit",
             applied_info=None, hooks=None) -> dict:
    root = root.resolve()
    now = now or datetime.now().astimezone()
    site = component["name"]
    store.site_root(root, site)
    state0, sha0 = load_state(root, site, now)         # a damaged list stops the run before anything is built
    for fid in applied:
        f = next((x for x in state0["findings"] if x["id"] == fid), None)
        if mode == "apply":
            break                                          # do_apply already checked under the lock; re-validated at commit
        if not f or f["status"] != "approved" or f["resolution"]:
            raise Stop(f"{fid} is not an approved, open finding; --applied only closes the recheck of an approved proposal")
    run = execute(root, component, npm, hooks)
    if hooks and hooks.get("before_commit"):
        hooks["before_commit"]()
    with store.Lock(root, site):
        state, sha = load_state(root, site, now)
        rebased = sha != sha0
        prev = state["last_run"]["report"] if state["last_run"] else None
        result = {}
        # a decision made meanwhile wins: only findings still approved and open count as applied
        still = tuple(i for i in applied if any(x["id"] == i and x["status"] == "approved" and not x["resolution"] for x in state["findings"]))

        def compose(report_name):
            work = wl.snapshot_copy(state)
            applied_files = applied_info["files"] if applied_info else []
            changes = wl.reconcile(work, run, now=now, report=report_name, proposals=proposals, editorial=editorial,
                                   applied=still, root=root, site_path=component["path"], verify_fn=make_verify(root),
                                   applied_files=applied_files)
            work["last_run"]["status"] = run["status"]
            result["state"], result["changes"] = work, changes
            return render_report(component=component, run=run, mode=mode, now=now, report_name=report_name, state=work,
                                 changes=changes, prev=prev, applied_info=applied_info, rebased=rebased)

        report_path, report_name = store.write_snapshot(root, site, stamp_of(now), compose, (hooks or {}).get("before_link"))
        new_state = result["state"]
        text = wl.render(new_state)
        if hooks and hooks.get("before_replace"):
            hooks["before_replace"]()
        try:
            store.replace_worklist(root, site, text, sha)
        except store.Conflict as error:
            raise store.Conflict(f"{error} The snapshot {report_path} was written and is valid; the work list was not updated.")
    wl_path = store.worklist_path(root, site)
    counts = {s: sum(1 for f in new_state["findings"] if wl.section_of(f) == s) for s in ("open", "parked", "history")}
    return {"site": site, "status": run["status"], "exit_code": 0 if run["status"] in ("clean", "clean-with-warnings") else 1,
            "report": str(report_path.relative_to(root)), "worklist": str(wl_path.relative_to(root)),
            "checks": {f: {"complete": v["complete"], "exit": v["exit"], "reason": v["reason"]} for f, v in run["families"].items()},
            "build_exit": run["build"]["exit"] if run["build"] else None,
            "changes": {k: v for k, v in result["changes"].items() if v}, "counts": counts, "rebased": rebased,
            "readonly_violations": run["changed"]}


# ------------------------------------------------------------------ decide / apply / show

def do_decide(root: Path, component: dict, ids, status, *, reason=None, change=False, now=None, hooks=None) -> dict:
    root = root.resolve()
    now = now or datetime.now().astimezone()
    site = component["name"]
    store.site_root(root, site)
    with store.Lock(root, site):
        text, sha = store.read_worklist(root, site)
        if text is None:
            raise Stop(f"no work list yet for {site}: run an audit first")
        state = wl.parse(text, site)
        rev = state["rev"]
        messages = wl.decide(state, ids, status, now=now, reason=reason, change=change)
        if hooks and hooks.get("before_replace"):
            hooks["before_replace"]()
        if state["rev"] != rev:
            store.replace_worklist(root, site, wl.render(state), sha)
    return {"site": site, "messages": messages}


def do_propose(root: Path, component: dict, proposals: dict, *, now=None) -> dict:
    root = root.resolve()
    now = now or datetime.now().astimezone()
    site = component["name"]
    store.site_root(root, site)
    with store.Lock(root, site):
        text, sha = store.read_worklist(root, site)
        if text is None:
            raise Stop(f"no work list yet for {site}: run an audit first")
        state = wl.parse(text, site)
        changes = wl.propose(state, proposals, now=now)
        if changes["proposal_changed"]:
            store.replace_worklist(root, site, wl.render(state), sha)
    return {"site": site, "changes": {k: v for k, v in changes.items() if v}}


def _edit_target(root: Path, site_path: str, rel: str) -> Path:
    p = Path(rel)
    if p.is_absolute() or ".." in p.parts:
        raise Stop(f"edit path '{rel}' must be relative and inside the site")
    if not rel.startswith(site_path.rstrip("/") + "/"):
        raise Stop(f"edit path '{rel}' is outside the site folder {site_path}")
    current = root
    for part in p.parts:
        current = current / part
        if current.is_symlink():
            raise Stop(f"edit path '{rel}' passes through a symlink")
    if not current.is_file():
        raise Stop(f"edit file '{rel}' does not exist")
    if project_files.private(p.parts) or project_files.IgnoreRules(root).ignored(rel):
        raise Stop(f"edit file '{rel}' is private or ignored; apply only changes project source files")
    return current


def _read_exact(path: Path, rel: str) -> str:
    """The file as UTF-8 text with its line endings untouched (no newline translation); anything else is refused."""
    try:
        return path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise Stop(f"edit file '{rel}' cannot be read as UTF-8 text ({error}); nothing was changed")


def do_apply(root: Path, component: dict, ids, *, npm=None, now=None, hooks=None) -> dict:
    root = root.resolve()
    now = now or datetime.now().astimezone()
    site, site_path = component["name"], component["path"]
    ids = list(dict.fromkeys(ids))                         # a repeated ID is applied once
    store.site_root(root, site)
    if hooks and hooks.get("before_apply"):
        hooks["before_apply"]()
    # Approval check and source change happen under one lock, on the freshly read work list: a decision made
    # meanwhile (wont-do, deferred, new proposal) is seen before anything is written, and no decision is overwritten.
    with store.Lock(root, site):
        state, _ = load_state(root, site, now)
        by_id = {f["id"]: f for f in state["findings"]}
        plan = []
        for fid in ids:
            f = by_id.get(fid)
            if f is None:
                raise Stop(f"unknown finding ID '{fid}'")
            if f["resolution"]:
                raise Stop(f"{fid} is already done")
            if f["status"] != "approved":
                raise Stop(f"{fid} is {f['status']}, not approved: nothing is changed. Approve the documented proposal first.")
            if f["approved_basis"] != wl.basis_hash(f):
                raise Stop(f"{fid}: proposal or starting point changed since the approval; decide again")
            if not f["proposal"]["edits"]:
                raise Stop(f"{fid}: its proposal has no mechanical edit; implement the approved scope by hand, then run `audit --applied {fid}`")
            plan.append(f)
        problems, _ = prerequisites(root, site_path, npm)
        if problems:
            raise Stop("cannot verify an applied change, so nothing was changed: " + "; ".join(problems))
        originals, spans = {}, {}
        for f in plan:
            for e in f["proposal"]["edits"]:
                path = _edit_target(root, site_path, e["file"])
                if path not in originals:
                    originals[path] = _read_exact(path, e["file"])
                content = originals[path]
                if not e["find"]:
                    raise Stop(f"{f['id']}: the text to replace is empty")
                if e["find"] == e["replace"]:
                    raise Stop(f"{f['id']}: edit does not change anything")
                n = content.count(e["find"])
                if n != 1:
                    raise Stop(f"{f['id']}: the text to replace occurs {n} times in {e['file']} (needs exactly 1). Already applied, or the file changed; nothing was changed")
                start = content.find(e["find"])
                spans.setdefault(path, []).append((start, start + len(e["find"]), e["replace"], f["id"], e["file"]))
        # every span refers to the ORIGINAL content; overlapping or contradicting spans are refused before the first write
        for path, items in spans.items():
            items.sort()
            for (s1, e1, _, id1, rel), (s2, e2, _, id2, _) in zip(items, items[1:]):
                if s2 < e1:
                    raise Stop(f"{id1} and {id2} change overlapping text in {rel}: contradicting request, nothing was changed")
        exclude = f"{store.REPORTS.as_posix()}/{site}/"
        s0 = source_state(root, exclude)
        contents = dict(originals)
        for path, items in spans.items():
            new = originals[path]
            for start, end, replace, _, _ in sorted(items, reverse=True):      # from the end: earlier offsets stay valid
                new = new[:start] + replace + new[end:]
            contents[path] = new
        written = []
        try:
            for path, new in contents.items():
                if new == originals[path]:
                    continue
                fd, tmp = tempfile.mkstemp(prefix=".optimize-apply-", dir=path.parent)
                try:
                    with os.fdopen(fd, "wb") as h:
                        h.write(new.encode("utf-8"))
                    os.chmod(tmp, path.stat().st_mode & 0o7777)
                    os.replace(tmp, path)
                except BaseException:
                    Path(tmp).unlink(missing_ok=True)
                    raise
                written.append(path)
        except BaseException:
            for path in written:
                path.write_bytes(originals[path].encode("utf-8"))
            raise
        files = sorted(p.relative_to(root).as_posix() for p in written)
        diff = ""
        for p in written:
            rel = p.relative_to(root).as_posix()
            diff += "".join(difflib.unified_diff(originals[p].splitlines(True), contents[p].splitlines(True), f"a/{rel}", f"b/{rel}"))
        s1 = source_state(root, exclude)
        stray = [c for c in state_diff(s0, s1) if c not in files and not c.startswith("git status")]
        if stray:
            raise Stop("files other than the approved scope changed during apply: " + ", ".join(stray))
    return do_audit(root, component, npm=npm, now=now, applied=tuple(ids), mode="apply",
                    applied_info={"ids": list(ids), "files": files, "diff": diff}, hooks=hooks)


def summarize(root: Path, component: dict) -> dict:
    site = component["name"]
    now = datetime.now().astimezone()
    text, sha = store.read_worklist(root.resolve(), site)
    if text is None:
        return {"site": site, "worklist": None, "message": "no work list yet"}
    state = wl.parse(text, site)
    rows = lambda sec: [{"id": f["id"], "title": f["title"], "location": f["location"], "class": f["class"], "status": f["status"], "attention": f["attention"]}
                        for f in sorted(state["findings"], key=lambda x: x["id"]) if wl.section_of(f) == sec]
    return {"site": site, "worklist": f".project/reports/{site}/optimize.md", "rev": state["rev"], "last_run": state["last_run"],
            "open": rows("open"), "parked": rows("parked"), "history": rows("history")}


# ------------------------------------------------------------------ CLI

def parse_args(argv):
    p = argparse.ArgumentParser(prog="audit.py")
    p.add_argument("command", choices=["audit", "propose", "decide", "apply", "show"])
    p.add_argument("ids", nargs="*", help="finding IDs (decide, apply)")
    p.add_argument("--site")
    p.add_argument("--cwd")
    p.add_argument("--last")
    p.add_argument("--root")
    p.add_argument("--status")
    p.add_argument("--reason")
    p.add_argument("--change", action="store_true", help="explicitly change an earlier decision")
    p.add_argument("--proposals", help="JSON file: {identity key or finding ID: proposal}")
    p.add_argument("--editorial", help="JSON file: list of editorial suggestions")
    p.add_argument("--applied", nargs="*", default=[], help="approved IDs implemented by hand, to be rechecked")
    p.add_argument("--npm", help="path of the npm executable (default: PATH)")
    return p.parse_args(argv)


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise Stop(f"cannot read {path}: {error}")


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        root = Path(args.root).resolve() if args.root else Path.cwd().resolve()
        component = sites.resolve(sites.load(root), root, args.site, args.cwd, args.last)["component"]
        manifest.require_consistent(root, component)     # contradictions stop before build, report or worklist
        if args.command == "audit":
            result = do_audit(root, component, npm=args.npm, applied=tuple(args.applied),
                              proposals=read_json(args.proposals) if args.proposals else None,
                              editorial=read_json(args.editorial) if args.editorial else None)
        elif args.command == "propose":
            if not args.proposals:
                raise Stop("propose needs --proposals FILE")
            result = do_propose(root, component, read_json(args.proposals))
        elif args.command == "decide":
            if not args.ids or not args.status:
                raise Stop("decide needs finding IDs and --status")
            result = do_decide(root, component, args.ids, args.status, reason=args.reason, change=args.change)
        elif args.command == "apply":
            if not args.ids:
                raise Stop("apply needs the IDs of approved findings")
            result = do_apply(root, component, args.ids, npm=args.npm)
        else:
            result = summarize(root, component)
        print(sites.as_json(result))
        return result.get("exit_code", EXIT_OK)
    except Ask as q:
        print(sites.as_json({"ask": str(q), "options": q.options}))
        return EXIT_ASK
    except Stop as s:
        print(f"STOP: {s}")
        return EXIT_STOP
    except OSError as error:
        print(f"STOP: a file operation failed ({error}). Nothing is reported as done; check .project/reports/ and `git status` before the next run.")
        return EXIT_STOP


if __name__ == "__main__":
    sys.exit(main())
