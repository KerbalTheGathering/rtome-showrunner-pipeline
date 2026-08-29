"""WHO THE SHOW IS. The wraparound layer, if this season has one.

THE SHOW IS NOT A SESSION. It has no SESSION_NO, it is never counted in
N_SESSIONS, and it makes N+1 short pieces rather than one film: a cold open,
then one interstitial in front of every film. If this season is just films, set
`SHOW = False` in ../season_identity.py and delete this folder -- season.py will
not look for it.

WHAT THE SHOW LAYER IS FOR, MECHANICALLY. It is the only part of the pipeline
where a character SPEAKS ON CAMERA, which is why it carries the whole lip-sync
apparatus (italk.py, mouth_open.py, sync_probe.py, which_source.py) and the
films do not. If your show has no talking head, you still want feature.py and
the cold open, and you can leave the lip-sync scripts unused.

    python identity.py        # print what the show thinks it is
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import os
import sys

# See _session_template/identity.py for why the season-level file has a
# different name: a script's own directory is sys.path[0].
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import season_identity as season                                   # noqa: E402

NAME = ""                        # e.g. "NEWSDESK"; the ComfyUI output folder
SESSION_NO = 0                   # ALWAYS 0. The show is not a session.
TITLE = ""                       # e.g. "THE NEWS DESK"
SLUG = ""                        # e.g. "news_desk"

SEED = 0
LATENT = (1216, 832)

STYLE_LORA, STYLE_W = "", 0.85
# THE FILMS' CHARACTER MUST NOT ARRIVE IN THE SHOW unless the show is about
# them. Leaving a character LoRA loaded here is how the host started coming out
# looking like the protagonist.
CHAR_LORA, CHAR_W = "", 0.0

# WHO SPEAKS IN THE SHOW, BY ROLE -- the same table shape as a film's
# identity.py, and for the same reason: script.py names a role, not an id.
#
# THE HOST IS SPOKEN ON CAMERA and driven through InfiniteTalk, so it is the
# voice whose TIMING the picture is a function of. See docs/04_lipsync.md
# before changing anything about how it is placed.
#
# ONE ON-CAMERA SPEAKER PER SHOT IS A LIMIT OF THE SYNC, NOT OF THIS TABLE.
# A second role here can speak off camera today (a caller, a voice from the
# next room, a station announcement) and that costs nothing. Two mouths moving
# in ONE shot is the thing this repo cannot do yet -- docs/04_lipsync.md says
# exactly where that stands and what it would take.
VOICES: dict[str, str] = {
    "host": "",
}

# Which television. The chain lives in crt.py; compare presets on real frames
# with tvtest.py before changing it. "" disables the tube pass entirely, which
# is what a show that is not on a television wants.
TV = "heavy"

# HOW A PLATE OF ONE SHAPE ENTERS A FRAME OF ANOTHER, from ../framing.py. The
# show generates at the delivery aspect so this almost never binds -- it is
# here because qc.py draws the plate through it, and drawing it through a
# centre crop the film does not use is how a review sheet shows you a frame
# nobody will ever see. `python ../framing.py --sheet` draws the options.
FIT = "crop"
FIT_OPTS: dict = {}              # e.g. {"anchor": "top"}

# WHAT SITS UNDER WHAT, from ../mixes.py. The show places the voice out of the
# InfiniteTalk driver and lays a sting over it -- fixed levels, nothing moving,
# which is `flat`. `ducked` would sidechain the sting to the host and is a
# reasonable thing to want on a show with a longer bed under it.
MIX = "flat"
MIX_OPTS: dict = {"music": 0.42}


def check() -> None:
    season.check()
    if not season.SHOW:
        sys.exit("FAIL: season_identity.SHOW is False but the show tree is "
                 "being run. Either set SHOW = True or delete show/.")
    missing = [k for k in ("NAME", "TITLE", "SLUG") if not globals()[k]]
    if not SEED:
        missing.append("SEED")
    if missing:
        sys.exit("FAIL: show/identity.py is still blank.\n"
                 "  Unfilled: " + ", ".join(missing) + "\n"
                 "  Read ../docs/04_lipsync.md if this show has a talking host.")
    # An empty id fails HERE rather than one line into a paid render. See the
    # same guard in _session_template/identity.py.
    blank = sorted(r for r, v in VOICES.items() if not v)
    if blank:
        sys.exit(f"FAIL: role(s) {blank} in VOICES have no voice id.\n"
                 f"  `python audition.py` casts one; "
                 f"`python _probes/cast.py` searches\n  the shared library by "
                 f"demographic if you have no candidates yet.")
    if SESSION_NO:
        sys.exit("FAIL: the show is not a session -- SESSION_NO must stay 0, "
                 "or it will be counted as a film and the running order will "
                 "have a hole in it")
    if NAME.upper() != NAME:
        sys.exit(f"FAIL: NAME {NAME!r} must be uppercase -- it becomes a "
                 f"ComfyUI output folder and the clip resolvers are case "
                 f"sensitive on the prefix")


CLIPS = (os.path.join(season_paths.COMFY_OUTPUT, f"{NAME}_clips")
         if NAME else "")

check()

# THE CLIP FOLDER IS CLAIMED FOR THIS SEASON, not merely named. See
# season_identity.claim_clips() -- a NAME reused between seasons otherwise makes
# a new build read the old season's clips, coherently and silently.
season.claim_clips(CLIPS, f"{__name__}")

if __name__ == "__main__":
    # -h/--help prints the docstring -- the usage has always lived
    # there; this makes it reachable without opening the file
    # (finding 146). Before main(), so no lock is taken and no
    # argument guard fires first.
    import sys as _hsys
    if "-h" in _hsys.argv or "--help" in _hsys.argv:
        print(__doc__ or "(no usage doc)")
        raise SystemExit(0)
    print(f"  show     {NAME}  --  {TITLE!r}")
    print(f"  parts    1 cold open + {season.N_SESSIONS} interstitials")
    print(f"  tube     {TV or '(none)'}")
    print(f"  clips    {CLIPS}")
