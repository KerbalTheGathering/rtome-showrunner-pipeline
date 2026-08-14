"""One part's plates, resolved the way the pipeline resolves them. JSON out.

THIS IS THE WORKER HALF OF contact.py AND IS NOT USUALLY RUN BY HAND. It exists
as a separate file, invoked once per part with the working directory set to that
part's folder, for the reason smoke.py gives at length: every tree owns an
`identity.py`, a `shot.py` and a `gen_still.py`, and one interpreter can only
hold one of each. A season-level sheet drawn in a single process would show the
FIRST part's plates under every part's heading, coherently, with nothing failing.

    python contact_probe.py                     # from inside a part folder
    python contact_probe.py --pretty            # readable, for debugging

WHAT IT RESOLVES, AND WHY NOT BY LISTING THE DIRECTORY.
`gen_still.plate()` applies PLATE_ALIAS (a beat that deliberately has no plate of
its own and borrows another's) and PLATE_FLIP (a whole-image mirror written out
as a derivative file). A sheet built by listing PNGs shows neither, so it shows
pictures the shoot will not use -- and reports a problem that is already fixed,
or hides one that is not. What comes back from here is what will actually be
handed to the generator.

A MISSING PLATE IS AN ANSWER, NOT AN ERROR. `gen_still.plate()` exits when a
beat has nothing, which is right for the shoot and wrong here: "these six beats
have no plate yet" is the single most useful thing this tool can say before the
plates exist. So the exit is caught and reported as a fact about the beat.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import season_paths                                                # noqa: E402


def load():
    """This part's `shot` and `gen_still`, imported INSIDE a function.

    IMPORTING THIS MODULE HAS TO BE FREE OF SIDE EFFECTS, including refusals.
    It is a script that only means anything with the working directory set to
    one part, so at module level both the sys.path surgery below and the guard
    that follows it would fire on any `import contact_probe` -- and smoke.py,
    which imports every module in the repo from the root, is exactly that. It
    caught this file the first time it ran, which is the argument for smoke.py
    made against the tool written to answer a different half of it.

    THE PART FOLDER IS THE WORKING DIRECTORY AND HAS TO BE PUT ON sys.path BY
    HAND. Running `python <root>/contact_probe.py` from inside a part sets
    sys.path[0] to the SCRIPT's directory -- the season root -- not to the cwd.
    So `import shot` would miss the part entirely and, if the root ever grew a
    module of that name, would find the wrong one instead of failing. Position
    0, so the part always wins.
    """
    cwd = os.getcwd()
    # RUN FROM THE WRONG PLACE, SAY SO. Without this the failure is a bare
    # `ModuleNotFoundError: No module named 'gen_still'`, which is true and
    # tells you nothing about the one thing you got wrong.
    if not os.path.exists(os.path.join(cwd, "shot.py")):
        sys.exit(f"FAIL: {cwd} is not a part folder -- there is no shot.py "
                 f"in it.\n"
                 f"  This is the worker half of contact.py and it runs with "
                 f"the working\n"
                 f"  directory set to ONE part. You probably want "
                 f"`python contact.py`.")
    sys.path.insert(0, cwd)
    import gen_still
    import shot
    return shot, gen_still


def beats(shot, gen_still) -> list[dict]:
    alias = getattr(shot, "PLATE_ALIAS", {})
    flip = getattr(shot, "PLATE_FLIP", set())
    graded = set(getattr(shot, "GRADED", ()))
    out = []
    for sid in shot.CUT:
        row = {
            "sid": sid,
            "what": (shot.BEAT[sid].get("what") or "").split(" -- ")[0],
            "alias": alias.get(sid),
            "flip": sid in flip,
            "graded": sid in graded,
            "seed": shot.plate_seed(sid),
            "takes": len(gen_still.existing(alias.get(sid, sid))),
            "plate": None,
        }
        try:
            row["plate"] = gen_still.plate(sid)
        except SystemExit:
            pass                     # no plate yet; that is the finding
        out.append(row)
    return out


def main() -> int:
    shot, gen_still = load()
    got = {
        "dir": os.path.basename(os.getcwd()),
        "name": shot.NAME,
        "title": getattr(shot, "TITLE", ""),
        "session_no": getattr(shot, "SESSION_NO", 0),
        # gen_still's own directory, not a second derivation of it -- the
        # `--obj` flat layer renders to a different one and this must follow
        # whichever the module is actually pointing at.
        "out": gen_still.OUT,
        "beats": beats(shot, gen_still),
    }
    json.dump(got, sys.stdout, indent=2 if "--pretty" in sys.argv else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
