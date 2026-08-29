"""Sample the FINISHED season file at every junction, not the parts.

A concat demuxer given twelve matching parts still has to be checked at the
seams, because the failure mode is not a crash -- it is a part that starts one
frame late, or an audio stream that drifts, or a segment that simply is not
where the running order says it is. Reading the parts proves the parts; reading
the OUTPUT proves the film.

Samples each interstitial mid-way (so the type is up) and the first second of
each film, and labels every cell with where it should be.

    python qc_feature.py
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_identity as season                                   # noqa: E402


import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import os
import subprocess
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feature  # noqa: E402
import parts    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
# DERIVED, for the same reason publish.py derives it: the feature moved to the
# season root and a checker looking in the old folder does not fail, it reports
# the feature missing and tells you to build the thing you already built.
OUT = feature.OUT
FF = feature.FF
SEASON = os.path.join(OUT, f"{season.SEASON_SLUG}.mp4")


def grab(t: float, dst: str) -> str:
    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                    "-ss", f"{t:.3f}", "-i", SEASON, "-frames:v", "1", dst],
                   check=True)
    return dst


def main() -> int:
    if not os.path.exists(SEASON):
        sys.exit("FAIL: build it with feature.py first")

    # THE RUNNING ORDER COMES FROM parts.py, WHICH IS WHERE IT LIVES.
    #
    # This loop used to read `feature.SEASON` and `feature.KREA` -- two names
    # feature.py has not had since it started reading parts.running_order().
    # So the one tool that looks at the DELIVERED file raised AttributeError
    # the first time anybody ran it, and a checker that cannot run has never
    # disagreed with anything. It is also why it kept its own second copy of
    # the running order in the first place: the same fact in two files.
    #
    # SAMPLED AT A FRACTION OF EACH PART, not at typed offsets. A short part
    # and a long one both get looked at three-quarters of the way in (where an
    # interstitial has its type fully up) and just after the join.
    marks, t = [], 0.0
    for label, mp4, _wav in parts.running_order():
        if not os.path.exists(mp4):
            sys.exit(f"FAIL: {label} is not built ({mp4}) -- but the season "
                     f"file is. It was joined from something else.")
        d = feature.probe(mp4)["secs"]
        marks.append((label, t + d * 0.75))
        if t:
            marks.append((f"into {label}", t + 0.9))
        t += d

    got = feature.probe(SEASON)["secs"]
    if abs(got - t) > 0.5:
        print(f"  !! the parts add up to {t:.2f}s but the season file is "
              f"{got:.2f}s -- every mark below is off by up to "
              f"{abs(got - t):.2f}s and the join is what to look at first")

    cells = []
    for i, (lab, at) in enumerate(marks):
        p = grab(at, os.path.join(OUT, f"_fq{i:02d}.png"))
        cells.append((f"{lab}   @{at:.1f}s", Image.open(p).convert("RGB")))

    cw = 640
    ch = round(cw * cells[0][1].size[1] / cells[0][1].size[0])
    cols = 4
    rows = (len(cells) + cols - 1) // cols
    sheet = Image.new("RGB", (cw * cols, (ch + 18) * rows), "black")
    d = ImageDraw.Draw(sheet)
    for i, (lab, im) in enumerate(cells):
        x, y = (i % cols) * cw, (i // cols) * (ch + 18)
        sheet.paste(im.resize((cw, ch), Image.LANCZOS), (x, y + 18))
        d.text((x + 5, y + 4), lab, fill="#ffdd99")
    dst = os.path.join(OUT, "qc_feature.png")
    sheet.save(dst)
    for f in os.listdir(OUT):
        if f.startswith("_fq"):
            os.remove(os.path.join(OUT, f))
    print(f"  {len(cells)} junctions -> {dst}  ({sheet.size[0]}x{sheet.size[1]})")
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
