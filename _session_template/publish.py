"""Copy the session's current plates, storyboard and film to its delivery folder.

WHY THIS EXISTS. Session #6's folder was populated by hand and drifted: it held
a pre-re-roll plate next to a film made from a different plate entirely, a
storyboard that predated the same change, and two versions of beat 01. Anyone
opening it was looking at a description of a film that no longer existed.

THE PLATE IS RESOLVED, NEVER TYPED -- same rule as everywhere else in this
pipeline. gen_still.plate() decides what the current take is, so a re-roll
propagates here without anyone remembering to update a list.

THE DESTINATION IS DERIVED from shot.SESSION_NO, so this file is safe to copy
into the next tree -- which is exactly how five other clone bugs got started.

FILENAMES ARE PRESERVED, NOT REGENERATED, where the folder already has one: the
hand-written slugs are nicer than anything derivable and are presumably what
gets browsed by. A beat with MORE THAN ONE file is reported and left alone --
that is a superseded take sitting next to a current one, and choosing which to
delete out of somebody's delivery folder is not this script's call.
"""

import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_still  # noqa: E402
import identity
import shot       # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
# DERIVED, NOT TYPED -- this file is copied into every session folder, and
# a typed destination is how five other clone bugs started.
DEST = os.path.join(identity.season.folder(), f"S{shot.SESSION_NO}")


def slug(text: str, n: int = 20) -> str:
    """The existing convention: lowercase, letters only, truncated."""
    return re.sub(r"[^a-z]", "", text.lower())[:n]


def main() -> int:
    os.makedirs(DEST, exist_ok=True)
    have = os.listdir(DEST)
    copied, made, ambiguous = 0, 0, []

    for sid in shot.CUT:
        src = gen_still.plate(sid)
        matches = [f for f in have
                   if f.startswith(f"{sid}_") and f.lower().endswith(".png")]
        if len(matches) > 1:
            ambiguous.append((sid, matches))
            continue
        if matches:
            name = matches[0]
        else:
            name = f"{sid}_{slug(shot.BEAT[sid]['what'].split('--')[0])}.png"
            made += 1
        shutil.copyfile(src, os.path.join(DEST, name))
        copied += 1
        print(f"  {sid}  {os.path.basename(src):24s} -> {name}")

    # THE NAME THE BOARD IS ACTUALLY WRITTEN UNDER. storyboard.py derives
    # its output as storyboard_{SLUG}.png (its own comment says why the
    # typed s03 name went); this file kept looking for the old spelling and
    # printed NOT BUILT YET forever while the board sat beside it (fault
    # 109) -- the delivery-folder drift this script exists to prevent.
    for name in (f"storyboard_{shot.SLUG}.png",
                 f"{shot.SLUG}.mp4"):
        p = os.path.join(OUT, name)
        if os.path.exists(p):
            shutil.copyfile(p, os.path.join(DEST, name))
            print(f"      {name}  ({os.path.getsize(p)/1e6:.1f} MB)")
        else:
            print(f"      {name}  NOT BUILT YET -- skipped")

    print(f"\n  {copied} plate(s) refreshed ({made} newly named)  ->  {DEST}")
    for sid, ms in ambiguous:
        print(f"  BEAT {sid} HAS {len(ms)} FILES and was left alone: "
              f"{', '.join(ms)}\n      one of these is a superseded take; "
              f"current is {os.path.basename(gen_still.plate(sid))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
