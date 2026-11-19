"""Access spy for the `edit` tests: runs `edit.py` as `__main__` under a Python audit hook that records every file the process
opens (path as given and its real path) and every directory it lists. Used to show that no file behind a symbolic link
is read: an unchanged external file hash cannot show that.

Usage: python3 -I -B edit_spy.py <log file> <edit.py> <edit arguments...>
The child processes of edit.py (the shared resolver, git, npm) are not covered by the hook."""
import json
import os
import runpy
import sys

LOG, SCRIPT, ARGS = sys.argv[1], sys.argv[2], sys.argv[3:]
records = []


def hook(event, args):
    if event in ("open", "os.listdir", "os.scandir") and args and isinstance(args[0], (str, bytes, os.PathLike)):
        raw = os.fsdecode(args[0])
        records.append({"event": event, "path": raw, "real": os.path.realpath(raw)})


sys.addaudithook(hook)
sys.argv = [SCRIPT, *ARGS]
code = 0
try:
    runpy.run_path(SCRIPT, run_name="__main__")
except SystemExit as exit_:
    code = exit_.code if isinstance(exit_.code, int) else (0 if exit_.code is None else 1)
finally:
    with open(LOG, "w", encoding="utf-8") as fh:
        json.dump(records, fh)
sys.exit(code)
