"""Static Astro sites: create, adopt, plan and verify (behaviour: references/setup.md).

One planner (`make_plan`) computes everything a run would do and validates it; `setup plan` prints it and stops,
`create`/`adopt` apply exactly that plan. So the pre-write verdict of plan and run cannot differ.
Python standard library only. Nothing here commits, pushes, talks to a server or installs globally.
"""
import copy
import hashlib
import json
import os
import re
import shlex
import stat
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from site_common import project_files
from site_common.errors import Stop as ProjectFilesError
import manifest
import ownership
import scratch
import validate
from clone import TPL, render, unresolved
from errors import Ask, Stop
from site_common import consistency
from site_common import manifest as shared_manifest
from site_common import schema as schemalib  # noqa: F401  (shared validator; used via manifest)

SKILL_DIR = Path(__file__).resolve().parents[1]
RES = SKILL_DIR / "templates"
OUTPUT_DIRS = ("node_modules", "dist", ".astro")   # git-ignored local output of install/build
LOCKFILE = "package-lock.json"
SEGMENT_RE = re.compile(r"^[A-Za-z0-9._-]+$")
ENV_RE = re.compile(r"^[A-Za-z0-9._-]+$")
TAIL_LINES = 40
STEPS = ("install", "build", "check")

# Injection points for tests (a failing write/rename/removal must roll back).
_replace = os.replace          # commit step: temp file -> final name
_restore = os.replace          # rollback: put the previous content back
_unlink = os.unlink            # rollback: remove a file this run created


def _write_all(fd, data):
    view = memoryview(data)
    while view:
        view = view[os.write(fd, view):]


_write = _write_all            # test injection: write the bytes of a staged file


class _Halt(Exception):
    """Planning cannot continue; the problem is already recorded."""


@dataclass
class Options:
    operation: str                       # create | adopt | verify
    site: str                            # stable internal site ID (manifest name, folder name, ownership key)
    root: str = None
    site_type: str = None
    sites_dir: str = None
    title: str = None
    aliases: tuple = ()
    port: int = None
    environment: str = None
    build: bool = False
    domain: str = None                   # public domain, only when explicitly given


@dataclass
class Write:
    path: Path
    data: bytes          # None for kind "dir"
    kind: str            # file | dir
    reason: str = ""


@dataclass
class Plan:
    operation: str
    site: str
    problems: list = field(default_factory=list)     # [(level, text)] level: ask | invalid | conflict
    changes: list = field(default_factory=list)      # [{"path", "action", "reason"}]
    findings: list = field(default_factory=list)     # [{"level": blocking|warning, "text"}]
    notes: list = field(default_factory=list)
    writes: list = field(default_factory=list)
    unchanged: bool = False
    root: Path = None
    site_dir: Path = None
    rel_site: str = ""
    type_cfg: dict = None
    component: dict = None
    tree_before: str = None
    manifest_file: Path = None
    templates_rendered: dict = field(default_factory=dict)   # site-relative path -> bytes (create)

    def add(self, level, text):
        self.problems.append((level, text))

    def change(self, path, action, reason=""):
        self.changes.append({"path": path, "action": action, "reason": reason})

    @property
    def state(self):
        levels = {level for level, _ in self.problems}
        for level, state in (("ask", "needs-input"), ("invalid", "invalid"), ("conflict", "conflict")):
            if level in levels:
                return state
        return "unchanged" if self.unchanged else "ok"


# ---------------------------------------------------------------- helpers

def sha_file(path: Path):
    return ownership.sha256(path.read_bytes()) if path.is_file() else None


def tree_hash(folder: Path) -> str:
    """Hash of every file (path, content) and symlink below folder, except node_modules."""
    digest = hashlib.sha256()
    for current, dirs, files in os.walk(folder, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(current) == folder and d == "node_modules"))
        for name in sorted(files + [d for d in dirs if (Path(current) / d).is_symlink()]):
            path = Path(current) / name
            rel = path.relative_to(folder).as_posix()
            if path.is_symlink():
                digest.update(f"L {rel} {os.readlink(path)}\n".encode())
            else:
                digest.update(f"F {rel} {ownership.sha256(path.read_bytes())}\n".encode())
    return digest.hexdigest()


def check_rel_dir(value, label) -> str:
    if not isinstance(value, str) or not value:
        raise Stop(f"{label} must be a relative folder path inside the repository")
    if value.startswith("/") or "\\" in value or re.match(r"^[A-Za-z]:", value):
        raise Stop(f"{label} '{value}' is an absolute path; it must be relative to the repository root")
    for part in value.split("/"):
        if part in ("", ".", ".."):
            raise Stop(f"{label} '{value}' contains '{part or 'an empty segment'}'; no '..' or empty segments allowed")
        if not SEGMENT_RE.match(part):
            raise Stop(f"{label} '{value}' contains characters outside A-Z a-z 0-9 . _ -")
    return value


def check_no_symlink(root: Path, parts, label):
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise Stop(f"{label}: '{current.relative_to(root).as_posix()}' is a symlink; setup does not write through symlinks")
        if not current.exists():
            break


def check_root(value) -> Path:
    root = Path(value).resolve() if value else Path.cwd().resolve()
    if not root.is_dir():
        raise Stop(f"--root {root} is not a folder")
    return root


def load_schema_bytes() -> bytes:
    if not manifest.PLUGIN_SCHEMA.is_file():
        raise Stop(f"{manifest.PLUGIN_SCHEMA} is missing: the plugin installation is incomplete. Nothing was written.")
    return manifest.PLUGIN_SCHEMA.read_bytes()   # the one schema of the plugin (skills/_shared/resources)


def template_files(type_cfg: dict, values: dict) -> dict:
    """site-relative path -> rendered bytes, from the one complete template folder of the type."""
    layer = RES / type_cfg["template"]
    if not layer.is_dir():
        raise Stop(f"Template folder missing: {layer}")
    chosen = {}
    for src in sorted(p for p in layer.rglob("*") if p.is_file()):
        rel = src.relative_to(layer)
        is_tpl = src.name.endswith(TPL)
        if is_tpl:
            rel = rel.with_name(src.name[: -len(TPL)])
        chosen[rel.as_posix()] = (src, is_tpl)
    rendered = {}
    for rel, (src, is_tpl) in sorted(chosen.items()):
        if ".." in Path(rel).parts or Path(rel).is_absolute():
            raise Stop(f"Template path escapes the site folder: {rel}")
        if is_tpl:
            text = render(src.read_text(encoding="utf-8"), values)
            left = unresolved(text)
            if left:
                raise Stop(f"Unresolved placeholders {left} in template {src.relative_to(RES)}")
            rendered[rel] = text.encode("utf-8")
        else:
            rendered[rel] = src.read_bytes()
    return rendered


def conformance(root: Path, target: Path, type_cfg: dict, rel_site: str) -> list:
    """Read-only findings of an existing site folder (adopt). Never repairs anything."""
    findings = []

    def add(level, text):
        findings.append({"level": level, "text": text})
    package = target / "package.json"
    scripts = {}
    if not package.is_file():
        add("blocking", f"{rel_site}/package.json is missing")
    else:
        try:
            data = json.loads(package.read_text(encoding="utf-8"))
            scripts = data.get("scripts", {}) if isinstance(data, dict) else {}
            if not isinstance(scripts, dict):
                scripts = {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            add("blocking", f"{rel_site}/package.json is not valid JSON")
        else:
            if "build" not in scripts:
                add("blocking", f"{rel_site}/package.json has no 'build' script")
            if "check" not in scripts:
                add("warning", "no 'check' script (SEO/accessibility audit); --build will report failed-check. Remedy: add the audit scripts of the astro-static template")
    for rel in type_cfg.get("ignored", []):
        if not project_files.is_ignored(root, f"{rel_site}/{rel}"):
            add("blocking", f"build output path not git-ignored: {rel_site}/{rel}")
    if not (target / LOCKFILE).is_file():
        add("warning", f"no {LOCKFILE}: installs are not reproducible. Remedy: run npm install and keep the lockfile in the project")
    for rel in ("rules/accessibility.md", "rules/seo.md"):
        if not (target / rel).is_file():
            add("warning", f"{rel_site}/{rel} is missing (binding site rule)")
    for rel in ("scripts/seo-check.mjs", "scripts/a11y-check.mjs"):
        if not (target / rel).is_file():
            add("warning", f"audit script {rel_site}/{rel} is missing")
    for config in sorted(target.glob("astro.config.*")):
        try:
            text = config.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if re.search(r"\badapter\s*:", text) or re.search(r"\boutput\s*:\s*['\"](server|hybrid)['\"]", text):
            add("warning", f"{config.name} suggests a non-static build (adapter or server output); heuristic, not verified")
    return findings


# ---------------------------------------------------------------- planning

def _validate_inputs(opts, config):
    site = validate.check_site_id(opts.site)
    domain = validate.check_domain(opts.domain) if opts.domain is not None else None
    if opts.operation == "create":
        site_type = validate.check_type(opts.site_type, config)
    else:
        site_type = opts.site_type or "astro-static"
        if site_type not in config["types"]:
            raise Stop(f"Unsupported type '{site_type}'. Supported: {', '.join(sorted(config['types']))}.")
    cfg = config["types"][site_type]
    validate.check_port(opts.port)
    if opts.title is not None and not opts.title.strip():
        raise Stop("--title must not be empty")
    aliases = list(opts.aliases)
    for alias in aliases:
        if not alias.strip() or alias != alias.strip() or "\n" in alias:
            raise Stop(f"--alias '{alias}' is empty or has surrounding whitespace")
    if len({a.lower() for a in aliases}) != len(aliases):
        raise Stop("--alias values must be unique")
    if opts.environment is not None and not ENV_RE.match(opts.environment):
        raise Stop(f"--environment '{opts.environment}' is not valid (A-Z a-z 0-9 . _ -)")
    return site, domain, site_type, cfg, aliases


def _schema_plan(plan, root, schema_file, record, new_bytes):
    """Decide what happens to the project's copy of the manifest schema. Returns the schema dict to validate with."""
    rel = schema_file.relative_to(root).as_posix()
    new_sha = ownership.sha256(new_bytes)
    new_schema = json.loads(new_bytes)
    action = None
    if not schema_file.exists():
        action, reason = "create", "manifest schema copy is absent"
    else:
        current = schema_file.read_bytes()
        cur_sha = ownership.sha256(current)
        recorded = record["project_files"].get(rel)
        if cur_sha == new_sha:
            plan.change(rel, "keep", "equals the current plugin schema" + ("" if recorded else " (no ownership record: not claimed as managed)"))
            return new_schema, None
        if recorded:
            if recorded["sha256"] == cur_sha:
                action, reason = "modify", f"managed file, unmodified (recorded hash {cur_sha[:12]} equals current): replaced by the current plugin schema"
            else:
                plan.add("conflict", f"{rel} was modified after setup wrote it (recorded {recorded['sha256'][:12]}, current {cur_sha[:12]}); "
                                     "not extended. Compare it with the plugin schema or restore the recorded version.")
        else:
            plan.add("conflict", f"{rel} has no ownership record and differs from the plugin schema (current {cur_sha[:12]}, plugin {new_sha[:12]}); "
                                 "an unknown or modified schema is never replaced automatically. "
                                 "Compare it with the plugin schema (skills/_shared/resources/website.schema.json).")
        if action is None:
            plan.change(rel, "conflict", "schema copy is custom, unknown or modified")
            return new_schema, None
    plan.change(rel, action, reason)
    return new_schema, Write(schema_file, new_bytes, "file", reason)


def _existing_differences(existing, expected):
    return [f"{k}: stored {existing.get(k)!r}, requested {expected.get(k)!r}"
            for k in sorted(set(existing) | set(expected)) if existing.get(k) != expected.get(k)]


def _plan_registered(plan, opts, record, existing, expected, target, schema_action):
    """The domain is registered: identical repetition = unchanged, anything else = conflict (never a write)."""
    domain, reasons = opts.site, []   # `domain` here is the site ID (ownership key)
    # Preconditions are re-checked on every repetition: "unchanged" only describes a site that still qualifies.
    if not target.is_dir():
        plan.add("invalid", f"{plan.rel_site} is registered but the folder is missing (or not a folder); nothing was written. "
                            "Restore the folder or fix the registration by hand; setup does not repair it.")
        return
    if opts.operation == "adopt":
        plan.findings = conformance(plan.root, target, plan.type_cfg, plan.rel_site)
        blocking = [f["text"] for f in plan.findings if f["level"] == "blocking"]
        if blocking:
            for text in blocking:
                plan.add("invalid", "blocking finding: " + text)
            return
    found = consistency.check(plan.root, existing)
    for text in found["conflicts"]:
        plan.add("invalid", "manifest and site configuration contradict each other: " + text)
    for text in found["unverifiable"]:
        plan.findings.append({"level": "warning", "text": text})
    if found["conflicts"]:
        return
    diff = _existing_differences(existing, expected)
    if diff:
        reasons.append("registered with different values (" + "; ".join(diff) + ")")
    entry = record["sites"].get(domain)
    want_mode = "created" if opts.operation == "create" else "adopted"
    if entry is None:
        reasons.append("registered without an ownership record (not created by this setup protocol)")
    elif entry["mode"] != want_mode:
        reasons.append(f"registered with mode '{entry['mode']}', this call is '{opts.operation}'")
    elif entry["type"] != expected["type"]:
        reasons.append(f"recorded type '{entry['type']}' differs from '{expected['type']}'")
    else:
        for rel, recorded in sorted(entry["files"].items()):
            path = target / rel
            if not path.is_file():
                reasons.append(f"managed file missing: {plan.rel_site}/{rel}")
            elif sha_file(path) != recorded:
                reasons.append(f"managed file modified: {plan.rel_site}/{rel}")
    if schema_action is not None:
        reasons.append("the project's manifest schema copy would have to change")
    if reasons:
        way = ("`setup verify` re-runs install/build/check on repaired files (it never regenerates); "
               "`setup update` and `--regenerate` are planned, not available. ") if opts.operation == "create" else ""
        hint = " use `adopt` to register an existing folder." if entry is None and opts.operation == "create" else ""
        plan.add("conflict", f"'{domain}' is already registered and this {opts.operation} is not an identical repetition: "
                             + "; ".join(reasons) + ". " + way + hint)
        return
    plan.unchanged = True
    plan.change(f".project/specs/website.json", "keep", "entry equals the requested values")
    plan.change(plan.rel_site, "keep", "managed files equal their recorded hashes" if entry["files"] else "adopted site, untouched")


def _plan(opts, plan):
    config = validate.load_config(RES)
    defaults = config["defaults"]
    site, domain, site_type, cfg, aliases = _validate_inputs(opts, config)
    root = check_root(opts.root)
    plan.root, plan.type_cfg = root, cfg
    sites_dir = check_rel_dir(opts.sites_dir or defaults["sites_dir"], "--path")
    check_no_symlink(root, sites_dir.split("/") + [site], "site path")
    check_no_symlink(root, [".project", "specs"], ".project/specs")
    for leaf in (".gitignore", defaults["tmp_dir"]):
        if (root / leaf).is_symlink():
            raise Stop(f"{leaf} is a symlink; setup does not write through symlinks")
    rel_site = f"{sites_dir}/{site}"
    # Validate existing local ignore syntax before any planned write.
    project_files.IgnoreRules(root).ignored(f"{rel_site}/dist/index.html")
    target = root / rel_site
    plan.site_dir, plan.rel_site = target, rel_site
    manifest_file, schema_file = manifest.files(root)
    plan.manifest_file = manifest_file
    managed_file = root / ownership.MANAGED
    record = ownership.load(managed_file)

    new_bytes = load_schema_bytes()
    type_names = list(config["types"])

    if manifest_file.exists():
        data = manifest.load(manifest_file)
        if not isinstance(data, dict):
            raise Stop(f"{manifest_file} is not a JSON object")
    else:
        data = json.loads(render((RES / "_manifest" / "static" / "website.json.tpl").read_text(encoding="utf-8"), {}))
    schema_dict, schema_write = _schema_plan(plan, root, schema_file, record, new_bytes)
    errors = manifest.problems(data, schema_dict, type_names)
    if errors:
        raise Stop("existing manifest is invalid:\n  " + "\n  ".join(errors))

    components = data["components"]
    existing = next((c for c in components if c["name"] == site), None)
    port = opts.port or (existing.get("port") if existing else None)
    if port is None and existing is not None:
        port = manifest.effective_ports(components)[components.index(existing)]   # registered without explicit port: compared, never rewritten
    elif port is None:
        port = manifest.next_port(components)    # 4321 in an empty project, else highest effective port + 1; stops at the range end
    site_url = f"https://{domain}" if domain else None
    values = {"name": site, "site": site, "type": site_type, "path": rel_site, "title": opts.title or site,
              "aliases": ", ".join(aliases), "port": port,
              "site_config": f"  site: '{site_url}',\n" if site_url else "",
              "site_value": json.dumps(site_url),
              "domain_line": f"Domain: {domain}" if domain else "Domain: not decided yet (manifest has no `domain`; no public URL is configured).",
              "lead_line": f'<p class="page-header__lead">{domain}</p>' if domain else ""}
    values.update({f"{k}_json": json.dumps(v) for k, v in list(values.items())})
    values["aliases_json"] = json.dumps(aliases)
    fragment = render((RES / "_manifest" / "component-static.json.tpl").read_text(encoding="utf-8"), values)
    left = unresolved(fragment)
    if left:
        raise Stop(f"Unresolved placeholders {left} in the manifest fragment")
    expected = json.loads(fragment)
    if domain:
        expected["domain"] = domain
    if opts.environment:
        expected["environment"] = opts.environment
    plan.component = expected

    if existing is not None:
        _plan_registered(plan, opts, record, existing, expected, target, schema_write)
        return

    # ---- not registered
    findings = []
    if opts.operation == "create":
        if target.exists() and (not target.is_dir() or any(target.iterdir())):
            plan.add("conflict", f"{rel_site} exists and is not registered: create never writes into an existing folder. "
                                 "Use `adopt` to register it.")
            raise _Halt
        plan.templates_rendered = template_files(cfg, values)
        planned = consistency.check_texts(domain, plan.templates_rendered[consistency.CONFIG].decode("utf-8"),
                                          plan.templates_rendered[consistency.LIB].decode("utf-8"))
        for text in planned["conflicts"] + planned["unverifiable"]:
            plan.add("invalid", "planned state is inconsistent (nothing was written): " + text)
        if plan.problems:
            raise _Halt
    else:
        if not target.is_dir():
            plan.add("invalid", f"{rel_site} does not exist (adopt needs an existing folder)")
            raise _Halt
        findings = conformance(root, target, cfg, rel_site)
        plan.findings = findings
        for finding in findings:
            if finding["level"] == "blocking":
                plan.add("invalid", "blocking finding: " + finding["text"])
        found = consistency.check(root, expected)
        for text in found["conflicts"]:
            plan.add("invalid", "the existing folder contradicts the requested domain: " + text)
        for text in found["unverifiable"]:
            plan.findings.append({"level": "warning", "text": text})
        plan.tree_before = tree_hash(target)

    # collisions with other sites (conflicts, not input errors)
    own_keys = [site.lower(), *([domain.lower()] if domain else []), *[a.lower() for a in aliases]]
    for other in components:
        for key in [other["name"], other.get("domain", ""), *other.get("aliases", [])]:
            if key and key.lower() in own_keys:
                plan.add("conflict", f"'{key}' is already a name or alias of site '{other['name']}'")
    if opts.port:
        for other, effective in zip(components, manifest.effective_ports(components)):
            if effective == opts.port:
                plan.add("conflict", f"port {opts.port} is already used by site '{other['name']}'"
                         + ("" if "port" in other else " (effective port derived from its position, the entry has no explicit port)"))
    if plan.problems:
        raise _Halt
    after = copy.deepcopy(data)
    after["components"].append(expected)
    errors = manifest.problems(after, schema_dict, type_names)
    if errors:
        plan.add("invalid", "resulting manifest would be invalid:\n  " + "\n  ".join(errors))
        raise _Halt

    # ---- writes (order: site files, scratch, schema, ownership record, manifest last)
    template_version = cfg["template_version"]
    writes = []
    for rel, data_bytes in plan.templates_rendered.items():
        writes.append(Write(target / rel, data_bytes, "file", "from template"))
        plan.change(f"{rel_site}/{rel}", "create", "from template")
    tmp_dir = defaults["tmp_dir"]
    if not (root / tmp_dir).is_dir():
        writes.append(Write(root / tmp_dir, None, "dir", "scratch folder"))
        plan.change(f"{tmp_dir}/", "create", "scratch folder, git-ignored")
    gitignore = root / ".gitignore"
    current = gitignore.read_text(encoding="utf-8") if gitignore.is_file() else ""
    updated = scratch.gitignore_after(current, tmp_dir)
    if updated is not None:
        writes.append(Write(gitignore, updated.encode("utf-8"), "file", f"{tmp_dir}/ ignore entry"))
        plan.change(".gitignore", "modify" if gitignore.exists() else "create", f"adds {tmp_dir}/")
    if schema_write:
        writes.append(schema_write)
    new_record = copy.deepcopy(record)
    if schema_write:
        new_record["project_files"][schema_file.relative_to(root).as_posix()] = {"sha256": ownership.sha256(new_bytes),
                                                                                 "template_version": template_version}
    new_record["sites"][site] = {"mode": "created" if opts.operation == "create" else "adopted", "type": site_type,
                                   "template_version": template_version,
                                   "files": {rel: ownership.sha256(b) for rel, b in sorted(plan.templates_rendered.items())}}
    writes.append(Write(managed_file, ownership.dumps(new_record), "file", "ownership record"))
    plan.change(ownership.MANAGED, "modify" if managed_file.exists() else "create", "hashes of the files written by this run")
    manifest_bytes = (json.dumps(after, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    writes.append(Write(manifest_file, manifest_bytes, "file", f"registers {site}"))
    plan.change(".project/specs/website.json", "modify" if manifest_file.exists() else "create", f"registers {site}")
    if opts.operation == "adopt":
        plan.change(rel_site, "keep", "adopt writes no file below the site folder")
    plan.writes = writes


def _plan_set_domain(opts, plan):
    """Later domain assignment: only the manifest `domain` and the two generated files that carry the address change.
    Site ID, folder, port and ownership keys stay. Anything that is not an unmodified generated file is a conflict (no write)."""
    config = validate.load_config(RES)
    site = validate.check_site_id(opts.site)
    if not opts.domain:
        raise Ask("Which domain should the site use (e.g. example.com)?")
    domain = validate.check_domain(opts.domain)
    root = check_root(opts.root)
    plan.root = root
    manifest_file, schema_file = manifest.files(root)
    plan.manifest_file = manifest_file
    if not manifest_file.is_file():
        raise Stop(f"{manifest_file} not found; '{site}' is not registered")
    data = manifest.load(manifest_file)
    errors = manifest.problems(data, schema_file, list(config["types"]))
    if errors:
        raise Stop("manifest is invalid:\n  " + "\n  ".join(errors))
    components = data["components"]
    component = next((c for c in components if c["name"] == site), None)
    if component is None:
        raise Stop(f"'{site}' is not registered in the manifest")
    check_no_symlink(root, component["path"].split("/"), "site path")
    plan.rel_site, plan.site_dir = component["path"], root / component["path"]
    plan.type_cfg = config["types"][component["type"]]
    if component.get("domain") == domain:
        found = consistency.check(root, component)
        if found["conflicts"]:
            plan.add("invalid", "manifest and site configuration contradict each other: " + "; ".join(found["conflicts"]))
            return
        plan.unchanged = True
        plan.change(".project/specs/website.json", "keep", f"domain is already {domain}")
        return
    if "domain" in component:
        plan.add("conflict", f"'{site}' already has the domain '{component['domain']}'; changing a decided domain is not available.")
        return
    other = next((c["name"] for c in components if c.get("domain") == domain or domain in c.get("aliases", [])), None)
    if other:
        plan.add("conflict", f"'{domain}' already belongs to site '{other}'")
        return
    before = consistency.check(root, component)
    if before["conflicts"] or before["unverifiable"]:
        plan.add("invalid", "the current configuration cannot be changed safely: " + "; ".join(before["conflicts"] + before["unverifiable"]))
        return
    record = ownership.load(root / ownership.MANAGED)
    entry = record["sites"].get(site)
    managed = (entry or {}).get("files", {})
    if not entry or entry["mode"] != "created":
        plan.add("conflict", f"'{site}' was not created by setup, so its address configuration is not managed here: set `site` in "
                             f"{component['path']}/astro.config.mjs and SITE in {component['path']}/src/lib/site.ts yourself, then add `domain` to the manifest.")
        return
    index = components.index(component)
    values = {"name": site, "site": site, "type": component["type"], "path": component["path"], "title": component.get("title", site),
              "aliases": ", ".join(component.get("aliases", [])), "port": component.get("port", manifest.effective_ports(components)[index]),
              "site_config": f"  site: 'https://{domain}',\n", "site_value": json.dumps(f"https://{domain}"),
              "domain_line": f"Domain: {domain}", "lead_line": f'<p class="page-header__lead">{domain}</p>'}
    values.update({f"{k}_json": json.dumps(v) for k, v in list(values.items())})
    values["aliases_json"] = json.dumps(component.get("aliases", []))
    rendered = template_files(plan.type_cfg, values)
    new_record = copy.deepcopy(record)
    writes = []
    for rel in (consistency.CONFIG, consistency.LIB):
        path = plan.site_dir / rel
        if rel not in managed or not path.is_file() or path.is_symlink() or sha_file(path) != managed[rel]:
            plan.add("conflict", f"{component['path']}/{rel} was changed after setup wrote it (or is missing); it is not replaced. "
                                 "Set the address there yourself, then add `domain` to the manifest.")
            continue
        writes.append(Write(path, rendered[rel], "file", "address of the site"))
        new_record["sites"][site]["files"][rel] = ownership.sha256(rendered[rel])
        plan.change(f"{component['path']}/{rel}", "modify", "site address from the new domain")
    if plan.problems:
        return
    expected = {}
    for key, value in component.items():
        expected[key] = value
        if key == "name":
            expected["domain"] = domain
    after = copy.deepcopy(data)
    after["components"][index] = expected
    errors = manifest.problems(after, schema_file, list(config["types"]))
    if errors:
        plan.add("invalid", "resulting manifest would be invalid:\n  " + "\n  ".join(errors))
        return
    planned = consistency.check_texts(domain, rendered[consistency.CONFIG].decode("utf-8"), rendered[consistency.LIB].decode("utf-8"))
    if planned["conflicts"] or planned["unverifiable"]:
        plan.add("invalid", "planned state is inconsistent (nothing was written): " + "; ".join(planned["conflicts"] + planned["unverifiable"]))
        return
    writes.append(Write(root / ownership.MANAGED, ownership.dumps(new_record), "file", "ownership record"))
    plan.change(ownership.MANAGED, "modify", "hashes of the two changed files")
    writes.append(Write(manifest_file, (json.dumps(after, indent=2, ensure_ascii=False) + "\n").encode("utf-8"), "file", f"domain of {site}"))
    plan.change(".project/specs/website.json", "modify", f"adds domain {domain} to {site}")
    plan.component, plan.writes = expected, writes


def make_plan(opts) -> Plan:
    plan = Plan(opts.operation, opts.site)
    try:
        if opts.operation == "set-domain":
            _plan_set_domain(opts, plan)
            return plan
        _plan(opts, plan)
    except _Halt:
        pass
    except Ask as question:
        plan.add("ask", str(question))
    except (Stop, ProjectFilesError) as stop:
        plan.add("invalid", str(stop))
    return plan


# ---------------------------------------------------------------- writing

def verify_written(plan: Plan) -> list:
    """Checks after the renames, before any build. Returns problems."""
    problems = []
    for w in plan.writes:
        if w.kind == "dir":
            if not w.path.is_dir():
                problems.append(f"missing folder: {w.path}")
        elif not w.path.is_file():
            problems.append(f"missing file: {w.path}")
        elif w.path.read_bytes() != w.data:
            problems.append(f"content differs from the plan: {w.path}")
    for rel in plan.templates_rendered:
        path = plan.site_dir / rel
        if plan.site_dir not in path.resolve().parents:
            problems.append(f"file outside {plan.site_dir}: {path}")
        elif path.suffix not in {".png", ".webp", ".ico", ".jpg"}:
            try:
                left = unresolved(path.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, OSError):
                continue
            if left:
                problems.append(f"unresolved placeholders {left} in {path}")
    try:
        data = manifest.load(plan.manifest_file)
        stored = next((c for c in data["components"] if c["name"] == plan.site), None)
        if stored != plan.component:
            problems.append(f"'{plan.site}' is not registered as planned in {plan.manifest_file}")
    except (Stop, KeyError, TypeError) as error:
        problems.append(f"manifest unreadable after writing: {error}")
    for rel in plan.type_cfg.get("ignored", []):
        if not project_files.is_ignored(plan.root, f"{plan.rel_site}/{rel}"):
            problems.append(f"not git-ignored: {plan.rel_site}/{rel}")
    if plan.tree_before is not None and tree_hash(plan.site_dir) != plan.tree_before:
        problems.append(f"{plan.rel_site} changed during adopt (it must stay byte-identical)")
    return problems


def _default_mode() -> int:
    mask = os.umask(0)
    os.umask(mask)
    return 0o666 & ~mask


def _stage(path: Path, data: bytes, mode: int, staged: list) -> Path:
    """Write data to a fresh, exclusively created temporary file next to `path` and return its real path.
    mkstemp creates with O_EXCL under an unpredictable name: an existing file or symlink is never opened.
    The path is recorded in `staged` right after creation, so every failure path can remove exactly this file."""
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".zw-tmp")
    tmp = Path(name)
    staged.append(tmp)
    try:
        _write(fd, data)
        os.fchmod(fd, mode)
    finally:
        os.close(fd)
    return tmp


def _ensure_dirs(path: Path, created: list):
    missing = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    for folder in reversed(missing):
        folder.mkdir()
        created.append(folder)


def apply(plan: Plan) -> dict:
    """Write the plan. Returns {"ok": True} or {"ok": False, "state": failed-rolled-back|failed-partial, "error", "remaining"}."""
    snapshots, created_dirs, staged, done, tmps = {}, [], [], [], {}
    for w in plan.writes:
        if w.kind == "file":
            snapshots[w.path] = (w.path.read_bytes(), stat.S_IMODE(w.path.stat().st_mode)) if w.path.exists() else None
    try:
        for w in plan.writes:
            if w.kind == "dir":
                _ensure_dirs(w.path, created_dirs)
        for w in plan.writes:
            if w.kind != "file":
                continue
            _ensure_dirs(w.path.parent, created_dirs)
            mode = snapshots[w.path][1] if snapshots[w.path] else _default_mode()
            tmps[w.path] = _stage(w.path, w.data, mode, staged)
        for w in plan.writes:
            if w.kind != "file":
                continue
            _replace(tmps[w.path], w.path)
            done.append(w.path)
        problems = verify_written(plan)
        if problems:
            raise Stop("verification failed:\n  " + "\n  ".join(problems))
        return {"ok": True}
    except Exception as error:   # noqa: BLE001 - every failure before the build is rolled back
        return _rollback(snapshots, created_dirs, staged, done, error)


def _rollback(snapshots, created_dirs, staged, done, error) -> dict:
    failures = []
    for path in reversed(done):
        try:
            previous = snapshots.get(path)
            if previous is None:
                _unlink(path)
            else:
                _restore(_stage(path, previous[0], previous[1], staged), path)
        except Exception as problem:   # noqa: BLE001
            failures.append(f"{path}: {problem}")
    for tmp in staged:
        try:
            tmp.unlink(missing_ok=True)
        except Exception as problem:   # noqa: BLE001
            failures.append(f"{tmp}: {problem}")
    for folder in reversed(created_dirs):
        try:
            folder.rmdir()
        except FileNotFoundError:
            pass
        except Exception as problem:   # noqa: BLE001
            failures.append(f"{folder}: {problem}")
    remaining = []
    for path, previous in snapshots.items():
        now = path.read_bytes() if path.is_file() else None
        if now != (previous[0] if previous else None):
            remaining.append(f"{path} ({'created by this run, still present' if previous is None else 'content not restored'})")
    remaining += [f"{t} (temporary file)" for t in staged if t.exists()]
    remaining += [f"{d}/ (folder created by this run, still present)" for d in created_dirs if d.exists()]
    state = "failed-partial" if remaining else "failed-rolled-back"
    return {"ok": False, "state": state, "error": str(error), "remaining": remaining, "rollback_errors": failures}


# ---------------------------------------------------------------- install / build / check

def default_runner(argv, cwd):
    """(ran, exit_code, output). A command that cannot be started did not run."""
    try:
        result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, errors="replace")
    except FileNotFoundError:
        return False, None, f"command not found: {argv[0]}"
    return True, result.returncode, (result.stdout or "") + (result.stderr or "")


def run_steps(site_dir: Path, cfg: dict, runner=None) -> dict:
    """Run install, build, check in order. A step that ran keeps its real exit code; later steps after a failure: ran false."""
    runner = runner or default_runner
    lock = site_dir / LOCKFILE
    lock_before = sha_file(lock)
    steps = {name: {"command": cfg.get(name, "npm run check" if name == "check" else None), "ran": False, "exit": None} for name in STEPS}
    failed, tail, notes = None, [], []
    for name in STEPS:
        if failed:
            continue
        ran, code, output = runner(shlex.split(steps[name]["command"]), site_dir)
        steps[name]["ran"], steps[name]["exit"] = ran, code
        if not ran or code != 0:
            failed, tail = name, output.strip().splitlines()[-TAIL_LINES:]
        elif name == "build" and not (site_dir / cfg["output"]).is_dir():
            failed, tail = "build", [f"build exited 0 but the output folder {cfg['output']}/ does not exist"]
    lock_after = sha_file(lock)
    lockfile = ("created" if lock_before is None and lock_after else "changed" if lock_before != lock_after
                else "unchanged" if lock_after else "absent")
    local = [f"{d}/" for d in OUTPUT_DIRS if (site_dir / d).is_dir()]
    if lockfile in ("created", "changed"):
        notes.append(f"{LOCKFILE} was {lockfile} by npm: versioned file, review it; no commit required for local work")
    return {"steps": steps, "failed": failed, "tail": tail, "lockfile": lockfile, "local_output": local, "notes": notes}


def _not_run():
    return {n: {"ran": False, "exit": None} for n in STEPS}


# ---------------------------------------------------------------- results

EXIT = {"updated": 0, "created": 0, "adopted": 0, "verified": 0, "unchanged": 0, "planned": 0, "needs-input": 2}


def _result(operation, domain, state, plan=None, **extra):
    result = {"state": state, "operation": operation, "site": domain,
              "changes": plan.changes if plan else [], "findings": plan.findings if plan else [],
              "notes": list(plan.notes) if plan else [], "verification": _not_run(), "exit": EXIT.get(state, 1)}
    result.update(extra)
    return result


def _problem_result(plan, state):
    return _result(plan.operation, plan.site, state, plan, problems=[text for _, text in plan.problems])


def plan_only(opts) -> dict:
    plan = make_plan(opts)
    if plan.state == "ok":
        return _result(opts.operation, opts.site, "planned", plan)
    if plan.state == "unchanged":
        return _result(opts.operation, opts.site, "unchanged", plan)
    return _problem_result(plan, plan.state)


def _attach_build(result, outcome, success_state):
    verification = {name: {"command": s["command"], "ran": s["ran"], "exit": s["exit"]} for name, s in outcome["steps"].items()}
    result["verification"] = verification
    result["lockfile"], result["local_output"] = outcome["lockfile"], outcome["local_output"]
    result["notes"] += outcome["notes"]
    if outcome["failed"]:
        result["state"] = "failed-check" if outcome["failed"] == "check" else "failed-build"
        result["failed_step"], result["output_tail"], result["exit"] = outcome["failed"], outcome["tail"], 1
        result["notes"].append("generated files and registration stay; restart with `setup verify " + result["site"] + "`")
    else:
        result["state"], result["exit"] = success_state, 0


def execute(opts, runner=None) -> dict:
    """create | adopt. Same planner as `plan`; then write, verify, optionally build."""
    plan = make_plan(opts)
    if plan.state in ("needs-input", "invalid", "conflict"):
        return _problem_result(plan, plan.state)
    if plan.unchanged:
        result = _result(opts.operation, opts.site, "unchanged", plan)
        if opts.build:
            _attach_build(result, run_steps(plan.site_dir, plan.type_cfg, runner), "unchanged")
        return result
    outcome = apply(plan)
    if not outcome["ok"]:
        return _result(opts.operation, opts.site, outcome["state"], plan, error=outcome["error"],
                       remaining=outcome["remaining"], rollback_errors=outcome["rollback_errors"])
    final = "created" if opts.operation == "create" else "adopted"
    result = _result(opts.operation, opts.site, final, plan)
    if opts.build:
        _attach_build(result, run_steps(plan.site_dir, plan.type_cfg, runner), final)
    return result


def set_domain(opts, plan_only_mode=False) -> dict:
    """setup set-domain <site> <domain>: later domain assignment; ID, folder, port and other assignments stay."""
    plan = make_plan(opts)
    if plan.state in ("needs-input", "invalid", "conflict"):
        return _problem_result(plan, plan.state)
    if plan.unchanged:
        return _result("set-domain", opts.site, "unchanged", plan)
    if plan_only_mode:
        return _result("set-domain", opts.site, "planned", plan)
    outcome = apply(plan)
    if not outcome["ok"]:
        return _result("set-domain", opts.site, outcome["state"], plan, error=outcome["error"],
                       remaining=outcome["remaining"], rollback_errors=outcome["rollback_errors"])
    return _result("set-domain", opts.site, "updated", plan)


def verify(opts, runner=None) -> dict:
    """Re-run install/build/check on the current content of a registered static site. Writes no site file."""
    plan = Plan("verify", opts.site)
    try:
        config = validate.load_config(RES)
        domain = validate.check_site_id(opts.site)    # the site ID (the manifest name)
        root = check_root(opts.root)
        manifest_file, schema_file = manifest.files(root)
        if not manifest_file.is_file():
            raise Stop(f"{manifest_file} not found; '{domain}' is not registered")
        data = manifest.load(manifest_file)
        errors = manifest.problems(data, schema_file, list(config["types"]))
        if errors:
            raise Stop("manifest is invalid:\n  " + "\n  ".join(errors))
        component = next((c for c in data["components"] if c["name"] == domain), None)
        if component is None:
            raise Stop(f"'{domain}' is not registered in the manifest")
        plan.notes.extend(shared_manifest.require_consistent(root, component))   # contradictions stop before install/build
        cfg = config["types"][component["type"]]
        site_dir = root / component["path"]
        check_no_symlink(root, component["path"].split("/"), "site path")
        if not site_dir.is_dir():
            raise Stop(f"site folder missing: {component['path']}")
        if not (site_dir / "package.json").is_file():
            raise Stop(f"{component['path']}/package.json is missing")
        record = ownership.load(root / ownership.MANAGED)
        entry = record["sites"].get(domain)
        if entry is None:
            plan.notes.append("no ownership record for this site: nothing is reported as managed")
        for rel, recorded in sorted((entry or {"files": {}})["files"].items()):
            path = site_dir / rel
            if not path.is_file():
                plan.change(f"{component['path']}/{rel}", "keep", "missing (kept as it is, not regenerated)")
            elif sha_file(path) != recorded:
                plan.change(f"{component['path']}/{rel}", "keep", "modified (kept)")
    except Ask as question:
        plan.add("ask", str(question))
        return _problem_result(plan, "needs-input")
    except (Stop, ProjectFilesError) as stop:
        plan.add("invalid", str(stop))
        return _problem_result(plan, "invalid")
    result = _result("verify", domain, "verified", plan)
    _attach_build(result, run_steps(site_dir, cfg, runner), "verified")
    return result


# ---------------------------------------------------------------- text output

def render_text(result: dict) -> str:
    lines = [f"setup {result['operation']} {result['site']}: {result['state']}"]
    for problem in result.get("problems", []):
        lines.append(f"  {problem}")
    if result.get("error"):
        lines.append(f"  error: {result['error']}")
    for key, title in (("remaining", "remaining after the failed rollback"), ("rollback_errors", "rollback errors")):
        if result.get(key):
            lines.append(f"  {title}:")
            lines += [f"    {item}" for item in result[key]]
    for change in result["changes"]:
        lines.append(f"  {change['action']:<8} {change['path']}" + (f"  ({change['reason']})" if change["reason"] else ""))
    for finding in result["findings"]:
        lines.append(f"  {finding['level']}: {finding['text']}")
    for step, info in result["verification"].items():
        lines.append(f"  {step}: " + (f"ran, exit {info['exit']}" if info["ran"] else "not run"))
    if result.get("failed_step"):
        lines.append(f"  {result['failed_step']} failed; last output lines:")
        lines += [f"    {line}" for line in result.get("output_tail", [])]
    if result.get("local_output"):
        lines.append("  local build output (git-ignored): " + ", ".join(result["local_output"]))
    if result.get("lockfile") in ("created", "changed"):
        lines.append(f"  {LOCKFILE}: {result['lockfile']} (versioned file created by npm, review; no commit required for local work)")
    for note in result["notes"]:
        lines.append(f"  note: {note}")
    return "\n".join(lines)
