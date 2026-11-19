"""Facts taken from git."""
import re
import subprocess
from pathlib import Path

from errors import Stop

REMOTE_RE = re.compile(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?$")


def run(args: list, cwd: Path) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Stop(f"{' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def repo_root(cwd: Path) -> Path:
    return Path(run(["git", "rev-parse", "--show-toplevel"], cwd))


def owner_repo(root: Path) -> tuple:
    url = run(["git", "remote", "get-url", "origin"], root)
    match = REMOTE_RE.search(url)
    if not match:
        raise Stop(f"Cannot read owner/repo from remote '{url}'.")
    return match.group(1).lower(), match.group(2).lower()


def is_ignored(root: Path, rel_path: str) -> bool:
    return subprocess.run(["git", "check-ignore", "-q", rel_path], cwd=root).returncode == 0
