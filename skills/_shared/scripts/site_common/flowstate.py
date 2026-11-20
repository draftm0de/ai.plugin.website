"""Versioned project state of the guided website flow (`.project/website/<site-id>/`). Standard library only.

Layout (all inside the selected website project, never in the installed plugin, never inside `sites/`):

    .project/website/<site-id>/flow.json            state record (schema_version 1), written only by this module
    .project/website/<site-id>/brief.json           the current brief (schema_version 1)
    .project/website/<site-id>/brief-history/rNNN.json   every saved brief revision (kept)
    .project/website/<site-id>/design/rNNN/         one immutable design revision: A.html, B.html, ..., index.html (comparison),
                                                    manifest.json, feedback.jsonl (append only)

Principles (docs/development/guided-flow.md):
* A file never proves a finished step. Every derived state is computed from the record AND the hashes of the real artifacts.
* Nothing is deleted or overwritten automatically. A changed brief or a newer design revision marks dependent results *stale*;
  variants, approvals and implementation records stay.
* Unknown or damaged formats are reported (`unreadable`) and block writes; they are never repaired or migrated.
* An approval is bound to one revision, one variant, one variant hash and one confirmed brief hash.
"""
import difflib
import hashlib
import json
import os
import re
import stat
import tempfile
from html.parser import HTMLParser
from pathlib import Path

from . import consistency
from . import manifest as manifest_lib
from .errors import Stop

SCHEMA_VERSION = 1
BASE = Path(".project") / "website"
FLOW = "flow.json"
BRIEF = "brief.json"
SITE_ID_RE = re.compile(r"^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$")
VARIANT_RE = re.compile(r"^[A-Z]$")
MAX_BYTES = 512 * 1024
FIELD_STATUS = ("confirmed", "proposed", "open")
REQUIRED_FIELDS = ("purpose", "audience", "offer", "message", "visitor_action", "tone", "site_language", "design_direction", "palette")
OPTIONAL_FIELDS = ("materials", "notes")
BRIEF_KEYS = {"schema_version", "revision", "fields", "palette_proposals"}
LANG_RE = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


# ------------------------------------------------------------------ file helpers

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def project_dir(root: Path, site: str) -> Path:
    if not SITE_ID_RE.match(site or ""):
        raise Stop(f"'{site}' is not a valid site ID")
    return Path(root) / BASE / site


def _no_links(root: Path, path: Path):
    """Refuse any symlink between the project root and path (itself included)."""
    current = Path(root)
    for part in path.relative_to(root).parts:
        current = current / part
        try:
            mode = os.lstat(current).st_mode
        except FileNotFoundError:
            return
        if stat.S_ISLNK(mode):
            raise Stop(f"{current} is a symlink; the flow state is neither read nor written through links. Nothing was changed.")


def read_bytes(root: Path, path: Path):
    """Bytes of a regular file inside the project, or None when absent. Raises Stop for links, non-files and oversized files."""
    _no_links(root, path)
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode):
        raise Stop(f"{path} is not a regular file. Nothing was changed.")
    if info.st_size > 8 * MAX_BYTES:
        raise Stop(f"{path} is larger than {8 * MAX_BYTES} bytes and is not read.")
    return path.read_bytes()


def write_atomic(root: Path, path: Path, data: bytes):
    _no_links(root, path.parent)
    path.parent.mkdir(parents=True, exist_ok=True)
    _no_links(root, path.parent)
    if path.exists() and (path.is_symlink() or not path.is_file()):
        raise Stop(f"{path} is not a regular file; not replaced.")
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def dumps(data) -> bytes:
    return (json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def _load_json(raw: bytes, label: str):
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Stop(f"{label} is not valid JSON ({error}); not repaired, not overwritten.")


# ------------------------------------------------------------------ brief

def validate_brief(brief, stored=False) -> list:
    """Problems of a brief document (strict; unknown keys are rejected, never dropped)."""
    errors = []
    if not isinstance(brief, dict):
        return ["the brief must be a JSON object"]
    if not _int(brief.get("schema_version")) or brief["schema_version"] != SCHEMA_VERSION:
        errors.append(f"schema_version must be the integer {SCHEMA_VERSION}")
    if "revision" in brief and not _int(brief["revision"], 1 if stored else 0):
        errors.append("revision must be an integer" + (" of at least 1" if stored else ""))
    elif stored and "revision" not in brief:
        errors.append("revision is missing")
    for key in set(brief) - BRIEF_KEYS:
        errors.append(f"unknown top-level key '{key}'")
    fields = brief.get("fields")
    if not isinstance(fields, dict):
        return errors + ["'fields' must be an object"]
    for key in set(fields) - set(REQUIRED_FIELDS) - set(OPTIONAL_FIELDS):
        errors.append(f"unknown field '{key}'")
    for key, field in fields.items():
        if not isinstance(field, dict) or set(field) - {"value", "status", "note"}:
            errors.append(f"field '{key}' must be an object with value, status and optional note")
            continue
        if field.get("status") not in FIELD_STATUS:
            errors.append(f"field '{key}': status must be one of {', '.join(FIELD_STATUS)}")
        if field.get("status") != "open" and field.get("value") in (None, "", [], {}):
            errors.append(f"field '{key}': a {field.get('status')} field needs a value")
    lang = fields.get("site_language", {}).get("value") if isinstance(fields.get("site_language"), dict) else None
    if lang is not None and not (isinstance(lang, str) and LANG_RE.match(lang)):
        errors.append("site_language must be a language tag such as de, en or pt-BR (the language of the website, not of the operator)")
    palette = fields.get("palette", {}).get("value") if isinstance(fields.get("palette"), dict) else None
    if palette is not None:
        errors += _palette_problems(palette, "palette")
    proposals = brief.get("palette_proposals", [])
    if not isinstance(proposals, list):
        errors.append("palette_proposals must be a list")
    else:
        for index, item in enumerate(proposals):
            errors += _palette_problems(item, f"palette_proposals[{index}]", need_reason=True)
    return errors


def _palette_problems(palette, where, need_reason=False) -> list:
    if not isinstance(palette, dict) or set(palette) - {"name", "colors", "rationale"}:
        return [f"{where} must be an object with name, colors and rationale"]
    out = []
    if not isinstance(palette.get("name"), str) or not palette["name"].strip():
        out.append(f"{where}.name is required")
    colors = palette.get("colors")
    if not isinstance(colors, dict) or "primary" not in colors or "background" not in colors:
        out.append(f"{where}.colors needs at least primary and background")
    else:
        for role, value in colors.items():
            if not (isinstance(value, str) and HEX_RE.match(value)):
                out.append(f"{where}.colors.{role} must be a #rrggbb colour")
    if need_reason and not (isinstance(palette.get("rationale"), str) and palette["rationale"].strip()):
        out.append(f"{where}.rationale (short reason) is required")
    return out


def brief_open_items(brief) -> list:
    items = []
    fields = brief.get("fields", {})
    for key in REQUIRED_FIELDS:
        field = fields.get(key)
        if not field:
            items.append(f"{key}: missing")
        elif field.get("status") != "confirmed":
            items.append(f"{key}: {field.get('status')}")
    return items


# ------------------------------------------------------------------ record

def empty_record(site: str) -> dict:
    return {"schema_version": SCHEMA_VERSION, "site": site, "brief": {"revision": 0, "confirmed": None},
            "design": {"revisions": [], "approval": None}, "implementation": None, "checks": None}


SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def _int(value, minimum=0) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _sha(value, nullable=False) -> bool:
    return (nullable and value is None) or (isinstance(value, str) and bool(SHA_RE.match(value)))


def _exact(obj, keys, where, errors) -> bool:
    if not isinstance(obj, dict):
        errors.append(f"{where} must be an object")
        return False
    for key in sorted(set(obj) - set(keys)):
        errors.append(f"{where}: unknown key '{key}'")
    for key in sorted(set(keys) - set(obj)):
        errors.append(f"{where}: missing key '{key}'")
    return set(obj) == set(keys)


def validate_record(record: dict, site: str) -> list:
    """Every field of flow.json, nested types and the relations between them. Returns problems; the record is not modified."""
    errors = []
    _exact(record, ("schema_version", "site", "brief", "design", "implementation", "checks"), "flow.json", errors)
    brief = record.get("brief")
    if _exact(brief, ("revision", "confirmed"), "brief", errors):
        if not _int(brief["revision"]):
            errors.append("brief.revision must be a non-negative integer")
        confirmed = brief["confirmed"]
        if confirmed is not None and _exact(confirmed, ("revision", "sha256", "statement"), "brief.confirmed", errors):
            if not _int(confirmed["revision"], 1) or (_int(brief["revision"]) and confirmed["revision"] > brief["revision"]):
                errors.append("brief.confirmed.revision must be an integer between 1 and brief.revision")
            if not _sha(confirmed["sha256"]):
                errors.append("brief.confirmed.sha256 must be a sha256")
            if not (isinstance(confirmed["statement"], str) and confirmed["statement"].strip()):
                errors.append("brief.confirmed.statement must be a non-empty string")
    design = record.get("design")
    revisions = {}
    if _exact(design, ("revisions", "approval"), "design", errors) and isinstance(design["revisions"], list):
        for index, rev in enumerate(design["revisions"], 1):
            where = f"design.revisions[{index - 1}]"
            if not _exact(rev, ("revision", "brief_revision", "brief_sha256", "variants", "comparison_sha256"), where, errors):
                continue
            if not _int(rev["revision"], 1) or rev["revision"] != index:
                errors.append(f"{where}.revision must be {index} (revisions are numbered without gaps)")
            if not _int(rev["brief_revision"], 1) or (isinstance(brief, dict) and _int(brief.get("revision")) and rev["brief_revision"] > brief["revision"]):
                errors.append(f"{where}.brief_revision must be an integer between 1 and brief.revision")
            for key in ("brief_sha256", "comparison_sha256"):
                if not _sha(rev[key]):
                    errors.append(f"{where}.{key} must be a sha256")
            variants = rev["variants"]
            if not isinstance(variants, dict) or len(variants) < 2:
                errors.append(f"{where}.variants must be an object with at least two variants")
                continue
            for name, entry in variants.items():
                if not VARIANT_RE.match(str(name)):
                    errors.append(f"{where}.variants: invalid variant name '{name}'")
                    continue
                if not _exact(entry, ("file", "sha256"), f"{where}.variants.{name}", errors):
                    continue
                if entry["file"] != f"{name}.html":
                    errors.append(f"{where}.variants.{name}.file must be '{name}.html'")
                if not _sha(entry["sha256"]):
                    errors.append(f"{where}.variants.{name}.sha256 must be a sha256")
            revisions[index] = rev
    elif isinstance(design, dict):
        errors.append("design.revisions must be a list")
    approval = design.get("approval") if isinstance(design, dict) else None
    if approval is not None and _exact(approval, ("revision", "variant", "variant_sha256", "brief_sha256", "statement", "index_sha256_at_approval"), "design.approval", errors):
        rev = revisions.get(approval["revision"]) if _int(approval["revision"], 1) else None
        if rev is None:
            errors.append("design.approval.revision refers to a revision that does not exist")
        else:
            entry = rev["variants"].get(approval["variant"]) if isinstance(rev.get("variants"), dict) and isinstance(approval["variant"], str) else None
            if not isinstance(entry, dict) or entry.get("sha256") != approval["variant_sha256"]:
                errors.append("design.approval.variant does not exist in that revision or its hash differs from the registered one")
            if approval["brief_sha256"] != rev.get("brief_sha256"):
                errors.append("design.approval.brief_sha256 differs from the brief the revision was made from")
        if not _sha(approval["variant_sha256"]) or not _sha(approval["brief_sha256"]) or not _sha(approval["index_sha256_at_approval"], nullable=True):
            errors.append("design.approval hashes must be sha256 values")
        if not (isinstance(approval["statement"], str) and approval["statement"].strip()):
            errors.append("design.approval.statement must be a non-empty string")
    impl = record.get("implementation")
    if impl is not None and _exact(impl, ("status", "approval_revision", "variant", "variant_sha256", "base_sha256", "result_sha256", "edit_session"), "implementation", errors):
        if impl["status"] not in ("started", "done"):
            errors.append("implementation.status must be started or done")
        rev = revisions.get(impl["approval_revision"]) if _int(impl["approval_revision"], 1) else None
        entry = rev["variants"].get(impl["variant"]) if rev and isinstance(rev.get("variants"), dict) and isinstance(impl["variant"], str) else None
        if not isinstance(entry, dict) or entry.get("sha256") != impl["variant_sha256"]:
            errors.append("implementation refers to a revision/variant that does not exist or whose hash differs")
        if not _sha(impl["base_sha256"], nullable=True):
            errors.append("implementation.base_sha256 must be a sha256 or null")
        if impl["status"] == "done" and not _sha(impl["result_sha256"]):
            errors.append("a done implementation needs result_sha256")
        if impl["status"] == "started" and (impl["result_sha256"] is not None or impl["edit_session"] is not None):
            errors.append("a started implementation has no result_sha256 and no edit_session")
        session = impl["edit_session"]
        if impl["status"] == "done":
            if not (isinstance(session, dict) and set(session) == {"folder", "original_sha256", "writes"}
                    and isinstance(session["folder"], str) and _sha(session["original_sha256"]) and _int(session["writes"], 1)):
                errors.append("a done implementation needs edit_session {folder, original_sha256, writes>=1}")
    checks = record.get("checks")
    if checks is not None and _exact(checks, ("for_sha256", "technical", "visual", "visual_note"), "checks", errors):
        if not _sha(checks["for_sha256"]):
            errors.append("checks.for_sha256 must be a sha256")
        for key in ("technical", "visual"):
            if checks[key] not in ("open", "passed", "failed"):
                errors.append(f"checks.{key} must be open, passed or failed")
        if not isinstance(checks["visual_note"], str):
            errors.append("checks.visual_note must be a string")
        if not isinstance(impl, dict) or impl.get("status") != "done":
            errors.append("checks are recorded without a finished implementation")
    if record.get("site") != site:
        errors.append(f"flow.json belongs to site {record.get('site')!r}, not {site!r}")
    if not _int(record.get("schema_version")) or record["schema_version"] != SCHEMA_VERSION:
        errors.append(f"schema_version must be the integer {SCHEMA_VERSION}")
    return errors


def load_record(root: Path, site: str):
    """(record | None when absent, problem | None). A damaged or unknown record is a problem, never replaced."""
    path = project_dir(root, site) / FLOW
    try:
        raw = read_bytes(root, path)
    except Stop as error:
        return None, str(error)
    if raw is None:
        return None, None
    try:
        record = _load_json(raw, str(path))
    except Stop as error:
        return None, str(error)
    if not isinstance(record, dict):
        return None, f"{path} is not a JSON object"
    if not _int(record.get("schema_version")) or record.get("schema_version") != SCHEMA_VERSION:
        return None, (f"{path} has schema_version {record.get('schema_version')!r}; this plugin reads version {SCHEMA_VERSION} only. "
                      "Nothing is migrated or overwritten.")
    if record.get("site") != site:
        return None, f"{path} belongs to site {record.get('site')!r}, not {site!r}"
    errors = validate_record(record, site)
    if errors:
        return None, f"{path} is damaged or inconsistent: " + "; ".join(errors[:8]) + (" ..." if len(errors) > 8 else "") + " Nothing is repaired or overwritten."
    return record, None


def save_record(root: Path, site: str, record: dict):
    write_atomic(root, project_dir(root, site) / FLOW, dumps(record))


def _require_writable(root: Path, site: str):
    record, problem = load_record(root, site)
    if problem:
        raise Stop(f"the flow state is unreadable: {problem} Nothing was written.")
    return record or empty_record(site)


# ------------------------------------------------------------------ derived status

def existing_artifacts(root: Path, site: str = None) -> list:
    """Names (not contents) of website/flow artifacts that exist although there is no manifest, so a project is not 'new'."""
    root = Path(root)
    found = []

    def present(rel):
        return os.path.lexists(root / rel)
    for rel in (".project/specs", ".project/reports"):
        folder = root / rel
        if os.path.lexists(folder):
            try:
                if folder.is_symlink() or any(folder.iterdir()):
                    found.append(rel + "/")
            except OSError:
                found.append(rel + "/ (unreadable)")
    flow = root / BASE
    if os.path.lexists(flow):
        try:
            names = [p.name for p in flow.iterdir()] if not flow.is_symlink() else ["(symlink)"]
        except OSError:
            names = ["(unreadable)"]
        if site is None and names:
            found.append(f"{BASE.as_posix()}/{', '.join(sorted(names))}")
        elif site is not None and (site in names or "(symlink)" in names or "(unreadable)" in names):
            found.append(f"{BASE.as_posix()}/{site}")
    sites_dir = root / "sites"
    if os.path.lexists(sites_dir):
        try:
            names = [p.name for p in sites_dir.iterdir()] if not sites_dir.is_symlink() else ["(symlink)"]
        except OSError:
            names = ["(unreadable)"]
        if site is None and names:
            found.append("sites/" + ", ".join(sorted(names)))
        elif site is not None and (site in names or "(symlink)" in names or "(unreadable)" in names):
            found.append(f"sites/{site}")
    return found


def setup_state(root: Path, site: str) -> dict:
    """missing | complete | contradictory, from the manifest, the configuration and the site folder (not from one file's existence)."""
    root = Path(root)
    manifest_file = root / manifest_lib.SPECS / manifest_lib.FILE
    if not manifest_file.is_file():
        leftovers = existing_artifacts(root, site)
        if leftovers:
            return {"state": "contradictory", "problems": [
                "website or flow artifacts exist (" + "; ".join(leftovers) + ") but .project/specs/website.json is missing. "
                "This is not a new project, so no new setup is started; nothing was changed. Restore the manifest or tell the person."]}
        return {"state": "missing", "problems": []}
    try:
        data = manifest_lib.load(manifest_file)
        errors = manifest_lib.problems(data, root / manifest_lib.SPECS / manifest_lib.SCHEMA)
    except Stop as error:
        return {"state": "contradictory", "problems": [str(error)]}
    if errors:
        return {"state": "contradictory", "problems": errors}
    component = next((c for c in data["components"] if c["name"] == site), None)
    if component is None:
        leftovers = [x for x in existing_artifacts(root, site) if x.endswith(f"/{site}")]
        if leftovers:
            return {"state": "contradictory", "problems": [
                f"the manifest has no site '{site}' but artifacts of it exist ({'; '.join(leftovers)}); no new setup is started and nothing was changed."]}
        return {"state": "missing", "problems": [], "note": f"the project has a manifest but no site '{site}'"}
    problems = []
    folder = root / component["path"]
    if not folder.is_dir() or folder.is_symlink():
        problems.append(f"site folder {component['path']} is missing or a link")
    else:
        for rel in ("package.json", "src/pages/index.astro"):
            if not (folder / rel).is_file():
                problems.append(f"{component['path']}/{rel} is missing")
    found = consistency.check(root, component)
    problems += found["conflicts"]
    unverifiable = found["unverifiable"]
    if problems:
        return {"state": "contradictory", "problems": problems, "unverifiable": unverifiable, "component": component}
    return {"state": "complete", "problems": [], "unverifiable": unverifiable, "component": component}


def _brief_current(root: Path, site: str):
    path = project_dir(root, site) / BRIEF
    raw = read_bytes(root, path)
    if raw is None:
        return None, None, None
    document = _load_json(raw, str(path))
    errors = validate_brief(document, stored=True)
    if errors:
        raise Stop(f"{path} is damaged: " + "; ".join(errors) + " It is not repaired or overwritten.")
    return document, sha256(raw), raw


def derive(root: Path, site: str) -> dict:
    """The complete derived state of one site. Read-only."""
    root = Path(root)
    result = {"site": site, "setup": setup_state(root, site), "problems": [], "stale": []}
    record, problem = load_record(root, site)
    if problem:
        result.update(state="unreadable", next_step="report-damaged-state", problems=[problem])
        return result
    record = record or empty_record(site)
    result["problems"] += result["setup"].get("problems", []) if result["setup"]["state"] == "contradictory" else []
    brief_state = _derive_brief(root, site, record, result)
    design_state = _derive_design(root, site, record, brief_state, result)
    impl_state = _derive_implementation(root, site, record, design_state, result)
    checks = _derive_checks(root, site, record, impl_state, result)
    result.update(brief=brief_state, design=design_state, implementation=impl_state, checks=checks)
    result["next_step"] = _next_step(result)
    result["state"] = "ok" if not [p for p in result["problems"] if p] else "problems"
    return result


def _derive_brief(root, site, record, result) -> dict:
    try:
        document, sha, _ = _brief_current(root, site)
    except Stop as error:
        result["problems"].append(str(error))
        return {"state": "damaged"}
    if document is None:
        if record["brief"]["revision"]:
            result["problems"].append("flow.json records a brief but brief.json is missing")
            return {"state": "damaged"}
        return {"state": "missing"}
    errors = validate_brief(document)
    if errors:
        result["problems"].append("brief.json is invalid: " + "; ".join(errors))
        return {"state": "damaged"}
    if document.get("revision") != record["brief"]["revision"]:
        result["problems"].append(f"brief.json is revision {document.get('revision')} but flow.json records {record['brief']['revision']}")
        return {"state": "damaged"}
    confirmed = record["brief"]["confirmed"]
    state = {"state": "in-progress", "revision": document["revision"], "sha256": sha, "open_items": brief_open_items(document)}
    if confirmed:
        if confirmed["sha256"] == sha:
            state["state"] = "confirmed"
        else:
            state["changed_since_confirmation"] = True
            state["confirmed_revision"] = confirmed["revision"]
    return state


def _variant_problems(root, site, revision) -> list:
    folder = project_dir(root, site) / "design" / f"r{revision['revision']:03d}"
    out = []
    for name, entry in sorted(revision["variants"].items()):
        try:
            raw = read_bytes(root, folder / entry["file"])
        except Stop as error:
            out.append(str(error))
            continue
        if raw is None:
            out.append(f"design revision {revision['revision']}: variant {name} ({entry['file']}) is missing")
        elif sha256(raw) != entry["sha256"]:
            out.append(f"design revision {revision['revision']}: variant {name} was changed after it was registered")
    for label, name, expected in (("comparison page", "index.html", revision["comparison_sha256"]), ("revision manifest", "manifest.json", None)):
        try:
            raw = read_bytes(root, folder / name)
        except Stop as error:
            out.append(str(error))
            continue
        if raw is None:
            out.append(f"design revision {revision['revision']}: the {label} ({name}) is missing")
        elif expected is not None and sha256(raw) != expected:
            out.append(f"design revision {revision['revision']}: the {label} ({name}) was changed after it was registered")
        elif expected is None and raw != dumps(revision):
            out.append(f"design revision {revision['revision']}: the {label} ({name}) differs from the registered record")
    return out


def _feedback_count(root, site, number) -> int:
    path = project_dir(root, site) / "design" / f"r{number:03d}" / "feedback.jsonl"
    try:
        raw = read_bytes(root, path)
    except Stop:
        return 0
    return len([line for line in (raw or b"").decode("utf-8", "replace").splitlines() if line.strip()])


def _derive_design(root, site, record, brief_state, result) -> dict:
    revisions = record["design"]["revisions"]
    if not revisions:
        return {"state": "missing", "revisions": 0}
    latest = revisions[-1]
    state = {"revisions": len(revisions), "latest": latest["revision"], "variants": sorted(latest["variants"]), "feedback_on_latest": _feedback_count(root, site, latest["revision"])}
    damaged = [p for rev in revisions for p in _variant_problems(root, site, rev)]
    if damaged:
        result["problems"] += damaged
        state["state"] = "damaged"
        return state
    confirmed = record["brief"]["confirmed"]
    basis_ok = brief_state.get("state") == "confirmed" and confirmed and latest["brief_sha256"] == confirmed["sha256"]
    if not basis_ok:
        state["state"] = "stale"
        state["reason"] = "the brief changed or is not confirmed since these variants were made"
        result["stale"].append("design")
    approval = record["design"]["approval"]
    if approval:
        state["approval"] = {k: approval[k] for k in ("revision", "variant")}
        reason = None
        if approval["revision"] != latest["revision"]:
            reason = f"revision {latest['revision']} was made after the approval of revision {approval['revision']}"
        elif not basis_ok or approval["brief_sha256"] != (confirmed or {}).get("sha256"):
            reason = "the brief changed after the approval"
        state["approval"]["stale"] = bool(reason)
        if reason:
            state["approval"]["reason"] = reason
            result["stale"].append("approval")
        if not reason:
            state["state"] = "approved"
            return state
    if "state" not in state:
        state["state"] = "revising" if state["feedback_on_latest"] else "variants"
    return state


def _index_sha(root, component) -> str:
    raw = read_bytes(root, Path(root) / component["path"] / "src" / "pages" / "index.astro")
    return sha256(raw) if raw is not None else None


def _derive_implementation(root, site, record, design_state, result) -> dict:
    impl = record.get("implementation")
    if not impl:
        return {"state": "missing"}
    if design_state.get("state") == "damaged":
        return {"state": "blocked", "reason": "a registered design artifact is missing or changed; the implementation record is kept but not used"}
    component = result["setup"].get("component")
    current = _index_sha(root, component) if component else None
    approval_ok = design_state.get("state") == "approved"
    same_approval = bool(record["design"]["approval"]) and impl["approval_revision"] == record["design"]["approval"]["revision"] \
        and impl["variant_sha256"] == record["design"]["approval"]["variant_sha256"]
    state = {"approval_revision": impl["approval_revision"], "variant": impl["variant"]}
    if not approval_ok or not same_approval:
        state["state"] = "stale"
        state["reason"] = "the approved design or the brief changed after the implementation was started; the written page is kept"
        result["stale"].append("implementation")
        return state
    if impl["status"] == "started":
        state["state"] = "started"
        if current != impl["base_sha256"]:
            state["page_changed_since_start"] = True      # edit result or change by the person: not decided without an edit result
        return state
    if current != impl["result_sha256"]:
        state["state"] = "user-changed"
        state["reason"] = "src/pages/index.astro differs from the page this flow wrote; it is not overwritten"
        return state
    state["state"] = "done"
    return state


def _derive_checks(root, site, record, impl_state, result) -> dict:
    checks = record.get("checks")
    base = {"technical": "open", "visual": "open"}
    if impl_state.get("state") != "done" or not checks:
        return base
    component = result["setup"].get("component")
    if not component or checks["for_sha256"] != _index_sha(root, component):
        return {**base, "outdated": True}
    return {"technical": checks["technical"], "visual": checks["visual"]}


def _next_step(result) -> str:
    setup, brief, design = result["setup"]["state"], result["brief"], result["design"]
    if setup == "missing":
        return "setup"
    if setup == "contradictory":
        return "resolve-setup"
    if brief["state"] == "damaged" or design.get("state") == "damaged" or result["implementation"].get("state") == "blocked":
        return "report-damaged-state"
    if brief["state"] in ("missing", "in-progress"):
        return "brief"
    if design["state"] in ("missing", "stale"):
        return "design"
    if design["state"] == "variants":
        return "design-choose"
    if design["state"] == "revising":
        return "design-revise"
    impl, checks = result["implementation"], result["checks"]
    if design["state"] == "approved":
        if impl["state"] == "started" and impl.get("page_changed_since_start"):
            return "resolve-implementation-conflict"
        if impl["state"] in ("missing", "started", "stale"):
            return "implement"
        if impl["state"] == "user-changed":
            return "resolve-user-change"
        if checks["technical"] != "passed" or checks["visual"] != "passed":
            return "checks"
        return "done"
    return "design"


# ------------------------------------------------------------------ operations

def brief_save(root: Path, site: str, document: dict) -> dict:
    errors = validate_brief(document)
    if errors:
        raise Stop("the brief is invalid; nothing was saved:\n  " + "\n  ".join(errors))
    record = _require_writable(root, site)
    current, _sha_unused, raw = _brief_current(root, site)
    if current is None and record["brief"]["revision"]:
        raise Stop("flow.json records a brief but brief.json is missing; nothing is overwritten. Restore it from brief-history/ first.")
    if current is not None and current["revision"] != record["brief"]["revision"]:
        raise Stop(f"brief.json is revision {current['revision']} but flow.json records {record['brief']['revision']} "
                   "(an earlier write was interrupted?). Nothing is overwritten or repaired; check brief-history/ first.")
    candidate = dict(document)
    candidate["revision"] = record["brief"]["revision"]
    if current is not None and dumps(candidate) == raw:
        return {"state": "unchanged", "revision": record["brief"]["revision"]}
    revision = record["brief"]["revision"] + 1
    candidate["revision"] = revision
    data = dumps(candidate)
    folder = project_dir(root, site)
    history = folder / "brief-history" / f"r{revision:03d}.json"
    kept = read_bytes(root, history)
    if kept is not None and kept != data:
        raise Stop(f"brief-history/r{revision:03d}.json already exists with different content (an earlier write was interrupted?). "
                   "History is never overwritten; nothing was saved. Compare the files and resolve it by hand.")
    if kept is None:
        write_atomic(root, history, data)
    write_atomic(root, folder / BRIEF, data)
    record["brief"]["revision"] = revision
    save_record(root, site, record)
    return {"state": "saved", "revision": revision, "open_items": brief_open_items(candidate),
            "invalidates": ["confirmation"] if record["brief"]["confirmed"] else []}


def brief_confirm(root: Path, site: str, statement: str) -> dict:
    if not statement or not statement.strip():
        raise Stop("a confirmation needs the person's explicit statement (--statement); a preselected option or silence is not one.")
    record = _require_writable(root, site)
    document, sha, _ = _brief_current(root, site)
    if document is None:
        raise Stop("there is no brief to confirm")
    if document["revision"] != record["brief"]["revision"]:
        raise Stop(f"brief.json is revision {document['revision']} but flow.json records {record['brief']['revision']}; nothing is confirmed.")
    errors = validate_brief(document)
    if errors:
        raise Stop("the brief is invalid: " + "; ".join(errors))
    open_items = brief_open_items(document)
    if open_items:
        raise Stop("the brief cannot be confirmed while required fields are not confirmed: " + ", ".join(open_items))
    confirmed = record["brief"]["confirmed"]
    if confirmed and confirmed["sha256"] == sha:
        return {"state": "unchanged", "revision": document["revision"]}
    record["brief"]["confirmed"] = {"revision": document["revision"], "sha256": sha, "statement": statement.strip()}
    save_record(root, site, record)
    return {"state": "confirmed", "revision": document["revision"]}


def _require_confirmed_brief(root, site, record):
    document, sha, _ = _brief_current(root, site)
    confirmed = record["brief"]["confirmed"]
    if document is None or not confirmed or confirmed["sha256"] != sha:
        raise Stop("the brief is not confirmed (or changed after its confirmation); design variants are only made from a confirmed brief.")
    return document, sha


def design_new(root: Path, site: str, feedback: str = None) -> dict:
    """Create (or resume) the directory of the next design revision. Earlier revisions stay untouched."""
    record = _require_writable(root, site)
    document, brief_sha = _require_confirmed_brief(root, site, record)
    if setup_state(root, site)["state"] != "complete":
        raise Stop("setup is not complete for this site; no design revision is started.")
    revisions = record["design"]["revisions"]
    folder = project_dir(root, site) / "design"
    number = (revisions[-1]["revision"] if revisions else 0) + 1
    target = folder / f"r{number:03d}"
    _no_links(root, target)
    if target.exists():
        return {"state": "resumed", "revision": number, "path": str(target.relative_to(root))}
    if revisions and not (record["design"]["approval"] or _feedback_count(root, site, revisions[-1]["revision"]) or
                          revisions[-1]["brief_sha256"] != brief_sha):
        raise Stop(f"revision {revisions[-1]['revision']} has no feedback yet; record the person's feedback (design-feedback) before a new revision.")
    target.mkdir(parents=True)
    if feedback and revisions:
        write_atomic(root, target / "from-feedback.txt", feedback.strip().encode("utf-8") + b"\n")
    return {"state": "created", "revision": number, "path": str(target.relative_to(root)), "brief_revision": document["revision"],
            "site_language": document["fields"]["site_language"]["value"], "palette": document["fields"]["palette"]["value"]}


class _Scan(HTMLParser):
    STRUCT = {"header", "nav", "main", "section", "article", "aside", "footer", "h1", "h2", "h3", "ul", "ol", "figure", "form", "blockquote", "table"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skeleton, self.stack, self.unmarked, self.open_texts = [], [], [], []
        self.lang, self.scripts, self.external, self.css, self._in_style = None, 0, [], [], False
        self.void = {"br", "img", "meta", "link", "hr", "input", "source"}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.lang = attrs.get("lang")
        if tag == "script":
            self.scripts += 1
        if tag == "style":
            self._in_style = True
        for key in ("src", "href", "action", "poster", "data"):
            value = (attrs.get(key) or "").strip().lower()
            if value.startswith(("http:", "https:", "//", "ftp:", "data:text/html")) or value.startswith("javascript:"):
                self.external.append(f"<{tag} {key}=...>")
        if "style" in attrs:
            self.css.append(attrs["style"])
        if tag in self.STRUCT:
            self.skeleton.append(tag)
        if tag not in self.void:
            self.stack.append("open" if "data-open-fact" in attrs else tag)

    def handle_endtag(self, tag):
        if tag == "style":
            self._in_style = False
        if tag in self.void:
            return
        while self.stack:
            if self.stack.pop() in ("open", tag):
                break

    def handle_data(self, data):
        if self._in_style:
            self.css.append(data)
            return
        text = " ".join(data.split())
        if not text:
            return
        if "open" in self.stack:
            self.open_texts.append(text)
        elif "title" not in self.stack:
            self.unmarked.append(text)


_RISKY = [
    (re.compile(r"(€|\bEUR\b|\bCHF\b|\bUSD\b|\$|£)\s?\d|\d\s?(€|\bEUR\b|\bCHF\b|\bUSD\b|\$|£)", re.I), "a price"),
    (re.compile(r"\d\s?%"), "a percentage"),
    (re.compile(r"\b(seit|since|gegründet|founded)\s+(19|20)\d{2}\b", re.I), "a founding year"),
    (re.compile(r"\b\d{1,3}\s+(jahre|years|patienten|patients|kunden|customers|clients)\b", re.I), "a count or duration"),
    (re.compile(r"\b(zertifiziert\w*|certified|accredited|akkreditiert\w*|ausgezeichnet\w*|award[- ]winning|testsieger|garantiert\w*|guaranteed|heilt|heilung|cures?)\b", re.I), "a qualification, award or guarantee"),
    (re.compile(r"\b(\+?\d[\d /-]{7,}\d)\b"), "a phone number"),
]


def validate_variant(text: str, brief: dict) -> dict:
    """Structural checks of one prototype (not a design review, not proof that no claim is invented). Returns {"problems", "skeleton"}."""
    problems = []
    if not text.lstrip().lower().startswith("<!doctype html"):
        problems.append("must start with <!doctype html>")
    if re.search(r"lorem ipsum|dolor sit amet|consectetur adipiscing", text, re.I):
        problems.append("contains placeholder filler text (lorem ipsum); write a real text draft")
    scan = _Scan()
    scan.feed(text)
    scan.close()
    if scan.scripts:
        problems.append("contains <script>; prototypes are static")
    if scan.external:
        problems.append("references external or script resources (" + ", ".join(sorted(set(scan.external))) + "); prototypes are self-contained")
    language = brief["fields"]["site_language"]["value"].split("-")[0].lower()
    if not scan.lang or scan.lang.split("-")[0].lower() != language:
        problems.append(f"<html lang> must be the website language '{language}' (found {scan.lang!r})")
    primary = brief["fields"]["palette"]["value"]["colors"]["primary"].lower()
    if primary not in " ".join(scan.css).lower():
        problems.append(f"the confirmed primary colour {primary} is not used in the styles")
    for chunk in scan.unmarked:
        for pattern, label in _RISKY:
            if pattern.search(chunk):
                problems.append(f"unmarked {label}: '{chunk[:60]}'. Facts the brief does not state must sit in an element with data-open-fact")
    if any(not t.strip() for t in scan.open_texts) or ("data-open-fact" in text and not scan.open_texts):
        problems.append("a data-open-fact element has no visible text")
    for required in ("h1",):
        if required not in scan.skeleton:
            problems.append("needs exactly one visible h1")
    if scan.skeleton.count("h1") > 1:
        problems.append("has more than one h1")
    return {"problems": problems, "skeleton": scan.skeleton, "open_facts": len(scan.open_texts)}


def _distinct(a, b) -> bool:
    return difflib.SequenceMatcher(None, a, b).ratio() <= 0.75


def comparison_page(revision: int, names) -> str:
    cells = "\n".join(f'<section><h2>Variante {n}</h2><iframe src="{n}.html" title="Variante {n}" loading="lazy"></iframe>'
                      f'<p><a href="{n}.html">Variante {n} einzeln</a></p></section>' for n in names)
    return ("<!doctype html>\n<html lang=\"de\"><head><meta charset=\"utf-8\"><title>Entwurfsvergleich Revision " + str(revision) + "</title>"
            "<style>body{font-family:system-ui,sans-serif;margin:1rem}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(24rem,1fr));gap:1rem}"
            "iframe{width:100%;height:42rem;border:1px solid #888}</style></head><body><h1>Entwurfsvergleich, Revision " + str(revision) +
            "</h1><p>Lokale Prototypen, nicht Teil der Website.</p><main>\n" + cells + "\n</main></body></html>\n")


def design_register(root: Path, site: str, revision: int) -> dict:
    record = _require_writable(root, site)
    document, brief_sha = _require_confirmed_brief(root, site, record)
    folder = project_dir(root, site) / "design" / f"r{revision:03d}"
    _no_links(root, folder)
    if not folder.is_dir():
        raise Stop(f"design/r{revision:03d} does not exist; start it with design-new")
    names = sorted(p.stem for p in folder.glob("*.html") if VARIANT_RE.match(p.stem))
    existing = next((r for r in record["design"]["revisions"] if r["revision"] == revision), None)
    if existing:
        problems = _variant_problems(root, site, existing)
        if problems:
            raise Stop("this revision is registered and was changed afterwards; revisions are immutable, make a new one:\n  " + "\n  ".join(problems))
        return {"state": "unchanged", "revision": revision, "variants": sorted(existing["variants"])}
    if revision != (record["design"]["revisions"][-1]["revision"] + 1 if record["design"]["revisions"] else 1):
        raise Stop("revisions are registered in order")
    if len(names) < 2:
        raise Stop(f"a design revision needs at least two variants (A.html, B.html, ...); found {len(names)}")
    scans, problems = {}, []
    for name in names:
        raw = read_bytes(root, folder / f"{name}.html")
        if len(raw) > MAX_BYTES:
            problems.append(f"{name}.html is larger than {MAX_BYTES} bytes")
            continue
        result = validate_variant(raw.decode("utf-8", "replace"), document)
        scans[name] = result["skeleton"]
        problems += [f"{name}.html: {p}" for p in result["problems"]]
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if a in scans and b in scans and not _distinct(scans[a], scans[b]):
                problems.append(f"variants {a} and {b} have (nearly) the same page structure; a colour change is not a second design direction")
    if problems:
        raise Stop("the variants are not registered:\n  " + "\n  ".join(problems))
    kept = read_bytes(root, folder / "manifest.json")
    if kept is not None:
        raise Stop(f"design/r{revision:03d}/manifest.json exists but the revision is not registered (an earlier write was interrupted?). It is not overwritten; resolve it by hand.")
    write_atomic(root, folder / "index.html", comparison_page(revision, names).encode("utf-8"))
    variants = {n: {"file": f"{n}.html", "sha256": sha256(read_bytes(root, folder / f"{n}.html"))} for n in names}
    entry = {"revision": revision, "brief_revision": document["revision"], "brief_sha256": brief_sha, "variants": variants,
             "comparison_sha256": sha256(read_bytes(root, folder / "index.html"))}
    write_atomic(root, folder / "manifest.json", dumps(entry))
    record["design"]["revisions"].append(entry)
    save_record(root, site, record)
    return {"state": "registered", "revision": revision, "variants": names, "comparison": str((folder / "index.html").relative_to(root))}


def design_feedback(root: Path, site: str, text: str) -> dict:
    if not text or not text.strip():
        raise Stop("feedback must not be empty")
    record = _require_writable(root, site)
    revisions = record["design"]["revisions"]
    if not revisions:
        raise Stop("there is no design revision to give feedback on")
    number = revisions[-1]["revision"]
    path = project_dir(root, site) / "design" / f"r{number:03d}" / "feedback.jsonl"
    old = read_bytes(root, path) or b""
    line = json.dumps({"text": text.strip()}, ensure_ascii=False).encode("utf-8") + b"\n"
    if old.endswith(line):
        return {"state": "unchanged", "revision": number}
    write_atomic(root, path, old + line)
    return {"state": "recorded", "revision": number}


def design_approve(root: Path, site: str, revision: int, variant: str, statement: str) -> dict:
    if not statement or not statement.strip():
        raise Stop("an approval needs the person's explicit statement (--statement). 'Variant B pleases me more' is a preference, not an approval of a revision.")
    record = _require_writable(root, site)
    _require_confirmed_brief(root, site, record)
    setup = setup_state(root, site)
    if setup["state"] != "complete":
        raise Stop("setup is not complete for this site; nothing is approved.")
    revisions = record["design"]["revisions"]
    if not revisions or revisions[-1]["revision"] != revision:
        raise Stop(f"revision {revision} is not the latest shown revision ({revisions[-1]['revision'] if revisions else 'none'}); an approval is bound to the revision the person saw.")
    latest = revisions[-1]
    if variant not in latest["variants"]:
        raise Stop(f"variant {variant} does not exist in revision {revision}")
    problems = _variant_problems(root, site, latest)
    if problems:
        raise Stop("the variants differ from what was registered; nothing is approved:\n  " + "\n  ".join(problems))
    confirmed = record["brief"]["confirmed"]
    if latest["brief_sha256"] != confirmed["sha256"]:
        raise Stop("the brief changed since these variants were made; make a new revision first.")
    approval = {"revision": revision, "variant": variant, "variant_sha256": latest["variants"][variant]["sha256"],
                "brief_sha256": confirmed["sha256"], "statement": statement.strip(),
                "index_sha256_at_approval": _index_sha(root, setup["component"])}
    current = record["design"]["approval"]
    if current and all(current.get(k) == approval[k] for k in ("revision", "variant", "variant_sha256", "brief_sha256")):
        return {"state": "unchanged", "revision": revision, "variant": variant}
    record["design"]["approval"] = approval
    save_record(root, site, record)
    return {"state": "approved", "revision": revision, "variant": variant}


def _valid_approval(root, site, record):
    derived_result = {"setup": setup_state(root, site), "problems": [], "stale": []}
    brief_state = _derive_brief(root, site, record, derived_result)
    design_state = _derive_design(root, site, record, brief_state, derived_result)
    if design_state.get("state") != "approved":
        raise Stop("there is no valid design approval (none given, or it is stale: " + design_state.get("approval", {}).get("reason", design_state.get("reason", "not approved")) + ")")
    return record["design"]["approval"], derived_result["setup"]["component"]


def implement_start(root: Path, site: str, accept_current_page: bool = False) -> dict:
    record = _require_writable(root, site)
    approval, component = _valid_approval(root, site, record)
    current = _index_sha(root, component)
    impl = record["implementation"]
    same = impl and impl["approval_revision"] == approval["revision"] and impl["variant_sha256"] == approval["variant_sha256"]
    if same and impl["status"] == "done":
        if current == impl["result_sha256"]:
            return {"state": "already-implemented", "revision": approval["revision"], "variant": approval["variant"]}
        raise Stop("the approved design was implemented, but src/pages/index.astro was changed afterwards. It is not overwritten; "
                   "the person decides whether the current page or the approved design wins.")
    if same and impl["status"] == "started":
        variant_file = f"design/r{approval['revision']:03d}/{approval['variant']}.html"
        if current == impl["base_sha256"]:
            return {"state": "resumed", "base_sha256": current, "variant_file": variant_file}
        if accept_current_page:      # the person agreed that the current page is the new starting point; the design approval stays valid
            impl["base_sha256"] = current
            save_record(root, site, record)
            return {"state": "started", "base_sha256": current, "variant_file": variant_file, "rebased": True}
        return {"state": "resumed-changed", "base_sha256": impl["base_sha256"], "current_sha256": current, "variant_file": variant_file,
                "message": "src/pages/index.astro differs from the start state. If an `edit` session wrote it, record that session with "
                           "implement-finish --edit-state <folder of that edit session>. Otherwise it may be the person's own change: "
                           "ask whether it is the new starting point (then implement-start --accept-current-page). Nothing was overwritten."}
    if current != approval["index_sha256_at_approval"] and not accept_current_page:
        raise Stop("src/pages/index.astro was changed after the approval (by the person or another tool). It is not overwritten. "
                   "Show the person the difference; continue with --accept-current-page only after they agree.")
    record["implementation"] = {"status": "started", "approval_revision": approval["revision"], "variant": approval["variant"],
                                "variant_sha256": approval["variant_sha256"], "base_sha256": current, "result_sha256": None, "edit_session": None}
    record["checks"] = None
    save_record(root, site, record)
    return {"state": "started", "base_sha256": current, "variant_file": f"design/r{approval['revision']:03d}/{approval['variant']}.html",
            "prototype_dir": str((project_dir(root, site) / 'design' / f"r{approval['revision']:03d}").relative_to(root))}


EDIT_FILE = "src/pages/index.astro"


def _edit_session_proof(root: Path, component: dict, impl: dict, folder, current: str) -> dict:
    """Read the state of an `edit` session (the folder `edit.py begin` returned) and check that it is the session of THIS implementation:
    same project and site, started from the recorded start state, at least one write of its own, and the last write is the current page.
    Plain consistency checks of edit's own record, no cryptography: edit.py is the only writer of that record. Read-only."""
    path = Path(folder)
    if not path.is_absolute() or os.path.islink(path) or not path.is_dir():
        raise Stop(f"--edit-state {folder} is not an edit session folder (absolute path of the folder `edit.py begin` returned).")
    area = Path(os.path.realpath(Path(tempfile.gettempdir()) / "zyris-website" / sha256(str(Path(root).resolve()).encode())[:12]))
    if Path(os.path.realpath(path)).parent != area:
        raise Stop("that edit session does not belong to this project (it is not in the project's own session area).")
    index = path / "index.json"
    try:
        info = os.lstat(index)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 4 * 1024 * 1024:
            raise OSError("not a regular file")
        state = json.loads(index.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise Stop("the edit session record is missing, a link or damaged; nothing was recorded.")
    if not isinstance(state, dict):
        raise Stop("the edit session record is damaged; nothing was recorded.")
    problems = []
    if state.get("root") != str(Path(root).resolve()):
        problems.append("it belongs to another project folder")
    if state.get("site") != component["name"] or state.get("site_path") != component["path"]:
        problems.append("it belongs to another site")
    if state.get("file") != EDIT_FILE:
        problems.append("it does not edit the start page")
    if state.get("original_sha") != impl["base_sha256"]:
        problems.append("it was not started from the recorded start state of this implementation (the page was changed in between, "
                        "or this is a later session on content that is not the recorded start)")
    writes = state.get("writes")
    if not isinstance(writes, list) or not writes or not all(isinstance(w, str) for w in writes):
        problems.append("it contains no write of its own (a check alone proves nothing)")
    elif writes[-1] != current or state.get("expected_sha") != current:
        problems.append("its last write is not the current content of the page (the page was changed after the edit session)")
    if problems:
        raise Stop("the edit session does not prove this implementation: " + "; ".join(problems) + ". Nothing was recorded, nothing overwritten. "
                   "A manual change of the page is not an implementation of the approved design; ask the person.")
    return {"folder": path.name, "original_sha256": state["original_sha"], "writes": len(writes)}


def implement_finish(root: Path, site: str, edit_state: str = None) -> dict:
    """Record the implementation as done, bound to this implementation, project, site, start hash and a proven write of an `edit` session."""
    record = _require_writable(root, site)
    approval, component = _valid_approval(root, site, record)
    impl = record["implementation"]
    if not impl or impl["approval_revision"] != approval["revision"] or impl["variant_sha256"] != approval["variant_sha256"]:
        raise Stop("no implementation is started for the current approval")
    current = _index_sha(root, component)
    if impl["status"] == "done":
        if impl["result_sha256"] == current:
            return {"state": "unchanged", "result_sha256": current}
        raise Stop("the implementation was recorded as done for different content; the page changed afterwards and is not overwritten.")
    if current == impl["base_sha256"]:
        raise Stop("src/pages/index.astro is unchanged since the start; nothing was implemented, so it is not recorded as done.")
    if not edit_state:
        raise Stop("an `edit` session of this implementation is needed (--edit-state: the folder `edit.py begin` returned; finish this record "
                   "before `edit.py finish`, which removes that folder).")
    session = _edit_session_proof(root, component, impl, edit_state, current)
    impl.update(status="done", result_sha256=current, edit_session=session)
    record["checks"] = None
    save_record(root, site, record)
    return {"state": "implemented", "result_sha256": current, "edit_session": session}


def record_checks(root: Path, site: str, technical_evidence: dict = None, visual: str = "open", visual_note: str = "") -> dict:
    """technical: only from an `edit.py check` result bound to the current page content. visual: reported by the person/agent."""
    record = _require_writable(root, site)
    derived = derive(root, site)
    if derived["implementation"].get("state") != "done":
        raise Stop("the implementation is not recorded as done; checks are not recorded")
    current = _index_sha(root, derived["setup"]["component"])
    technical = "open"
    if technical_evidence is not None:
        build, check = technical_evidence.get("build", {}), technical_evidence.get("check", {})
        if technical_evidence.get("checked_sha") != current:
            raise Stop("the check result does not belong to the current content of src/pages/index.astro; run the checks again")
        if technical_evidence.get("state") == "checked" and build.get("exit") == 0 and check.get("exit") == 0:
            technical = "passed"
        elif technical_evidence.get("state") == "failed":
            technical = "failed"
        else:
            technical = "open"
    if visual not in ("open", "passed", "failed"):
        raise Stop("visual must be open, passed or failed")
    if visual == "passed" and not visual_note.strip():
        raise Stop("a passed visual check needs a note of what was looked at (--visual-note)")
    record["checks"] = {"for_sha256": current, "technical": technical, "visual": visual, "visual_note": visual_note.strip()}
    save_record(root, site, record)
    return {"state": "recorded", "technical": technical, "visual": visual}
