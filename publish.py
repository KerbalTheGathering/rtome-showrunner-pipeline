"""Put the finished season where the user actually watches it.

WAS DONE BY HAND THE FIRST TIME and that is why this exists: the season now has
a reason to be rebuilt (a change to the tube, a re-shot segment, a re-cut film)
and every rebuild has to land in the same three places with the same names, or
the delivery folder quietly accumulates two versions of one film.

    <DELIVER>/<SEASON_FOLDER>/<SEASON_SLUG>.mp4          the feature
    <DELIVER>/<SEASON_FOLDER>/<SEASON_SLUG>_share.mp4    720x540
    <DELIVER>/<EXTRA>/<SEASON_SLUG>_540p.mp4             the optional extra copy

  Every one of those names comes out of season_identity.py. Nothing here is
  typed, because this file is copied along with everything else.

THE SHARE CUT IS A LANCZOS DOWNSCALE AND THAT MATTERS MORE THAN IT USED TO. The
interstitials now carry a 2.25-pixel scanline, which is 0.44 cycles per pixel --
far above what survives a halving. A naive scaler folds it back as moire that
crawls over the presenter's jacket; lanczos lowpasses first, so the share cut
simply looks like a smaller television. Checked, not assumed: qc pulls a frame.

    python publish.py             # verify, build the share cut, copy
    python publish.py --check     # say what it would do, touch nothing
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import season_paths                                                # noqa: E402


import os
import shutil
import subprocess
import sys

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import season_identity as season                                   # noqa: E402

import feature

FF = season_paths.FFMPEG
HERE = os.path.dirname(os.path.abspath(__file__))
# WHERE THE FEATURE IS IS feature.py'S FACT, NOT A SECOND COPY OF IT. This read
# `os.path.join(HERE, "out")`, which was the same directory only for as long as
# both files sat in `show/`. Deriving it means moving the join once moves the
# publisher with it -- and if it ever moves again, this cannot be left behind
# pointing at an empty folder and reporting the feature missing.
OUT = feature.OUT

ONE = season.DELIVER
SEASON_DIR = season.folder()
MEMES = os.path.join(ONE, season.EXTRA) if season.EXTRA else ""

FEATURE = os.path.join(OUT, f"{season.SEASON_SLUG}.mp4")
SHARE = os.path.join(OUT, f"{season.SEASON_SLUG}_share.mp4")
# The cold open comes out of the discovered running order like everything
# else, so a season without one simply has nothing to copy.
COLD = next((mp4 for label, mp4, _wav in feature.parts.running_order()
             if label == "COLD OPEN"), None)

# SHARE_H WAS TYPED AS 540, AND IT WAS 4:3 FOR EXACTLY ONE SEASON.
#
# The comment here used to read "matched to what shipped, probed off the
# published file rather than guessed" -- which was true, and also the whole
# problem: it was probed off the REFERENCE season, which delivered 4:3, and
# then carried as a literal into every season cloned from the template
# afterward. A 16:9 season squashed its share cut to 4:3 silently -- ffmpeg's
# `scale` filter does not refuse a wrong aspect, it just produces a
# distorted picture, and nothing downstream compares it against the source.
#
# SHARE_H IS NOW DERIVED FROM THE SEASON'S OWN ASPECT, the same rule as
# everywhere else in this repo: a fact about this season is read from
# season_identity, never retyped. Snapped to even because yuv420p needs an
# even height.
SHARE_W = 720
SHARE_H = round(SHARE_W * season.H / season.W / 2) * 2


def main() -> int:
    check = "--check" in sys.argv
    for p in [x for x in (FEATURE, COLD) if x]:
        if not os.path.exists(p):
            sys.exit(f"FAIL: {p} missing -- run feature.py")

    print(f"  feature   {os.path.getsize(FEATURE)/1e6:>8.1f} MB  {FEATURE}")
    if check:
        print("\n  --check: would build the share cut and copy to")
        # `if d` -- MEMES is "" on a season with no EXTRA folder, and printing
        # it listed a blank line as a destination. That blank line was the only
        # warning anybody got before the real run fell over on it.
        for d in [x for x in (SEASON_DIR, MEMES) if x]:
            print(f"    {d}")
        return 0

    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                    "-i", FEATURE,
                    "-vf", f"scale={SHARE_W}:{SHARE_H}:flags=lanczos",
                    "-c:v", "libx264", "-crf", "23", "-preset", "slow",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", SHARE], check=True)
    print(f"  share     {os.path.getsize(SHARE)/1e6:>8.1f} MB  {SHARE_W}x{SHARE_H}")

    # THE SECOND COPY IS OPTIONAL AND USED NOT TO BE.
    #
    # season_identity.EXTRA is documented as "a second folder every render is
    # copied to, or ''", and this read `os.makedirs(MEMES)` unconditionally.
    # On any season that left it blank -- which is the default, and what the
    # comment invites -- MEMES is "" and os.makedirs("") raises WinError 3
    # AFTER the share cut has been encoded. So publish.py did all of its work,
    # printed both sizes, and then died on the last step of the last script in
    # the pipeline, on a value the season was explicitly allowed to leave
    # empty.
    #
    # Found by the first season that had no EXTRA folder, which is to say the
    # first season that took the default.
    os.makedirs(SEASON_DIR, exist_ok=True)
    drops = [(FEATURE, os.path.join(SEASON_DIR, os.path.basename(FEATURE))),
             (SHARE, os.path.join(SEASON_DIR, os.path.basename(SHARE))),
             *([(COLD, os.path.join(SEASON_DIR, "cold_open.mp4"))] if COLD else [])]
    if MEMES:
        os.makedirs(MEMES, exist_ok=True)
        drops.append((SHARE,
                      os.path.join(MEMES, f"{season.SEASON_SLUG}_540p.mp4")))
    for src, dst in drops:
        shutil.copy2(src, dst)
        print(f"  -> {dst}")
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
