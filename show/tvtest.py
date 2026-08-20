"""Compare the tube presets on real frames before committing to a re-bake.

A full re-bake is roughly two and a half thousand frames through the whole
chain, and a CRT pass is exactly the kind of thing that looks right in a
thumbnail and wrong at size -- or right at size and illegible in a thumbnail.
So this renders the SAME frames through every preset and writes two sheets:

    out/tvtest.png          scaled down, three segments x every preset. This is
                            the "from across the room" judgement: does it read
                            as a television.
    out/tvtest_detail.png   1:1 crops, no scaling at all. This is the only way
                            to judge scanline pitch and grille -- a sheet that
                            has been resized has resampled the very pattern you
                            are trying to look at, and will lie to you.

The detail sheet carries a BOARD crop and a CORNER crop, because the two things
this pass can break are legibility of the number and the shape of the glass.

    python tvtest.py                # all presets, segments 01 03 05
    python tvtest.py 02 06          # different segments
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

import assemble
import crt
import edit
import shot

HERE = os.path.dirname(os.path.abspath(__file__))
FF = season_paths.FFMPEG
WORK = os.path.join(HERE, "_work")
OUT = os.path.join(HERE, "out")

ORDER = ["signed", "tube", "heavy"]
LABEL = {"signed": "signed  (what shipped)",
         "tube": "tube  (recommended)",
         "heavy": "heavy"}

# 1:1 crops as frame fractions: the board type, and the bottom-left corner.
BOARD_CROP = (0.60, 0.13, 0.93, 0.45)
CORNER_CROP = (0.00, 0.70, 0.24, 1.00)

FONT = season_paths.font("arialbd.ttf")


def raw(sid: str, i: int) -> Image.Image:
    """One upscaled, type-stamped frame from the synced segment."""
    src = os.path.join(WORK, f"synced_{sid}.mp4")
    if not os.path.exists(src):
        sys.exit(f"FAIL: {src} missing -- run lipsync.py")
    png = os.path.join(WORK, f"tvtest_{sid}_{i}.png")
    if not os.path.exists(png):
        subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                        "-i", src, "-vf", f"select=eq(n\\,{i})", "-frames:v", "1",
                        png], check=True)
    im = Image.open(png).convert("RGB")
    w, h = assemble.dims(*im.size)
    im = im.resize((w, h), Image.LANCZOS)
    # The same line-by-line reveal the bake does, so an early frame in the roll
    # strip shows the board as empty as it actually is at that moment.
    marks = [round(t * assemble.FPS) for t in
             [t for _, t in edit.offsets(sid)]][:len(shot.BOARD_TYPE[sid])]
    return assemble.draw_board(im, sid, sum(1 for m in marks if i >= m))


def frame_for(sid: str) -> tuple[Image.Image, int]:
    """A frame near the END, so every line of the bounty is on the board.

    The type lands line by line, so a frame from the head would compare three
    empty boards and tell you nothing about legibility.
    """
    i = int(edit.FRAMES[sid] * 0.88)
    return raw(sid, i), i


def cap(im: Image.Image, text: str, px: int = 22) -> Image.Image:
    f = ImageFont.truetype(FONT, px)
    band = px + 12
    out = Image.new("RGB", (im.width, im.height + band), (16, 16, 18))
    out.paste(im, (0, band))
    ImageDraw.Draw(out).text((8, 6), text, font=f, fill=(235, 232, 226))
    return out


def crop(im: Image.Image, box: tuple) -> Image.Image:
    w, h = im.size
    return im.crop((int(box[0] * w), int(box[1] * h),
                    int(box[2] * w), int(box[3] * h)))


def main() -> int:
    # A SPREAD ACROSS THE REEL, DERIVED. This defaulted to ["01", "03", "05"]
    # -- the six-segment reference reel's first/middle/last -- and on any reel
    # shorter than five segments the default FAILS a tool whose whole job is
    # to be looked at. First, middle and last of whatever the reel actually
    # is; on a reel of one or two, the set collapses to what exists.
    spread = sorted({shot.CUT[0], shot.CUT[len(shot.CUT) // 2], shot.CUT[-1]})
    want = [a for a in sys.argv[1:] if not a.startswith("-")] or spread
    bad = [s for s in want if s not in shot.CUT]
    if bad:
        sys.exit(f"FAIL: {bad} are not segments")
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)

    rows, details = [], []
    for sid in want:
        base, i = frame_for(sid)
        print(f"  [{sid}] frame {i}  {base.width}x{base.height}  "
              f"{len(shot.BOARD_TYPE[sid])} line(s)")
        done = {p: crt.tube(base, p, i) for p in ORDER}

        # scaled row -- the across-the-room read
        cells = [cap(done[p].resize((480, 360), Image.LANCZOS),
                     f"{sid}   {LABEL[p]}") for p in ORDER]
        row = Image.new("RGB", (sum(c.width for c in cells),
                                max(c.height for c in cells)), (16, 16, 18))
        x = 0
        for c in cells:
            row.paste(c, (x, 0))
            x += c.width
        rows.append(row)

        # 1:1 detail -- NOT resized, on purpose
        for box, what in ((BOARD_CROP, "board"), (CORNER_CROP, "corner")):
            cells = [cap(crop(done[p], box), f"{sid} {what}  {p}", 18)
                     for p in ORDER]
            d = Image.new("RGB", (sum(c.width for c in cells),
                                  max(c.height for c in cells)), (16, 16, 18))
            x = 0
            for c in cells:
                d.paste(c, (x, 0))
                x += c.width
            details.append(d)

    def stack(imgs, path):
        out = Image.new("RGB", (max(i.width for i in imgs),
                                sum(i.height for i in imgs)), (16, 16, 18))
        y = 0
        for i in imgs:
            out.paste(i, (0, y))
            y += i.height
        out.save(path)
        print(f"  -> {path}  {out.width}x{out.height}")

    stack(rows, os.path.join(OUT, "tvtest.png"))
    stack(details, os.path.join(OUT, "tvtest_detail.png"))

    # THE ROLL IS A MOTION EFFECT AND A SHEET CANNOT SHOW IT, but it can show
    # the two things that would be wrong in every frame of it: how far the
    # picture is displaced, and whether the blanking bar at the seam reads as a
    # television or as a corrupt file.
    P = crt.PRESETS[assemble.TV]
    if P["roll"]:
        sid = want[0]
        n = P["roll"]
        idx = [0, n // 4, n // 2, (3 * n) // 4, n - 1, n + 2]
        cells = [cap(crt.tube(raw(sid, i), assemble.TV, i).resize(
            (360, 270), Image.LANCZOS),
            f"{sid}  frame {i}" + ("   locked" if i >= n else ""), 18)
            for i in idx]
        stack([_row(cells[:3]), _row(cells[3:])],
              os.path.join(OUT, "tvtest_roll.png"))
    return 0


def _row(cells):
    out = Image.new("RGB", (sum(c.width for c in cells),
                            max(c.height for c in cells)), (16, 16, 18))
    x = 0
    for c in cells:
        out.paste(c, (x, 0))
        x += c.width
    return out


if __name__ == "__main__":
    sys.exit(main())
