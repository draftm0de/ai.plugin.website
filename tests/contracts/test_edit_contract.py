"""Contracts of the migrated `edit` skill: identity against the source inventory (explicit change lists, reversible), skill text,
call patterns and pre-approvals derived from each other, communication block, shipped-runtime hygiene and the "not available"
boundary. Structural/text checks only: they prove no product behaviour and no host acceptance."""
import ast
import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "edit"
TEXT = (SKILL / "SKILL.md").read_text(encoding="utf-8")
REFERENCE = (SKILL / "references" / "edit.md").read_text(encoding="utf-8")
INVENTORY = json.loads((ROOT / "docs/migration/source-inventory.json").read_text())
PREFIX = INVENTORY["plugin_root"] + "/"
SOURCE = {e["path"][len(PREFIX):]: e["sha256"] for e in INVENTORY["files"] if e["path"].startswith(PREFIX)}
RUNTIME = SKILL / "scripts" / "edit.py"


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


# Migration adaptation (docs/migration/changes.md, Etappe 5 A): new text -> old text. Reversing the protection list first and then this
# list must give back the recorded source bytes: the diff to the source is exactly these two lists. Generated from the files.
MIGRATION = [('#!/usr/bin/env python3\n'
  '"""Guard rails for the `edit` skill of the Website plugin (reference: references/edit.md). Standard library only.\n'
  '\n',
  '#!/usr/bin/env python3\n"""Guard rails for /zyris-website:edit (contract: contracts/edit.md). Standard library only.\n\n'),
 ('HERE = Path(__file__).resolve().parent\n'
  'RESOLVER = HERE.parents[1] / "_shared" / "scripts" / "which_site.py"     # the shared resolver; no copy\n'
  'SUPPORTED_TYPE = "astro-static"\n',
  'HERE = Path(__file__).resolve().parent\n'
  'RESOLVER = HERE.parent / "optimize" / "which_site.py"     # the existing resolver; no copy\n'
  'SUPPORTED_TYPE = "astro-static"\n'),
 ('            if read_regular(safe_target(root, site["path"], rel)) is None:\n'
  '                return {**base, "message": f"{rel} does not exist; the `setup` skill of the Website plugin creates the start page"}, 1\n'
  '        except Refused as r:\n',
  '            if read_regular(safe_target(root, site["path"], rel)) is None:\n'
  '                return {**base, "message": f"{rel} does not exist; /zyris-website:setup creates the start page"}, 1\n'
  '        except Refused as r:\n'),
 ('    except (OSError, ValueError):\n'
  '        return {**base, "message": "package.json missing or invalid; the `setup` skill of the Website plugin sets the site up"}, 1\n'
  '    scripts = pkg.get("scripts") or {}\n',
  '    except (OSError, ValueError):\n'
  '        return {**base, "message": "package.json missing or invalid; /zyris-website:setup"}, 1\n'
  '    scripts = pkg.get("scripts") or {}\n'),
 ('        if s not in scripts:\n'
  '            problems.append((f"package.json has no \'{s}\' script", "run `verify` of the `setup` skill of the Website plugin or add the '
  'script"))\n'
  '    if not any((sd / l).is_file() for l in LOCKFILES):\n',
  '        if s not in scripts:\n'
  '            problems.append((f"package.json has no \'{s}\' script", "run /zyris-website:setup verify or add the script"))\n'
  '    if not any((sd / l).is_file() for l in LOCKFILES):\n')]

PROTECTION = [('import os\nimport re\nimport secrets\n', 'import os\nimport secrets\n'),
 ('import secrets\nimport stat\nimport shutil\n', 'import secrets\nimport shutil\n'),
 ('HERE = Path(__file__).resolve().parent\n'
  'PLUGIN_ROOT = HERE.parents[2]                              # the installed plugin: never a place for state or backups\n'
  'RESOLVER = HERE.parents[1] / "_shared" / "scripts" / "which_site.py"     # the shared resolver; no copy\n',
  'HERE = Path(__file__).resolve().parent\n'
  'RESOLVER = HERE.parents[1] / "_shared" / "scripts" / "which_site.py"     # the shared resolver; no copy\n'),
 ('TAIL = 2000\n'
  'SECRET_RE = re.compile(r"""(?im)\\b([A-Z0-9_-]*(?:TOKEN|SECRET|PASSWORD|PASSWD|API[_-]?KEY|AUTH)[A-Z0-9_-]*)["\']?[ \\t]*[=:][ '
  '\\t]*"""\n'
  '                       r"""(?:"(?:[^"\\\\\\n]|\\\\.)*(?:"|$)|\'(?:[^\'\\\\\\n]|\\\\.)*(?:\'|$)|[^\\r\\n]*)""")\n'
  '\n',
  'TAIL = 2000\n\n'),
 ('        self.state, self.extra = state, extra\n'
  '\n'
  '\n'
  'class SiteRefused(Refused):\n'
  '    """The site, the manifest or the resolver is not usable. This says nothing about the target file: it is never a\n'
  '    `conflict` and never changes the state of a session."""\n'
  '\n',
  '        self.state, self.extra = state, extra\n\n'),
 ('def git(root, *args):\n'
  '    try:\n'
  '        return subprocess.run(["git", *args], cwd=root, capture_output=True)\n'
  '    except OSError as error:                  # git missing or not runnable: a missing tool, reported by the callers, not a crash\n'
  '        return subprocess.CompletedProcess(["git", *args], 127, b"", str(error).encode())\n'
  '\n',
  'def git(root, *args):\n    return subprocess.run(["git", *args], cwd=root, capture_output=True)\n\n'),
 ('\n'
  'STATE_KEYS = ("token", "root", "site", "site_path", "file", "expected_sha", "original_sha", "writes", "repair_rounds",\n'
  '              "check_failed_since_write", "checks", "conflict")\n'
  '\n'
  '\n'
  'def check_state_area(root: Path):\n'
  '    """The backup area <TMPDIR>/zyris-website/<project hash> must be reached without a symbolic link below the temp folder\n'
  '    and must lie neither inside the website project nor inside the installed plugin."""\n'
  '    area = own_parent(root)\n'
  '    cur = Path(tempfile.gettempdir()).resolve()\n'
  '    for part in area.parts[len(Path(tempfile.gettempdir()).parts):]:\n'
  '        cur = cur / part\n'
  '        if cur.is_symlink():\n'
  '            raise Refused("refused", f"the backup area contains a symlink: {cur}; nothing was written")\n'
  '    for other, what in ((root, "the website project"), (PLUGIN_ROOT, "the installed plugin")):\n'
  '        other = other.resolve()\n'
  '        if cur == other or other in cur.parents:\n'
  '            raise Refused("refused", f"the backup area {cur} lies inside {what}; set TMPDIR to a folder outside it. Nothing was '
  'written")\n'
  '\n'
  '\n'
  'def safe_read(path: Path, limit: int = 4_000_000) -> bytes:\n'
  '    """Bytes of a regular file opened without following a link (O_NOFOLLOW) and checked on the open descriptor."""\n'
  '    if os.path.islink(path):                          # refused before any open: no access attempt on whatever the link points to\n'
  '        raise OSError(f"{path} is a symbolic link")\n'
  '    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0))      # O_NOFOLLOW also closes the race after the '
  'check\n'
  '    try:\n'
  '        if not stat.S_ISREG(os.fstat(fd).st_mode):\n'
  '            raise OSError(f"{path} is not a regular file")\n'
  '        with os.fdopen(fd, "rb", closefd=False) as fh:\n'
  '            return fh.read(limit)\n'
  '    finally:\n'
  '        os.close(fd)\n'
  '\n'
  '\n'
  'def is_real_dir(path: Path) -> bool:\n'
  '    try:\n'
  '        return stat.S_ISDIR(os.lstat(path).st_mode)\n'
  '    except OSError:\n'
  '        return False\n'
  '\n'
  '\n'
  'def check_session_folder(folder: str) -> Path:\n'
  '    """Before anything inside the session folder is read: it must be a real directory (no link) inside <TMPDIR>/zyris-website/<12 '
  'hex>,\n'
  '    reached without a symbolic link below the temp folder."""\n'
  '    path = Path(os.path.abspath(folder))\n'
  '    area = path.parent\n'
  '    base = Path(os.path.realpath(tempfile.gettempdir()))\n'
  '    if not (re.fullmatch(r"[0-9a-f]{12}", area.name) and area.parent.name == "zyris-website"\n'
  '            and os.path.realpath(area.parent.parent) == str(base)):\n'
  '        raise Refused("refused", "state folder is not ours")\n'
  '    cur = base\n'
  '    for part in (area.parent.name, area.name, path.name):\n'
  '        cur = cur / part\n'
  '        if not is_real_dir(cur):\n'
  '            raise Refused("refused", "state folder is not ours (missing, or a symbolic link instead of a folder)")\n'
  '    return path\n'
  '\n'
  '\n'
  'def load_state(folder: str) -> dict:\n',
  '\ndef load_state(folder: str) -> dict:\n'),
 ('def load_state(folder: str) -> dict:\n    path = check_session_folder(folder)\n    try:\n',
  'def load_state(folder: str) -> dict:\n    f = Path(folder) / "index.json"\n    try:\n'),
 ('    try:\n        st = json.loads(safe_read(path / "index.json").decode("utf-8"))\n    except (OSError, ValueError):\n',
  '    try:\n        st = json.loads(f.read_text(encoding="utf-8"))\n    except (OSError, ValueError):\n'),
 ('    except (OSError, ValueError):\n'
  '        raise Refused("refused", f"no usable edit state in {folder} (missing, a link or damaged)")\n'
  '    if not isinstance(st, dict) or any(k not in st for k in STATE_KEYS):\n'
  '        raise Refused("refused", "state folder is not ours")\n'
  '    try:\n',
  '    except (OSError, ValueError):\n        raise Refused("refused", f"no edit state in {folder}")\n    try:\n'),
 ('    try:\n'
  '        owner = safe_read(path / ".owner", 256).decode("utf-8").strip()\n'
  '    except (OSError, ValueError):\n'
  '        raise Refused("refused", "state folder is not ours")\n',
  '    try:\n'
  '        owner = (Path(folder) / ".owner").read_text().strip()\n'
  '    except OSError:\n'
  '        raise Refused("refused", "state folder is not ours")\n'),
 ('        raise Refused("refused", "state folder is not ours")\n'
  '    if st.get("token") != owner or not isinstance(st.get("root"), str) or path.parent != '
  'Path(os.path.realpath(own_parent(Path(st["root"])))):\n'
  '        raise Refused("refused", "state folder is not ours")\n',
  '        raise Refused("refused", "state folder is not ours")\n'
  '    if st.get("token") != owner or Path(folder).resolve().parent != own_parent(Path(st["root"])).resolve():\n'
  '        raise Refused("refused", "state folder is not ours")\n'),
 ('        raise Refused("refused", "state folder is not ours")\n    check_state_area(Path(st["root"]))\n    return st\n',
  '        raise Refused("refused", "state folder is not ours")\n    return st\n'),
 ('def save_state(folder, st):\n'
  '    """Private, exclusively created temp file in the (already validated) session folder, then an atomic replace of index.json.\n'
  '    An existing link or foreign file is never written through, never used as temp file and never removed."""\n'
  '    fd, tmp = tempfile.mkstemp(prefix=".index-", suffix=".tmp", dir=folder)\n'
  '    try:\n'
  '        with os.fdopen(fd, "w", encoding="utf-8") as fh:\n'
  '            fh.write(json.dumps(st, indent=2))\n'
  '            fh.flush()\n'
  '            os.fsync(fh.fileno())\n'
  '        os.replace(tmp, Path(folder) / "index.json")\n'
  '    except BaseException:\n'
  '        Path(tmp).unlink(missing_ok=True)\n'
  '        raise\n'
  '\n',
  'def save_state(folder, st):\n'
  '    tmp = Path(folder) / "index.json.tmp"\n'
  '    tmp.write_text(json.dumps(st, indent=2), encoding="utf-8")\n'
  '    os.replace(tmp, Path(folder) / "index.json")\n'
  '\n'),
 ('    if res.returncode != 0:\n'
  '        raise SiteRefused("refused", "site no longer resolves: " + (res.stdout + res.stderr).strip())\n'
  '    site = site_json(res)\n'
  '    if site["site"] != st["site"] or site["path"] != st["site_path"] or site.get("type") != SUPPORTED_TYPE:\n',
  '    if res.returncode != 0:\n'
  '        raise Refused("refused", "site no longer resolves: " + (res.stdout + res.stderr).strip())\n'
  '    site = json.loads(res.stdout)\n'
  '    if site["site"] != st["site"] or site["path"] != st["site_path"] or site.get("type") != SUPPORTED_TYPE:\n'),
 ('    if site["site"] != st["site"] or site["path"] != st["site_path"] or site.get("type") != SUPPORTED_TYPE:\n'
  '        raise SiteRefused("refused", "the resolved site differs from the one this session began with")\n'
  '    return safe_target(root, site["path"], st["file"])\n',
  '    if site["site"] != st["site"] or site["path"] != st["site_path"] or site.get("type") != SUPPORTED_TYPE:\n'
  '        raise Refused("refused", "the resolved site differs from the one this session began with")\n'
  '    return safe_target(root, site["path"], st["file"])\n'),
 ('        data = read_regular(bound_target(st))\n'
  '    except SiteRefused:\n'
  '        raise                                   # the site is unusable: not a statement about the file, no conflict is recorded\n'
  '    except Refused as r:\n',
  '        data = read_regular(bound_target(st))\n    except Refused as r:\n'),
 ('def resolve(root: Path, site=None, cwd=None, last=None):\n'
  '    if not RESOLVER.is_file():\n'
  '        raise SiteRefused("stop", f"the shared site resolver is missing ({RESOLVER}); the plugin path is missing or outdated, nothing '
  'was changed")\n'
  '    cmd = [sys.executable, "-I", "-B", str(RESOLVER), "--root", str(root)]      # -B: never write bytecode into the installed plugin\n'
  '    for flag, val in (("cwd", cwd), ("last", last)):\n',
  'def resolve(root: Path, site=None, cwd=None, last=None):\n'
  '    cmd = [sys.executable, "-I", str(RESOLVER), "--root", str(root)]\n'
  '    for flag, val in (("cwd", cwd), ("last", last)):\n'),
 ('\n'
  'def site_json(res) -> dict:\n'
  '    try:\n'
  '        site = json.loads(res.stdout)\n'
  '    except ValueError:\n'
  '        site = None\n'
  '    if not isinstance(site, dict) or "site" not in site or "path" not in site:\n'
  '        raise SiteRefused("stop", "the site resolver returned no site description: " + (res.stdout + res.stderr).strip()[:300])\n'
  '    return site\n'
  '\n'
  '\n'
  'def preflight(args):\n',
  '\ndef preflight(args):\n'),
 ('    if res.returncode == 2:\n'
  '        try:\n'
  '            asking = "ask" in json.loads(res.stdout)\n'
  '        except (ValueError, TypeError):\n'
  '            asking = False\n'
  '        if asking:\n'
  '            print(res.stdout.strip())\n'
  '            return 2\n'
  '        return out({"state": "stop", "message": "the site resolver failed without a question: " + (res.stdout + '
  'res.stderr).strip()[:300]}, 1)\n'
  '    if res.returncode != 0:\n',
  '    if res.returncode == 2:\n        print(res.stdout.strip())\n        return 2\n    if res.returncode != 0:\n'),
 ('        return out({"state": "stop", "message": (res.stdout + res.stderr).strip()}, 1)\n'
  '    return out(*check_site(root, site_json(res)))\n'
  '\n',
  '        return out({"state": "stop", "message": (res.stdout + res.stderr).strip()}, 1)\n'
  '    site = json.loads(res.stdout)\n'
  '    return out(*check_site(root, site))\n'
  '\n'),
 ('    try:\n'
  '        raw = read_regular(sd / "package.json")          # a symlinked package.json is refused, never read\n'
  '        pkg = json.loads(raw.decode("utf-8")) if raw is not None else None\n'
  '    except (Refused, OSError, ValueError):\n'
  '        pkg = None\n'
  '    if not isinstance(pkg, dict):\n'
  '        return {**base, "message": "package.json missing, not a regular file or invalid; the `setup` skill of the Website plugin sets '
  'the site up"}, 1\n'
  '    scripts = pkg.get("scripts")\n'
  '    scripts = scripts if isinstance(scripts, dict) else {}\n'
  '    problems = []\n',
  '    try:\n'
  '        pkg = json.loads((sd / "package.json").read_text(encoding="utf-8"))\n'
  '    except (OSError, ValueError):\n'
  '        return {**base, "message": "package.json missing or invalid; the `setup` skill of the Website plugin sets the site up"}, 1\n'
  '    scripts = pkg.get("scripts") or {}\n'
  '    problems = []\n'),
 ('        return out({"state": "stop", "message": (res.stdout + res.stderr).strip()}, 1)\n'
  '    site = site_json(res)\n'
  '    if site["site"] != args.site:\n',
  '        return out({"state": "stop", "message": (res.stdout + res.stderr).strip()}, 1)\n'
  '    site = json.loads(res.stdout)\n'
  '    if site["site"] != args.site:\n'),
 ('    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")\n'
  '    check_state_area(root)                            # before anything is created: outside project and plugin, no symlink\n'
  '    parent = own_parent(root)\n',
  '    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")\n    parent = own_parent(root)\n'),
 ('        st["repair_rounds"] += 1\n'
  '    try:\n'
  '        atomic_replace(target, new)\n'
  '    except OSError as error:                          # the private temp file is removed; the target was not replaced\n'
  '        raise Refused("stop", f"could not write {st[\'file\']} ({error}); the file is unchanged and nothing is reported as written")\n'
  '    st["expected_sha"] = sha(new)\n',
  '        st["repair_rounds"] += 1\n    atomic_replace(target, new)\n    st["expected_sha"] = sha(new)\n'),
 ('def write(args):\n'
  '    try:\n'
  '        data = Path(args.content_file).read_bytes()\n'
  '    except OSError as error:\n'
  '        raise Refused("stop", f"cannot read the content file ({error}); nothing was written")\n'
  '    return guarded_write(args, lambda cur: data)\n',
  'def write(args):\n    data = Path(args.content_file).read_bytes()\n    return guarded_write(args, lambda cur: data)\n'),
 ('    def fn(cur):\n'
  '        try:\n'
  '            find, repl = args.find.encode("utf-8"), args.replace.encode("utf-8")\n'
  '        except UnicodeEncodeError:\n'
  '            raise Refused("stop", "find or replace text is not valid UTF-8; nothing was written")\n'
  '        if not find:\n'
  '            raise Refused("stop", "find text is empty")\n'
  '        n = cur.count(find)                           # on bytes: exactly the named bytes change, line endings stay as they are\n'
  '        if n != 1:\n',
  '    def fn(cur):\n        text = cur.decode("utf-8")\n        n = text.count(args.find)\n        if n != 1:\n'),
 ('            raise Refused("stop", f"find text occurs {n} times, expected exactly once")\n'
  '        return cur.replace(find, repl)\n'
  '    return guarded_write(args, fn)\n',
  '            raise Refused("stop", f"find text occurs {n} times, expected exactly once")\n'
  '        return text.replace(args.find, args.replace).encode("utf-8")\n'
  '    return guarded_write(args, fn)\n'),
 ('\n'
  'def redact(text: str) -> str:\n'
  '    """Known secret fields (NAME containing TOKEN, SECRET, PASSWORD, PASSWD, API_KEY or AUTH, so also Authorization and\n'
  '    Proxy-Authorization, followed by = or :) lose their value: a quoted value completely (spaces and escaped quotes included; an '
  'unclosed\n'
  '    quote runs to the end of the line), any other value, including an authentication scheme such as `Bearer`, to the end of the line, '
  'because\n'
  '    its end cannot be told. A pattern list, not a detector: secrets in other forms are not recognised, and harmless text after a field\n'
  '    is redacted too."""\n'
  '    return SECRET_RE.sub(lambda m: f"{m.group(1)}=<redacted>", text)\n'
  '\n'
  '\n'
  'def run_npm(npm, script, cwd):\n',
  '\ndef run_npm(npm, script, cwd):\n'),
 ('def run_npm(npm, script, cwd):\n'
  '    try:\n'
  '        p = subprocess.run([npm, "run", script], cwd=cwd, capture_output=True, text=True, errors="replace")\n'
  '    except OSError as error:                          # the tool cannot be started: not run, never "failed" or "passed"\n'
  '        return {"ran": False, "exit": None, "unavailable": True, "reason": f"could not run: {error}"}\n'
  '    return {"ran": True, "exit": p.returncode, "tail": redact(p.stdout + p.stderr)[-TAIL:]}      # redact first, then cut\n'
  '\n',
  'def run_npm(npm, script, cwd):\n'
  '    p = subprocess.run([npm, "run", script], cwd=cwd, capture_output=True, text=True)\n'
  '    return {"ran": True, "exit": p.returncode, "tail": (p.stdout + p.stderr)[-TAIL:]}\n'
  '\n'),
 ('    build = run_npm(args.npm, "build", sd)\n'
  '    if build.get("unavailable"):\n'
  '        chk = {"ran": False, "exit": None, "reason": "not run: the build could not be started"}\n'
  '    elif build["exit"] == 0:\n'
  '        assert_base(st, args.state, "during the build")\n',
  '    build = run_npm(args.npm, "build", sd)\n    if build["exit"] == 0:\n        assert_base(st, args.state, "during the build")\n'),
 ('    ok = build["exit"] == 0 and chk["exit"] == 0\n'
  '    unavailable = bool(build.get("unavailable") or chk.get("unavailable"))\n'
  '    if not unavailable:                                     # a tool that could not start is no failure of the change: no repair round\n'
  '        st["check_failed_since_write"] = not ok\n'
  '    st["checks"].append({"build": build["exit"], "check": chk["exit"], "sha": st["expected_sha"], **({"unavailable": True} if '
  'unavailable else {})})\n'
  '    save_state(args.state, st)\n',
  '    ok = build["exit"] == 0 and chk["exit"] == 0\n'
  '    st["check_failed_since_write"] = not ok\n'
  '    st["checks"].append({"build": build["exit"], "check": chk["exit"], "sha": st["expected_sha"]})\n'
  '    save_state(args.state, st)\n'),
 ('    save_state(args.state, st)\n'
  '    return out({"state": "checked" if ok else "not-run" if unavailable else "failed", "build": build, "check": chk, "checked_sha": '
  'st["expected_sha"],\n'
  '                "repair_rounds_used": st["repair_rounds"], "repair_rounds_left": max(0, REPAIR_LIMIT - st["repair_rounds"])}, 0 if ok '
  'else 1)\n',
  '    save_state(args.state, st)\n'
  '    return out({"state": "checked" if ok else "failed", "build": build, "check": chk, "checked_sha": st["expected_sha"],\n'
  '                "repair_rounds_used": st["repair_rounds"], "repair_rounds_left": max(0, REPAIR_LIMIT - st["repair_rounds"])}, 0 if ok '
  'else 1)\n'),
 ('\n'
  'def read_backup(folder, st) -> bytes:\n'
  '    """The original backup, read without following a link in any component below the session folder; it must still be the original."""\n'
  '    cur = Path(folder)\n'
  '    for part in ("original", *Path(st["file"]).parts[:-1]):\n'
  '        cur = cur / part\n'
  '        if not is_real_dir(cur):\n'
  '            raise Refused("refused", "the original backup is damaged or replaced (not a plain folder); nothing was read")\n'
  '    try:\n'
  '        data = safe_read(cur / Path(st["file"]).name)\n'
  '    except OSError:\n'
  '        raise Refused("refused", "the original backup is damaged or replaced (not a plain file); nothing was read")\n'
  '    if sha(data) != st["original_sha"]:\n'
  '        raise Refused("refused", "the original backup differs from the recorded original; it is not shown as this run\'s original")\n'
  '    return data\n'
  '\n'
  '\n'
  'def total_diff(st, folder) -> str:\n',
  '\ndef total_diff(st, folder) -> str:\n'),
 ('def total_diff(st, folder) -> str:\n'
  '    orig = read_backup(folder, st).decode("utf-8", "replace").splitlines(True)   # bytes: a line-ending change shows up\n'
  '    now = read_regular(bound_target(st)).decode("utf-8", "replace").splitlines(True)\n'
  '    return "".join(difflib.unified_diff(orig, now, "original/" + st["file"], "final/" + st["file"]))\n',
  'def total_diff(st, folder) -> str:\n'
  '    orig = (Path(folder) / "original" / st["file"]).read_text(encoding="utf-8").splitlines(True)\n'
  '    now = read_regular(bound_target(st)).decode("utf-8").splitlines(True)\n'
  '    return "".join(difflib.unified_diff(orig, now, "original/" + st["file"], "final/" + st["file"]))\n'),
 ('    return out({"file": st["file"], "diff": total_diff(st, args.state)})\n'
  '\n'
  '\n'
  'class CleanupRefused(OSError):\n'
  '    """The backup tree is not exactly what this run created; nothing was removed."""\n'
  '\n'
  '\n'
  'def plan_own_removal(folder: Path, st: dict) -> list:\n'
  '    """Checks the WHOLE backup tree against the exact expected objects (names, types, original content) and returns the removal\n'
  '    order. Any unexpected entry, replaced object or link stops everything, before the first deletion."""\n'
  '    parts = Path(st["file"]).parts\n'
  '    expected = {folder: {".owner": "f", "index.json": "f", "original": "d"}}\n'
  '    cur = folder / "original"\n'
  '    for part in parts[:-1]:\n'
  '        expected[cur] = {part: "d"}\n'
  '        cur = cur / part\n'
  '    expected[cur] = {parts[-1]: "f"}\n'
  '    if not is_real_dir(folder):\n'
  '        raise CleanupRefused("the session folder is not a plain folder")\n'
  '    for directory, names in expected.items():\n'
  '        if not is_real_dir(directory):\n'
  '            raise CleanupRefused(f"{directory.relative_to(folder)} is missing or replaced (not a plain folder)")\n'
  '        found = {p.name: p for p in directory.iterdir()}\n'
  '        if set(found) != set(names):\n'
  '            odd = sorted(set(found) ^ set(names))\n'
  '            raise CleanupRefused(f"unexpected or missing entries in {directory.relative_to(folder) if directory != folder else \'.\'}: '
  '{\', \'.join(odd)}")\n'
  '        for name, kind in names.items():\n'
  '            mode = os.lstat(found[name]).st_mode\n'
  '            if (kind == "f" and not stat.S_ISREG(mode)) or (kind == "d" and not stat.S_ISDIR(mode)):\n'
  '                raise CleanupRefused(f"{found[name].relative_to(folder)} was replaced by another kind of object")\n'
  '    backup = folder / "original" / Path(*parts)\n'
  '    try:\n'
  '        if sha(safe_read(backup)) != st["original_sha"]:\n'
  '            raise CleanupRefused("the backup file no longer equals the recorded original")\n'
  '    except OSError as error:\n'
  '        raise CleanupRefused(f"the backup file cannot be verified ({error})")\n'
  '    chain = [backup]\n'
  '    cur = backup.parent\n'
  '    while cur != folder:\n'
  '        chain.append(cur)\n'
  '        cur = cur.parent\n'
  '    return chain + [folder / ".owner", folder / "index.json", folder]\n'
  '\n'
  '\n'
  'def remove_own_folder(folder: Path, st: dict):\n'
  '    """Removes exactly the objects `begin` and the run created, and only after the complete tree has been verified."""\n'
  '    steps = plan_own_removal(folder, st)\n'
  '    for step in steps:\n'
  '        step.rmdir() if step.is_dir() and not step.is_symlink() else step.unlink()\n'
  '\n',
  '    return out({"file": st["file"], "diff": total_diff(st, args.state)})\n\n'),
 ('        tech = "stale: the file was written after the last check"\n'
  '    elif last.get("unavailable"):\n'
  '        tech = "not run: npm could not be started"\n'
  '    else:\n',
  '        tech = "stale: the file was written after the last check"\n    else:\n'),
 ('            try:\n                remove_own_folder(folder, st)\n                report["backup"] = "removed (own folder only)"\n',
  '            try:\n                shutil.rmtree(folder)\n                report["backup"] = "removed (own folder only)"\n'),
 ('                del report["backup_folder"]\n'
  '            except CleanupRefused as e:\n'
  '                report["backup"] = f"kept (nothing removed); cleanup refused: {e}"\n'
  '            except OSError as e:\n',
  '                del report["backup_folder"]\n            except OSError as e:\n'),
 ('            except OSError as e:\n'
  '                left = sorted(str(p.relative_to(folder)) for p in folder.rglob("*")) if folder.is_dir() else []\n'
  '                report["backup"] = f"kept; cleanup failed part-way ({e}); remaining: {\', \'.join(left) if left else \'nothing\'}"\n'
  '    return out(report)\n',
  '            except OSError as e:\n                report["backup"] = f"kept; removal failed: {e}"\n    return out(report)\n'),
 ('        return out({"state": r.state, "message": str(r), **r.extra}, 1)\n'
  '    except (OSError, UnicodeError, ValueError) as error:\n'
  '        return out({"state": "stop", "message": f"a file or process operation failed ({error}). Nothing is reported as done; "\n'
  '                    "read the file and the git status before the next step"}, 1)\n'
  '\n',
  '        return out({"state": r.state, "message": str(r), **r.extra}, 1)\n\n')]


class IdentityTests(unittest.TestCase):
    def test_edit_helper_differs_from_the_source_only_by_the_listed_hunks(self):
        text = RUNTIME.read_text(encoding="utf-8")
        for new, old in reversed(PROTECTION):          # the protection corrections were applied last: undo them first
            self.assertEqual(text.count(new), 1, ("protection", new[:70]))
            text = text.replace(new, old)
        for new, old in reversed(MIGRATION):
            self.assertEqual(text.count(new), 1, ("migration", new[:70]))
            text = text.replace(new, old)
        self.assertEqual(sha_bytes(text.encode()), SOURCE["scripts/edit/edit.py"], "diff exceeds the change lists")

    def test_the_migration_list_is_only_renames_and_the_resolver_path(self):
        joined = "".join(new for new, _ in MIGRATION)
        self.assertEqual(len(MIGRATION), 5)
        self.assertIn('RESOLVER = HERE.parents[1] / "_shared" / "scripts" / "which_site.py"', joined)
        for _, old in MIGRATION:
            self.assertTrue(re.search(r"/zyris-website:|optimize|contracts/edit", old), old[:80])    # each hunk replaces an old name or path

    def test_inventoried_edit_and_publish_sources_are_accounted_for(self):
        changes = (ROOT / "docs/migration/changes.md").read_text()
        for source in ("scripts/edit/edit.py", "skills/edit/SKILL.md", "contracts/edit.md", "tests/edit/helpers.py", "tests/edit/test_edit.py",
                       "tests/behavior/cases.md", "skills/publish/SKILL.md", "contracts/publish.md", "templates/github/workflows/README.md"):
            self.assertIn(source, SOURCE, source)
            self.assertIn(source, changes, source)
        for target in ("skills/edit/scripts/edit.py", "skills/edit/SKILL.md", "skills/edit/references/edit.md", "skills/publish/SKILL.md",
                       "tests/support/edit_helpers.py", "tests/behavior/edit_cases.md"):
            self.assertIn(target, changes, target)

    def test_the_skill_ships_only_text_and_the_single_helper(self):
        found = {p.relative_to(SKILL).as_posix() for p in SKILL.rglob("*") if p.is_file()}
        self.assertEqual(found, {"SKILL.md", "references/edit.md", "scripts/edit.py"})

    def test_exactly_five_public_skills_and_a_shared_folder_without_skill_md(self):
        skills = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
        self.assertEqual(skills, {"setup", "preview", "optimize", "edit", "publish"})
        self.assertFalse((ROOT / "skills" / "_shared" / "SKILL.md").exists())

    def test_the_resolver_is_the_shared_one_and_there_is_no_copy(self):
        self.assertTrue((ROOT / "skills/_shared/scripts/which_site.py").is_file())
        self.assertEqual([p for p in (ROOT / "skills").rglob("which_site.py")], [ROOT / "skills/_shared/scripts/which_site.py"])
        text = RUNTIME.read_text()
        self.assertIn('HERE.parents[1] / "_shared" / "scripts" / "which_site.py"', text)
        self.assertNotRegex(text, r"""["']optimize["']""")
        self.assertEqual(len(re.findall(r"import (errors|sites|manifest|schema)\b", text)), 0)


class RuntimeHygieneTests(unittest.TestCase):
    def test_only_standard_library_is_imported(self):
        for node in ast.walk(ast.parse(RUNTIME.read_text())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module] if isinstance(node, ast.ImportFrom) and node.module else []
            for name in names:
                self.assertIn(name.split(".")[0], sys.stdlib_module_names, name)

    def test_the_runtime_never_installs_and_uses_only_read_git_commands(self):
        text = RUNTIME.read_text()
        self.assertNotRegex(text, r"""["'](install|ci|i|update|add)["']""")
        calls = set(re.findall(r'git\(root,\s*"([a-z-]+)"', text))
        self.assertEqual(calls, {"rev-parse", "status"})
        self.assertNotIn("rmtree", text)                      # the cleanup never deletes a tree it has not verified object by object
        for verb in ("commit", "push", "add", "reset", "checkout", "stash", "clean", "restore", "rm", "mv", "apply", "merge"):
            self.assertNotRegex(text, r"""git\(root,\s*["']%s["']""" % verb)
        self.assertEqual(re.findall(r"""\[npm, "run", script\]""", text), ['[npm, "run", script]'])

    def test_resolver_child_process_never_writes_bytecode(self):
        self.assertIn('[sys.executable, "-I", "-B", str(RESOLVER)', RUNTIME.read_text())

    def test_no_developer_paths_source_checkout_or_old_names_in_the_skill_payload(self):
        bad = ("www.draftmode", "ai.plugins", "interview-coach", "/Users/", "CLAUDE_PLUGIN_ROOT", "templates/setup", "contracts/", "draftmode.io",
               "HANDOVER", "fux-law", "familien-recht", "/zyris-website:", "ZYRIS_WEBSITE_STATE_DIR", "PYTHONPATH")
        for path in SKILL.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                for word in bad:
                    if word == "PYTHONPATH" and path.name in ("SKILL.md", "edit.md"):
                        continue                                  # the skill text says "no PYTHONPATH"
                    if word == "ZYRIS_WEBSITE_STATE_DIR" and path.name == "edit.md":
                        continue                                  # the reference states that edit does not use it (Q5)
                    self.assertNotIn(word, text, (path.relative_to(ROOT), word))

    def test_internal_names_are_unchanged_by_decision_q5(self):
        self.assertIn('"zyris-website"', RUNTIME.read_text())               # the backup area folder under TMPDIR
        self.assertIn("edit-{site['site']}-{stamp}", RUNTIME.read_text())

    def test_no_state_or_bytecode_in_the_installed_skill(self):
        self.assertEqual(list(SKILL.rglob("__pycache__")), [])
        self.assertEqual(list(SKILL.rglob("*.pyc")), [])

    def test_tests_use_only_fictional_site_names(self):
        for path in list((ROOT / "tests").rglob("*edit*")) + [ROOT / "tests/support/edit_helpers.py"]:
            if path.is_file() and path.suffix in (".py", ".md") and path.name != "test_edit_contract.py":
                text = path.read_text(encoding="utf-8")
                for word in ("draftmode.io", "fux-law", "familien-recht", "www.draftmode"):
                    self.assertNotIn(word, text, (path.name, word))


class SkillTextTests(unittest.TestCase):
    def front(self):
        return TEXT.split("---")[1]

    def test_frontmatter_name_matches_the_folder_and_has_a_description(self):
        self.assertRegex(self.front(), r"(?m)^name: edit$")
        self.assertRegex(self.front(), r"(?m)^description: \S")

    def test_allowed_tools_are_exactly_the_narrow_patterns_of_the_call_forms(self):
        tools = re.findall(r"(?m)^  - '(.+)'$", self.front())
        self.assertEqual(tools, ['Bash(python3 -B "${CLAUDE_SKILL_DIR}/scripts/edit.py" *)',
                                 'Bash(python3 -B "${CLAUDE_SKILL_DIR}/../preview/scripts/control.py" *)',
                                 'Bash(test -f "${CLAUDE_SKILL_DIR}/scripts/edit.py")',
                                 'Bash(test -f "${CLAUDE_SKILL_DIR}/../preview/scripts/control.py")'])
        for tool in tools:
            self.assertNotRegex(tool, r"python3 \*|python3:\*|Bash\(\*\)|Bash\(sh|Bash\(bash|Bash\(npm|Bash\(git|Bash\(cd|Bash\(rm")
        calls = re.findall(r'(?m)^python3 -B "\$\{CLAUDE_SKILL_DIR\}/((?:\.\./preview/)?scripts/\w+\.py)" (\S+)', TEXT)
        self.assertEqual({c[0] for c in calls}, {"scripts/edit.py", "../preview/scripts/control.py"})   # every call is covered by exactly one pattern
        python_patterns = [t for t in tools if t.startswith("Bash(python3")]
        for script, _ in calls:
            covering = [t for t in python_patterns if f'"${{CLAUDE_SKILL_DIR}}/{script}" *)' in t]
            self.assertEqual(len(covering), 1, script)
        for pattern in python_patterns:
            self.assertTrue(any(f"/{script}\"" in pattern for script, _ in calls), pattern)
        for script in ("scripts/edit.py", "../preview/scripts/control.py"):
            self.assertIn(f'test -f "${{CLAUDE_SKILL_DIR}}/{script}"', TEXT)
        self.assertEqual(len(re.findall(r"python3 -B", self.front())), 2)

    def test_every_call_form_writes_the_script_path_as_one_quoted_argument_with_python3_dash_B(self):
        for line in TEXT.splitlines():
            if "scripts/" in line and line.startswith("python3"):
                self.assertRegex(line, r'^python3 -B "\$\{CLAUDE_SKILL_DIR\}/(\.\./preview/)?scripts/\w+\.py" ')
        self.assertNotIn("PYTHONPATH=", TEXT)
        self.assertNotIn("cd ", TEXT.replace("cd <", ""))

    def test_the_call_forms_cover_the_seven_helper_commands_and_the_documented_preview_verbs(self):
        listed = re.findall(r'(?m)^python3 -B "\$\{CLAUDE_SKILL_DIR\}/scripts/edit\.py" (\w+)', TEXT)
        self.assertEqual(listed, ["preflight", "begin", "write", "replace", "check", "diff", "finish"])
        helper = RUNTIME.read_text()
        for name in listed:
            self.assertIn(f'add_parser("{name}")' if name in ("preflight", "begin") else f'"{name}"', helper, name)
        for flag in ("--cwd", "--last", "--root", "--site", "--state", "--content-file", "--find", "--replace", "--visual-done", "--visual-substitute", "--visual-not-done"):
            self.assertIn(f'"{flag}"', helper, flag)
            self.assertIn(flag, TEXT, flag)
        control = (ROOT / "skills/preview/scripts/control.py").read_text()
        for verb in ("start", "status", "inspect"):
            self.assertIn(f"`{verb}`", TEXT.replace("<start|status>", "`start` `status`") + " `inspect`")
            self.assertIn(f'"{verb}"', control, verb)
        for flag in ("--page", "--expect"):
            self.assertIn(flag, control, flag)
        self.assertNotIn('"--npm"', TEXT)
        self.assertNotIn("--npm", re.sub(r"`--npm`[^\n]*", "", TEXT))      # the test hook is not a call form of the skill

    def test_claude_and_codex_path_handling_are_separated(self):
        for needle in ("**Claude:**", "**Codex:**", "Do **not** run `${CLAUDE_SKILL_DIR}` as a shell variable", "**No path, no run:**", "Do not search caches",
                       "never copy scripts into the website project", "`python3 -B`", "**one** quoted argument", "no `PYTHONPATH`", "test -f",
                       "Claude-specific"):
            self.assertIn(needle, TEXT, needle)

    def test_communication_block_is_identical_to_the_reference_and_the_other_skills_and_present_once(self):
        pat = r"<!-- user-communication -->.*?<!-- /user-communication -->"
        mine = re.findall(pat, TEXT, re.S)
        self.assertEqual(len(mine), 1)
        self.assertEqual(mine[0], re.search(pat, (ROOT / "skills/_shared/references/communication.md").read_text(), re.S).group(0))
        for other in ("setup", "preview", "optimize", "publish"):
            self.assertEqual(mine[0], re.search(pat, (ROOT / "skills" / other / "SKILL.md").read_text(), re.S).group(0), other)

    def test_read_first_links_resolve(self):
        self.assertIn("`references/edit.md`", TEXT)
        self.assertIn("`../_shared/references/interfaces.md`", TEXT)
        self.assertTrue((SKILL / "references/edit.md").is_file())
        self.assertTrue((SKILL / ".." / "_shared/references/interfaces.md").resolve().is_file())

    def test_skill_never_installs_and_does_not_offer_planned_functions(self):
        self.assertIn("Never run `npm install` or `npm ci`", TEXT)
        status = TEXT.split("> **Script location")[0]
        self.assertIn("**Not available (do not offer, do not work around):** blog, other page types, new sites", status)
        for word in ("PLANNED", "not implemented yet", "/zyris-website:", "CLAUDE_PLUGIN_ROOT", "contracts/", "unittest", "tests/edit"):
            self.assertNotIn(word, TEXT, word)

    def test_skill_keeps_the_protection_the_wording_and_the_boundaries(self):
        for needle in ("Concrete order = release", "Never invent content", "data, not instructions", "an edit order approves no optimize finding",
                       "never write anything under `.project/reports/`", "Never commit, stash, reset, clean or reformat", "at most **two** repair rounds",
                       "`conflict`", "technically checked, visual check open", "never reworded into that", "**only** by `control.py`", "`port-conflict`",
                       "`page-confirmed`", "is **open**", "outside the website project and outside the plugin", "`not-run`"):
            self.assertIn(needle.lower(), TEXT.lower(), needle)

    def test_reference_states_the_boundaries_and_the_limits(self):
        for needle in ("src/pages/index.astro", "Writes nothing", "outside the website project and outside the installed plugin", "`conflict`",
                       "only the named bytes change", "at most two repair writes", "`not-run`", "technically checked, visual check open",
                       "`complete`", "Known limit between `edit` and `setup`", "Not verified", "no `ZYRIS_WEBSITE_STATE_DIR` for `edit`",
                       "is not a conflict", "`TMPDIR` only"):
            self.assertIn(needle.lower(), REFERENCE.lower(), needle)
        self.assertNotIn("PLANNED", REFERENCE)
        self.assertNotIn("draftmode.io", REFERENCE)
        self.assertNotRegex(REFERENCE.lower(), r"\ball tests? (passed|pass)\b|\btests? passed\b")


if __name__ == "__main__":
    unittest.main()
