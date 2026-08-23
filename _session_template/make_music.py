"""The score cues for this film -- one per entry in edit.CUES, generated to
the length the picture is, on ACE-Step 1.5, LOCALLY, through ../score.py.

THIS REPLACED THE ELEVENLABS MUSIC CALL (ninth season, LOSS OF SIGNAL; the
operator's call, 2026-08-21: ACE for the whole season). The old file is in
git history. What changed and why:

  * $0.00 a minute against $0.15. A season's score is re-generated every
    time a cut changes length, and it changes length every time a line is
    re-taken. On the paid model that was a bill for editing.
  * ACE PINS BPM, KEY AND TIME SIGNATURE (memory: ace-step-local-music).
    Cues generated independently are made one score by the KEY FAMILY,
    not by asking the prose to "continue the same piece" -- so every cue
    here carries a key, and a season decides its family once.
  * ../score.py owns the graph, the pad and `usable_seconds()`. A file that
    is the right length can still END IN DIGITAL SILENCE, which is why the
    last line of main() measures where the music actually stops instead
    of trusting the file's duration.

LENGTHS DERIVED from edit.cue_spans(), never typed. Where the cues come in
is edit.CUES' fact -- `CROSSOVER_SID` used to be declared here AND in
assemble.py, and they disagreed.

    python make_music.py            # every cue that is not on disk
    python make_music.py --force    # re-generate them all

A FILM WITH NO SCORE is edit.CUES = [] and this file does nothing; it is a
real answer and the bus copes with it (docs/01_process.md, "the bus").
"""
from __future__ import annotations

# THE CUES BELOW ARE THE TEMPLATE'S EXAMPLE, NOT YOUR SCORE.
# preflight.py refuses to render while this line is here. Delete it when you
# have replaced the cue table -- and only then.
#
# WHY THIS FILE CARRIES THE SENTINEL AT ALL. Its cues decide what the film
# sounds like, and a clone that keeps them scores a lighthouse elegy under a
# comedy and nothing downstream can tell.
EXAMPLE_CONTENT = True

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import score                                                        # noqa: E402

import os
import sys

import edit
import identity

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_music")

# ONE ENTRY PER NAME IN edit.CUES. `tags` is ACE's comma-separated style
# line -- instruments, mood, era, "instrumental" -- and the three pinned
# numbers are what make the cues one score. Keep a melody OUT of the voice's
# register on anything narrated: the bus ducks the level, it cannot duck
# the pitch.
CUES: dict[str, dict] = {
    # EXAMPLE CONTENT -- replace all of it.
    "main": {"tags": "slow wistful bolero, nylon-string guitar melody, soft "
                     "upright bass, brushed percussion, warm and unhurried, "
                     "minor key, instrumental, no vocals",
             "bpm": 76, "key": "A minor", "ts": "4", "seed": 1},
    "late": {"tags": "solo nylon-string guitar, sparse, exposed, slow, then "
                     "quietly gathering, minor key, instrumental, no vocals",
             "bpm": 76, "key": "A minor", "ts": "4", "seed": 2},
}

PROMPTS = CUES        # the name ../contract.py reads the cue table by


def main() -> int:
    spans = edit.cue_spans()
    missing = [c["name"] for c in spans if c["name"] not in CUES]
    if missing:
        sys.exit(f"FAIL: no cue design for {missing} -- edit.CUES asks for them")
    if not spans:
        print("  no cues: this film is unscored (edit.CUES is empty)")
        return 0
    print("  picture " + "  ".join(f"[{c['name']}] beat {c['sid']} at {c['start']:.1f}s "
                                  f"for {c['secs']:.1f}s" for c in spans))
    short = []
    for c in spans:
        name, need = c["name"], c["secs"]
        path = os.path.join(OUT, f"{name}.mp3")
        if os.path.exists(path) and "--force" not in sys.argv:
            print(f"  [{name}] on disk", end="")
        else:
            print(f"  [{name}] ACE {need + score.PAD:.0f}s ...", end="", flush=True)
            score.render(name, need, CUES[name], OUT, identity.NAME)
        live = score.usable_seconds(path)
        print(f"   music stops at {live:.1f}s, needs {need:.1f}s  "
              f"{'ok' if live >= need else 'SHORT'}")
        if live < need:
            short.append(name)
    if short:
        sys.exit(f"FAIL: {short} stop before the picture does -- re-run with --force")
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
