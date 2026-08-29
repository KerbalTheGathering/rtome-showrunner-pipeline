"""Prove the delivered film IS the cut — every beat opens on its own clip.

LENGTH IS THE CHECK THAT CANNOT FAIL INTERESTINGLY. A film with two shots
transposed is exactly the right length; so is a film whose every beat baked
from one clip repeated; so is a rebuild that quietly resolved a beat to last
season's clip folder. verify.py measures the devices and the mix, contract.py
proves the tables agree — and until this file, nothing asked whether the
picture at beat 07's timecode is beat 07's picture. Two forks shipped that
class of fault past every green check they had.

THE METHOD, AND WHY THERE IS A CONTROL. For every beat: pull the frame the
finished mp4 shows just after that beat's cut, pull the frame its clip shows
at the same offset past its in-point, and compare. Alone that proves nothing —
a comparison with no failure mode is a vacuous check, and this repo has
written enough of those to know. So every beat is ALSO compared against a
clip from the far side of the cut, and the right clip must beat the wrong one
by a margin. On the fork that proved this design, honest matches scored
1.2–4.9 and wrong clips 20.9–80.8; the gap is the evidence the test can fail.

TIMESTAMPS ARE DERIVED FROM THE SAME EDIT TABLE THE FILM WAS CUT FROM — the
boundary of beat i is the cumulative frame count of the beats before it, the
same arithmetic the bake uses, so this cannot drift out of step with the cut.
The sample lands past the incoming transition's reach, not on the boundary
itself, because a device mid-fire matches nothing honestly.

WHAT A FAILURE MEANS. Not always a transposition: the comparison centre-crops
the clip to the delivery aspect, which is the default fit. A film using `pad`
or a strongly anchored crop will score worse and may need MARGIN loosened —
look at the two frames it names before believing either verdict. The check
ranks; the eye decides. A film that passes here has its cut confirmed at
every one of its joins.

    python verify_cut.py            # every beat
    python verify_cut.py 07 12      # just these
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import os
import subprocess
import sys

import numpy as np
from PIL import Image

import edit
import identity
import make_video
import shot

HERE = os.path.dirname(os.path.abspath(__file__))
MP4 = os.path.join(HERE, "out", f"{shot.SLUG}.mp4")
OUT = os.path.join(HERE, "_verify", "cut")
FPS = float(identity.season.FPS)

# How far past the cut to sample. At least clear of the incoming device, at
# most a third of the beat, never less than a third of a second.
MIN_INTO = 0.35
# The right clip must beat the wrong one by this much. Fork-proven at 1.25;
# loosen (with a note in the season's log) only for a pad/anchored fit.
MARGIN = 1.25
CELL = (320, 180)


def grab(src: str, t: float, dst: str) -> str | None:
    # ALWAYS EXTRACTED FRESH. This cached on os.path.exists once, so a
    # re-shot beat was verified against frames pulled from the PREVIOUS
    # bake -- the verifier confirming a film that no longer existed (fault
    # 102). A stale-mtime check would still miss a retimed edit table over
    # unchanged clips; a frame per beat costs tenths of a second and a
    # check must measure what is on disk NOW. The PNG stays for the eye.
    if os.path.exists(dst):
        os.remove(dst)
    subprocess.run([season_paths.ff("ffmpeg"), "-v", "error", "-y",
                    "-ss", f"{max(t, 0.0):.3f}", "-i", src,
                    "-frames:v", "1", dst], capture_output=True)
    return dst if os.path.exists(dst) else None


def arr(path: str, aspect: float) -> np.ndarray:
    """Centre-crop to the delivery aspect, then down to one comparison size."""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    if w / h > aspect + 1e-3:                 # too wide -- crop the sides
        cw = int(h * aspect)
        im = im.crop(((w - cw) // 2, 0, (w + cw) // 2, h))
    elif w / h < aspect - 1e-3:               # too tall -- crop top and bottom
        ch = int(w / aspect)
        im = im.crop((0, (h - ch) // 2, w, (h + ch) // 2))
    return np.asarray(im.resize(CELL, Image.LANCZOS), dtype=np.float32)


def main() -> int:
    if not os.path.exists(MP4):
        sys.exit(f"FAIL: no film at {MP4} -- run assemble.py first")
    os.makedirs(OUT, exist_ok=True)
    rows = edit.table()
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    aspect = identity.season.W / identity.season.H

    # The boundary of beat i, in frames, by the bake's own arithmetic.
    bounds, t = [], 0
    for r in rows:
        bounds.append(t)
        t += round(r["beat"] * FPS)

    ok, bad = 0, []
    n = len(rows)
    for i, r in enumerate(rows):
        sid = r["sid"]
        if only and sid not in only:
            continue
        prev_trans = rows[i - 1]["trans"] if i else 0.0
        into = min(r["beat"] / 3.0, max(MIN_INTO, prev_trans + 0.1))

        f_film = grab(MP4, bounds[i] / FPS + into,
                      os.path.join(OUT, f"film_{sid}.png"))
        f_right = grab(make_video.clip(sid), r["ss"] + into,
                       os.path.join(OUT, f"clip_{sid}.png"))
        # The control, from the far side of the running order so a
        # neighbouring shot of the same location cannot flatter the test.
        w = rows[(i + n // 2) % n]
        f_wrong = grab(make_video.clip(w["sid"]), w["ss"] + 0.3,
                       os.path.join(OUT, f"clip_{w['sid']}_ctl.png"))
        if not (f_film and f_right and f_wrong):
            bad.append((sid, "frame extraction failed", 0.0, 0.0))
            continue

        a = arr(f_film, aspect)
        d_right = float(np.abs(a - arr(f_right, aspect)).mean())
        d_wrong = float(np.abs(a - arr(f_wrong, aspect)).mean())
        if d_right * MARGIN < d_wrong:
            ok += 1
        else:
            bad.append((sid, f"vs own clip {d_right:.1f}, vs {w['sid']} "
                             f"{d_wrong:.1f}", d_right, d_wrong))

    print(f"  {ok}/{ok + len(bad)} cuts open on their own clip")
    if bad:
        print(f"  !! {len(bad)} did not -- LOOK at the frames in {OUT} "
              f"before believing either verdict:")
        for sid, why, _, _ in bad:
            print(f"     beat {sid}: {why}")
        return 1
    print("  and every one was further from a clip it should not match -- "
          "the control is what\n  makes this a check rather than a claim.")
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
