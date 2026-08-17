"""Shot lengths for the cold open. Typed, because there is no voice to derive from.

Every other tree in this season sizes its clips off measured VO. There is no VO
here -- that is the point of the cold open -- so these are editorial choices and
nothing else. They are stated once, here, and everything downstream reads them.

WHY THESE THREE NUMBERS. The first shot has to be long enough to stop feeling
like a title background and start feeling like a place: nine seconds is about
where an audience stops waiting and starts looking. The second is the longest
because it is the only one with anybody in it. The third is the shortest and
should feel a beat too short -- the water closes, and the film moves on before
you are finished with it.
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402

import identity                                                    # noqa: E402
import shot                                                        # noqa: E402

# THE SEASON'S RATE, DERIVED. `24` was typed in eleven files beside a
# season_identity.FPS that already said so -- and feature.py asserts every
# part matches, so a season at another rate would have been caught only
# after every part was baked.
FPS = identity.season.FPS

# The title card, drawn in assemble.py over the last shot's final frame.
TITLE_HOLD = 4.0


def grid(seconds: float) -> int:
    """H3's 17k+5 frame grid at 24fps, always UP."""
    n = max(5, round(seconds * FPS))
    return n + (5 - (n % 17)) % 17


FRAMES = {sid: grid(shot.SECS[sid]) for sid in shot.CUT}
SECS = {sid: FRAMES[sid] / FPS for sid in shot.CUT}

# THERE IS NO RUN-UP HERE, AND THAT IS A DECISION. `_session_template/edit.py`
# carries RUNUP -- shoot a beat longer and discard the opening, because a model
# conditioned on a still opens at ~0.3 of its own peak movement. Two reasons it
# is not in this tree: a cold open has no in-point at all (assemble.py explodes
# from frame zero, so buying a run-up would need the machinery as well as the
# number), and a cold open's shots are the ones that START something -- the
# ramp out of the still is the shot, not a fault in it. A cold open that has to
# cut into mid-action wants both, and should copy the film tree's version
# rather than inventing a second one.

# WHAT EACH SHOT WILL COST THE CARD, AT THE CANVAS IT WILL ACTUALLY GET.
#
# This computed `FRAMES * 128 * 96` -- 1024x768, typed as two magic numbers --
# and asserted against a 3.7M ceiling that the measurements in
# season_paths.BUDGET_M say had already thrashed twice, once for 33 minutes. So
# it was a check with the wrong number, against a canvas h3_shoot.py no longer
# necessarily uses: it picks per clip now, off the same budget.
#
# Both come from season_paths, which is the one file that knows about the card.
CANVAS = {sid: season_paths.pick_canvas(FRAMES[sid], identity.season.W,
                                        identity.season.H)
          for sid in shot.CUT}
TOKENS = {sid: season_paths.latent_m(FRAMES[sid], CANVAS[sid]) * 1e6
          for sid in shot.CUT}

for _sid, _t in TOKENS.items():
    assert _t / 1e6 <= season_paths.BUDGET_M, (
        f"shot {_sid} is {FRAMES[_sid]}f at {CANVAS[_sid][0]}x{CANVAS[_sid][1]}"
        f" = {_t/1e6:.2f}M latent tokens, past the {season_paths.BUDGET_M:.2f}M "
        f"budget even on the smallest canvas this aspect offers. Shorten it in "
        f"shot.SECS, or raise SEASON_LATENT_BUDGET_M if this card is bigger "
        f"than the one that was measured.")


def main() -> int:
    print(f"  {'shot':>5} {'asked':>7} {'frames':>7} {'clip':>7} "
          f"{'canvas':>10} {'tokens':>8}")
    for sid in shot.CUT:
        print(f"  {sid:>5} {shot.SECS[sid]:>7.1f} {FRAMES[sid]:>7} "
              f"{SECS[sid]:>7.2f} "
              f"{CANVAS[sid][0]:>5}x{CANVAS[sid][1]:<4} "
              f"{TOKENS[sid]/1e6:>7.2f}M")
    tot = sum(SECS.values())
    print(f"\n  {tot:.2f}s of picture + {TITLE_HOLD:.1f}s title = "
          f"{tot + TITLE_HOLD:.2f}s cold open")
    print(f"  {sum(FRAMES.values())} frames to shoot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
