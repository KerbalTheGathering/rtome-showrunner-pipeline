"""Bake the whole season with one command.

WHY THIS EXISTS AND NOT A LIST OF COMMANDS IN A NOTE. The season this template
came from was rebuilt part by part, from whichever directory you happened to be
standing in, in an order you had to remember. That is how six interstitials
shipped from the wrong picture source three times running: the step that would
have caught it was a separate command nobody ran.

So the running order is worked out from the disk (parts.py) and the whole thing
is one invocation. Every part is rebuilt from its own sources, then the join
happens, then the checks that can only be made ACROSS parts run.

ORDER MATTERS AND IT IS NOT ALPHABETICAL. feature.py verifies each part's PCM
mix against its own picture and refuses a stale one, so everything has to be
current before the join.

EACH PART ALREADY USES EVERY CORE (see docs/07_performance.md), so the parts run
one after another rather than together -- sixteen bakes times eight folders
would only thrash the disk.

    python season.py                  # everything, then join
    python season.py --films          # the films only
    python season.py --parts          # every part, but do not join
    python season.py S3_HARBOUR          # just this folder
    python season.py --no-checks      # skip smoke.py and contract.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

import parts
import season_identity as season

ROOT = os.path.dirname(os.path.abspath(__file__))


def run(where: str, what: str, script: str = "assemble.py",
        args: list[str] | None = None) -> float:
    print(f"\n{'=' * 70}\n  {os.path.basename(where)}  --  {what}\n{'=' * 70}",
          flush=True)
    t0 = time.time()
    r = subprocess.run([sys.executable, script, *(args or [])], cwd=where)
    dt = time.time() - t0
    if r.returncode:
        sys.exit(f"\nFAIL: {os.path.basename(where)}/{script} exited "
                 f"{r.returncode} after {dt:.0f}s.\n"
                 f"  Nothing further was built. Parts already finished are "
                 f"still on disk and will not be rebuilt unless you ask for "
                 f"them by name.")
    print(f"  [done in {dt / 60:.1f} min]", flush=True)
    return dt


def main() -> int:
    argv = sys.argv[1:]
    ss, bad = parts.audit()
    if bad:
        print("  the season does not describe itself consistently:")
        for b in bad:
            print(f"    {b}")
        sys.exit("\nFAIL: fix the identity files before building anything. "
                 "`python parts.py` explains the layout.")

    # THE TWO CHECKS THAT COST NOTHING, BEFORE THE ONE THAT COSTS HOURS.
    #
    # A module that cannot be imported and two tables that disagree both fail
    # LATE otherwise -- after the plates, after the VO, somewhere inside a bake
    # that has been running for twenty minutes. Or worse, they do not fail at
    # all: a beat table keyed by an id another film also has resolves cleanly
    # and renders the wrong thing. Four seconds here against that.
    #
    # `--no-checks` exists because a rebuild of one finished part should not be
    # blocked by a tree you are still writing.
    if "--no-checks" not in argv:
        for tool in ("smoke.py", "contract.py"):
            r = subprocess.run([sys.executable, os.path.join(ROOT, tool)],
                               cwd=ROOT)
            if r.returncode:
                sys.exit(f"\nFAIL: {tool} refused. Nothing was built.\n"
                         f"  Run `python {tool}` on its own to read it in "
                         f"full, or `python season.py --no-checks` to build "
                         f"anyway.")

    named = [a for a in argv if not a.startswith("-")]
    show = parts.show_dir()
    cold = parts.cold_open_dir()
    todo: list[tuple[str, str]] = []

    if named:
        known = {r["dir"]: r for r in ss}
        for n in named:
            if n in known:
                todo.append((known[n]["path"], known[n]["title"]))
            elif show and n == "show":
                todo.append((show, "the interstitials"))
            elif cold and n == "cold_open":
                todo.append((cold, "the cold open"))
            else:
                sys.exit(f"FAIL: {n!r} is not a session folder. Known: "
                         f"{sorted(known) + (['show'] if show else [])}")
        join = False
    else:
        films = [(r["path"], r["title"]) for r in ss]
        if "--films" in argv:
            todo, join = films, False
        else:
            # COLD OPEN, THEN FILMS, THEN SHOW. The cold open depends on
            # nothing and is the front door. The show goes LAST because its
            # interstitials are cut against the films they introduce -- build
            # it first and it is built against the previous version of them.
            todo = ([(cold, "the cold open")] if cold else [])
            todo += films
            todo += [(show, "the interstitials")] if show else []
            join = "--parts" not in argv

    print(f"  {season.SEASON}: {len(todo)} part(s) to bake"
          + (", then the join" if join else ", no join"))
    t0 = time.time()
    times = [(os.path.basename(w), run(w, what)) for w, what in todo]

    # THE JOIN DOES NOT DEPEND ON THERE BEING A SHOW, AND IT USED TO.
    #
    # This block read `if not show: sys.exit("the join lives in
    # show/feature.py ...  Add one, or join the films by hand.")` -- so
    # `SHOW = False`, a mode this driver offers and season_identity.py
    # documents, could bake every part and then refuse to produce the one
    # artefact the whole run exists for. The suggested remedy was to add a
    # wraparound you had already declared you did not want.
    #
    # feature.py lives at the season root now. It never needed anything from
    # the show tree; see its docstring.
    if join:
        run(ROOT, "the season as one video", "feature.py")

    print(f"\n{'=' * 70}\n  timings")
    for name, dt in times:
        print(f"    {name:<22} {dt / 60:>5.1f} min")
    print(f"    {'TOTAL':<22} {(time.time() - t0) / 60:>5.1f} min")
    if join:
        print(f"\n  now: python publish.py")
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
