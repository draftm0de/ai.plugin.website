#!/usr/bin/env python3
"""Website plugin, skill `preview`: runtime control: start | status | stop | inspect of the dev server of one site.

Terminal path (host independent): this script starts the dev server itself in its own
process group, writes an ownership record and only ever signals a process group that
the record and live OS evidence prove to be its own. Launch name and port are never proof.

Exit codes: 0 running-new | running-reused | not-running | stopped | page-confirmed, 1 every failure state,
2 a choice is needed (ambiguous site). Output: one JSON object on stdout.
"""
import argparse
import hashlib
import html
import json
import math
import os
import re
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from html.parser import HTMLParser
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "_shared" / "scripts"))   # shared package `site_common` (resolver, manifest validator, errors)

import preview  # noqa: E402
from site_common import sites  # noqa: E402
from site_common.errors import EXIT_ASK, EXIT_OK, EXIT_STOP, Ask, Stop  # noqa: E402

READY_TIMEOUT = 60.0     # default seconds until the server must answer
MAX_TIMEOUT = 600.0      # finite upper bound for --timeout (seconds); larger, non-finite and non-positive values are rejected
POLL_INTERVAL = 0.5
REQUEST_TIMEOUT = 2.0    # per readiness request
STOP_GRACE = 10.0        # seconds after SIGTERM before SIGKILL of our own group
LOG_TAIL = 15
DEV_EXTRA_ARGS = ["--ignore-lock"]
MAX_PAGE_BYTES = 2_000_000
FAILURES = {"page-not-reachable", "page-other-site", "page-stale", "page-identity-unknown", "page-identity-only",
            "port-conflict", "failed-early-exit", "timeout", "unknown-owner", "starting", "needs-install", "failed",
            "insufficient-evidence", "unsafe-state", "failed-after-start"}


class EvidenceError(Exception):
    """An operating-system fact cannot be established. kind: missing | denied | failed | not-attributed."""

    def __init__(self, tool, kind, detail):
        super().__init__(f"{tool}: {kind}: {detail}")
        self.tool, self.kind, self.detail = tool, kind, detail


class UnsafeState(Exception):
    """A state path is a symlink, a foreign file or otherwise not ours; nothing was followed, written or removed."""


def parse_timeout(value) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise Stop(f"--timeout must be a number of seconds, got {value!r}.")
    if not math.isfinite(number) or number <= 0 or number > MAX_TIMEOUT:
        raise Stop(f"--timeout must be a finite number of seconds greater than 0 and at most {MAX_TIMEOUT:g}, got {value!r}.")
    return number


# ---------------------------------------------------------------- state files
# Directory 0700 owned by us; files created exclusively (O_EXCL|O_NOFOLLOW), 0600; an existing path that is a
# symlink, not a regular file or not owned by us is never read, written, followed, replaced or removed.

def state_dir() -> Path:
    override = os.environ.get("ZYRIS_WEBSITE_STATE_DIR")
    return Path(override) if override else Path(tempfile.gettempdir()) / "zyris-website"


def project_hash(root: Path) -> str:
    return hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:12]


def _is_mine(st) -> bool:
    return st.st_uid == os.geteuid()


def ensure_state_dir(root: Path) -> Path:
    base = state_dir()
    try:
        base.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise UnsafeState(f"cannot prepare {base.parent}: {error}")
    path = base / project_hash(root)
    for d in (base, path):
        try:
            os.mkdir(d, 0o700)
        except FileExistsError:
            pass
        except OSError as error:
            raise UnsafeState(f"cannot create state directory {d}: {error}")
        st = os.lstat(d)
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode) or not _is_mine(st) or st.st_mode & 0o022:
            raise UnsafeState(f"state directory {d} is a symlink, not a directory, not owned by this user or writable by others; left untouched")
    return path


def _check_name(site: str) -> None:
    if not site or Path(site).name != site or site in (".", ".."):
        raise UnsafeState(f"site name {site!r} is not usable as a file name")


def record_file(root: Path, site: str) -> Path:
    _check_name(site)
    return state_dir() / project_hash(root) / f"preview-{site}.json"


def _lstat(path: Path):
    try:
        return os.lstat(path)
    except FileNotFoundError:
        return None


def check_state_area(path: Path) -> None:
    """Read-only check (lstat only, creates nothing) of the state area a state file lives in, before ANY access to the file:
    the base directory (`<TMPDIR>/zyris-website` or the override) and the project directory below it must each be absent
    (a normal case: nothing is known yet) or a real directory (no symlink) owned by us and not writable by group/others.
    The base is checked first, because a link there would make the lstat of the project directory follow it. Ancestors of the
    base (the system temp folder, which may legitimately sit behind a system link such as /var -> /private/var) are not examined.
    Raises UnsafeState; an unsafe area is never evidence of ownership."""
    project = path.parent
    for directory in (project.parent, project):
        st = _lstat(directory)
        if st is None:
            return
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode) or not _is_mine(st) or st.st_mode & 0o022:
            raise UnsafeState(f"state directory {directory} is a symlink, not a directory, not owned by this user or writable by others; "
                              "nothing in it was read, changed, removed or used as evidence")


def check_target(path: Path) -> None:
    """The target of a record write must be absent or a regular file of ours, in a safe state area."""
    check_state_area(path)
    st = _lstat(path)
    if st is not None and (not stat.S_ISREG(st.st_mode) or not _is_mine(st)):
        raise UnsafeState(f"{path} exists and is a symlink, a non-regular file or not ours; left untouched")


def read_record(path: Path):
    check_state_area(path)
    st = _lstat(path)
    if st is None:
        return None
    if not stat.S_ISREG(st.st_mode) or not _is_mine(st):
        raise UnsafeState(f"{path} exists and is a symlink, a non-regular file or not ours; not read, not followed")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as error:
        raise UnsafeState(f"{path} cannot be opened safely: {error}")
    with os.fdopen(fd, "r", encoding="utf-8", errors="replace") as handle:
        try:
            data = json.loads(handle.read(1_000_000))
        except ValueError:
            return None
    return data if isinstance(data, dict) else None


def _unlink_if_same(path: Path, fd_stat) -> None:
    try:
        check_state_area(path)
    except UnsafeState:
        return
    st = _lstat(path)
    if st is not None and stat.S_ISREG(st.st_mode) and (st.st_dev, st.st_ino) == (fd_stat.st_dev, fd_stat.st_ino):
        try:
            os.unlink(path)
        except OSError:
            pass


def write_record(path: Path, record: dict) -> None:
    """Exclusive staging file in the same directory, then atomic rename. Only the staging file we created is cleaned up."""
    check_target(path)
    staging = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    fd = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    mine = os.fstat(fd)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(record, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        check_target(path)
        os.replace(staging, path)
    except BaseException:
        _unlink_if_same(staging, mine)
        raise


def remove_own(path: Path) -> bool:
    """Unlink a regular file of ours; never a symlink, a foreign file or anything in an unsafe state area."""
    try:
        check_state_area(path)
    except UnsafeState:
        return False
    st = _lstat(path)
    if st is None or not stat.S_ISREG(st.st_mode) or not _is_mine(st):
        return False
    try:
        os.unlink(path)
    except OSError:
        return False
    return True


def open_log(directory: Path, site: str, start_id: str):
    """New exclusive log file for this start; returns (path, fd)."""
    path = directory / f"preview-{site}-{start_id}.log"
    return path, os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)


def own_log_path(root: Path, record):
    """The recorded log path, only if it is a plain file of ours inside this project's state directory."""
    log = record.get("log") if record else None
    if not isinstance(log, str):
        return None
    path = Path(log)
    if path.parent != state_dir() / project_hash(root) or not path.name.startswith("preview-") or not path.name.endswith(".log"):
        return None
    try:
        check_state_area(path)
    except UnsafeState:
        return None
    st = _lstat(path)
    return path if st is not None and stat.S_ISREG(st.st_mode) and _is_mine(st) else None


def log_tail(path) -> list:
    if path is None:
        return []
    try:
        check_state_area(Path(path))
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read(200_000).splitlines()[-LOG_TAIL:]
    except (OSError, UnsafeState):
        return []


# ------------------------------------------------------------------ OS probes

def _run_tool(argv):
    """Run ps/lsof. Distinguishes missing, denied and failing tools; rc 0 and 1 are normal answers."""
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=10, env={**os.environ, "LC_ALL": "C"})
    except FileNotFoundError as error:
        raise EvidenceError(argv[0], "missing", str(error))
    except PermissionError as error:
        raise EvidenceError(argv[0], "denied", str(error))
    except subprocess.TimeoutExpired:
        raise EvidenceError(argv[0], "failed", "timed out after 10 s")
    except OSError as error:
        raise EvidenceError(argv[0], "failed", str(error))
    denied = re.search(r"permission|not permitted|denied", done.stderr, re.I)
    if done.returncode not in (0, 1):
        raise EvidenceError(argv[0], "denied" if denied else "failed", f"exit {done.returncode}: {done.stderr.strip()[:200]}")
    if done.returncode == 1 and not done.stdout.strip() and denied:
        raise EvidenceError(argv[0], "denied", done.stderr.strip()[:200])
    return done


def _ps(field: str, pid: int):
    out = _run_tool(["ps", "-o", f"{field}=", "-p", str(pid)]).stdout.strip()
    return out or None


def proc_info(pid):
    """Identity of a live process: start time, process group, command line. None if gone or zombie."""
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return None
    stat_ = _ps("stat", pid)
    if stat_ is None or stat_.startswith("Z"):
        return None
    start, pgid, command = _ps("lstart", pid), _ps("pgid", pid), _ps("command", pid)
    if not (start and pgid and command):
        return None
    try:
        return {"pid": pid, "start": start, "pgid": int(pgid), "command": command}
    except ValueError:
        raise EvidenceError("ps", "failed", f"unparsable process group {pgid!r}")


def port_listeners(port: int):
    """PIDs listening on the TCP port (empty list: none). Raises EvidenceError when lsof cannot answer."""
    out = _run_tool(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"]).stdout
    return sorted({int(x) for x in out.split() if x.isdigit()})


def probe_os_evidence() -> None:
    """Before a start/status/stop: ps must see this very process and lsof must see a listening socket of this process."""
    me = proc_info(os.getpid())
    if me is None:
        raise EvidenceError("ps", "failed", "cannot see its own process")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        probe.listen(1)
        if os.getpid() not in port_listeners(probe.getsockname()[1]):
            raise EvidenceError("lsof", "failed", "cannot see a listening socket of its own process (blocked or restricted?)")


def port_bound(port: int) -> bool:
    for family, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            with socket.socket(family, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                if s.connect_ex((host, port)) == 0:
                    return True
        except OSError:
            continue
    return False


def http_ready(port: int, path: str = "/") -> bool:
    """True for HTTP 2xx/3xx (urllib follows redirects, so the final status counts)."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=REQUEST_TIMEOUT) as r:
            return 200 <= r.status < 400
    except (urllib.error.URLError, OSError, ValueError):
        return False


def describe_foreign(port: int) -> list:
    out = []
    try:
        pids = port_listeners(port)
    except EvidenceError:
        return out
    for pid in pids:
        try:
            info = proc_info(pid)
        except EvidenceError:
            info = None
        out.append({"pid": pid, "command": info["command"] if info else None, "start": info["start"] if info else None})
    return out


# ------------------------------------------------------------------ ownership

def verify(root: Path, component: dict, record) -> dict:
    """Decide whether the recorded instance is ours. Returns {verdict, matched_on, reason, attributed}.

    verdicts: none (no usable record) | stale (record, process gone or replaced) |
              foreign (record of another project/site/dir/port, or port held by another process) |
              ours (process evidence agrees). `attributed` is True only when every listener of the port was
              seen and belongs to the recorded process group; an HTTP answer without it proves nothing.
    Raises EvidenceError when ps/lsof cannot answer.
    """
    if record is None:
        return {"verdict": "none", "matched_on": [], "reason": "no ownership record", "attributed": False}
    site_dir = str((root / component["path"]).resolve())
    for key, want in (("project_root", str(root.resolve())), ("site", component["name"]), ("working_dir", site_dir)):
        if record.get(key) != want:
            return {"verdict": "foreign", "matched_on": [], "reason": f"record {key} is {record.get(key)!r}, expected {want!r}", "attributed": False}
    matched = ["project_root", "site", "working_dir"]
    info = proc_info(record.get("pid"))
    if info is None:
        return {"verdict": "stale", "matched_on": matched, "reason": "recorded process is gone", "attributed": False}
    # The command line is NOT compared: it changes while the child execs (observed: wrapper, then the real command).
    # Identity is PID + process start time + process group (the group id is the PID of our session leader).
    if info["start"] != record.get("process_start_time") or info["pgid"] != record.get("pgid"):
        return {"verdict": "stale", "matched_on": matched, "reason": "PID now belongs to a different process (start time or process group differ)", "attributed": False}
    matched += ["pid", "process_start_time", "pgid"]
    if record.get("port") != component["port"]:
        return {"verdict": "foreign", "matched_on": matched, "reason": f"record port {record.get('port')} differs from manifest port {component['port']}", "attributed": False}
    listeners = port_listeners(record["port"])
    if listeners:
        other = [p for p in listeners if (proc_info(p) or {}).get("pgid") != record["pgid"]]
        if other:
            return {"verdict": "foreign", "matched_on": matched, "attributed": False,
                    "reason": f"port {record['port']} is held by process(es) {other} outside the recorded process group"}
        matched.append("port_listener_in_group")
    return {"verdict": "ours", "matched_on": matched, "reason": "all evidence agrees", "attributed": bool(listeners)}


def kill_group(pgid: int, sig) -> None:
    try:
        os.killpg(pgid, sig)
    except ProcessLookupError:
        pass


def group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass       # macOS answers EPERM for a group that holds only zombies: decide by the process table
    # a group that only holds zombies counts as gone
    out = _run_tool(["ps", "-A", "-o", "pgid=,stat="]).stdout.split("\n")
    return any(l.split()[:1] == [str(pgid)] and not l.split()[1].startswith("Z") for l in out if len(l.split()) >= 2)


def stop_group(pgid: int) -> str:
    kill_group(pgid, signal.SIGTERM)
    deadline = time.monotonic() + STOP_GRACE
    while time.monotonic() < deadline:
        if not group_alive(pgid):
            return "terminated"
        time.sleep(0.2)
    kill_group(pgid, signal.SIGKILL)
    time.sleep(0.5)
    return "killed" if not group_alive(pgid) else "survived"


def _group_state(pgid: int):
    """True: group has no members; False: members exist; None: cannot tell (EPERM, e.g. a group of zombies on macOS)."""
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return None
    return False


def terminate_own(popen) -> dict:
    """End the process group this call created (start_new_session: group id == popen.pid), using only our own
    Popen handle: no ps/lsof, no recorded or guessed IDs. While the leader is unreaped its PID cannot be recycled;
    after it was reaped the group id is signalled only while the group still has members (they descend from our
    leader). Result: {result: stopped|incomplete, how, detail}."""
    pgid = popen.pid
    detail = []

    def settle(timeout):
        end = time.monotonic() + timeout
        while True:
            leader_gone = popen.poll() is not None
            group = _group_state(pgid)
            if leader_gone and group is True:
                return True
            if time.monotonic() >= end:
                return False
            time.sleep(0.1)

    try:
        for sig, wait, name in ((signal.SIGTERM, STOP_GRACE, "SIGTERM"), (signal.SIGKILL, 3.0, "SIGKILL")):
            if popen.poll() is not None and _group_state(pgid) is True:
                break
            try:
                os.killpg(pgid, sig)
            except ProcessLookupError:
                pass
            except OSError as error:
                detail.append(f"{name} to group {pgid} failed: {error}")
                continue
            if settle(wait):
                return {"result": "stopped", "how": "terminated" if sig == signal.SIGTERM else "killed", "detail": detail}
            detail.append(f"group {pgid} still has members after {name}")
        if popen.poll() is not None and _group_state(pgid) is True:
            return {"result": "stopped", "how": "already-exited", "detail": detail}
        if popen.poll() is not None and _group_state(pgid) is None:     # EPERM after the leader is reaped: ask the process table
            try:
                if not group_alive(pgid):
                    return {"result": "stopped", "how": "only-zombies-left", "detail": detail}
            except EvidenceError as error:
                detail.append(f"cannot confirm with ps: {error}")
    except Exception as error:      # cleanup must never raise
        detail.append(f"cleanup error: {error!r}")
    return {"result": "incomplete", "how": None, "detail": detail or ["group could not be confirmed gone"]}


def _remove_record_if_mine(rfile, start_id):
    try:
        rec = read_record(rfile)
    except UnsafeState:
        return False
    return bool(rec and rec.get("start_id") == start_id and remove_own(rfile))


# ---------------------------------------------------------------- the verbs

def _base(component, root, state, **extra):
    out = {"state": state, "started": False, "site": component["name"], "port": component["port"],
           "project_root": str(root.resolve()), "working_dir": str((root / component["path"]).resolve())}
    out.update(extra)
    return out


def _evidence(rec, check):
    return {"start_id": rec.get("start_id"), "pid": rec.get("pid"), "process_start_time": rec.get("process_start_time"),
            "matched_on": check["matched_on"], "log": rec.get("log")}


def _drop_record(root, rfile, record):
    """Remove a stale record and the recorded log, each only if it is a plain file of ours."""
    log = own_log_path(root, record)
    if log is not None:
        remove_own(log)
    remove_own(rfile)


def _wait_ready(component, root, rec, popen, timeout, path_log):
    """Poll until the recorded instance answers AND the listener is attributed to its process group."""
    deadline = time.monotonic() + timeout
    answered = False
    while True:
        if popen is not None and popen.poll() is not None:
            extra = {"exit_code": popen.returncode, "log_tail": log_tail(path_log)}
            if popen.returncode == 0 and port_bound(component["port"]):
                extra.update(message="the dev command exited 0 but a server answers on the port outside our process group "
                                     "(the dev server detached itself). It is NOT adopted and NOT stopped; stop it with the tool that started it.",
                             foreign=describe_foreign(component["port"]))
            return "failed-early-exit", extra
        info = proc_info(rec["pid"])
        if info is None or info["start"] != rec["process_start_time"]:
            return "failed-early-exit", {"log_tail": log_tail(path_log)}
        if http_ready(component["port"], "/"):
            check = verify(root, component, rec)
            if check["verdict"] == "foreign":
                return "port-conflict", {"reason": check["reason"], "foreign": describe_foreign(component["port"])}
            if check["verdict"] == "ours" and check["attributed"]:
                return "ready", {"check": check}
            answered = True      # something answers, but no listener is attributed to our group (yet)
        if time.monotonic() >= deadline:
            if answered:
                return "insufficient-evidence", {"kind": "not-attributed", "tool": "lsof",
                                                 "message": "an HTTP server answers on the port but no listening socket of our process group was seen; readiness is not reported"}
            return "timeout", {"log_tail": log_tail(path_log)}
        time.sleep(POLL_INTERVAL)


def cmd_start(root, component, args):
    site_dir = root / component["path"]
    if not (site_dir / "node_modules").is_dir():
        return _base(component, root, "needs-install", message=f"Run 'npm install' in {component['path']} first.")
    probe_os_evidence()                                   # before any write or start
    directory = ensure_state_dir(root)
    rfile = record_file(root, component["name"])
    check_target(rfile)
    entry = preview.launch_entry(component)
    preview.write_launch(root, component)
    record = read_record(rfile)
    check = verify(root, component, record)
    url = f"http://localhost:{component['port']}{args.page if args.page.startswith('/') else '/' + args.page}"
    if check["verdict"] == "ours":
        state, extra = _wait_ready(component, root, record, None, args.timeout, own_log_path(root, record))
        if state == "ready":
            return _base(component, root, "running-reused", url=url, **_evidence(record, check))
        return _base(component, root, state, url=url, **extra, **_evidence(record, check))
    if check["verdict"] == "stale":
        _drop_record(root, rfile, record)
    if port_bound(component["port"]):
        return _base(component, root, "port-conflict", url=url,
                     message=f"port {component['port']} is in use by a process this skill did not start; nothing was signalled or adopted. "
                             "It is not stopped, taken over or moved: check the page that answers there with 'inspect --expect <current text>' and open that URL; "
                             "do not start a second server (no host preview_start) and do not change the port.",
                     next_step="inspect",
                     reason=check["reason"] if check["verdict"] in ("foreign", "stale") else "no ownership record",
                     foreign=describe_foreign(component["port"]))
    # Astro (>= 7) detaches the dev server into its own session when it detects an AI-agent environment
    # (observed 2026-11-17: the foreground command exits 0, the server lives on outside our process group).
    # `--ignore-lock` is Astro's documented opt-out: one foreground server, so its process group stays ours.
    command = [entry["runtimeExecutable"], *entry["runtimeArgs"], *DEV_EXTRA_ARGS]
    start_id = str(uuid.uuid4())
    lfile, log_fd = open_log(directory, component["name"], start_id)
    try:
        try:
            popen = subprocess.Popen(command, cwd=root, stdin=subprocess.DEVNULL, stdout=log_fd, stderr=subprocess.STDOUT,
                                     start_new_session=True)
        except OSError as error:
            remove_own(lfile)
            return _base(component, root, "failed", message=f"nothing was started: cannot run {command[0]}: {error}")
    finally:
        os.close(log_fd)
    # ---- from here on a process exists. Every exit path below ends in _after_start(), which ends it again or says it could not.
    ctx = {"start_id": start_id, "record_written": False, "step": "identify the started process", "info": None}
    try:
        info = None
        for _ in range(20):
            info = proc_info(popen.pid)
            if info or popen.poll() is not None:
                break
            time.sleep(0.05)
        ctx["info"] = info
        if info is None:
            if popen.poll() is not None:
                return _after_start(component, root, popen, lfile, rfile, ctx, "failed-early-exit", url,
                                    {"exit_code": popen.returncode, "log_tail": log_tail(lfile)})
            raise EvidenceError("ps", "failed", f"the started process {popen.pid} is alive but could not be identified")
        rec = {"start_id": start_id, "project_root": str(root.resolve()), "site": component["name"],
               "working_dir": str(site_dir.resolve()), "launch_name": entry["name"], "port": component["port"],
               "host_server_id": None, "pid": popen.pid, "pgid": info["pgid"], "process_start_time": info["start"],
               "command_line_at_start": info["command"], "started_at": datetime.now(timezone.utc).isoformat(),
               "surface": "terminal", "log": str(lfile)}
        ctx["step"] = "write the ownership record"
        write_record(rfile, rec)
        ctx["record_written"] = True
        ctx["step"] = "wait for readiness"
        state, extra = _wait_ready(component, root, rec, popen, args.timeout, lfile)
        if state == "ready":
            ctx["step"] = "final verification"
            final = verify(root, component, rec)
            if final["verdict"] != "ours" or not final["attributed"]:
                raise EvidenceError("lsof", "failed", f"final verification did not confirm the instance: {final['reason']}")
            return _base(component, root, "running-new", started=True, url=url, **_evidence(rec, final))
        if state == "timeout":
            ctx["step"] = "final verification"
            return _base(component, root, "timeout", started=True, url=url, left_running=True, waited_seconds=args.timeout, **extra,
                         **_evidence(rec, verify(root, component, rec)))
        return _after_start(component, root, popen, lfile, rfile, ctx, state, url, extra)
    except BaseException as error:
        out = _after_start(component, root, popen, lfile, rfile, ctx, "failed-after-start", url, {"cause": _describe(error)})
        if not isinstance(error, Exception):
            raise
        return out


def _describe(error) -> dict:
    if isinstance(error, EvidenceError):
        return {"type": "EvidenceError", "tool": error.tool, "kind": error.kind, "detail": error.detail}
    return {"type": type(error).__name__, "detail": str(error)}


def _after_start(component, root, popen, lfile, rfile, ctx, state, url, extra):
    """End the instance this call started and report truthfully what is left. A process WAS started."""
    cleanup = terminate_own(popen)
    info = ctx.get("info") or {}
    cause = extra.get("cause")
    because = f" Cause: {cause.get('type')}: {cause.get('detail')}." if cause else ""
    facts = {"started": True, "pid": popen.pid, "pgid": popen.pid, "process_start_time": info.get("start"),
             "start_id": ctx["start_id"], "failed_step": ctx["step"], "cleanup": cleanup}
    if cleanup["result"] == "stopped":
        tail = log_tail(lfile)
        if ctx["record_written"]:
            _remove_record_if_mine(rfile, ctx["start_id"])
        remove_own(lfile)
        extra = {**extra, "log_tail": extra.get("log_tail") or tail}
        message = (f"A dev server process (pid {popen.pid}, group {popen.pid}) WAS started by this call; step '{ctx['step']}' "
                   f"did not complete.{because} The instance was ended again ({cleanup['how']}); no process of this start remains.")
        if state != "failed-after-start":
            return _base(component, root, state, **{"url": url, **extra, **facts})
        return _base(component, root, "failed-after-start", **{"url": url, **extra, **facts, "message": message})
    # cleanup incomplete: keep every start fact (record if it exists, log) and say the state is open
    kept = {"record": str(rfile) if ctx["record_written"] else None, "log": str(lfile)}
    message = (f"A dev server process (pid {popen.pid}, group {popen.pid}, started at {info.get('start') or 'unknown'}) WAS started by this call; "
               f"step '{ctx['step']}' did not complete.{because} The cleanup is INCOMPLETE ({'; '.join(cleanup['detail'])}). "
               "The process group may still be running. Record (if written) and log were kept. Verify the process "
               "yourself before stopping it; this skill did not take it over.")
    return _base(component, root, "failed-after-start", **{"url": url, **extra, **facts, "message": message, "cause_state": state, "kept": kept})


def cmd_status(root, component, args):
    probe_os_evidence()
    rfile = record_file(root, component["name"])
    record = read_record(rfile)
    check = verify(root, component, record)
    url = f"http://localhost:{component['port']}/"
    if check["verdict"] == "ours":
        if http_ready(component["port"], "/"):
            if check["attributed"]:
                return _base(component, root, "running-reused", url=url, **_evidence(record, check))
            return _base(component, root, "insufficient-evidence", kind="not-attributed", tool="lsof", url=url,
                         message="an HTTP server answers on the port but no listening socket of our process group was seen; not reported as running",
                         **_evidence(record, check))
        return _base(component, root, "starting", url=url, message="process is ours and alive but does not answer yet", **_evidence(record, check))
    if check["verdict"] == "foreign":
        return _base(component, root, "unknown-owner", reason=check["reason"],
                     message="evidence does not prove this instance is ours; nothing was done", foreign=describe_foreign(component["port"]))
    extra = {}
    if port_bound(component["port"]):
        extra = {"foreign_candidate": describe_foreign(component["port"]),
                 "message": f"port {component['port']} is in use, but not by an instance this skill started for this project"}
    return _base(component, root, "not-running", reason=check["reason"], stale_record=check["verdict"] == "stale", **extra)


def cmd_stop(root, component, args):
    probe_os_evidence()
    rfile = record_file(root, component["name"])
    record = read_record(rfile)
    check = verify(root, component, record)
    if check["verdict"] == "foreign":
        return _base(component, root, "unknown-owner", reason=check["reason"],
                     message="refused: the evidence does not prove this instance is ours; no signal was sent. Stop it yourself.",
                     foreign=describe_foreign(component["port"]))
    if check["verdict"] != "ours":
        if check["verdict"] == "stale":
            _drop_record(root, rfile, record)
        extra = {"foreign_candidate": describe_foreign(component["port"])} if port_bound(component["port"]) else {}
        return _base(component, root, "not-running", reason=check["reason"], stale_record=check["verdict"] == "stale",
                     message="nothing of ours to stop; no signal was sent", **extra)
    recheck = verify(root, component, record)             # immediately before the signal
    if recheck["verdict"] != "ours":
        return _base(component, root, "unknown-owner", reason=recheck["reason"], message="evidence changed; no signal was sent")
    how = stop_group(record["pgid"])
    gone = not group_alive(record["pgid"]) and not port_bound(component["port"])
    if not gone:
        return _base(component, root, "failed", message=f"stop ended with '{how}' but the instance or its port is still alive", **_evidence(record, check))
    _drop_record(root, rfile, record)
    return _base(component, root, "stopped", how=how, **_evidence(record, check))


# ------------------------------------------------------------------ inspect (the visible page, separate from the process)

def site_identity(site_dir: Path):
    """(SITE url, SITE_NAME) read from src/lib/site.ts; None for a value that cannot be read."""
    try:
        text = (site_dir / "src" / "lib" / "site.ts").read_text(encoding="utf-8")
    except OSError:
        return None, None

    def const(name):
        m = re.search(rf"export const {name}\b[^=]*=\s*(\"(?:[^\"\\]|\\.)*\"|'[^']*')", text)
        if not m:
            return None
        raw = m.group(1)
        try:
            return json.loads(raw) if raw[0] == '"' else raw[1:-1]
        except ValueError:
            return None
    return const("SITE"), const("SITE_NAME")


def fetch_page(port: int, page: str):
    """(status, html) of the page on 127.0.0.1, bypassing caches; (None, reason) when unreachable."""
    req = urllib.request.Request(f"http://127.0.0.1:{port}{page}", headers={"Cache-Control": "no-cache", "Pragma": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT * 2) as r:
            return r.status, r.read(MAX_PAGE_BYTES).decode("utf-8", "replace")
    except (urllib.error.URLError, OSError, ValueError) as error:
        return None, str(error)


def _meta(doc: str, pattern: str):
    m = re.search(pattern, doc, re.I)
    return html.unescape(m.group(1)) if m else None


def same_site_url(canonical: str, site_url: str) -> bool:
    """Structured comparison: same scheme, host and port (no userinfo), and a path at or below the site's path
    on a segment boundary. 'https://site.test.other.example/' is NOT 'https://site.test'."""
    try:
        a, b = urllib.parse.urlsplit(canonical.strip()), urllib.parse.urlsplit(site_url.strip())
        if a.scheme.lower() not in ("http", "https") or a.scheme.lower() != b.scheme.lower():
            return False
        if a.username or a.password or b.username or b.password or not a.hostname or not b.hostname:
            return False
        default = {"http": 80, "https": 443}[a.scheme.lower()]
        if a.hostname.lower() != b.hostname.lower() or (a.port or default) != (b.port or default):
            return False
    except ValueError:
        return False
    base = b.path.rstrip("/")
    return base == "" or a.path == base or a.path.startswith(base + "/")


_SKIP = {"head", "script", "style", "template", "noscript"}
_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
_INLINE = {"a", "abbr", "b", "bdi", "bdo", "cite", "code", "data", "dfn", "em", "i", "kbd", "mark", "q", "s", "samp",
           "small", "span", "strong", "sub", "sup", "time", "u", "var"}


class _VisibleText(HTMLParser):
    """Text in the body markup only: no script, style, template, noscript, head/metadata, comments or elements with the
    `hidden` attribute. A static parse cannot know CSS visibility; the browser check stays necessary."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.skip = [], []

    def handle_starttag(self, tag, attrs):
        if tag in _VOID:
            if not self.skip and tag == "br":
                self.parts.append(" ")
            return
        hidden = any(k == "hidden" for k, _ in attrs)
        if self.skip or tag in _SKIP or hidden:
            self.skip.append(tag)
        elif tag not in _INLINE:
            self.parts.append(" ")

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if self.skip:
            if tag in self.skip:
                while self.skip and self.skip.pop() != tag:
                    pass
        elif tag not in _INLINE:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def visible_text(doc: str) -> str:
    parser = _VisibleText()
    parser.feed(doc)
    parser.close()
    return " ".join("".join(parser.parts).split())


def cmd_inspect(root, component, args):
    """Does the page that answers on the manifest port belong to THIS site and show the current content?

    Independent of who runs the server: no process is started, signalled or adopted, and the manifest port is
    never changed. The process verdict (ours / not ours) is reported next to it as a separate fact.
    """
    page = args.page if args.page.startswith("/") else "/" + args.page
    url = f"http://localhost:{component['port']}{page}"
    try:
        probe_os_evidence()
        record = read_record(record_file(root, component["name"]))
        process = "ours" if verify(root, component, record)["verdict"] == "ours" else "not-managed-by-this-skill"
    except (EvidenceError, UnsafeState):
        process = "unknown"
    base = {"url": url, "process": process, "expected_checked": list(args.expect or [])}
    status, doc = fetch_page(component["port"], page)
    if status is None or not (200 <= status < 400):
        return _base(component, root, "page-not-reachable", message="no page answers on the site's port", detail=str(doc)[:200], **base)
    site_url, site_name = site_identity(root / component["path"])
    canonical = _meta(doc, r'<link[^>]+rel="canonical"[^>]+href="([^"]*)"')
    served_name = _meta(doc, r'<meta[^>]+property="og:site_name"[^>]+content="([^"]*)"')
    if not site_url or not site_name or not canonical or served_name is None:
        return _base(component, root, "page-identity-unknown",
                     message="the identity of the page or of the site could not be read; the page is not used as evidence", **base)
    if not same_site_url(canonical, site_url) or served_name != site_name:
        return _base(component, root, "page-other-site",
                     message="the page on this port belongs to a different site; it is not used as evidence",
                     served_site=served_name, served_canonical=canonical, **base)
    expected = list(args.expect or [])
    if not expected or any(not e.strip() for e in expected):
        return _base(component, root, "page-identity-only",
                     message="the page belongs to this site, but no (or an empty) expected content was given, so the current editing state is not confirmed", **base)
    seen = visible_text(doc)
    missing = [e for e in expected if " ".join(e.split()) not in seen]
    if missing:
        return _base(component, root, "page-stale",
                     message="the page belongs to this site but does not show the current content in its text; it is not used as evidence",
                     missing_count=len(missing), **base)
    return _base(component, root, "page-confirmed", message="the page text of this site contains the expected current content; this is a pre-check, display and visibility still need the browser", visibility_checked=False, **base)


VERBS = {"start": cmd_start, "status": cmd_status, "stop": cmd_stop, "inspect": cmd_inspect}


def run(args) -> dict:
    args.timeout = parse_timeout(args.timeout)            # before anything is read, started or written
    root = Path(args.root).resolve() if args.root else Path.cwd().resolve()
    components = sites.load(root)
    result = sites.resolve(components, root, args.site, args.cwd, args.last)
    if args.verb not in ("start", "inspect") and result["confirm"]:
        raise Ask(f"'{result['component']['name']}' was used last in this conversation. Is that the site to {args.verb}?",
                  [{"name": result["component"]["name"]}])
    component = result["component"]
    if not (root / component["path"]).is_dir():
        raise Stop(f"Site folder missing: {root / component['path']}")
    try:
        out = VERBS[args.verb](root, component, args)
    except EvidenceError as error:
        out = _base(component, root, "insufficient-evidence", tool=error.tool, kind=error.kind,
                    message=f"{error.tool} is {error.kind}: {error.detail}. Without it ownership and readiness cannot be proven; nothing was started, "
                            "adopted or signalled by this check.")
    except UnsafeState as error:
        out = _base(component, root, "unsafe-state", message=str(error))
    out["selection"] = {"reason": result["reason"], "confirm": result["confirm"]}
    return out


def parse(argv):
    p = argparse.ArgumentParser(prog="control.py")
    p.add_argument("verb", choices=sorted(VERBS))
    p.add_argument("site", nargs="?", help="domain, folder, title or alias")
    p.add_argument("--page", default="/")
    p.add_argument("--expect", action="append", default=[], help="inspect: text the current page must show (repeatable)")
    p.add_argument("--cwd")
    p.add_argument("--last")
    p.add_argument("--root")
    p.add_argument("--timeout", default=str(READY_TIMEOUT),
                   help=f"seconds to wait for readiness (start): finite, > 0, at most {MAX_TIMEOUT:g}; default {READY_TIMEOUT:g}")
    return p.parse_args(argv)


def main(argv=None) -> int:
    try:
        out = run(parse(argv))
        print(sites.as_json(out))
        return EXIT_STOP if out["state"] in FAILURES else EXIT_OK
    except Ask as q:
        print(sites.as_json({"ask": str(q), "options": q.options}))
        return EXIT_ASK
    except Stop as s:
        print(f"STOP: {s}")
        return EXIT_STOP


if __name__ == "__main__":
    sys.exit(main())
