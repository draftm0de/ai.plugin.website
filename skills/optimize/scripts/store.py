"""Safe storage of optimize reports and the work list (standard library only).

Layout (per canonical site name from the manifest):
  .project/reports/<site>/optimize/<timestamp>.md   immutable snapshots, created exclusively
  .project/reports/<site>/optimize.md               the one authoritative work list, replaced atomically

Guarantees: the site name is validated, no path component below the repository root may be a
symlink, snapshots never overwrite (a collision gets a numeric suffix), the work list is replaced
only through a private temp file in the same folder (os.replace), updates are serialised by an
exclusively created lock file, and a changed work list is detected by its SHA-256.
"""
import hashlib
import os
import re
import tempfile
import time
from pathlib import Path

from site_common.errors import Stop

SITE_RE = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")
REPORTS = Path(".project") / "reports"
WORKLIST = "optimize.md"
SNAPSHOTS = "optimize"
LOCK = ".optimize.lock"


class Conflict(Stop):
    """The work list changed or is locked by someone else; nothing was overwritten."""


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _no_symlinks(root: Path, target: Path):
    """Every existing component from root down to target must be a real directory (or the final file)."""
    current = root
    for part in target.relative_to(root).parts:
        current = current / part
        if current.is_symlink():
            raise Stop(f"refusing to use {current}: it is a symlink (report paths must stay inside the repository)")


def site_root(root: Path, site: str, create: bool = False) -> Path:
    """.project/reports/<site>/ after validating the name and every component; optionally create it."""
    if not isinstance(site, str) or not SITE_RE.match(site) or ".." in site:
        raise Stop(f"site name '{site}' is not usable as a report folder name")
    root = root.resolve()
    target = root / REPORTS / site
    _no_symlinks(root, target)
    if create:
        current = root
        for part in target.relative_to(root).parts:
            current = current / part
            if current.is_symlink():
                raise Stop(f"refusing to use {current}: it is a symlink")
            current.mkdir(exist_ok=True)
            if not current.is_dir():
                raise Stop(f"{current} exists and is not a folder")
    resolved = target.resolve()
    if root not in resolved.parents and resolved != root:
        raise Stop(f"report path escapes the repository: {resolved}")
    return target


def snapshot_dir(root: Path, site: str, create: bool = False) -> Path:
    base = site_root(root, site, create)
    path = base / SNAPSHOTS
    _no_symlinks(root.resolve(), path)
    if create:
        path.mkdir(exist_ok=True)
        if path.is_symlink() or not path.is_dir():
            raise Stop(f"{path} must be a real folder")
    return path


def worklist_path(root: Path, site: str) -> Path:
    base = site_root(root, site)
    path = base / WORKLIST
    _no_symlinks(root.resolve(), path)
    return path


def read_worklist(root: Path, site: str):
    """Return (text, sha256) or (None, None) when no work list exists yet."""
    path = worklist_path(root, site)
    if not path.exists():
        return None, None
    if not path.is_file():
        raise Stop(f"{path} is not a regular file")
    try:
        text = path.read_bytes().decode("utf-8")     # no newline translation: carriage returns inside proposal text are part of the stored text
    except (OSError, UnicodeDecodeError) as error:
        raise Stop(f"{path} cannot be read as a UTF-8 work list ({error}). Nothing was changed. Restore it from git or move it aside to start a new list.")
    return text, sha256_text(text)


def _private_tmp(directory: Path, prefix: str, text: str) -> Path:
    fd, name = tempfile.mkstemp(prefix=prefix, suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "wb") as handle:           # byte-exact: the text is stored exactly as rendered
            handle.write(text.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(name, 0o644)
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise
    return Path(name)


def write_snapshot(root: Path, site: str, stamp: str, make_text, before_link=None) -> tuple:
    """Create <stamp>.md exclusively (never overwrites); on collision use <stamp>-2.md, -3.md, ...

    make_text(report_name) is called per candidate name so the text can name itself. Returns (path, report_name)
    where report_name is the work-list-relative reference 'optimize/<file>'. before_link is a test hook.
    """
    directory = snapshot_dir(root, site, create=True)
    for n in range(1, 1000):
        file = f"{stamp}.md" if n == 1 else f"{stamp}-{n}.md"
        final = directory / file
        if final.exists() or final.is_symlink():
            continue
        name = f"{SNAPSHOTS}/{file}"
        tmp = _private_tmp(directory, ".snapshot-", make_text(name))
        try:
            if before_link:
                before_link(final)
            os.link(tmp, final)   # atomic and never overwrites: fails if the name appeared meanwhile
        except FileExistsError:
            continue
        finally:
            tmp.unlink(missing_ok=True)
        return final, name
    raise Stop(f"no free report name for {stamp} in {directory}")


class Lock:
    """Exclusive lock file next to the work list; a leftover lock is reported, never broken silently."""

    def __init__(self, root: Path, site: str):
        self.path = site_root(root, site, create=True) / LOCK
        self.held = False

    def __enter__(self):
        try:
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
        except FileExistsError:
            raise Conflict(
                f"another optimize run holds {self.path}. If no run is active (an earlier run was killed), "
                "check that and remove that lock file by hand; the work list itself is unchanged.")
        with os.fdopen(fd, "w") as handle:
            handle.write(f"pid={os.getpid()} time={time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n")
        self.held = True
        return self

    def __exit__(self, *exc):
        if self.held:
            self.path.unlink(missing_ok=True)
            self.held = False


def replace_worklist(root: Path, site: str, text: str, expected_sha):
    """Atomically replace the work list; Conflict if its content is not the one the caller started from."""
    path = worklist_path(root, site)
    current, sha = read_worklist(root, site)
    if sha != expected_sha:
        raise Conflict(
            f"{path} was changed while this run was working (expected {str(expected_sha)[:12]}, found {str(sha)[:12]}). "
            "Nothing was overwritten; run the command again.")
    tmp = _private_tmp(path.parent, ".optimize-", text)
    try:
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
