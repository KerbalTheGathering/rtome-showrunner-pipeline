"""Contact sheet of a tree's plates AS THE PIPELINE RESOLVES THEM.

ONE FILE, NOT TWO COPIES (finding 140). This was byte-identical in `show/`
and `cold_open/`; each keeps a thin shim so `python sheet.py` works
unchanged inside the tree. The tree is resolved through the `shot` and
`gen_still` modules the shim puts first on sys.path.

READS THROUGH gen_still.plate(), NOT OFF THE DIRECTORY. That is the whole point:
plates may be mirrored by PLATE_FLIP, and a sheet built by listing PNGs
would show the unflipped originals and report a consistency problem that has
already been fixed -- or hide one that has not. What is on screen here is what
the shoot and the assembler will actually use.

    python sheet.py             # the plates, resolved
    python sheet.py --raw       # the output directory, probes and rejects too
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import season_paths                                                # noqa: E402


import os
import sys

from PIL import Image, ImageDraw

try:
    import gen_still  # noqa: E402  -- the TREE'S, via the shim's sys.path
    import shot       # noqa: E402
except ModuleNotFoundError:
    sys.exit("FAIL: sheet.py reads a tree's shot.py and gen_still.py -- run "
             "it from inside a tree (each carries a shim), not at the season "
             "root.")

# THE TREE IS WHERE `shot` CAME FROM, not where this file lives.
HERE = os.path.dirname(os.path.abspath(shot.__file__))
OUT = os.path.join(HERE, "out")
SRC = os.path.join(season_paths.COMFY_OUTPUT, shot.NAME)
CELL_W = 840


def main() -> int:
    raw = "--raw" in sys.argv
    want = [a for a in sys.argv[1:] if not a.startswith("-")]

    if raw:
        files = sorted(f for f in os.listdir(SRC) if f.endswith(".png"))
        if want:
            files = [f for f in files if f.rsplit("_", 1)[0] in want]
        ims = [(f, Image.open(os.path.join(SRC, f)).convert("RGB"))
               for f in files]
    else:
        sids = want or list(shot.CUT)
        ims = []
        for sid in sids:
            p = gen_still.plate(sid)
            tag = ("  [flipped]"
                   if sid in getattr(shot, "PLATE_FLIP", set()) else "")
            ims.append((f"{sid}  {os.path.basename(p)}{tag}",
                        Image.open(p).convert("RGB")))
    if not ims:
        sys.exit(f"FAIL: nothing to show in {SRC}")

    w, h = ims[0][1].size
    cw = CELL_W
    ch = round(cw * h / w)
    cols = 2 if len(ims) > 1 else 1
    rows = (len(ims) + cols - 1) // cols

    sheet = Image.new("RGB", (cw * cols, (ch + 20) * rows), "black")
    d = ImageDraw.Draw(sheet)
    for i, (name, im) in enumerate(ims):
        x, y = (i % cols) * cw, (i // cols) * (ch + 20)
        sheet.paste(im.resize((cw, ch), Image.LANCZOS), (x, y + 20))
        d.text((x + 6, y + 5), name, fill="#ffdd99")

    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, "sheet_raw.png" if raw else "sheet.png")
    sheet.save(dst)
    print(f"  {len(ims)} plate(s) -> {dst}  ({sheet.size[0]}x{sheet.size[1]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
