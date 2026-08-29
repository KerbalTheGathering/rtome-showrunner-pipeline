"""Measure how open the announcer's mouth is, and pick a closed-mouth anchor.

WHY THIS EXISTS. italk.py's plate() takes frame START_FRAME[sid] of the clean
bake as the first frame of the generated segment, and its own comment says the
anchor's mouth becomes the segment's opening mouth. Only "02" ever got a value,
so segments 01, 04 and 05 open on a mouth that is already hanging open over the
lead-in silence -- 01 for the whole 0.40s before he says a word.

THE MEASUREMENT, AND WHY IT IS NOT THE OLD ONE. An earlier pass used the dark
pixel fraction inside a mouth box and it read flat, because the box contained a
large permanently dark moustache and the metric was measuring that. This uses
the 106-point landmark model instead: the mouth points spread vertically when
the jaw drops, which is the thing itself rather than a stand-in for it.

AND IT IS NOT BELIEVED UNTIL IT AGREES WITH THE EYES. `--check` scores frames
that have already been LOOKED at -- known open, known shut -- and refuses to
report a separation it cannot demonstrate. A proxy validated only against its
own aggregate is how the last one passed while being wrong.

    python mouth_open.py --check         # prove the metric on seen frames
    python mouth_open.py --pick 01 04 05 # best closed-mouth anchor per segment
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shot  # noqa: E402  -- which segments this reel actually has

HERE = os.path.dirname(os.path.abspath(__file__))
FF = season_paths.FFMPEG
WORK = os.path.join(HERE, "_work")
OUT = os.path.join(HERE, "out")
FONT = season_paths.font("arialbd.ttf")

# THE MEASUREMENT LIVES AT THE SEASON ROOT NOW (../mouth.py, fault 149):
# a film tree's mouth_scan.py needs it and a SHOW = False season has no
# show/ folder to find it in. What stays here is the show-specific work --
# the ground-truth --check gate and the anchor picking, which read THIS
# tree's clips and shot.py. The names are re-exported so this module's
# consumers (it_articulate.py) keep working unchanged.
from mouth import MOUTH, app, size_of, head, grab, openness  # noqa: F401,E402

SEARCH = 60                     # anchor must sit inside the lead-in, not later

# Frames already LOOKED at, in it_sync_mouths.png and it_open_strip.png.
# (clip, frame, "open" | "shut")
SEEN = [
    ("synced_01.mp4", 0, "open"), ("synced_01.mp4", 96, "shut"),
    ("synced_01.mp4", 43, "open"),
    ("synced_02.mp4", 0, "shut"), ("synced_02.mp4", 103, "shut"),
    ("synced_03.mp4", 0, "shut"), ("synced_03.mp4", 244, "open"),
    ("synced_04.mp4", 0, "open"), ("synced_04.mp4", 82, "shut"),
    ("synced_05.mp4", 0, "open"), ("synced_05.mp4", 48, "open"),
    ("synced_05.mp4", 69, "shut"), ("synced_05.mp4", 262, "shut"),
    ("synced_06.mp4", 0, "shut"), ("synced_06.mp4", 27, "open"),
]


def check() -> int:
    rows = []
    for clip, i, label in SEEN:
        v = openness(grab(os.path.join(WORK, clip), i))
        rows.append((clip, i, label, v))
        print(f"  {clip:>16} f{i:<5d} {label:>5}  {v if v is None else f'{v:.4f}'}")
    op = [v for _, _, l, v in rows if l == "open" and v is not None]
    sh = [v for _, _, l, v in rows if l == "shut" and v is not None]
    if not op or not sh:
        sys.exit("FAIL: no usable scores")
    print(f"\n  POOLED across segments:  open min {min(op):.4f}   "
          f"shut max {max(sh):.4f}")
    if min(op) <= max(sh):
        print("  OVERLAPS -- there is NO absolute open/shut threshold. The "
              "score depends on\n  how big the face is in that segment's "
              "framing, so it is not comparable\n  between segments and must "
              "never be thresholded.")

    # THE PROPERTY ACTUALLY RELIED ON. Picking an anchor only ever compares
    # frames of ONE clip against each other, so within-clip ranking is the
    # thing that has to hold -- and it is a different claim from the pooled one.
    print("\n  WITHIN each segment (the comparison an anchor pick actually makes):")
    ok = True
    for clip in sorted({c for c, _, _, _ in rows}):
        o = [v for c, _, l, v in rows if c == clip and l == "open" and v]
        s = [v for c, _, l, v in rows if c == clip and l == "shut" and v]
        if not o or not s:
            print(f"  {clip:>16}  only {'open' if o else 'shut'} samples -- "
                  f"not a test")
            continue
        good = min(o) > max(s)
        ok &= good
        print(f"  {clip:>16}  shut<={max(s):.4f}  open>={min(o):.4f}  "
              f"{'SEPARATED' if good else 'OVERLAP'}")
    if ok:
        print("\n  Every segment separates. The metric may be used to RANK "
              "frames of one clip,\n  and for nothing else.")
        return 0
    print("\n  -> DO NOT trust this metric; the frames must be picked by eye.")
    return 1


def pick(sids: list[str]) -> int:
    CW, CH = 150, 118
    f = ImageFont.truetype(FONT, 14)
    fb = ImageFont.truetype(FONT, 17)
    out = Image.new("RGB", (30 + 8 * (CW + 6), len(sids) * (CH + 52) + 10),
                    (16, 16, 18))
    d = ImageDraw.Draw(out)
    best = {}
    for j, sid in enumerate(sids):
        src = os.path.join(WORK, f"clean_{sid}.mp4")
        ims = head(src, SEARCH)
        sc = []
        for i, im in enumerate(ims):
            v = openness(im)
            if v is not None:
                sc.append((v, i))
        if not sc:
            sys.exit(f"FAIL: no face in {src}")
        sc.sort()
        best[sid] = sc[0][1]
        print(f"  {sid}  best f{sc[0][1]} ({sc[0][0]:.4f})   "
              f"next: {', '.join(f'f{i}({v:.3f})' for v, i in sc[1:6])}")
        y = 10 + j * (CH + 52)
        d.text((12, y), f"segment {sid}  -> anchor frame {sc[0][1]}  "
                        f"(openness {sc[0][0]:.4f}); shown: 8 most closed",
               font=fb, fill=(235, 232, 226))
        fs = app().get(ims[sc[0][1]])
        bb = max(fs, key=lambda x: (x.bbox[2] - x.bbox[0]) *
                 (x.bbox[3] - x.bbox[1])).bbox
        for c, (v, i) in enumerate(sc[:8]):
            im = Image.fromarray(ims[i][:, :, ::-1], "RGB")
            fh = bb[3] - bb[1]
            im = im.crop((int(bb[0]), int(bb[1] + 0.52 * fh),
                          int(bb[2]), int(bb[3] + 0.06 * fh)))
            px = 30 + c * (CW + 6)
            out.paste(im.resize((CW, CH), Image.LANCZOS), (px, y + 24))
            col = (110, 220, 130) if c == 0 else (150, 150, 160)
            ImageDraw.Draw(out).rectangle(
                [px, y + 24, px + CW - 1, y + 24 + CH - 1], outline=col, width=2)
            d.text((px + 2, y + 24 + CH + 2), f"f{i}  {v:.4f}", font=f, fill=col)
    p = os.path.join(OUT, "mouth_anchor.png")
    out.save(p)
    print(f"\n  -> {p}")
    print("  START_FRAME = " + repr(best))
    return 0


def main() -> int:
    if "--check" in sys.argv:
        return check()
    sids = [a for a in sys.argv[1:] if not a.startswith("-")]
    bad = [s for s in sids if s not in shot.CUT]
    if bad:
        sys.exit(f"FAIL: {bad} are not segments of this reel ({list(shot.CUT)})")
    if "--pick" in sys.argv:
        # EVERY SEGMENT BY DEFAULT, FROM shot.CUT. This defaulted to
        # `["01", "04", "05"]` -- the three segments that happened to need an
        # anchor on ANOTHER reel. In a tree with different segments that is two
        # ids which do not exist and one which does, so it measured a third of
        # the reel, printed a START_FRAME dict covering a third of the reel,
        # and reported success. The unmeasured segments then anchor on frame 0,
        # which is the defect the anchor exists to remove.
        return pick(sids or list(shot.CUT))
    print(__doc__)
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
