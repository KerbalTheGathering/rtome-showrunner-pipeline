"""Preview the board type and the television grade on the PLATES.

Cheap de-risk, and it can run before a single clip exists. The type layout, the
font size, the right-alignment, whether he covers a line, and how heavy the TV
pass reads are all decidable from a still -- and all of them are much more
annoying to discover after baking 2257 frames.

Draws every segment at its FINAL state (all three lines up), because that is the
worst case for fit and for occlusion.

    python typetest.py
"""
from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assemble   # noqa: E402
import crt        # noqa: E402
import gen_still  # noqa: E402
import shot       # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")


def main() -> int:
    cells = []
    for sid in shot.CUT:
        im = Image.open(gen_still.plate(sid)).convert("RGB")
        w, h = assemble.dims(*im.size)
        im = im.resize((w, h), Image.LANCZOS)
        im = assemble.draw_board(im, sid, len(shot.BOARD_TYPE[sid]))
        # THE SAME PASS THE BAKE RUNS. This called assemble.tv(), a function
        # that has never existed -- assemble.TV is the DIAL and crt.tube()
        # is the pass -- so every run of this tool died on its first segment
        # (fault 110). Frame 0 is right for a still; an empty dial skips the
        # tube, exactly as _bake_one does.
        if assemble.TV:
            im = crt.tube(im, assemble.TV, 0)
        n = len(shot.BOARD_TYPE[sid])
        cells.append((f"{sid}   {n} line(s)" + ("   EMPTY BOARD" if not n else ""),
                      im))

    cw = 900
    ch = round(cw * cells[0][1].size[1] / cells[0][1].size[0])
    sheet = Image.new("RGB", (cw * 2, (ch + 20) * ((len(cells) + 1) // 2)), "black")
    d = ImageDraw.Draw(sheet)
    for i, (lab, im) in enumerate(cells):
        x, y = (i % 2) * cw, (i // 2) * (ch + 20)
        sheet.paste(im.resize((cw, ch), Image.LANCZOS), (x, y + 20))
        d.text((x + 6, y + 5), lab, fill="#ffdd99")
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, "typetest.png")
    sheet.save(dst)
    print(f"  -> {dst}  ({sheet.size[0]}x{sheet.size[1]})")
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
