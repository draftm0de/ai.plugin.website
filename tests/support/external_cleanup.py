"""Cleanup rules for the real-tool external test (deterministic logic, no network, no npm, no process is started here).

Preview processes are checked and stopped only through the preview controller (`control.py status|stop`), which proves
ownership itself. Nothing is ever signalled by port or guessed PID. An unclear state signals nothing and keeps the fixture.
"""
import shutil
import subprocess

NOT_RUNNING = "not-running"
OURS_RUNNING = ("running-reused", "starting")


def _ask(control, verb):
    """Run one controller verb; returns (data or None, problem or None). Never raises for ordinary failures."""
    try:
        rc, data = control(verb)
    except subprocess.TimeoutExpired:
        return None, f"{verb}: controller call timed out"
    except Exception as exc:  # noqa: BLE001 - any failure of the call means "unclear", reported below
        return None, f"{verb}: controller call failed ({type(exc).__name__}: {exc})"
    if not isinstance(data, dict) or "state" not in data:
        return None, f"{verb}: unreadable controller output"
    return data, None


def ensure_preview_stopped(control):
    """Return (ended, note). `ended` is True only when the controller itself reports `not-running` for our site.

    `control(verb)` runs `control.py <verb>` for the fixture site and returns (exit code, parsed JSON or None).
    """
    data, problem = _ask(control, "status")
    if problem:
        return False, problem
    if data["state"] == NOT_RUNNING:
        return True, "no own preview process"
    if data["state"] not in OURS_RUNNING:
        return False, f"status: ownership not established (state {data['state']}); nothing was signalled"
    stopped, problem = _ask(control, "stop")
    if problem:
        return False, problem
    again, problem = _ask(control, "status")
    if problem:
        return False, "after stop: " + problem
    if again["state"] == NOT_RUNNING:
        return True, "own preview process stopped (stop: %s)" % stopped["state"]
    return False, f"after stop the controller still reports {again['state']} (stop: {stopped['state']})"


def finalize_fixture(base, passed, preview_ended, note="", rmtree=shutil.rmtree, say=print):
    """Delete the fixture only after a passed test AND a confirmed end of the own processes; otherwise keep everything.

    Deletion errors are not hidden (no ignore_errors): they propagate, but only reached on success, so an earlier test
    failure is never displaced. Returns True when the fixture was deleted.
    """
    if passed and preview_ended:
        rmtree(base)
        return True
    reason = "test did not complete" if not passed else "own test processes not confirmed ended"
    say(f"KEPT fixture, logs and state data ({reason}): {base}" + (f" | {note}" if note else ""))
    return False
