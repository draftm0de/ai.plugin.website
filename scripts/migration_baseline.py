#!/usr/bin/env python3
"""Read-only drift check of a source tree against a historical migration inventory.

Development tool only (not shipped runtime). It never writes a baseline, never
imports or starts code from the checked tree and reads only the files the
inventory lists, plus a directory listing of the plugin root to find new files.

Supported inventory formats:
  website-migration-source-inventory/1    (files below ``plugin_root`` or repo root)
  website-migration-reference-baseline/1  (paths relative to a common parent)

Exit codes: 0 no drift, 1 drift found, 2 usage or damaged inventory.

Symlinks (in inventoried paths, their parent components, or new ones) are never followed; they are
reported as drift. Inventory paths must be relative and stay below the base; ``plugin_root`` is required
for source inventories and is the only tree that is listed.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath

SOURCE_FORMAT = "website-migration-source-inventory/1"
REFERENCE_FORMAT = "website-migration-reference-baseline/1"
ALWAYS_IGNORED_PARTS = {"__pycache__"}
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class InventoryError(Exception):
    """The inventory itself is damaged or unsafe; nothing of the tree was read."""


def valid_rel(value, what: str) -> str:
    """A relative POSIX path that stays below its base; returns it or raises InventoryError."""
    if not isinstance(value, str) or not value:
        raise InventoryError(f"{what}: path must be a non-empty string")
    if "\x00" in value or "\\" in value:
        raise InventoryError(f"{what}: path contains NUL or backslash: {value!r}")
    pure = PurePosixPath(value)
    if pure.is_absolute() or re.match(r"^[A-Za-z]:", value):
        raise InventoryError(f"{what}: absolute path not allowed: {value!r}")
    if value.endswith("/") or any(part in ("", ".", "..") for part in value.split("/")):
        raise InventoryError(f"{what}: path must not contain empty, '.' or '..' components: {value!r}")
    return value


def sha256_file(path: Path) -> str:
    """Hash a regular file opened without following a final symlink."""
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    digest = hashlib.sha256()
    with os.fdopen(fd, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_path(root: Path, rel: str) -> tuple[str, str]:
    """Walk ``rel`` below ``root`` component by component with lstat, never following links.

    Returns (state, detail): ok | missing | symlink | not-regular."""
    current = root
    parts = rel.split("/")
    for index, part in enumerate(parts):
        current = current / part
        try:
            mode = os.lstat(current).st_mode
        except FileNotFoundError:
            return "missing", ""
        except OSError as exc:
            return "unreadable", str(exc)
        if stat.S_ISLNK(mode):
            return "symlink", "/".join(parts[: index + 1])
        if index < len(parts) - 1 and not stat.S_ISDIR(mode):
            return "not-regular", "/".join(parts[: index + 1])
        if index == len(parts) - 1 and not stat.S_ISREG(mode):
            return "not-regular", rel
    return "ok", ""


def load_inventory(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InventoryError(f"inventory unreadable: {path}: {exc}")
    if not isinstance(data, dict) or data.get("format") not in (SOURCE_FORMAT, REFERENCE_FORMAT):
        found = data.get("format") if isinstance(data, dict) else type(data).__name__
        raise InventoryError(f"unsupported inventory format in {path}: {found}")
    files = data.get("files")
    if not isinstance(files, list):
        raise InventoryError("inventory has no 'files' list")
    seen = set()
    for index, entry in enumerate(files):
        where = f"files[{index}]"
        if not isinstance(entry, dict):
            raise InventoryError(f"{where}: entry must be an object")
        valid_rel(entry.get("path"), where)
        if entry["path"] in seen:
            raise InventoryError(f"{where}: duplicate path {entry['path']}")
        seen.add(entry["path"])
        digest = entry.get("sha256")
        if not isinstance(digest, str) or not SHA_RE.match(digest):
            raise InventoryError(f"{where}: sha256 must be 64 lowercase hex digits")
    if data["format"] == SOURCE_FORMAT:
        valid_rel(data.get("plugin_root"), "plugin_root")
        excluded = data.get("excluded", [])
        if not isinstance(excluded, list) or not all(isinstance(e, dict) and isinstance(e.get("pattern"), str) and e["pattern"] for e in excluded):
            raise InventoryError("excluded: must be a list of objects with a non-empty string 'pattern'")
        repo = data.get("repository", {})
    else:
        repos = data.get("repositories", {})
        if not isinstance(repos, dict):
            raise InventoryError("repositories: must be an object")
        for name, recorded in repos.items():
            valid_rel(name, f"repositories[{name!r}]")
            if "/" in name:
                raise InventoryError(f"repositories[{name!r}]: must be a single folder name")
            _check_recorded_git(recorded, f"repositories[{name!r}]")
        return data
    _check_recorded_git(repo, "repository")
    return data


def _check_recorded_git(recorded, where: str) -> None:
    if not isinstance(recorded, dict):
        raise InventoryError(f"{where}: must be an object")
    if "head" in recorded and not isinstance(recorded["head"], str):
        raise InventoryError(f"{where}.head: must be a string")
    status = recorded.get("status_porcelain")
    if status is not None and not (isinstance(status, list) and all(isinstance(s, str) for s in status)):
        raise InventoryError(f"{where}.status_porcelain: must be a list of strings")


def _excluded(rel: str, patterns: list[str]) -> bool:
    parts = set(rel.split("/"))
    if parts & ALWAYS_IGNORED_PARTS or rel.endswith((".pyc", ".pyo")) or rel.rsplit("/", 1)[-1] == ".DS_Store":
        return True
    return any(fnmatch.fnmatch(rel, p) for p in patterns)


def _dir_excluded(rel: str, patterns: list[str]) -> bool:
    """Do not even list a directory whose content the exclusions cover (private/generated areas)."""
    return rel.rsplit("/", 1)[-1] in ALWAYS_IGNORED_PARTS or any(fnmatch.fnmatch(rel + "/_", p) for p in patterns)


def compare_files(root: Path, entries: list[dict]) -> dict[str, list[str]]:
    """Classify every inventoried path without following symlinks."""
    result = {"changed": [], "missing": [], "unreadable": [], "unsafe": []}
    for entry in entries:
        rel, expected = entry["path"], entry["sha256"]
        state, detail = inspect_path(root, rel)
        if state == "missing":
            result["missing"].append(rel)
        elif state == "symlink":
            result["unsafe"].append(f"{rel} (symlink at {detail}; not followed)")
        elif state == "not-regular":
            result["unsafe"].append(f"{rel} (not a regular file at {detail}; not read)")
        elif state == "unreadable":
            result["unreadable"].append(rel)
        else:
            try:
                actual = sha256_file(root / rel)
            except OSError:
                result["unreadable"].append(rel)
                continue
            if actual != expected:
                result["changed"].append(rel)
    return result


def find_new_files(root: Path, plugin_root: str, known: set[str], exclusions: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Return (new files, new symlinks, problems). Never scans anything but ``plugin_root``."""
    state, detail = inspect_path_dir(root, plugin_root)
    if state != "ok":
        return [], [], [f"plugin_root {plugin_root}: {state}{(' at ' + detail) if detail else ''}; nothing scanned"]
    found, links = [], []
    for current, dirs, files in os.walk(root / plugin_root, followlinks=False):
        rel_dir = Path(current).relative_to(root).as_posix()
        kept = []
        for name in sorted(dirs):
            rel = f"{rel_dir}/{name}"
            if os.path.islink(Path(current) / name):
                if rel not in known and not _excluded(rel, exclusions) and not _dir_excluded(rel, exclusions):
                    links.append(rel)
            elif not _dir_excluded(rel, exclusions):
                kept.append(name)
        dirs[:] = kept
        for name in sorted(files):
            rel = f"{rel_dir}/{name}"
            if rel in known or _excluded(rel, exclusions):
                continue
            (links if os.path.islink(Path(current) / name) else found).append(rel)
    return sorted(found), sorted(links), []


def inspect_path_dir(root: Path, rel: str) -> tuple[str, str]:
    current = root
    parts = rel.split("/")
    for index, part in enumerate(parts):
        current = current / part
        try:
            mode = os.lstat(current).st_mode
        except OSError:
            return "missing", ""
        if stat.S_ISLNK(mode):
            return "symlink", "/".join(parts[: index + 1])
        if not stat.S_ISDIR(mode):
            return "not-a-directory", "/".join(parts[: index + 1])
    return "ok", ""


def git_lines(repo: Path, *args: str) -> list[str] | None:
    try:
        out = subprocess.run(
            ["git", "-c", "core.fsmonitor=false", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.splitlines() if out.returncode == 0 else None


def git_state(repo: Path) -> dict:
    head = git_lines(repo, "rev-parse", "HEAD")
    status = git_lines(repo, "status", "--porcelain")
    return {"head": head[0] if head else None, "status": status}


def check_git(repo: Path, recorded: dict, plugin_root: str | None) -> list[str]:
    """Informational comparison only; unrelated repository changes are not content drift."""
    notes = []
    state = git_state(repo)
    if state["head"] is None:
        return [f"git state unreadable: {repo}"]
    if recorded.get("head") and state["head"] != recorded["head"]:
        notes.append(f"HEAD differs: recorded {recorded['head']} actual {state['head']}")
    if recorded.get("status_porcelain") is not None and state["status"] is not None:
        old, new = set(recorded["status_porcelain"]), set(state["status"])
        for label, lines in (("added", sorted(new - old)), ("removed", sorted(old - new))):
            for line in lines:
                scope = "plugin" if plugin_root and plugin_root in line else "outside plugin"
                notes.append(f"status line {label} ({scope}): {line}")
    return notes


def run(inventory_path: Path, root: Path, strict_git: bool = False) -> tuple[int, list[str]]:
    data = load_inventory(inventory_path)
    lines: list[str] = []
    drift = False
    entries = data["files"]
    result = compare_files(root, entries)
    new, links, problems = [], [], []
    git_notes: list[str] = []
    if data["format"] == SOURCE_FORMAT:
        plugin_root = data["plugin_root"]
        exclusions = [e["pattern"] for e in data.get("excluded", [])]
        new, links, problems = find_new_files(root, plugin_root, {e["path"] for e in entries}, exclusions)
        if (root / ".git").exists() and not os.path.islink(root / ".git"):
            git_notes = check_git(root, data.get("repository", {}), plugin_root)
        else:
            git_notes = ["not a git checkout: git state not compared"]
    else:
        for name, recorded in data.get("repositories", {}).items():
            state, _ = inspect_path_dir(root, name)
            if state != "ok":
                problems.append(f"repository {name}: {state}; git state not compared")
                continue
            git_notes += [f"{name}: {n}" for n in check_git(root / name, recorded, None)]
    for title, items in (("changed", result["changed"]), ("missing", result["missing"]), ("unreadable", result["unreadable"]),
                         ("unsafe path", result["unsafe"]), ("new relevant file", new), ("new symlink", links),
                         ("unsafe plugin root", problems)):
        for item in items:
            lines.append(f"DRIFT {title}: {item}")
            drift = True
    for note in git_notes:
        lines.append(f"NOTE git: {note}")
        if strict_git and not note.startswith("not a git"):
            drift = True
    lines.append(
        f"SUMMARY files={len(entries)} changed={len(result['changed'])} missing={len(result['missing'])} "
        f"unreadable={len(result['unreadable'])} unsafe={len(result['unsafe'])} new={len(new)} new_symlinks={len(links)} "
        f"-> {'DRIFT' if drift else 'NO DRIFT'}"
    )
    return (1 if drift else 0), lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--inventory", required=True, type=Path, help="historical inventory JSON (read only)")
    parser.add_argument("--root", required=True, type=Path,
                        help="tree the inventory paths resolve against (source repo; for a reference baseline the common parent)")
    parser.add_argument("--strict-git", action="store_true", help="treat HEAD/status differences as drift")
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        print(f"STOP: root is not a directory: {args.root}", file=sys.stderr)
        return 2
    try:
        code, lines = run(args.inventory, args.root, args.strict_git)
    except InventoryError as exc:
        print(f"STOP: invalid inventory: {exc}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
