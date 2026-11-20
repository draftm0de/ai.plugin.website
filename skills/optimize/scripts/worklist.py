"""The optimize work list: state, reconciliation with a new audit, decisions, rendering and parsing.

`optimize.md` is the only status source. Its human-readable sections are generated from one
machine-readable JSON block at the end of the same file (format below); the block carries a
SHA-256 and the generated text must equal what the block renders to, so a hand edit, a
truncated write or a merge accident is detected instead of being trusted or silently overwritten.
Decisions are changed only through `decide` (audit.py), never by editing the text.

Decision status (exactly four): proposed, approved, deferred, wont-do. "Done" is not a decision:
it is a `resolution` record (with the check evidence) and moves the finding to the history while
the decision and its log stay with it.
"""
import copy
import hashlib
import json
import re

import findings as fx
from site_common.errors import Stop

FORMAT = "website-manager-optimize-worklist"
VERSION = 1
STATUSES = ("proposed", "approved", "deferred", "wont-do")
BEGIN_RE = re.compile(r"<!-- website-manager-optimize:state sha256=([0-9a-f]{64}) -->\n```json\n(.*?)\n```\n<!-- /website-manager-optimize:state -->\n?", re.S)
FAMILIES = ("seo", "a11y")


class WorklistError(Stop):
    pass


def iso(now) -> str:
    return now.isoformat(timespec="seconds")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def new_state(site: str, now) -> dict:
    return {"format": FORMAT, "version": VERSION, "site": site, "rev": 0, "created": iso(now), "updated": iso(now),
            "counters": {}, "last_run": None, "findings": []}


# ---------------------------------------------------------------- proposals

def normalize_proposal(raw: dict, fallback: str, kind_default: str) -> dict:
    """Proposal = what exactly would change. `edits` ([{file, find, replace}]) makes it mechanically applicable."""
    raw = raw or {}
    edits = raw.get("edits") or ([raw["edit"]] if raw.get("edit") else [])
    return {
        "summary": raw.get("summary") or fallback,
        "kind": raw.get("kind") or kind_default,       # draft = concrete text, rule = from a rule file, opinion = editorial judgement
        "current": raw.get("current"),
        "proposed": raw.get("proposed"),
        "edits": [{"file": e["file"], "find": e["find"], "replace": e["replace"]} for e in edits],
        "source": raw.get("source"),
        "limits": raw.get("limits"),
        "verify": raw.get("verify"),                    # editorial only: {file, present|absent} source-text check
    }


def proposal_hash(p: dict) -> str:
    return sha(canonical({k: p.get(k) for k in ("summary", "current", "proposed", "edits")}))


def basis_hash(f: dict) -> str:
    return sha(proposal_hash(f["proposal"]) + "|" + f["evidence"]["message"])


# ---------------------------------------------------------------- reconcile

def _next_id(state: dict, family: str) -> str:
    prefix = fx.FAMILY_PREFIX[family]
    n = state["counters"].get(prefix, 0) + 1
    state["counters"][prefix] = n
    return f"{prefix}-{n:03d}"


def _log(f: dict, now, status: str, note: str, report=None):
    f["decision_log"].append({"at": iso(now), "status": status, "note": note, **({"report": report} if report else {})})


def _find(state: dict, key: str):
    return next((f for f in state["findings"] if f["key"] == key), None)


def _pick_proposal(proposals: dict, f_key: str, f_id: str):
    return proposals.get(f_id) or proposals.get(f_key)


def _new_finding(state, raw, now, report, proposal_raw, root, site_path) -> dict:
    title, why, rule, level, reason, generic = fx.catalog_entry(raw["criterion"])
    family = raw["family"]
    cls = raw["class"]
    f = {
        "id": _next_id(state, family), "key": fx.identity_key(raw), "family": family, "class": cls,
        "criterion": raw["criterion"], "location": raw["location"], "detail": raw.get("detail", ""),
        "title": title, "why": why, "rule": f"{rule} (file: {FAMILY_RULES_PATH(site_path, family)})" if family in fx.FAMILY_RULES else rule,
        "source_files": fx.source_files(root, site_path, raw["location"]) if root else [],
        "evidence": {"message": raw["message"], "occurrences": raw.get("occurrences", 1)},
        "proposal": normalize_proposal(proposal_raw, generic, "draft" if (proposal_raw or {}).get("proposed") else "rule"),
        "priority": {"level": level if cls != fx.WARNING or level != "high" else "medium", "reason": reason},
        "method": f"output of {fx.FAMILY_SCRIPT.get(family, 'a supplied editorial review')}, evaluated by the optimize adapter; exit code taken from the process",
        "limits": LIMITS[family],
        "first_found": {"at": iso(now), "report": report}, "last_checked": {"at": iso(now), "report": report},
        "reports": [report], "status": "proposed", "decision_log": [], "approved_basis": None,
        "attention": None, "notes": [], "resolution": None, "resolved_before": [], "reappeared": 0,
        "applied": None, "not_observed": False,
    }
    _log(f, now, "proposed", "first found", report)
    return f


def FAMILY_RULES_PATH(site_path: str, family: str) -> str:
    return f"{site_path}/{fx.FAMILY_RULES[family]}"


LIMITS = {
    "seo": "Static check of the built HTML in dist/. Lengths are heuristics (script thresholds are looser than the seo.md bands). No live server, redirect, ranking or snippet claim.",
    "a11y": "Static HTML/CSS check only. Contrast, keyboard path, focus, zoom/reflow and screen-reader output need a manual check.",
    "editorial": "Editorial judgement supplied by the reviewer, not a machine check. Only the property named in `verify` (source text) can be confirmed locally.",
}


def _void_if_changed(f, now, report, changes):
    if f["status"] == "approved" and f["approved_basis"] != basis_hash(f):
        f["status"] = "proposed"
        f["approved_basis"] = None
        f["attention"] = "approval void: the proposal or the starting point changed since it was approved; decide again"
        _log(f, now, "proposed", f["attention"], report)
        changes["approval_void"].append(f["id"])


def set_proposal(f, proposal_raw, now, report, changes):
    """Replace the stored proposal when a new one differs. wont-do never gets a new proposal."""
    if proposal_raw is None or f["status"] == "wont-do":
        return
    new = normalize_proposal(proposal_raw, f["proposal"]["summary"], "draft" if proposal_raw.get("proposed") else f["proposal"]["kind"])
    if proposal_hash(new) != proposal_hash(f["proposal"]):
        f["proposal"] = new
        _log(f, now, f["status"], "proposal updated", report)
        changes["proposal_changed"].append(f["id"])


def propose(state: dict, proposals: dict, *, now, report=None) -> dict:
    """Store proposals for existing findings (key = finding ID or identity key). Approved ones whose proposal changes become void."""
    changes = {"proposal_changed": [], "approval_void": [], "ignored": []}
    for ref, raw in proposals.items():
        f = next((x for x in state["findings"] if ref in (x["id"], x["key"])), None)
        if f is None or f["resolution"]:
            raise Stop(f"no open finding '{ref}' for this proposal; nothing was changed")
    for ref, raw in proposals.items():
        f = next(x for x in state["findings"] if ref in (x["id"], x["key"]))
        if f["status"] == "wont-do":
            changes["ignored"].append(f["id"])
            continue
        set_proposal(f, raw, now, report, changes)
        _void_if_changed(f, now, report, changes)
    if changes["proposal_changed"]:
        state["rev"] += 1
        state["updated"] = iso(now)
    return changes


def _touch(f, now, report, raw, proposal_raw, changes):
    old_msg = f["evidence"]["message"]
    f["class"] = raw["class"]
    f["evidence"] = {"message": raw["message"], "occurrences": raw.get("occurrences", 1)}
    f["last_checked"] = {"at": iso(now), "report": report}
    if report not in f["reports"]:
        f["reports"].append(report)
    f["not_observed"] = False
    set_proposal(f, proposal_raw, now, report, changes)
    if old_msg != raw["message"]:
        changes["evidence_changed"].append(f["id"])


def _resolve(f, now, report, via, evidence, changed_files=None):
    f["resolution"] = {"at": iso(now), "report": report, "via": via, "evidence": evidence, "changed_files": changed_files or []}
    f["attention"] = None
    f["not_observed"] = False


def reconcile(state: dict, run: dict, *, now, report: str, proposals=None, editorial=None, applied=(), root=None,
              site_path="", verify_fn=None, applied_files=()) -> dict:
    """Merge one audit run into the state. Pure apart from `verify_fn` (reads source text for editorial verify).

    run["families"][fam] = {"complete": bool, "reason": str, "raw": [...], "exit": int|None}
    Absence of a finding counts as fixed only for a family whose check ran completely in this run.
    """
    proposals = proposals or {}
    changes = {k: [] for k in ("new", "unchanged", "resolved", "reappeared", "proposal_changed", "evidence_changed",
                               "approval_void", "not_observed", "recheck_failed", "recheck_incomplete", "kept")}
    seen = set()
    for fid in applied:
        target = next((x for x in state["findings"] if x["id"] == fid), None)
        if target:
            target["applied"] = {"at": iso(now), "report": report, "files": list(applied_files)}
    for fam in FAMILIES:
        info = run["families"].get(fam)
        if not info or not info["complete"]:
            continue
        for raw in info["raw"]:
            key = fx.identity_key(raw)
            seen.add(key)
            existing = _find(state, key)
            proposal_raw = _pick_proposal(proposals, key, existing["id"] if existing else "")
            if existing is None:
                f = _new_finding(state, raw, now, report, proposal_raw, root, site_path)
                state["findings"].append(f)
                changes["new"].append(f["id"])
                continue
            if existing["resolution"]:
                existing["resolved_before"].append(existing["resolution"])
                existing["resolution"] = None
                existing["reappeared"] += 1
                existing["status"] = "proposed"
                existing["approved_basis"] = None
                existing["applied"] = None
                existing["attention"] = "reappeared after it was marked done; decide again"
                _log(existing, now, "proposed", existing["attention"], report)
                changes["reappeared"].append(existing["id"])
            _touch(existing, now, report, raw, proposal_raw, changes)
            if existing["id"] in applied:
                # the change just made is the reason the evidence differs: not a void approval; the approved scope stays
                existing["approved_basis"] = basis_hash(existing)
            else:
                _void_if_changed(existing, now, report, changes)
            if existing["id"] in applied:
                existing["attention"] = ("applied, but the recheck still reports it (report " + report +
                                         "); approval kept; fix within the approved scope or revise the proposal")
                existing["notes"].append({"at": iso(now), "text": existing["attention"]})
                changes["recheck_failed"].append(existing["id"])
            elif existing["id"] not in changes["new"] and existing["id"] not in changes["reappeared"]:
                changes["unchanged"].append(existing["id"])
    # absence in a complete family
    for f in state["findings"]:
        if f["resolution"] or f["family"] not in FAMILIES:
            continue
        info = run["families"].get(f["family"])
        if f["key"] in seen:
            continue
        if not info or not info["complete"]:
            if f["id"] in applied:
                reason = (info or {}).get("reason") or "check not run"
                f["attention"] = f"applied, recheck of {f['family']} incomplete ({reason}); finding stays open, approval kept; next step: fix the prerequisite and run the audit again"
                f["notes"].append({"at": iso(now), "text": f["attention"]})
                changes["recheck_incomplete"].append(f["id"])
            else:
                changes["kept"].append(f["id"])
            continue
        if f["status"] in ("deferred", "wont-do"):
            f["not_observed"] = True
            f["last_checked"] = {"at": iso(now), "report": report}
            changes["not_observed"].append(f["id"])
            continue
        evidence = (f"not reported by {fx.FAMILY_SCRIPT[f['family']]} in a complete run (exit {info['exit']}) "
                    f"after a successful build")
        via = "apply" if (f["id"] in applied or f.get("applied")) else "external"
        files = (f.get("applied") or {}).get("files", [])
        _resolve(f, now, report, via, evidence, files)
        f["last_checked"] = {"at": iso(now), "report": report}
        if report not in f["reports"]:
            f["reports"].append(report)
        _log(f, now, f["status"], f"done ({via}): {evidence}", report)
        changes["resolved"].append(f["id"])
    # editorial suggestions: never closed by absence
    for item in editorial or []:
        raw = {"family": "editorial", "class": fx.EDITORIAL, "criterion": item["criterion"], "location": item.get("location", fx.GLOBAL),
               "detail": item.get("detail", ""), "message": item.get("evidence", item.get("title", "editorial suggestion")), "occurrences": 1}
        key = fx.identity_key(raw)
        existing = _find(state, key)
        proposal_raw = item.get("proposal")
        if existing is None:
            f = _new_finding(state, raw, now, report, proposal_raw, root, site_path)
            f["title"] = item.get("title", f["title"])
            f["why"] = item.get("why", "editorial judgement")
            f["rule"] = item.get("rule", "editorial judgement (no rule file)")
            f["priority"] = {"level": item.get("priority", {}).get("level", "low"), "reason": item.get("priority", {}).get("reason", "editorial")}
            f["method"] = item.get("method", "reviewer judgement; not a machine check")
            state["findings"].append(f)
            changes["new"].append(f["id"])
        else:
            if existing["resolution"]:
                existing["resolved_before"].append(existing["resolution"])
                existing["resolution"] = None
                existing["reappeared"] += 1
                existing["status"] = "proposed"
                existing["approved_basis"] = None
                existing["attention"] = "suggested again after it was marked done; decide again"
                _log(existing, now, "proposed", existing["attention"], report)
                changes["reappeared"].append(existing["id"])
            _touch(existing, now, report, raw, proposal_raw, changes)
            _void_if_changed(existing, now, report, changes)
    if verify_fn:
        trusted = run.get("status") not in ("incomplete", "readonly-violated")
        for f in state["findings"]:
            v = f["proposal"].get("verify")
            if f["family"] != "editorial" or f["resolution"] or not v or f["status"] in ("deferred", "wont-do"):
                continue
            if not trusted:
                # a failed build, missing prerequisite or violated guard proves nothing: stay open and approved
                if f["id"] in applied:
                    f["attention"] = (f"applied, but the recheck is not valid (run status {run.get('status')}); finding stays open, "
                                      "approval kept; next step: fix the build or the missing prerequisite and run the audit again")
                    f["notes"].append({"at": iso(now), "text": f["attention"]})
                    changes["recheck_incomplete"].append(f["id"])
                elif f["id"] not in changes["kept"]:
                    changes["kept"].append(f["id"])
                continue
            ok, text = verify_fn(v)
            if ok:
                _resolve(f, now, report, "apply" if (f["id"] in applied or f.get("applied")) else "external",
                         f"source-text check passed ({text}); this confirms the text change only, not any effect on rankings or readers",
                         (f.get("applied") or {}).get("files", []))
                _log(f, now, f["status"], "done: " + f["resolution"]["evidence"], report)
                changes["resolved"].append(f["id"])
    state["rev"] += 1
    state["updated"] = iso(now)
    state["last_run"] = {
        "report": report, "at": iso(now), "status": run.get("status"),
        "families": {fam: {"complete": bool(run["families"].get(fam, {}).get("complete")), "exit": run["families"].get(fam, {}).get("exit")} for fam in FAMILIES},
        "changes": {k: v for k, v in changes.items() if v},
    }
    return changes


# ---------------------------------------------------------------- decisions

def decide(state: dict, ids, status: str, *, now, reason=None, change=False) -> list:
    """Record a decision per finding ID. Changing an existing decision requires change=True."""
    if status not in STATUSES:
        raise Stop(f"unknown status '{status}'; allowed: {', '.join(STATUSES)}")
    messages = []
    by_id = {f["id"]: f for f in state["findings"]}
    for fid in ids:
        f = by_id.get(fid)
        if f is None:
            raise Stop(f"unknown finding ID '{fid}' (known: {', '.join(sorted(by_id)) or 'none'})")
        if f["resolution"]:
            raise Stop(f"{fid} is done (history); it can be decided again only if it reappears")
        if status == f["status"]:
            messages.append(f"{fid}: already {status}, nothing changed")
            continue
        if f["status"] != "proposed" and not change:
            raise Stop(f"{fid} is already {f['status']}. Changing an earlier decision needs an explicit instruction (--change).")
        f["status"] = status
        f["approved_basis"] = basis_hash(f) if status == "approved" else None
        f["attention"] = None
        f["not_observed"] = f["not_observed"] and status in ("deferred", "wont-do")
        _log(f, now, status, reason or "decision recorded" + (" (explicit change)" if change else ""))
        if reason:
            f["decision_log"][-1]["reason"] = reason
        messages.append(f"{fid}: {status}")
    if messages:
        state["rev"] += 1
        state["updated"] = iso(now)
    return messages


# ---------------------------------------------------------------- render

def section_of(f: dict) -> str:
    if f["resolution"]:
        return "history"
    return "open" if f["status"] in ("proposed", "approved") else "parked"


def _code(text) -> str:
    text = str(text).replace("\n", " ")
    return "`" + text.replace("`", "'") + "`"


def render_finding(f: dict, report_dir_rel: str = "optimize") -> str:
    p = f["proposal"]
    out = [f"### {f['id']} - {f['title']} ({fx.CLASS_LABEL[f['class']]}) - {f['status']}"]
    if f["attention"]:
        out.append(f"- **Attention:** {f['attention']}")
    out.append(f"- Criterion: {_code(f['criterion'])} - rule: {f['rule']}")
    loc = f"URL {_code(f['location'])}" if f["location"].startswith("/") else f"scope {_code(f['location'])}"
    src = ", ".join(_code(s) for s in f["source_files"]) or "not determined"
    out.append(f"- Location: {loc}; source file(s): {src}" + (f"; detail {_code(f['detail'])}" if f["detail"] else ""))
    occ = f["evidence"]["occurrences"]
    out.append(f"- Evidence: {_code(f['evidence']['message'])}" + (f" ({occ} occurrences)" if occ > 1 else ""))
    out.append(f"- Why an improvement may be worthwhile: {f['why']}")
    out.append(f"- Proposal ({p['kind']}): {p['summary']}")
    if p.get("current") is not None:
        out.append(f"  - current: {_code(p['current'])}")
    if p.get("proposed") is not None:
        out.append(f"  - proposed: {_code(p['proposed'])}")
    for e in p.get("edits", []):
        out.append(f"  - applicable edit in {_code(e['file'])}: replace {_code(e['find'])} with {_code(e['replace'])}")
    if p.get("source"):
        out.append(f"  - source: {p['source']}")
    if p.get("limits"):
        out.append(f"  - limits: {p['limits']}")
    out.append(f"- Priority: {f['priority']['level']} - {f['priority']['reason']}")
    out.append(f"- Method: {f['method']}")
    out.append(f"- Limits: {f['limits']}")
    out.append(f"- First found: {f['first_found']['at']} ({_rel(f['first_found']['report'], report_dir_rel)}); last checked: {f['last_checked']['at']} ({_rel(f['last_checked']['report'], report_dir_rel)})"
               + (f"; reappeared {f['reappeared']}x" if f["reappeared"] else ""))
    out.append("- Reports: " + ", ".join(_rel(r, report_dir_rel) for r in f["reports"]))
    if f["not_observed"]:
        out.append("- Not reported in the latest complete run (appears fixed outside optimize). The decision is kept; nothing is closed without it.")
    if f["resolution"]:
        r = f["resolution"]
        out.append(f"- **Done** {r['at']} via {r['via']} ({_rel(r['report'], report_dir_rel)}): {r['evidence']}" +
                   (f"; changed files: {', '.join(_code(c) for c in r['changed_files'])}" if r["changed_files"] else ""))
    if f["resolved_before"]:
        out.append("- Earlier resolutions: " + "; ".join(f"{r['at']} via {r['via']} ({_rel(r['report'], report_dir_rel)})" for r in f["resolved_before"]))
    out.append("- Decision log:")
    for e in f["decision_log"]:
        why = f" - reason: {e['reason']}" if e.get("reason") else ""
        out.append(f"  - {e['at']}: {e['status']} - {e['note']}{why}")
    for n in f["notes"][-3:]:
        out.append(f"  - note {n['at']}: {n['text']}")
    return "\n".join(out)


def _rel(report: str, base: str) -> str:
    return f"[{report}]({report})" if report else "-"


def render(state: dict) -> str:
    groups = {"open": [], "parked": [], "history": []}
    for f in sorted(state["findings"], key=lambda x: x["id"]):
        groups[section_of(f)].append(f)
    lr = state["last_run"]
    lines = [
        f"# Optimize work list: {state['site']}",
        "",
        "<!-- website-manager-optimize:worklist v1 - generated file. Change decisions with `audit.py decide`, not by editing this text; a hand edit makes the next run stop. -->",
        "",
        "This is the one authoritative status source for `/website-manager:optimize` on this site. Snapshots of single runs are in [optimize/](optimize/) and never change.",
        "Decision status: `proposed` (open), `approved` (this proposal is released for implementation), `deferred`, `wont-do`. Done is a recorded result of a passed recheck, not a decision.",
        "",
    ]
    if lr:
        done = [f"{k}: {'complete' if v['complete'] else 'INCOMPLETE'} (exit {v['exit']})" for k, v in sorted(lr["families"].items())]
        lines += [f"Last run: {lr['at']} - result `{lr['status']}` - report [{lr['report']}]({lr['report']}) - checks: {'; '.join(done)}", ""]
    else:
        lines += ["No audit has run yet.", ""]
    titles = {"open": "Open work (proposed, approved)", "parked": "Deferred and rejected (decisions kept)", "history": "Done (history with implementation and check evidence)"}
    for sec in ("open", "parked", "history"):
        lines += [f"## {titles[sec]}", ""]
        if not groups[sec]:
            lines += ["None.", ""]
        for f in groups[sec]:
            lines += [render_finding(f), ""]
    body = json.dumps(state, indent=1, sort_keys=True, ensure_ascii=False).replace("<", "\\u003c")
    lines += ["## Machine-readable state", "",
              "Generated copy of everything above. Do not edit.", "",
              f"<!-- website-manager-optimize:state sha256={sha(body)} -->", "```json", body, "```", "<!-- /website-manager-optimize:state -->", ""]
    return "\n".join(lines)


def parse(text: str, site: str) -> dict:
    """Read a work list; Stop with a clear message if it is damaged, edited by hand or for another site."""
    m = BEGIN_RE.search(text)
    if not m:
        raise WorklistError("optimize.md has no intact machine-readable state block (damaged or edited). Nothing was changed. Restore it from git or move it aside to start a new list.")
    if sha(m.group(2)) != m.group(1):
        raise WorklistError("optimize.md: the state block does not match its checksum (edited or truncated). Nothing was changed. Restore it from git.")
    try:
        state = json.loads(m.group(2))
    except json.JSONDecodeError as error:
        raise WorklistError(f"optimize.md: state block is not valid JSON ({error}). Nothing was changed.")
    problems = validate(state, site)
    if problems:
        raise WorklistError("optimize.md is invalid: " + "; ".join(problems) + ". Nothing was changed.")
    if render(state) != text:
        raise WorklistError("optimize.md was edited by hand (the text differs from its state block). Nothing was changed and no decision was overwritten. Restore the file from git, or change decisions only with `audit.py decide`.")
    return state


def validate(state, site: str) -> list:
    if not isinstance(state, dict) or state.get("format") != FORMAT:
        return ["not a website-manager-optimize work list"]
    if state.get("version") != VERSION:
        return [f"unsupported version {state.get('version')}"]
    if state.get("site") != site:
        return [f"belongs to site '{state.get('site')}', not '{site}'"]
    problems, ids, keys = [], set(), set()
    required = ("id", "key", "family", "class", "status", "proposal", "evidence", "decision_log", "reports")
    for f in state.get("findings", []):
        if not isinstance(f, dict) or any(k not in f for k in required):
            problems.append("a finding lacks required fields")
            continue
        if f["status"] not in STATUSES:
            problems.append(f"{f['id']}: invalid status '{f['status']}'")
        if f["id"] in ids or f["key"] in keys:
            problems.append(f"{f['id']}: duplicate id or identity")
        ids.add(f["id"])
        keys.add(f["key"])
    return problems


def snapshot_copy(state: dict) -> dict:
    return copy.deepcopy(state)
