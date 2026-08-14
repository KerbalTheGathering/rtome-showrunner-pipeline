"""DE-RISK THE HOST BEFORE WRITING SIX SEGMENTS. Free, local, ~40s each.

THE PRODUCTION ORDER SAYS THIS COMES FIRST and it has paid for itself in every
session that obeyed it. Four questions, in the order that would hurt most:

  flat   Does the flat television light survive the STYLE LORA? A painterly one is
         trained on dramatic painted work and every other session in the season
         asks it for deep black shadow. If it drags this back to chiaroscuro the
         interstitial reads as a seventh scene rather than an interruption, and
         the whole format is wrong. THIS IS THE ONE THAT MATTERS.

  blank  Does the display board stay empty? The type is drawn in post over that
         board. If the model insists on filling it with garbage lettering there
         is nowhere to put the bounty and the set has to be redesigned.

  seed   Does the same man come back at a different seed? There is NO character
         LoRA here -- his identity is carried entirely by the words. Six plates
         need to look like six shots of one presenter.

  mood   Does he survive being deflated? Segment six has no bounty to announce
         and he has to play that. If the mood swing fetches a different man the
         sixth slot needs a different solution.

    python hosttest.py            # all four
    python hosttest.py flat seed  # named probes only

A PASSING VARIANT IS ONE SAMPLE, NOT A LAW -- preflight rule 32, and #4's two
headline conclusions were both seed-specific. What this buys is the right to
start writing, not certainty.
"""
from __future__ import annotations

import os as _os, sys as _sys
# THREE DIRNAMES REACH THE SEASON ROOT FROM HERE, TWO ONLY REACH show/. This
# preamble was copied verbatim from show/*.py, which lives one level higher --
# so `import season_paths` failed outright and every probe in this folder was
# unrunnable. Nothing noticed, because nothing in this repo imported them.
_here = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:0] = [_os.path.dirname(_here),                     # show/ -- edit, script
                 _os.path.dirname(_os.path.dirname(_here))]   # the season root
import season_paths                                                # noqa: E402


import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_still  # noqa: E402
import shot       # noqa: E402

BASE = shot._STYLE + shot._NOTEXT + shot._FRAME + shot._SET + shot._HOST

PROBES = {
    # The reference. Hands doing something specific, because an unoccupied hand
    # rises -- the oldest rule in this project and it applies to a still too.
    "flat": (BASE + "He is mid-sentence with his mouth open, leaning forward "
             "over the desk with both forearms resting on it and one hand "
             "turned palm-up toward the camera.", shot.SEED),

    # Same words, different draw. Identity is carried by the block alone.
    "seed": (BASE + "He is mid-sentence with his mouth open, leaning forward "
             "over the desk with both forearms resting on it and one hand "
             "turned palm-up toward the camera.", 884102),

    # The board is the thing the type lands on. Pushed to the front of the
    # description and given more of the frame, to find out whether asking for
    # more of it is what makes the model want to write on it.
    "blank": (shot._STYLE + shot._NOTEXT +
              "Medium shot from straight on at desk height. A large display "
              "board stands on a wooden easel beside the presenter, taking up "
              "the right half of the frame, its face completely blank, empty "
              "and unmarked. " + shot._SET + shot._HOST +
              "He stands beside the board with one hand held flat against the "
              "bottom corner of it and the other at his side.", shot.SEED),

    # Segment six. Same man, nothing to sell.
    "mood": (BASE + "He sits back from the desk with both hands flat on it, his "
             "mouth closed and his shoulders dropped, looking straight down the "
             "camera with nothing to say and a small apologetic set to his face.",
             shot.SEED),
}


def main() -> int:
    want = [a for a in sys.argv[1:] if not a.startswith("-")] or list(PROBES)
    bad = [w for w in want if w not in PROBES]
    if bad:
        sys.exit(f"FAIL: no probe(s) {bad} -- have {sorted(PROBES)}")

    print(f"  {len(want)} probe(s), local, $0.00 -> "
          + os.path.join(season_paths.COMFY_OUTPUT, shot.NAME))
    rc = 0
    for name in want:
        prompt, seed = PROBES[name]
        rc |= gen_still.render(f"t_{name}", prompt, f"probe: {name}", seed)
    return rc


if __name__ == "__main__":
    sys.exit(main())
