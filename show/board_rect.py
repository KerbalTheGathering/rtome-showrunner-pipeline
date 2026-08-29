"""THIS SHOW'S board, measured. A configuration of ../surface.py, not a copy.

WHAT IS EDITORIAL AND WHAT IS MECHANICAL. Finding the largest flat area of a
given colour in a given part of a frame is mechanical and lives in
`../surface.py`, where a season that draws its type on a whiteboard, a
newspaper or a departures screen can use it too. WHICH colour and WHICH part of
the frame are facts about this show's set, and they live here.

    python board_rect.py            # measure, draw out/surface.png
    python board_rect.py --emit     # print the dict to paste into shot.py
    python board_rect.py 01 04      # just these segments

THE TWO SETTINGS BELOW ARE THE WHOLE FILE, and both were found by looking.

  * THE BOARD IS ALWAYS IN THE RIGHT HALF. Confirmed on all six by a coarse
    red-channel map, not assumed. Searching only x > 0.45 removes the
    presenter, the potted palm and most of the painted backdrop outright.
  * THE HINT IS `teal`, and the felt is found per plate as the commonest teal
    in that region rather than by a fixed threshold. A hard cut on red worked
    for four plates and failed on the two whose whole palette is darker --
    their painted SEA sits at R~85, below a threshold picked from the other
    four, so a darkness rule calibrated on some of the material swept the ocean
    up with the felt. I read that as "the board was already right-side, the
    flip broke it" and un-flipped two plates for no reason. The verification
    sheet showed it immediately.

    SAME ERROR AS THE PITCH METRIC, ONE DAY APART: a fixed threshold, validated
    on some of the material, applied to all of it. When six samples differ in
    overall level, thresholds have to be found PER SAMPLE.

AND THE SHEET IS THE POINT. It finds the SURFACE, not the USABLE AREA: on a real
reel the lower third of a correctly-detected board had a counter, a ledger and a
mug in front of it. `shot.TYPE_INSET_B` is what that costs, and it can only be
set by eye off the drawn frame.
"""
from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# THE SET, IN TWO NUMBERS. Change these when the set changes; do not change
# ../surface.py, which knows nothing about this show and should keep it that way.
HINT = "teal"
SEARCH_X = 0.45


def main() -> int:
    args = [sys.executable, os.path.join(ROOT, "surface.py"),
            os.path.basename(HERE), *sys.argv[1:],
            f"--hint={HINT}", f"--x-from={SEARCH_X}"]
    return subprocess.run(args, cwd=ROOT).returncode


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
