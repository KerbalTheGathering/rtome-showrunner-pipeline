"""Which picture did the shipped segment actually come from?

`assemble.py --synced` reads the InfiniteTalk render. WITHOUT the flag it reads
the raw H3 clip -- the take whose mouth was never driven by the voice at all.
Both are the same plate, the same length and the same framing, so the two bakes
are indistinguishable in a frame grab and the flag is the entire difference
between a lip-synced segment and one that merely looks like one.

That is a silent failure mode, so it gets a measurement rather than a habit.

HOW. Per-frame motion energy -- the mean absolute difference between one frame
and the last -- is a signature of WHEN things move, and it survives the CRT
pass, the upscale and the type, none of which are temporal. Correlating the
shipped segment's signature against both candidates says which one it is, and
the margin says how sure.
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import os
import subprocess
import sys

import numpy as np

import shot

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "_work")
OUT = os.path.join(HERE, "out")
FF = season_paths.FFMPEG
CLIPS = os.path.join(season_paths.COMFY_OUTPUT, f"{shot.NAME}_clips")

GW, GH = 96, 72          # tiny: this is a timing signature, not a picture


def motion(path: str) -> np.ndarray:
    raw = subprocess.run(
        [season_paths.ff("ffmpeg"), "-v", "error", "-i", path,
         "-vf", f"scale={GW}:{GH},format=gray", "-f", "rawvideo", "-"],
        capture_output=True, check=True).stdout
    f = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
    f = f[:len(f) // (GW * GH) * (GW * GH)].reshape(-1, GH, GW)
    d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))
    return (d - d.mean()) / (d.std() + 1e-9)


def h3_clip(sid: str) -> str | None:
    got = sorted(f for f in os.listdir(CLIPS)
                 if f.startswith(f"s{sid}_") and f.endswith(".mp4")
                 and "rej" not in f
                 and os.path.getsize(os.path.join(CLIPS, f)) > 0)  # fault 124
    return os.path.join(CLIPS, got[-1]) if got else None


def main() -> int:
    print(f"  {'seg':>4} {'r vs synced':>12} {'r vs H3 raw':>12}  verdict")
    bad = []
    for sid in shot.CUT:
        ship = os.path.join(OUT, f"bounty_{sid}.mp4")
        syn = os.path.join(WORK, f"synced_{sid}.mp4")
        h3 = h3_clip(sid)
        if not (os.path.exists(ship) and os.path.exists(syn) and h3):
            print(f"  {sid:>4}  missing an input")
            continue
        a = motion(ship)
        rs, rh = [], []
        for cand, acc in ((syn, rs), (h3, rh)):
            b = motion(cand)
            n = min(len(a), len(b))
            # A few frames of slack: SHIFT moves 04 by three, and the H3 clip
            # is a different length from the render on some segments.
            best = max(float(np.corrcoef(a[k:n], b[:n - k])[0, 1])
                       for k in range(0, 6))
            acc.append(best)
        verdict = "SYNCED" if rs[0] > rh[0] else "H3 RAW  <-- NOT LIP SYNCED"
        if rs[0] <= rh[0]:
            bad.append(sid)
        print(f"  {sid:>4} {rs[0]:>12.3f} {rh[0]:>12.3f}  {verdict}")
    if bad:
        # fault 129: the old advice said `assemble.py --synced`, a flag the
        # assembler announces it ignores -- synced_XX.mp4 on disk IS the
        # picture by default, so a bake from the H3 take means the synced
        # render is missing or was bypassed with --raw.
        print(f"\n  FAIL: {', '.join(bad)} were baked from the H3 take.\n"
              f"  synced_XX.mp4 is the default picture when it exists -- run "
              f"italk.py for these\n  segments if the render is missing, then "
              f"rebuild: python assemble.py {' '.join(bad)}")
        return 1
    print("\n  all six came from the InfiniteTalk render")
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
