"""A filmstrip per bought clip, on a sheet, so the session is QC'd as a session.

WHY A SHEET AND NOT FIFTEEN PLAYBACKS. What goes wrong in an i2v buy is mostly
INVENTED CONTENT -- an animal, a boat, a figure that the plate never had and the
prompt never asked for -- and that is spotted by scanning, not by watching. Beat 01
came back with two quadrupeds on the beach and a swan that are in no plate.

IT WAS ONE FRAME PER CLIP AND THAT COULD NOT SEE MOTION AT ALL. A single late
sample catches invented CONTENT, which is what it was written for, and is blind
by construction to everything that happens BETWEEN frames: a character
lip-syncing to a song nobody sings, an object that comes apart halfway through
and continues as two, a light that ramps up over four seconds. A fork shipped a
film with all three, past a checker of this shape, and the user found them on
first viewing.

So it samples ACROSS the clip now. Frame zero is still skipped -- an i2v model
conditions on it, so it always matches the plate and tells you nothing -- and
the last frame is still avoided because it is sometimes a fade. The strip runs
between those two.

Whole-frame numbers were considered and rejected for the same job: a mouth is
about 1% of the picture, so any mean over the frame reads it as noise. What
finds these faults is frames across time, looked at. See docs/06_verification.md
rules 5 and 7.

This is a LOOK, not a checker -- it cannot pass or fail anything, and it deliberately
does not try. The plate contact sheet is next to it for comparison; what the eye is
doing is diffing two sheets.
"""

import os
import subprocess
import sys

from PIL import Image, ImageDraw

# THE SEASON ROOT, THEN THIS TREE. `import edit` puts season_paths in
# sys.modules and that is NOT the same thing as putting it in this module's
# namespace: every use of season_paths below was a NameError, in three copies
# of this file, on the first frame anybody tried to shoot. smoke.py exists
# because nothing else in the repo could see it.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import season_paths  # noqa: E402
import edit        # noqa: E402
import make_video  # noqa: E402
import shot        # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_qc")
FF = season_paths.FFMPEG

COLS = 1           # one clip per row -- a row IS the filmstrip
TILE = 300         # per-frame width; a row is N of these
N = 5              # frames per clip
FIRST, LAST = 0.12, 0.94   # skip the conditioning frame and any tail fade


def strip(sid: str) -> list[str]:
    """N frames spread across one clip, earliest first."""
    src = make_video.clip(sid)
    dur = edit.SECS[sid]
    out = []
    for i in range(N):
        f = FIRST + (LAST - FIRST) * (i / max(N - 1, 1))
        dst = os.path.join(OUT, f"f{sid}_{i}.png")
        subprocess.run([season_paths.ff("ffmpeg"), "-v", "error", "-y",
                        "-ss", f"{dur * f:.2f}", "-i", src,
                        "-frames:v", "1", dst], check=True)
        if os.path.exists(dst):
            out.append(dst)
    return out


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    sids = list(shot.CUT)

    strips = []
    for sid in sids:
        ims = []
        for p in strip(sid):
            im = Image.open(p).convert("RGB")
            im.thumbnail((TILE, TILE), Image.LANCZOS)
            ims.append(im)
        if ims:
            strips.append((sid, ims))
    if not strips:
        sys.exit("FAIL: no clips resolved -- nothing to QC")

    tw, th = strips[0][1][0].size
    pad, bar = 6, 22
    sheet = Image.new("RGB", (N * (tw + pad) + pad,
                              len(strips) * (th + bar + pad) + pad),
                      (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    for r, (sid, ims) in enumerate(strips):
        y = pad + r * (th + bar + pad)
        for c, im in enumerate(ims):
            sheet.paste(im, (pad + c * (tw + pad), y))
        d.text((pad + 3, y + th + 4),
               f"{sid}  {edit.SECS[sid]}s  --  {N} frames, "
               f"{FIRST:.0%} to {LAST:.0%}", fill=(230, 230, 230))

    dst = os.path.join(OUT, "clips_sheet.png")
    sheet.save(dst)
    print(f"  {len(strips)} clips x {N} frames -> {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
