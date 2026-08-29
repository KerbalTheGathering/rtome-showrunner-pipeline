"""One cue under the cold open, on ACE-Step 1.5, LOCALLY (../score.py).

It runs every shot in shot.SECS plus the title hold, and the length is
DERIVED from edit -- typed once, here, it drifted from the picture the first
time a shot was re-timed. ACE pins bpm / key / time signature, so put the
cold open in the SEASON'S KEY FAMILY: the films' cues are generated on their
own and the key is what makes them one score (memory: ace-step-local-music).

THIS REPLACED THE ELEVENLABS MUSIC CALL (ninth season; $0.00 a minute
against $0.15, and a cold open is re-scored every time its title hold
moves). The old file is in git history.

    python make_music.py            # once; on disk after that
    python make_music.py --force    # re-generate
"""
from __future__ import annotations

# THE CUE BELOW IS THE TEMPLATE'S EXAMPLE, NOT YOUR SCORE.
# preflight.py refuses to render while this line is here. Delete it when you
# have replaced the cue -- and only then.
EXAMPLE_CONTENT = True

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import score                                                        # noqa: E402

import os
import sys

import edit
import identity

HERE = os.path.dirname(os.path.abspath(__file__))
MUSIC = os.path.join(HERE, "_music")
WANT_S = sum(edit.SECS.values()) + edit.TITLE_HOLD

# EXAMPLE CONTENT -- replace it.
CUE = {"tags": "slow spare muted trumpet melody, brushed upright bass, soft "
               "brushed snare, warm electric piano chords, minor key, patient, "
               "a little melancholy, recorded close and warm, instrumental, "
               "no vocals",
       "bpm": 62, "key": "A minor", "ts": "4", "seed": 1}


def main() -> int:
    # Unknown arguments are refused, not ignored (fault 141): a typo like
    # --forc silently meant "reuse everything on disk", which reads as a
    # successful re-render.
    _bad = [a for a in sys.argv[1:] if a != "--force"]
    if _bad:
        sys.exit(f"FAIL: unrecognised argument(s) {_bad} -- this tool takes "
                 f"only --force (re-render existing cues)")
    path = os.path.join(MUSIC, "open.mp3")
    if os.path.exists(path) and "--force" not in sys.argv:
        print("  [open] on disk", end="")
    else:
        print(f"  [open] ACE {WANT_S + score.PAD:.0f}s ...", end="", flush=True)
        score.render("open", WANT_S, CUE, MUSIC, identity.NAME)
    live = score.usable_seconds(path)
    print(f"   music stops at {live:.1f}s, needs {WANT_S:.1f}s  "
          f"{'ok' if live >= WANT_S else 'SHORT'}")
    if live < WANT_S:
        sys.exit("FAIL: the cue stops before the title does -- re-run with --force")
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
