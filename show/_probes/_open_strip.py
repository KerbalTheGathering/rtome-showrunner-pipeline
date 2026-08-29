"""The first ten frames of every synced segment, cropped to the mouth.

The standing test on this stack: at TRUE SILENCE the mouth must be closed, and
the eyes decide that, not a metric. The red frames are the ones before the
first word -- every one of them should be a closed mouth, and any that is not
is the anchor's fault (see italk.START_FRAME).

    python _open_strip.py

WHY IT HAS A main() AT ALL. It used to do the whole job at module level with no
`if __name__` guard, which meant importing it -- to check it still runs, to
read a constant out of it, anything -- shelled out to ffmpeg sixty times. That
made it the one file in the repo smoke.py had to refuse to look at.
"""
from __future__ import annotations

import os as _os, sys as _sys
_here = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:0] = [_os.path.dirname(_here),                     # show/ -- edit, script
                 _os.path.dirname(_os.path.dirname(_here))]   # the season root
import season_paths  # noqa: E402

import os          # noqa: E402
import subprocess  # noqa: E402
import sys         # noqa: E402

import numpy as np                                   # noqa: E402
from PIL import Image, ImageDraw, ImageFont          # noqa: E402

import edit        # noqa: E402
import it_sync     # noqa: E402
import script      # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
W = os.path.join(HERE, "_work")
OUT = os.path.join(os.path.dirname(HERE), "out")      # the SHOW tree's, not _probes' (fault 122)
CW, CH = 150, 120
N = 10


def main() -> int:
    f = ImageFont.truetype(season_paths.font("arialbd.ttf"), 14)
    fb = ImageFont.truetype(season_paths.font("arialbd.ttf"), 17)
    sids = list(script.SIDS)
    out = Image.new("RGB", (30 + N * (CW + 6), len(sids) * (CH + 52) + 10),
                    (16, 16, 18))
    d = ImageDraw.Draw(out)
    for j, sid in enumerate(sids):
        p = os.path.join(W, f"synced_{sid}.mp4")
        w, h = it_sync.size_of(p)
        sw = 480
        sh = int(round(480 * h / w))
        mb, _ub, _face = it_sync.boxes(p, sw, sh)
        lead = edit.offsets(sid)[0][1]
        y = 10 + j * (CH + 52)
        d.text((12, y), f"segment {sid}   first speech at {lead:.2f}s = frame "
                        f"{round(lead * 24)}   (frames 0-{N - 1} must be a "
                        f"CLOSED mouth)", font=fb, fill=(235, 232, 226))
        for i in range(N):
            # `\,` INSIDE AN f-STRING IS AN INVALID PYTHON ESCAPE, not an
            # ffmpeg one -- the comma has to reach ffmpeg escaped and Python
            # has to be told the backslash is literal. It was an unraw
            # f-string, which is a SyntaxWarning today and an error later.
            raw = subprocess.run(
                [season_paths.ff("ffmpeg"), "-v", "error", "-i", p,
                 "-vf", rf"select=eq(n\,{i}),scale={sw}:{sh}",
                 "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                capture_output=True, check=True).stdout
            im = (Image.fromarray(np.frombuffer(raw, np.uint8)
                                  .reshape(sh, sw, 3), "RGB")
                  .crop(mb).resize((CW, CH), Image.LANCZOS))
            px = 30 + i * (CW + 6)
            out.paste(im, (px, y + 24))
            col = (255, 90, 70) if i < round(lead * 24) else (110, 220, 130)
            ImageDraw.Draw(out).rectangle(
                [px, y + 24, px + CW - 1, y + 24 + CH - 1], outline=col,
                width=2)
            d.text((px + 2, y + 24 + CH + 2), f"f{i}  {i / 24:.2f}s",
                   font=f, fill=col)
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, "it_open_strip.png")
    out.save(dst)
    print("->", dst)
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
