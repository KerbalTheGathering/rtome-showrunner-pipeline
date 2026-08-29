"""One batch at a time, enforced at process entry. Import and call `solo()`.

WHY THIS IS NOT ALREADY COVERED BY `busy()`. Every generator in this repo
refuses to submit while the ComfyUI queue is non-empty, and that guard is
correct: it is what stops two renders fighting over one card. It answers *"is
this action safe"*.

It cannot answer *"should this process exist"*, and that is the gap. Four copies
of a batch tool once ran at once -- a backgrounded launch outlived its shell
invisibly, so a second was started, then a third. **Nothing was corrupted.** Each
copy correctly waited for an empty queue, and they waited on each other, behind
one stuck job at the head. GPU at 0%, no output, and nothing in any log to say
why, because from inside each process the world looked exactly like a slow
render.

> **A guard that prevents corruption but permits deadlock is half a guard.**
> The missing half is upstream: do not let the second copy start.

A STALE LOCK IS TAKEN OVER, NOT OBEYED. The file holds a PID; if that process is
gone the lock is a leftover and is claimed. Otherwise every `kill -9` -- which is
exactly how you end a wedged render -- leaves a file that blocks the next run,
and the safety device becomes the thing you delete without reading at 4am.

    import solo
    solo.solo("plates")                     # refuses if another is running
    solo.solo("plates", force=True)         # override, for when you are sure

The lock lives in the part's own directory, so a season CAN legitimately run
`cold_open` and a session tree at once if the card has room -- the thing being
prevented is two copies of the SAME stage, which is never wanted.
"""
from __future__ import annotations

import atexit
import os
import subprocess
import sys


def _alive(pid: int) -> bool:
    """Is this PID a live process?

    Windows has no `os.kill(pid, 0)` semantics, and this repo runs there, so
    the check shells out. **An unanswerable question is treated as "dead"** --
    a lock that cannot be verified must not be allowed to block work forever,
    which is the same reasoning as taking over a stale one.
    """
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    try:
        if os.name == "nt":
            out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                                 capture_output=True, text=True,
                                 timeout=15).stdout
            return str(pid) in out
        os.kill(pid, 0)
        return True
    except Exception:                                        # noqa: BLE001
        return False


def solo(name: str, where: str | None = None, force: bool = False) -> None:
    """Refuse to start if another copy of stage `name` is already running."""
    where = where or os.path.dirname(os.path.abspath(sys.argv[0] or "."))
    d = os.path.join(where, "_locks")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{name}.lock")

    me = str(os.getpid())

    def _release() -> None:
        # ONLY THE OWNER DELETES. The old cleanup removed the file if it
        # existed, so after a force=True takeover the LOSER's exit deleted
        # the WINNER's lock, and a third copy then started clean against a
        # running second -- the guard opening the door it exists to close
        # (fault 103).
        try:
            with open(path, encoding="utf-8") as fh:
                mine = fh.read().strip() == me
            if mine:
                os.remove(path)
        except OSError:
            pass

    # THE ACQUIRE IS ATOMIC. exists() then open("w") was check-then-act:
    # two copies launched in the same breath -- the backgrounded double
    # start the docstring describes -- both passed the exists check and
    # both ran (fault 103). O_EXCL makes the filesystem the referee.
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(me)
        atexit.register(_release)
        return
    except FileExistsError:
        pass

    try:
        old = int(open(path, encoding="utf-8").read().strip() or 0)
    except Exception:                                        # noqa: BLE001
        old = 0
    if _alive(old) and not force:
        sys.exit(
            f"FAIL: {name} is already running as PID {old}.\n"
            f"  Two copies of a stage share one GPU and one ComfyUI queue.\n"
            f"  They do not corrupt each other -- they DEADLOCK, silently,\n"
            f"  each waiting for a queue the other keeps filling.\n"
            f"  Stop that process, or pass --force if you are certain it is "
            f"gone.")
    print(f"  (--force: taking the {name} lock over live PID {old})"
          if _alive(old) else
          f"  (stale {name} lock from dead PID {old}, taking it over)")

    # The takeover itself can race a second taker, so it goes through an
    # atomic replace and then BELIEVES THE FILE: exactly one PID is in it
    # afterwards, and any copy that is not that PID bows out.
    tmp = f"{path}.{me}"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(me)
    os.replace(tmp, path)
    try:
        with open(path, encoding="utf-8") as fh:
            won = fh.read().strip() == me
    except OSError:
        won = False
    if not won:
        sys.exit(f"FAIL: another copy claimed the {name} lock in the same "
                 f"moment -- it is running; this one is not needed.")
    atexit.register(_release)
