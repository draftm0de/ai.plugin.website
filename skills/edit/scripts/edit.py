#!/usr/bin/env python3
"""Guard rails for the `edit` skill of the Website plugin (reference: references/edit.md). Standard library only.

It does NOT decide what to write; the model does. It provides what the contract found missing:

  preflight  site (existing resolver, called as a process), type, rules, target, prerequisites; writes nothing
  begin      resolves the site itself (existing resolver), checks the prerequisites, records the starting state
             (HEAD, git status incl. untracked, hash of the target) and stores the immutable original backup
  write      replace the target with new content, guarded by the expected hash (conflict = nothing written)
  replace    same, for one text that occurs exactly once
  check      npm run build, then npm run check, real exit codes; stale dist/ is never evidence. The file must
             equal the expected hash before and after the checks; the result is bound to that content
  diff       total diff: original against the current file (only while the file is the one this run wrote)
  finish     report; `complete` only if the last check belongs to the current content; removes only the backup
             folder this run created, and only after a clean, fully checked, visually inspected end

The site is never taken from the caller: the folder comes from the manifest through the resolver, on every command.
There is no command that creates files: the first scope only edits the start page that setup created.

Exit codes as in the other skills: 0 ok, 1 STOP (JSON/text with state), 2 ASK (resolver ambiguity).
First scope: the only writable file is src/pages/index.astro of the site. Everything else is refused.
"""
import argparse
import difflib
import hashlib
import json
import os
import re
import secrets
import stat
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN_ROOT = HERE.parents[2]                              # the installed plugin: never a place for state or backups
RESOLVER = HERE.parents[1] / "_shared" / "scripts" / "which_site.py"     # the shared resolver; no copy
SUPPORTED_TYPE = "astro-static"
ALLOWED = ("src/pages/index.astro",)                       # first scope: the start page only
BINDING_RULES = ("accessibility.md", "seo.md")
LOCKFILES = ("package-lock.json", "npm-shrinkwrap.json")
REPAIR_LIMIT = 2
TAIL = 2000
SECRET_RE = re.compile(r"""(?im)\b([A-Z0-9_-]*(?:TOKEN|SECRET|PASSWORD|PASSWD|API[_-]?KEY|AUTH)[A-Z0-9_-]*)["']?[ \t]*[=:][ \t]*"""
                       r"""(?:"(?:[^"\\\n]|\\.)*(?:"|$)|'(?:[^'\\\n]|\\.)*(?:'|$)|[^\r\n]*)""")


class Refused(Exception):
    def __init__(self, state, message, **extra):
        super().__init__(message)
        self.state, self.extra = state, extra


class SiteRefused(Refused):
    """The site, the manifest or the resolver is not usable. This says nothing about the target file: it is never a
    `conflict` and never changes the state of a session."""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def out(obj, code=0):
    print(json.dumps(obj, indent=2, ensure_ascii=False))
    return code


def git(root, *args):
    try:
        return subprocess.run(["git", *args], cwd=root, capture_output=True)
    except OSError as error:                  # git missing or not runnable: a missing tool, reported by the callers, not a crash
        return subprocess.CompletedProcess(["git", *args], 127, b"", str(error).encode())


# ---------------------------------------------------------------- paths

def safe_target(root: Path, site_rel: str, rel: str) -> Path:
    """rel must be on the allow-list; site_rel (from the manifest) must be relative and inside root;
    no component from the root down to the file may be a symlink."""
    clean = Path(rel).as_posix()
    if Path(rel).is_absolute() or ".." in Path(rel).parts or clean not in ALLOWED:
        raise Refused("refused", f"{rel}: outside the ordered scope (allowed: {', '.join(ALLOWED)})")
    if not site_rel or Path(site_rel).is_absolute() or ".." in Path(site_rel).parts:
        raise Refused("refused", f"site path '{site_rel}' is not a relative path inside the project")
    cur = root
    for part in (*Path(site_rel).parts, *Path(clean).parts):
        cur = cur / part
        if cur.is_symlink():
            raise Refused("refused", f"symlink in path: {cur}")
    if root.resolve() not in cur.resolve().parents:
        raise Refused("refused", "target resolves outside the project")
    return root / site_rel / clean


def read_regular(path: Path):
    """Bytes of a regular file, None when absent; a symlink or non-file is refused."""
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise Refused("refused", f"not a regular file: {path}")
    return path.read_bytes() if path.exists() else None


def atomic_replace(path: Path, data: bytes):
    mode = path.stat().st_mode & 0o7777
    fd, tmp = tempfile.mkstemp(prefix=".edit-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------- state

def own_parent(root: Path) -> Path:
    return Path(tempfile.gettempdir()) / "zyris-website" / sha(str(root).encode())[:12]


STATE_KEYS = ("token", "root", "site", "site_path", "file", "expected_sha", "original_sha", "writes", "repair_rounds",
              "check_failed_since_write", "checks", "conflict")


def check_state_area(root: Path):
    """The backup area <TMPDIR>/zyris-website/<project hash> must be reached without a symbolic link below the temp folder
    and must lie neither inside the website project nor inside the installed plugin."""
    area = own_parent(root)
    cur = Path(tempfile.gettempdir()).resolve()
    for part in area.parts[len(Path(tempfile.gettempdir()).parts):]:
        cur = cur / part
        if cur.is_symlink():
            raise Refused("refused", f"the backup area contains a symlink: {cur}; nothing was written")
    for other, what in ((root, "the website project"), (PLUGIN_ROOT, "the installed plugin")):
        other = other.resolve()
        if cur == other or other in cur.parents:
            raise Refused("refused", f"the backup area {cur} lies inside {what}; set TMPDIR to a folder outside it. Nothing was written")


def safe_read(path: Path, limit: int = 4_000_000) -> bytes:
    """Bytes of a regular file opened without following a link (O_NOFOLLOW) and checked on the open descriptor."""
    if os.path.islink(path):                          # refused before any open: no access attempt on whatever the link points to
        raise OSError(f"{path} is a symbolic link")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0))      # O_NOFOLLOW also closes the race after the check
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError(f"{path} is not a regular file")
        with os.fdopen(fd, "rb", closefd=False) as fh:
            return fh.read(limit)
    finally:
        os.close(fd)


def is_real_dir(path: Path) -> bool:
    try:
        return stat.S_ISDIR(os.lstat(path).st_mode)
    except OSError:
        return False


def check_session_folder(folder: str) -> Path:
    """Before anything inside the session folder is read: it must be a real directory (no link) inside <TMPDIR>/zyris-website/<12 hex>,
    reached without a symbolic link below the temp folder."""
    path = Path(os.path.abspath(folder))
    area = path.parent
    base = Path(os.path.realpath(tempfile.gettempdir()))
    if not (re.fullmatch(r"[0-9a-f]{12}", area.name) and area.parent.name == "zyris-website"
            and os.path.realpath(area.parent.parent) == str(base)):
        raise Refused("refused", "state folder is not ours")
    cur = base
    for part in (area.parent.name, area.name, path.name):
        cur = cur / part
        if not is_real_dir(cur):
            raise Refused("refused", "state folder is not ours (missing, or a symbolic link instead of a folder)")
    return path


def load_state(folder: str) -> dict:
    path = check_session_folder(folder)
    try:
        st = json.loads(safe_read(path / "index.json").decode("utf-8"))
    except (OSError, ValueError):
        raise Refused("refused", f"no usable edit state in {folder} (missing, a link or damaged)")
    if not isinstance(st, dict) or any(k not in st for k in STATE_KEYS):
        raise Refused("refused", "state folder is not ours")
    try:
        owner = safe_read(path / ".owner", 256).decode("utf-8").strip()
    except (OSError, ValueError):
        raise Refused("refused", "state folder is not ours")
    if st.get("token") != owner or not isinstance(st.get("root"), str) or path.parent != Path(os.path.realpath(own_parent(Path(st["root"])))):
        raise Refused("refused", "state folder is not ours")
    check_state_area(Path(st["root"]))
    return st


def save_state(folder, st):
    """Private, exclusively created temp file in the (already validated) session folder, then an atomic replace of index.json.
    An existing link or foreign file is never written through, never used as temp file and never removed."""
    fd, tmp = tempfile.mkstemp(prefix=".index-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(st, indent=2))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, Path(folder) / "index.json")
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def porcelain(root) -> list:
    raw = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout
    return sorted(e.decode("utf-8", "replace") for e in raw.split(b"\0") if e)


def bound_target(st) -> Path:
    """The target, re-derived through the resolver on every use: the state cannot point anywhere else."""
    root = Path(st["root"])
    res = resolve(root, st["site"])
    if res.returncode != 0:
        raise SiteRefused("refused", "site no longer resolves: " + (res.stdout + res.stderr).strip())
    site = site_json(res)
    if site["site"] != st["site"] or site["path"] != st["site_path"] or site.get("type") != SUPPORTED_TYPE:
        raise SiteRefused("refused", "the resolved site differs from the one this session began with")
    return safe_target(root, site["path"], st["file"])


def observe(st):
    """(sha or None when absent, problem or None) of the target now; never follows a symlink."""
    try:
        data = read_regular(bound_target(st))
    except SiteRefused:
        raise                                   # the site is unusable: not a statement about the file, no conflict is recorded
    except Refused as r:
        return None, str(r)
    return (sha(data) if data is not None else None), None


def assert_base(st, folder, when="before this step"):
    found, problem = observe(st)
    if problem or found != st["expected_sha"]:
        st["conflict"] = True
        save_state(folder, st)
        raise Refused("conflict", problem or f"{st['file']} {'was removed' if found is None else 'changed outside this run'} {when}; "
                      "nothing written, the newer content is kept", expected=st["expected_sha"], found=found or "absent/unusable",
                      backup_kept=str(folder))


# ---------------------------------------------------------------- preflight

def resolve(root: Path, site=None, cwd=None, last=None):
    if not RESOLVER.is_file():
        raise SiteRefused("stop", f"the shared site resolver is missing ({RESOLVER}); the plugin path is missing or outdated, nothing was changed")
    cmd = [sys.executable, "-I", "-B", str(RESOLVER), "--root", str(root)]      # -B: never write bytecode into the installed plugin
    for flag, val in (("cwd", cwd), ("last", last)):
        if val:
            cmd += [f"--{flag}", val]
    if site:
        cmd.append(site)
    return subprocess.run(cmd, capture_output=True, text=True)


def site_json(res) -> dict:
    try:
        site = json.loads(res.stdout)
    except ValueError:
        site = None
    if not isinstance(site, dict) or "site" not in site or "path" not in site:
        raise SiteRefused("stop", "the site resolver returned no site description: " + (res.stdout + res.stderr).strip()[:300])
    return site


def preflight(args):
    root = Path(args.root or os.getcwd()).resolve()
    res = resolve(root, args.site, args.cwd, args.last)
    if res.returncode == 2:
        try:
            asking = "ask" in json.loads(res.stdout)
        except (ValueError, TypeError):
            asking = False
        if asking:
            print(res.stdout.strip())
            return 2
        return out({"state": "stop", "message": "the site resolver failed without a question: " + (res.stdout + res.stderr).strip()[:300]}, 1)
    if res.returncode != 0:
        return out({"state": "stop", "message": (res.stdout + res.stderr).strip()}, 1)
    return out(*check_site(root, site_json(res)))


def check_site(root: Path, site: dict):
    """Everything that must hold before the first content change (flow step 4). Writes nothing."""
    base = {"state": "stop", "site": site["site"], "path": site["path"]}
    if site.get("type") != SUPPORTED_TYPE:
        return {**base, "message": f"site type '{site.get('type')}' is not supported; edit works on {SUPPORTED_TYPE} only and does not migrate"}, 1
    sd = root / site["path"]
    missing = [r for r in BINDING_RULES if r not in site.get("rule_files", [])]
    if missing:
        return {**base, "message": f"binding rule file missing: {', '.join(missing)} (in {site['rules']})"}, 1
    for rel in ALLOWED:
        try:
            if read_regular(safe_target(root, site["path"], rel)) is None:
                return {**base, "message": f"{rel} does not exist; the `setup` skill of the Website plugin creates the start page"}, 1
        except Refused as r:
            return {**base, "message": str(r)}, 1
    try:
        raw = read_regular(sd / "package.json")          # a symlinked package.json is refused, never read
        pkg = json.loads(raw.decode("utf-8")) if raw is not None else None
    except (Refused, OSError, ValueError):
        pkg = None
    if not isinstance(pkg, dict):
        return {**base, "message": "package.json missing, not a regular file or invalid; the `setup` skill of the Website plugin sets the site up"}, 1
    scripts = pkg.get("scripts")
    scripts = scripts if isinstance(scripts, dict) else {}
    problems = []
    if not (sd / "node_modules").is_dir():
        problems.append(("node_modules missing", f"cd {site['path']} && npm ci"))
    for s in ("build", "check"):
        if s not in scripts:
            problems.append((f"package.json has no '{s}' script", "run `verify` of the `setup` skill of the Website plugin or add the script"))
    if not any((sd / l).is_file() for l in LOCKFILES):
        problems.append(("lockfile missing", f"cd {site['path']} && npm install (creates package-lock.json; review and commit it)"))
    if git(root, "rev-parse", "HEAD").returncode != 0:
        problems.append(("git unavailable or no commit", "initialise the repository / commit once"))
    if problems:
        return {**base, "message": "prerequisites missing; nothing was changed", "missing": [p[0] for p in problems],
                "commands_for_the_person": [p[1] for p in problems]}, 1
    return {"state": "ready", "site": site["site"], "title": site["title"], "path": site["path"], "reason": site["reason"],
            "confirm": site["confirm"], "target": list(ALLOWED), "rules": site["rules"], "rule_files": site["rule_files"],
            "brand_files": site["brand_files"]}, 0


# ---------------------------------------------------------------- begin / write

def begin(args):
    root = Path(args.root).resolve()
    res = resolve(root, args.site)
    if res.returncode != 0:
        return out({"state": "stop", "message": (res.stdout + res.stderr).strip()}, 1)
    site = site_json(res)
    if site["site"] != args.site:
        raise Refused("refused", f"'{args.site}' is not the exact name of the resolved site '{site['site']}'")
    report, code = check_site(root, site)           # prerequisites before any writable session
    if code != 0:
        return out(report, code)
    rel = ALLOWED[0]
    data = read_regular(safe_target(root, site["path"], rel))
    head = git(root, "rev-parse", "HEAD").stdout.decode().strip()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    check_state_area(root)                            # before anything is created: outside project and plugin, no symlink
    parent = own_parent(root)
    parent.mkdir(parents=True, exist_ok=True)
    for n in range(100):
        folder = parent / (f"edit-{site['site']}-{stamp}" + ("" if n == 0 else f"-{n}"))
        try:
            folder.mkdir(mode=0o700)       # exclusive: never reuses a folder
            break
        except FileExistsError:
            continue
    else:
        raise Refused("stop", "could not create a backup folder")
    token = secrets.token_hex(8)
    (folder / ".owner").write_text(token)
    bak = folder / "original" / rel
    bak.parent.mkdir(parents=True)
    bak.write_bytes(data)
    h = sha(data)
    st = {"token": token, "root": str(root), "site": site["site"], "site_path": site["path"], "file": rel, "head": head,
          "porcelain_start": porcelain(root), "original_sha": h, "expected_sha": h, "writes": [], "repair_rounds": 0,
          "check_failed_since_write": False, "checks": [], "conflict": False}
    save_state(folder, st)
    return out({"state": "begun", "state_folder": str(folder), "site": site["site"], "path": site["path"], "original_sha": h,
                "head": head, "uncommitted_at_start": st["porcelain_start"]})


def guarded_write(args, new_bytes_fn):
    st = load_state(args.state)
    assert_base(st, args.state)
    target = bound_target(st)
    cur = read_regular(target)
    cur_sha = sha(cur)
    new = new_bytes_fn(cur)
    if new == cur:
        return out({"state": "unchanged", "sha": cur_sha, "message": "file already equals the intended result; nothing written"})
    if st["check_failed_since_write"]:
        if st["repair_rounds"] >= REPAIR_LIMIT:
            raise Refused("repair-limit", f"{REPAIR_LIMIT} repair rounds used; report the remaining failures instead of writing again")
        st["repair_rounds"] += 1
    try:
        atomic_replace(target, new)
    except OSError as error:                          # the private temp file is removed; the target was not replaced
        raise Refused("stop", f"could not write {st['file']} ({error}); the file is unchanged and nothing is reported as written")
    st["expected_sha"] = sha(new)
    st["writes"].append(st["expected_sha"])
    st["check_failed_since_write"] = False
    save_state(args.state, st)
    return out({"state": "written", "sha": st["expected_sha"], "repair_rounds": st["repair_rounds"]})


def write(args):
    try:
        data = Path(args.content_file).read_bytes()
    except OSError as error:
        raise Refused("stop", f"cannot read the content file ({error}); nothing was written")
    return guarded_write(args, lambda cur: data)


def replace(args):
    def fn(cur):
        try:
            find, repl = args.find.encode("utf-8"), args.replace.encode("utf-8")
        except UnicodeEncodeError:
            raise Refused("stop", "find or replace text is not valid UTF-8; nothing was written")
        if not find:
            raise Refused("stop", "find text is empty")
        n = cur.count(find)                           # on bytes: exactly the named bytes change, line endings stay as they are
        if n != 1:
            raise Refused("stop", f"find text occurs {n} times, expected exactly once")
        return cur.replace(find, repl)
    return guarded_write(args, fn)


# ---------------------------------------------------------------- check / diff / finish

def redact(text: str) -> str:
    """Known secret fields (NAME containing TOKEN, SECRET, PASSWORD, PASSWD, API_KEY or AUTH, so also Authorization and
    Proxy-Authorization, followed by = or :) lose their value: a quoted value completely (spaces and escaped quotes included; an unclosed
    quote runs to the end of the line), any other value, including an authentication scheme such as `Bearer`, to the end of the line, because
    its end cannot be told. A pattern list, not a detector: secrets in other forms are not recognised, and harmless text after a field
    is redacted too."""
    return SECRET_RE.sub(lambda m: f"{m.group(1)}=<redacted>", text)


def run_npm(npm, script, cwd):
    try:
        p = subprocess.run([npm, "run", script], cwd=cwd, capture_output=True, text=True, errors="replace")
    except OSError as error:                          # the tool cannot be started: not run, never "failed" or "passed"
        return {"ran": False, "exit": None, "unavailable": True, "reason": f"could not run: {error}"}
    return {"ran": True, "exit": p.returncode, "tail": redact(p.stdout + p.stderr)[-TAIL:]}      # redact first, then cut


def check(args):
    st = load_state(args.state)
    assert_base(st, args.state, "before the checks")
    sd = Path(st["root"]) / st["site_path"]
    build = run_npm(args.npm, "build", sd)
    if build.get("unavailable"):
        chk = {"ran": False, "exit": None, "reason": "not run: the build could not be started"}
    elif build["exit"] == 0:
        assert_base(st, args.state, "during the build")
        chk = run_npm(args.npm, "check", sd)
    else:
        chk = {"ran": False, "exit": None, "reason": "not run: build failed; dist/ of an earlier build is not evidence"}
    assert_base(st, args.state, "during the checks")        # the result below belongs to exactly this content
    ok = build["exit"] == 0 and chk["exit"] == 0
    unavailable = bool(build.get("unavailable") or chk.get("unavailable"))
    if not unavailable:                                     # a tool that could not start is no failure of the change: no repair round
        st["check_failed_since_write"] = not ok
    st["checks"].append({"build": build["exit"], "check": chk["exit"], "sha": st["expected_sha"], **({"unavailable": True} if unavailable else {})})
    save_state(args.state, st)
    return out({"state": "checked" if ok else "not-run" if unavailable else "failed", "build": build, "check": chk, "checked_sha": st["expected_sha"],
                "repair_rounds_used": st["repair_rounds"], "repair_rounds_left": max(0, REPAIR_LIMIT - st["repair_rounds"])}, 0 if ok else 1)


def read_backup(folder, st) -> bytes:
    """The original backup, read without following a link in any component below the session folder; it must still be the original."""
    cur = Path(folder)
    for part in ("original", *Path(st["file"]).parts[:-1]):
        cur = cur / part
        if not is_real_dir(cur):
            raise Refused("refused", "the original backup is damaged or replaced (not a plain folder); nothing was read")
    try:
        data = safe_read(cur / Path(st["file"]).name)
    except OSError:
        raise Refused("refused", "the original backup is damaged or replaced (not a plain file); nothing was read")
    if sha(data) != st["original_sha"]:
        raise Refused("refused", "the original backup differs from the recorded original; it is not shown as this run's original")
    return data


def total_diff(st, folder) -> str:
    orig = read_backup(folder, st).decode("utf-8", "replace").splitlines(True)   # bytes: a line-ending change shows up
    now = read_regular(bound_target(st)).decode("utf-8", "replace").splitlines(True)
    return "".join(difflib.unified_diff(orig, now, "original/" + st["file"], "final/" + st["file"]))


def diff(args):
    st = load_state(args.state)
    assert_base(st, args.state)             # a foreign state of the file is never presented as this run's diff
    return out({"file": st["file"], "diff": total_diff(st, args.state)})


class CleanupRefused(OSError):
    """The backup tree is not exactly what this run created; nothing was removed."""


def plan_own_removal(folder: Path, st: dict) -> list:
    """Checks the WHOLE backup tree against the exact expected objects (names, types, original content) and returns the removal
    order. Any unexpected entry, replaced object or link stops everything, before the first deletion."""
    parts = Path(st["file"]).parts
    expected = {folder: {".owner": "f", "index.json": "f", "original": "d"}}
    cur = folder / "original"
    for part in parts[:-1]:
        expected[cur] = {part: "d"}
        cur = cur / part
    expected[cur] = {parts[-1]: "f"}
    if not is_real_dir(folder):
        raise CleanupRefused("the session folder is not a plain folder")
    for directory, names in expected.items():
        if not is_real_dir(directory):
            raise CleanupRefused(f"{directory.relative_to(folder)} is missing or replaced (not a plain folder)")
        found = {p.name: p for p in directory.iterdir()}
        if set(found) != set(names):
            odd = sorted(set(found) ^ set(names))
            raise CleanupRefused(f"unexpected or missing entries in {directory.relative_to(folder) if directory != folder else '.'}: {', '.join(odd)}")
        for name, kind in names.items():
            mode = os.lstat(found[name]).st_mode
            if (kind == "f" and not stat.S_ISREG(mode)) or (kind == "d" and not stat.S_ISDIR(mode)):
                raise CleanupRefused(f"{found[name].relative_to(folder)} was replaced by another kind of object")
    backup = folder / "original" / Path(*parts)
    try:
        if sha(safe_read(backup)) != st["original_sha"]:
            raise CleanupRefused("the backup file no longer equals the recorded original")
    except OSError as error:
        raise CleanupRefused(f"the backup file cannot be verified ({error})")
    chain = [backup]
    cur = backup.parent
    while cur != folder:
        chain.append(cur)
        cur = cur.parent
    return chain + [folder / ".owner", folder / "index.json", folder]


def remove_own_folder(folder: Path, st: dict):
    """Removes exactly the objects `begin` and the run created, and only after the complete tree has been verified."""
    steps = plan_own_removal(folder, st)
    for step in steps:
        step.rmdir() if step.is_dir() and not step.is_symlink() else step.unlink()


def finish(args):
    st = load_state(args.state)
    found, problem = observe(st)
    if problem or found != st["expected_sha"]:
        st["conflict"] = True
        save_state(args.state, st)
    base = {"file": st["file"], "writes": len(st["writes"]), "repair_rounds": st["repair_rounds"], "backup": "kept", "backup_folder": args.state}
    if st["conflict"]:
        return out({**base, "outcome": "conflict: nothing complete", "technical": "invalid", "visual": "performed" if args.visual_done else "open",
                    "detail": problem or "the file differs from what this run last wrote or checked; its state is not attributed to this run",
                    "total_diff": "withheld: the file no longer is this run's result"}, 1)
    last = st["checks"][-1] if st["checks"] else None
    if not last:
        tech = "not run"
    elif last["sha"] != st["expected_sha"]:
        tech = "stale: the file was written after the last check"
    elif last.get("unavailable"):
        tech = "not run: npm could not be started"
    else:
        tech = "passed" if last["build"] == 0 and last["check"] == 0 else "failed"
    ok = tech == "passed"
    now = porcelain(Path(st["root"]))
    if not ok:
        outcome = f"technical checks {tech}: not complete"
    elif args.visual_done:
        outcome = "complete"
    else:
        outcome = "technically checked, visual check open"
    report = {**base, "outcome": outcome, "technical": tech, "visual": "performed" if args.visual_done else "open",
              "visual_substitutes": list(args.visual_substitute), "visual_not_done": list(args.visual_not_done),
              "git_status_delta_since_begin": sorted(set(now) ^ set(st["porcelain_start"])), "total_diff": total_diff(st, args.state)}
    if ok and args.visual_done:
        folder = Path(args.state)
        if folder.name.startswith("edit-") and not folder.is_symlink():
            try:
                remove_own_folder(folder, st)
                report["backup"] = "removed (own folder only)"
                del report["backup_folder"]
            except CleanupRefused as e:
                report["backup"] = f"kept (nothing removed); cleanup refused: {e}"
            except OSError as e:
                left = sorted(str(p.relative_to(folder)) for p in folder.rglob("*")) if folder.is_dir() else []
                report["backup"] = f"kept; cleanup failed part-way ({e}); remaining: {', '.join(left) if left else 'nothing'}"
    return out(report)


# ---------------------------------------------------------------- cli

def parse(argv):
    p = argparse.ArgumentParser(prog="edit.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("preflight")
    s.add_argument("site", nargs="?")
    s.add_argument("--cwd")
    s.add_argument("--last")
    s.add_argument("--root")
    s = sub.add_parser("begin")
    s.add_argument("--root", required=True)
    s.add_argument("--site", required=True, help="exact site name as the resolver reports it")
    for name in ("write", "replace", "check", "diff", "finish"):
        s = sub.add_parser(name)
        s.add_argument("--state", required=True)
        if name == "write":
            s.add_argument("--content-file", required=True)
        if name == "replace":
            s.add_argument("--find", required=True)
            s.add_argument("--replace", required=True)
        if name == "check":
            s.add_argument("--npm", default="npm")
        if name == "finish":
            s.add_argument("--visual-done", action="store_true")
            s.add_argument("--visual-substitute", action="append", default=[],
                           help="a check done in place of the real one, e.g. 'narrow window instead of browser zoom' (repeatable)")
            s.add_argument("--visual-not-done", action="append", default=[],
                           help="an optional or impossible visual check that was not done (repeatable)")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse(argv)
    try:
        return globals()[args.cmd](args)
    except Refused as r:
        return out({"state": r.state, "message": str(r), **r.extra}, 1)
    except (OSError, UnicodeError, ValueError) as error:
        return out({"state": "stop", "message": f"a file or process operation failed ({error}). Nothing is reported as done; "
                    "read the file and the git status before the next step"}, 1)


if __name__ == "__main__":
    sys.exit(main())
