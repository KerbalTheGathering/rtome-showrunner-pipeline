"""Rank the cuts where the LOOK jumps — drift BETWEEN shots, not within one.

TWO SEASONS CLOSED WITH THE SAME LINE IN THEIR LOGS: clip-level QC corrects
colour drift *within* a clip and has nothing to say about drift *between* two
shots rendered weeks — or, now that films mix generation models by shot type,
minutes but models — apart. A film can pass every per-clip check and still
pulse at a join, because no check ever put adjacent shots side by side as
numbers.

THIS IS THE CHEAP TIER OF THAT CHECK, AND DELIBERATELY SO. Per beat, in cut
order: mean luma and mean saturation of the frame each cut lands on, then the
jump to the next beat, ranked against the film's own median jump. A film is
ALLOWED to jump — day into night, forge into starfield, that is editing — so
this is advisory by construction and exits 0 always. What it buys is an
ordering: "look here first" on the contact sheet, instead of "look at
everything". Metrics rank suspicion; the sheet decides. The failure mode it
must not have is the one whole-frame means always have — it cannot SEE a
local fault at all, and does not claim to; qc_clips.py's filmstrips are for
those.

CUT FRAMES, NOT FIRST FRAMES. The joint the eye sees is the LAST frame of
beat n against the FIRST frame of beat n+1, so that is the pair measured —
an i2v clip that walked its colour across its own length shows up here at
full size, where two first frames would agree perfectly.

    python qc_drift.py            # every join, ranked
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
import make_video

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_qc", "drift")

# A join whose jump exceeds this multiple of the film's median jump is worth
# an eye. Ranked output makes the exact number matter less than the order.
FLAG = 2.5


def grab(src: str, t: float, dst: str) -> str | None:
    if not os.path.exists(dst):
        subprocess.run([season_paths.ff("ffmpeg"), "-v", "error", "-y",
                        "-ss", f"{max(t, 0.0):.3f}", "-i", src,
                        "-frames:v", "1", dst], capture_output=True)
    return dst if os.path.exists(dst) else None


def stats(path: str) -> tuple[float, float]:
    im = Image.open(path).convert("RGB").resize((320, 180), Image.LANCZOS)
    a = np.asarray(im, dtype=np.float32)
    hsv = np.asarray(im.convert("HSV"), dtype=np.float32)
    return float(a.mean()), float(hsv[:, :, 1].mean())


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    rows = edit.table()
    ends = []
    for r in rows:
        sid = r["sid"]
        clip = make_video.clip(sid)
        head = grab(clip, r["ss"] + 0.1, os.path.join(OUT, f"{sid}_in.png"))
        tail = grab(clip, r["ss"] + r["beat"] - 0.15,
                    os.path.join(OUT, f"{sid}_out.png"))
        if not (head and tail):
            print(f"  {sid}: could not sample -- skipped")
            continue
        ends.append((sid, stats(head), stats(tail)))

    joins = []
    for (sa, _ia, oa), (sb, ib, _ob) in zip(ends, ends[1:]):
        dl, ds = abs(ib[0] - oa[0]), abs(ib[1] - oa[1])
        joins.append((sa, sb, dl, ds, dl + ds))
    if not joins:
        sys.exit("FAIL: fewer than two beats sampled -- nothing to rank")

    med = float(np.median([j[4] for j in joins])) or 1.0
    print(f"  {len(joins)} joins, median jump {med:.1f}  "
          f"(flagging over {FLAG:.1f}x median)\n")
    print(f"  {'join':>9} {'dLuma':>7} {'dSat':>7} {'x-med':>6}")
    for sa, sb, dl, ds, tot in sorted(joins, key=lambda j: -j[4]):
        x = tot / med
        print(f"  {sa:>4}->{sb:<4} {dl:>7.1f} {ds:>7.1f} {x:>6.2f}"
              + ("   <-- look here first" if x > FLAG else ""))
    print(f"\n  frames in {OUT} -- a flagged join may be an EDIT (day into "
          f"night is allowed);\n  the ranking says where to look, not what "
          f"is wrong. Advisory: exits 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
