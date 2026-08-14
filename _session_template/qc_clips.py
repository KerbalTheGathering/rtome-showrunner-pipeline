"""One frame per bought clip, on a sheet, so the session is QC'd as a session.

WHY A SHEET AND NOT FIFTEEN PLAYBACKS. What goes wrong in an i2v buy is mostly
INVENTED CONTENT -- an animal, a boat, a figure that the plate never had and the
prompt never asked for -- and that is spotted by scanning, not by watching. Beat 01
came back with two quadrupeds on the beach and a swan that are in no plate.

THE FRAME IS TAKEN LATE ON PURPOSE. Seedance conditions on the FIRST frame, so frame
zero always matches the plate and tells you nothing; drift accumulates, so the honest
sample is near the end. Taken at 80% of duration rather than the last frame because
the last frame is sometimes a fade.

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

COLS = 5
TILE = 440
AT = 0.80          # fraction of the clip to sample


def frame(sid: str, dst: str) -> None:
    src = make_video.clip(sid)
    t = edit.SECS[sid] * AT
    subprocess.run([season_paths.ff("ffmpeg"), "-v", "error", "-y",
                    "-ss", f"{t:.2f}", "-i", src, "-frames:v", "1", dst],
                   check=True)


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    sids = list(shot.CUT)

    tiles = []
    for sid in sids:
        p = os.path.join(OUT, f"f{sid}.png")
        frame(sid, p)
        im = Image.open(p).convert("RGB")
        im.thumbnail((TILE, TILE), Image.LANCZOS)
        tiles.append((sid, im))

    tw, th = tiles[0][1].size
    rows = (len(tiles) + COLS - 1) // COLS
    pad, bar = 8, 22
    sheet = Image.new("RGB", (COLS * (tw + pad) + pad,
                              rows * (th + bar + pad) + pad), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    for i, (sid, im) in enumerate(tiles):
        x = pad + (i % COLS) * (tw + pad)
        y = pad + (i // COLS) * (th + bar + pad)
        sheet.paste(im, (x, y))
        d.text((x + 3, y + th + 4), f"{sid}  {edit.SECS[sid]}s @{AT:.0%}",
               fill=(230, 230, 230))

    dst = os.path.join(OUT, "clips_sheet.png")
    sheet.save(dst)
    print(f"  {len(tiles)} frames -> {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
