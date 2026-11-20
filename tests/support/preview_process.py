"""Base class and helpers for the process tests of the `preview` controller: real local processes on free 127.0.0.1 ports, a fake `npm`
on PATH, temporary projects and a private state dir per test. No real site, no network, no real npm.

Cleanup runs after failed assertions too and signals a process only when its current identity (PID, start time, process group or a
marker in its command line) still equals what the test recorded when the test itself started it."""
import io
import json
import os
import signal
import shutil
import socket
import stat
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from tests.support import preview_helpers as helpers
import control  # noqa: E402  (importable after preview_helpers set up sys.path)

FAKE_NPM = '''#!PYTHON
# fake `npm --prefix <path> run dev -- --port <n>`; behaviour from <prefix>/.fake ("ok" | "crash" | "hang" | "slow")
import os, subprocess, sys, time
a = sys.argv[1:]
prefix, port = a[a.index("--prefix") + 1], int(a[a.index("--port") + 1])
flag = os.path.join(prefix, ".fake")
mode = open(flag).read().strip() if os.path.exists(flag) else "ok"
if mode == "crash":
    print("fake dev server: boom", flush=True); sys.exit(3)
if mode == "hang":
    time.sleep(600)
if mode == "detach":     # like Astro in an agent environment: server in its own session, command exits 0
    child = subprocess.Popen([sys.executable, "-c", "import sys,os,http.server\\nopen(sys.argv[2],'w').write(str(os.getpid()))\\nhttp.server.HTTPServer(('127.0.0.1',int(sys.argv[1])),http.server.BaseHTTPRequestHandler).serve_forever()", str(port), os.path.abspath(os.path.join(prefix, ".pid"))], start_new_session=True)
    time.sleep(1.0); sys.exit(0)
SERVER = """
import sys, time, http.server
if sys.argv[2] == "slow": time.sleep(1.5)
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
    def log_message(self, *a): pass
http.server.HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
"""
subprocess.Popen([sys.executable, "-c", SERVER, str(port), mode]).wait()
'''


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def manifest(port):
    return {"version": 2, "components": [{**helpers._static("site.test", title="Site", port=port), "domain": "site.test"}]}


def run(root, verb, *argv):
    out = io.StringIO()
    with redirect_stdout(out):
        code = control.main([verb, "--root", str(root), *argv])
    text = out.getvalue()
    try:
        return code, json.loads(text)
    except ValueError:
        return code, text


class ControlBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        npm = self.bin / "npm"
        npm.write_text(FAKE_NPM.replace("PYTHON", sys.executable, 1))
        npm.chmod(npm.stat().st_mode | stat.S_IXUSR)
        self.tools = self.tmp / "tools"          # only ps and lsof (and nothing else) for tests that need to break them
        self.tools.mkdir()
        for name in ("ps", "lsof"):
            (self.tools / name).symlink_to(shutil.which(name))
        patch = mock.patch.dict(os.environ, {"PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
                                             "WEBSITE_MANAGER_STATE_DIR": str(self.tmp / "state")})
        patch.start()
        self.addCleanup(patch.stop)
        self.roots = []
        self.listeners = []
        self.spawned = []                         # (pid, start time) of every dev command this test started
        self.extra_pids = []                      # (pid, marker that must be in its command line)
        real_popen = control.subprocess.Popen

        def tracking_popen(argv, *a, **kw):
            proc = real_popen(argv, *a, **kw)
            if isinstance(argv, list) and argv and argv[0] == "npm":
                self.spawned.append(proc.pid)
            return proc
        popen_patch = mock.patch.object(control.subprocess, "Popen", tracking_popen)
        popen_patch.start()
        self.addCleanup(popen_patch.stop)
        self.start_times = {}
        self.addCleanup(self.cleanup)             # registered last = runs first, also after failed assertions
        self.port = free_port()

    def project(self, port=None, mode="ok"):
        root = helpers.make_repo(manifest(port or self.port), ("site.test",))
        (root / "sites" / "site.test" / "node_modules").mkdir()
        (root / "sites" / "site.test" / ".fake").write_text(mode)
        self.roots.append(root)
        return root

    def put_record(self, root, record):
        control.ensure_state_dir(root)
        control.write_record(control.record_file(root, "site.test"), record)

    def snapshot_starts(self):
        """Remember the start time of every dev command seen so far (identity proof for the cleanup)."""
        for pid in self.spawned:
            if pid not in self.start_times:
                info = control.proc_info(pid)
                if info:
                    self.start_times[pid] = info["start"]

    def cleanup(self):
        problems = []
        for s in self.listeners:
            s.close()
        self.snapshot_starts()
        # records written by this test (state dir is inside self.tmp): identity = pid + start time + process group
        for rf in (self.tmp / "state").glob("*/preview-*.json"):
            try:
                if not stat.S_ISREG(os.lstat(rf).st_mode):      # a FIFO/link planted by a test must never be opened here
                    continue
                rec = json.loads(rf.read_text())
                if not isinstance(rec.get("pid"), int):
                    continue
                info = control.proc_info(rec["pid"])
                if info and info["start"] == rec["process_start_time"] and info["pgid"] == rec["pgid"]:
                    control.stop_group(rec["pgid"])
                    self.start_times.pop(rec["pid"], None)
            except Exception as error:   # keep cleaning
                problems.append(f"record {rf.name}: {error!r}")
        for pid, start in list(self.start_times.items()):
            info = control.proc_info(pid)
            if info and info["start"] == start and info["pgid"] == pid:
                control.stop_group(pid)
        for pid, marker in self.extra_pids:
            info = control.proc_info(pid)
            if info and marker in info["command"]:
                os.kill(pid, signal.SIGTERM)
        time.sleep(0.3)
        for pid, start in self.start_times.items():
            info = control.proc_info(pid)
            if info and info["start"] == start and info["pgid"] == pid:
                problems.append(f"test process {pid} (started {start}) is still running")
        for pid, marker in self.extra_pids:
            info = control.proc_info(pid)
            if info and marker in info["command"]:
                problems.append(f"test process {pid} is still running")
        if problems:
            self.fail("test process cleanup failed: " + "; ".join(problems))

    def foreign_listener(self, port=None):
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", port or self.port))
        s.listen(5)
        self.listeners.append(s)
        return s


class AccessSpy:
    """Controlled access spy for protection tests. While active it records every attempt to open, unlink, remove, rename, replace
    or write a path whose real location lies inside one of the given (fictional, external) directories, and records every signal
    (`os.kill`, `os.killpg`) WITHOUT delivering it. Metadata-only calls (lstat/stat/listdir) are not content access and are not
    recorded. An unchanged hash alone would not show that a file was never read; this does."""

    def __init__(self, *external):
        self.roots = [os.path.realpath(p) for p in external]
        self.hits = []          # (operation, real path)
        self.signals = []       # (operation, args)

    def _inside(self, target):
        try:
            real = os.path.realpath(os.fspath(target))
        except (TypeError, ValueError):
            return None
        return real if any(real == r or real.startswith(r + os.sep) for r in self.roots) else None

    def __enter__(self):
        import builtins
        import io
        spy = self
        originals = {}

        def wrap(owner, name, record_paths=1):
            real = getattr(owner, name)
            originals[(owner, name)] = real

            def spied(*args, **kwargs):
                for target in args[:record_paths]:
                    hit = spy._inside(target) if not isinstance(target, int) else None
                    if hit:
                        spy.hits.append((name, hit))
                return real(*args, **kwargs)
            setattr(owner, name, spied)

        for name, count in (("open", 1), ("unlink", 1), ("remove", 1), ("rmdir", 1), ("replace", 2), ("rename", 2)):
            wrap(os, name, count)
        wrap(builtins, "open")
        wrap(io, "open")
        for name in ("kill", "killpg"):
            originals[(os, name)] = getattr(os, name)
            setattr(os, name, lambda *a, _n=name: spy.signals.append((_n, a)))
        self._originals = originals
        return self

    def __exit__(self, *exc):
        for (owner, name), real in self._originals.items():
            setattr(owner, name, real)
        return False
