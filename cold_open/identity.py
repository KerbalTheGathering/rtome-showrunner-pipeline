"""WHO THE COLD OPEN IS. The front door of the season.

WHY THE SEASON HAS ONE AT ALL. Before it existed, the reference season began on
a man behind a desk saying "Good morning" -- a front door for the SHOW, with
nothing above the films saying what you were watching. Twenty-seven wordless
seconds of place and a title fixed that, and it is the single cheapest part of
the whole build: no dialogue, no lip sync, no interstitial timing.

IT IS NOT A SESSION AND NOT PART OF THE SHOW. SESSION_NO stays 0 so parts.py
does not count it as a film, and it lives in its own folder rather than inside
show/ because it has its own assemble.py and one folder cannot have two.

DELETE THIS FOLDER for a season with no cold open. parts.py notices it is gone
and the running order simply starts on the first interstitial.

    python identity.py
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import season_identity as season                                   # noqa: E402

NAME = ""                        # e.g. "OPEN"; the ComfyUI output folder
SESSION_NO = 0                   # ALWAYS 0

# The title that comes up over the last few seconds. This is the SEASON's title,
# so it is taken from the season identity rather than typed -- a cold open
# announcing a different name from the feature it opens is the whole failure
# mode this template is built around.
TITLE = season.SEASON_TITLE
SLUG = "cold_open"

# The line ABOVE the season title on the card -- a series name, a character,
# a studio, or "" for none. Typed into assemble.py in the reference season,
# which is exactly the leak this file closes.
TITLE_SUPER = ""

# WHICH TITLE CARD, from ../cards.py. `plain` is the centred two-line stack
# the cold open has always drawn; `over_colour` puts the season's name on flat
# colour instead of over the water, which is what a front door that is not a
# place wants. `python ../cards.py --sheet` draws them all.
TITLE_CARD = "plain"
TITLE_CARD_OPTS: dict = {}

# THE LOOK, from ../grades.py, and it applies to every frame of the open. There
# is no shot.GRADED here -- the cold open is one continuous place and grading
# part of it would be a device, not a look. `python ../grades.py --sheet`.
GRADE = "none"
GRADE_OPTS: dict = {}

# HOW A PLATE ENTERS THE FRAME, from ../framing.py. The open shoots at the
# delivery aspect so this rarely binds; it is here so a season that changes
# aspect mid-way has one answer rather than three.
FIT = "crop"
FIT_OPTS: dict = {}

# WHAT SITS UNDER WHAT, from ../mixes.py. The open has one cue and no voice, so
# `flat` at unity is exactly what it always did -- the point of routing it
# through the library is that the bus owns the LENGTH. This chain had an
# `atrim` and no `apad`, so a cue file shorter than the picture ended the audio
# early and `-shortest` cut the open to match, with nothing to notice.
MIX = "flat"
MIX_OPTS: dict = {"music": 1.0}

SEED = 0
LATENT = (1216, 832)

STYLE_LORA, STYLE_W = "", 0.85
# No character. The cold open is a place, not a person -- and a character LoRA
# here will put the protagonist in a landscape that is meant to be empty.
CHAR_LORA, CHAR_W = "", 0.0


def check() -> None:
    season.check()
    missing = [k for k in ("NAME",) if not globals()[k]]
    if not SEED:
        missing.append("SEED")
    if missing:
        sys.exit("FAIL: cold_open/identity.py is still blank.\n"
                 "  Unfilled: " + ", ".join(missing) + "\n"
                 "  Or delete cold_open/ if this season does not have one.")
    if SESSION_NO:
        sys.exit("FAIL: the cold open is not a session -- SESSION_NO must "
                 "stay 0 or it will be counted as a film")


CLIPS = (os.path.join(season_paths.COMFY_OUTPUT, f"{NAME}_clips")
         if NAME else "")

check()

# THE CLIP FOLDER IS CLAIMED FOR THIS SEASON, not merely named. See
# season_identity.claim_clips() -- a NAME reused between seasons otherwise makes
# a new build read the old season's clips, coherently and silently.
season.claim_clips(CLIPS, f"{__name__}")

if __name__ == "__main__":
    print(f"  cold open  {NAME}  --  titles {TITLE!r}")
    print(f"  clips      {CLIPS}")
