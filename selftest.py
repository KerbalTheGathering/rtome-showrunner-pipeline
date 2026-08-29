"""Regression tests for the pure logic the static review hardened.

WHAT THIS IS AND IS NOT. smoke.py asks whether every module EXECUTES;
nothing asked whether the shared functions still BEHAVE. Thirty-five
faults were fixed by reading in one pass (learnings, "The static review"),
and the only thing preventing their return was a comment. This file is
the tripwire: each test pins one fixed behaviour, named by its fault
number, and fails in a sentence if it comes back.

FAST, LOCAL, BORING. No GPU, no network, no ffmpeg, no framework -- pure
Python and a couple of spawned children, a few seconds total. Run it
after editing any of the files it covers; season.py does not run it for
you (it guards the TEMPLATE's logic, not a season's content).

    python selftest.py            # all of it
    python selftest.py -v         # say each test as it runs

Two functions are knowingly NOT covered here: edit.vo_dur's mtime cache
(needs ffprobe on a real take -- exercised by any bake) and feature.py's
dip cache key (inline in main(); extract it before testing it).
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

VERBOSE = "-v" in sys.argv
FAILURES: list[str] = []


def run(name: str, fn) -> None:
    if VERBOSE:
        print(f"  {name} ...", flush=True)
    try:
        fn()
    except BaseException as e:                                   # noqa: BLE001
        FAILURES.append(f"{name}: {e}")
        print(f"  FAIL {name}: {e}")
    else:
        if VERBOSE:
            print(f"       ok")


def expect_exit(fn, needle: str) -> None:
    """The callable must refuse via SystemExit whose message carries needle."""
    try:
        fn()
    except SystemExit as e:
        assert needle in str(e.code), (
            f"refused, but the message {str(e.code)[:80]!r} does not "
            f"say {needle!r}")
        return
    raise AssertionError("did not refuse at all")


# --------------------------------------------------------------------------
# mixes.sum_to -- fault 106 (one-input pad) and fault 73 (n-input pad)


def test_sum_to() -> None:
    import mixes
    one = mixes.sum_to(["[a]"], "[out]", total=10.0)
    assert "apad=whole_dur=10.000" in one and "atrim=0:10.000" in one, (
        "a lone input with a total must be padded to it (fault 106); "
        f"got {one!r}")
    bare = mixes.sum_to(["[a]"], "[out]")
    assert "anull" in bare and "apad" not in bare, (
        f"a lone input with NO total stays a plain pass-through; got {bare!r}")
    many = mixes.sum_to(["[a]", "[b]"], "[out]", total=7.5)
    assert many.count("apad=whole_dur=7.500") == 2, (
        "every input of an amix must end at the bus length (fault 73); "
        f"got {many!r}")
    expect_exit(lambda: mixes.sum_to([], "[out]"), "no inputs")


# --------------------------------------------------------------------------
# the five registries -- fault 125 (docstring-less entry refused in a sentence)


def test_registries() -> None:
    import cards
    import devices
    import framing
    import grades
    import mixes

    def bare(_a=None, _b=None, _c=None, _d=None):                # no docstring
        return None

    expect_exit(lambda: devices.register("_selftest")(bare), "docstring")
    expect_exit(lambda: grades.register("_selftest")(bare), "docstring")
    expect_exit(lambda: framing.register("_selftest")(bare), "docstring")
    expect_exit(lambda: mixes.register("_selftest")(bare), "docstring")
    expect_exit(lambda: cards.register("_selftest")(bare), "docstring")


# --------------------------------------------------------------------------
# subs.shape -- fault 114 (floors first, the de-overlap genuinely last)


def _extract(path: str, start: str, stop: str) -> str:
    src = open(path, encoding="utf-8").read()
    a, b = src.index(start), src.index(stop)
    return textwrap.dedent(src[a:b])


def test_subs_shape() -> None:
    # subs.py imports the season identity, which a template cannot satisfy,
    # so shape() is executed out of its source against a stub namespace --
    # the same trick contract.py uses for a blank season.
    ns = {"WRAP": 42, "MAX_LINES": 2, "MIN_SECS": 1.0, "PAD": 0.10,
          "LABELS": {}}
    exec("import textwrap\n"                                     # noqa: S102
         "def wrap(t):\n    return textwrap.wrap(t, WRAP)\n", ns)
    exec(_extract(os.path.join(HERE, "subs.py"),                 # noqa: S102
                  "def shape", "def write"), ns)
    wordy = ("one two three four five six seven eight nine ten eleven "
             "twelve thirteen fourteen fifteen sixteen")
    cues = [{"start": 0.0, "end": 0.5, "role": "r", "text": wordy,
             "on_screen": [], "part": "p", "lid": "L1"},
            {"start": 0.6, "end": 2.0, "role": "r", "text": "next",
             "on_screen": [], "part": "p", "lid": "L2"}]
    out = ns["shape"](cues)
    for a, b in zip(out, out[1:]):
        assert a["end"] <= b["start"], (
            f"overlapping cues shipped (fault 114): {a['end']:.2f} past "
            f"{b['start']:.2f}")
    assert out[-1]["end"] >= out[-1]["start"] + 1.0, (
        "the final cue lost its readability floor")


# --------------------------------------------------------------------------
# solo.py -- fault 103 (atomic acquire, stale takeover, owner-only release)


def test_solo_lock() -> None:
    child = ("import solo, os, sys\n"
             "solo.solo(sys.argv[1], where=sys.argv[2])\n"
             "print('GOT', os.getpid()); sys.stdout.flush()\n"
             "if len(sys.argv) > 3:\n"
             "    import time; time.sleep(float(sys.argv[3]))\n")
    with tempfile.TemporaryDirectory() as w:
        script = os.path.join(w, "_child.py")
        open(script, "w", encoding="utf-8").write(child)
        env = dict(os.environ, PYTHONPATH=HERE)
        p1 = subprocess.Popen([sys.executable, script, "plates", w, "5"],
                              stdout=subprocess.PIPE, text=True, env=env)
        try:
            import time
            deadline = time.time() + 4
            lock = os.path.join(w, "_locks", "plates.lock")
            while not os.path.exists(lock) and time.time() < deadline:
                time.sleep(0.05)
            assert os.path.exists(lock), "first copy never took the lock"
            r2 = subprocess.run([sys.executable, script, "plates", w],
                                capture_output=True, text=True, env=env,
                                timeout=30)
            assert r2.returncode != 0 and "already running" in (
                r2.stdout + r2.stderr), (
                "a second copy of a stage was allowed to start (fault 103)")
        finally:
            p1.wait(timeout=30)
        assert not os.path.exists(lock), (
            "the owner's exit did not release its own lock")
        os.makedirs(os.path.dirname(lock), exist_ok=True)
        open(lock, "w", encoding="utf-8").write("999999")
        r3 = subprocess.run([sys.executable, script, "plates", w],
                            capture_output=True, text=True, env=env,
                            timeout=30)
        assert r3.returncode == 0 and "taking it over" in r3.stdout, (
            "a stale lock from a dead PID must be taken over, not obeyed")


# --------------------------------------------------------------------------
# italk.next_take -- fault 132 (the slice is derived from the sid)


def test_next_take() -> None:
    with tempfile.TemporaryDirectory() as w:
        for f in ("s01_00001_.mp4", "s01_00002_.mp4", "s01x_00001_.mp4"):
            open(os.path.join(w, f), "w").close()
        ns = {"os": os, "CLIPS": w}
        exec(_extract(                                           # noqa: S102
            os.path.join(HERE, "_session_template", "italk.py"),
            "def next_take", "def main"), ns)
        got = os.path.basename(ns["next_take"]("01"))
        assert got == "s01_00003_.mp4", f"beat 01 -> {got}"
        got = os.path.basename(ns["next_take"]("01x"))
        assert got == "s01x_00002_.mp4", (
            f"a continuation sid parsed the wrong columns (fault 132): "
            f"next take for 01x -> {got}")


# --------------------------------------------------------------------------
# script.py's tag-habit assert -- fault 133 (share of the SCRIPT, and a
# habit requires repetition)


def test_tag_habit() -> None:
    block = _extract(os.path.join(HERE, "_session_template", "script.py"),
                     "_tags = [", "# PROVEN-SAFE")

    def outcome(lines) -> str | None:
        try:
            exec(block, {"LINES": lines})                        # noqa: S102
        except AssertionError as e:
            return str(e)
        return None

    line = lambda i, tag: (f"{i:02d}", f"{i:02d}", "narrator", 0.4,  # noqa: E731
                           (f"[{tag}] " if tag else "") + "words here")
    ten = [line(i, "dry" if i < 2 else "") for i in range(10)]
    err = outcome(ten)
    assert err is None, (
        f"two tags on a ten-line film is 20% of the script, not a habit "
        f"(fault 133); refused with: {err}")
    six = [line(i, "dry" if i < 3 else "") for i in range(6)]
    assert outcome(six) is not None, (
        "three identical tags on six lines (50%) IS a habit and must refuse")


# --------------------------------------------------------------------------
# direction.py -- its own built-in self-check (seven catches, five passes)


def test_direction() -> None:
    r = subprocess.run([sys.executable, os.path.join(HERE, "direction.py")],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, (
        f"direction.py's self-check failed:\n{(r.stdout + r.stderr)[-400:]}")


# --------------------------------------------------------------------------


def main() -> int:
    run("mixes.sum_to pads every shape of input (faults 73, 106)", test_sum_to)
    run("all five registries refuse a docstring-less entry (fault 125)",
        test_registries)
    run("subs.shape never ships an overlap (fault 114)", test_subs_shape)
    run("solo.py: atomic acquire, refusal, takeover, owner release "
        "(fault 103)", test_solo_lock)
    run("italk.next_take derives its slice from the sid (fault 132)",
        test_next_take)
    run("the tag-habit assert measures the script (fault 133)",
        test_tag_habit)
    run("direction.py still catches its seven phrasings", test_direction)

    n = 7
    if FAILURES:
        print(f"\n  FAIL: {len(FAILURES)} of {n} regression tests -- a "
              f"fixed fault is on its way back. The fault number in the "
              f"test name is the learnings.md entry to reread.")
        return 1
    print(f"  {n} regression tests pass -- the static review's fixes hold.")
    return 0


if __name__ == "__main__":
    # -h/--help prints the docstring -- the usage has always lived
    # there; this makes it reachable without opening the file
    # (finding 146). Before main(), so no lock is taken and no
    # argument guard fires first.
    import sys as _hsys
    if "-h" in _hsys.argv or "--help" in _hsys.argv:
        print(__doc__ or "(no usage doc)")
        raise SystemExit(0)
    sys.exit(main())
