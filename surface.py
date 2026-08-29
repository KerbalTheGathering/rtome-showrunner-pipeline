"""Find the largest flat surface in a plate, and DRAW THE ANSWER BACK ON.

WHY THIS IS MEASURED AND NOT TYPED. Anything that must be spelled correctly is
not generated -- it is drawn at bake resolution over a surface the plate left
blank. So the assembler needs a rectangle per plate, and numbers read off a
contact sheet by eye are wrong by enough to push a line off the felt and onto
the wooden frame. It looks fine in the source and wrong in the film.

WHY IT IS A SEASON-LEVEL FILE. This began as `show/board_rect.py`, which is very
good and is welded to ONE GREEN FELT BOARD IN THE RIGHT HALF OF THE FRAME. The
mechanism has nothing to do with felt: given a colour hint and a region to look
in, it finds the largest flat area of that colour and returns a rect. Which
means a season can put type on a whiteboard, a newspaper, a departures screen or
a shop window, and that is most of what a different genre needs.

    python surface.py show 01 02        # measure named beats of a tree
    python surface.py show --emit       # print the dict to paste into shot.py
    python surface.py show --hint=teal --x-from=0.45

HOW IT SEPARATES THE SURFACE FROM EVERYTHING THE SAME COLOUR AS IT, which the
first attempt got wrong. A board of green felt and a painted sea are both teal,
so "is it teal" selects almost the whole frame. Two things fix it:

  1. A SEARCH REGION. Confirmed by looking, not assumed. Searching only one part
     of the frame removes the presenter, the potted palm and most of the painted
     backdrop outright.
  2. THE MODE, NOT A FIXED THRESHOLD. A hard cut worked for four plates and
     failed on the two whose whole palette is darker -- their painted sea sat
     below a threshold picked from the other four. So the surface colour is
     found PER PLATE as the commonest matching colour in the search region (it
     is by far the largest flat area there) and pixels are taken within a
     distance of THAT. Nothing is carried between plates.

     Same error as a pitch metric one day earlier: a fixed threshold, validated
     on some of the material, applied to all of it.

WHAT IT CANNOT DO AND MUST NOT PRETEND TO: IT FINDS THE SURFACE, NOT THE USABLE
AREA. On a real reel the lower third of a correctly-detected board had a
counter, a ledger and a mug in front of it. The rect was right and the type
would still have landed behind furniture. That is what the TYPE_INSET_B in
shot.py is for, and it can only be set BY EYE off a drawn frame. This tool
cannot see occlusion and does not try.

WHICH IS WHY IT DRAWS A VERIFICATION SHEET. A threshold that finds the wrong
rectangle returns a perfectly plausible set of numbers, and this project has
been burned by a metric that was confidently precise about the wrong thing. The
detected rect is stroked back onto the plate with the type bands marked, and the
sheet gets LOOKED AT before anything is written down.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw

import parts
import season_paths

ROOT = os.path.dirname(os.path.abspath(__file__))

STEP = 6                      # sample every Nth pixel; a usable surface is big
TOL = 26                      # max per-channel distance from the modal colour
INSET = 0.035                 # shrink off the frame/bezel, fraction of the box
QUANT = 12                    # colour bucket size when finding the mode
MIN_HITS = 300                # below this it is a smudge, not a surface
BANDS = 3                     # type bands drawn on the verification sheet


# NAMED HINTS RATHER THAN THRESHOLDS AT THE CALL SITE. Each is a predicate over
# one pixel: "is this the KIND of colour the surface is". It is deliberately
# loose -- the mode does the precision, this only has to exclude the obviously
# wrong half of the frame. Add one when your season's surface is not here.
HINTS = {
    "teal":  lambda r, g, b: g > r + 12 and b > r + 8 and abs(g - b) < 34,
    "green": lambda r, g, b: g > r + 18 and g > b + 12,
    "blue":  lambda r, g, b: b > r + 18 and b > g + 10,
    "white": lambda r, g, b: min(r, g, b) > 165 and max(r, g, b) - min(r, g, b) < 26,
    "paper": lambda r, g, b: min(r, g, b) > 120 and r >= g >= b - 8
                             and r - b < 60,
    "dark":  lambda r, g, b: max(r, g, b) < 78,
    "any":   lambda r, g, b: True,
}


def measure(path: str, hint: str = "teal",
            x_from: float = 0.0, x_to: float = 1.0,
            y_from: float = 0.0, y_to: float = 1.0):
    """(rect in frame fractions, the modal colour it locked onto).

    Returns (None, mode) when the search region holds no surface worth the
    name, and (None, None) when it holds nothing matching the hint at all --
    two different answers, because "your hint is wrong" and "your search region
    is wrong" want two different fixes.
    """
    want = HINTS.get(hint)
    if want is None:
        sys.exit(f"FAIL: no colour hint named {hint!r}. Known: "
                 f"{', '.join(sorted(HINTS))}")
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    xs_range = range(int(w * x_from), int(w * x_to), STEP)
    ys_range = range(int(h * y_from), int(h * y_to), STEP)

    hist: dict[tuple, int] = {}
    for y in ys_range:
        for x in xs_range:
            r, g, b = px[x, y]
            if want(r, g, b):
                k = (r // QUANT, g // QUANT, b // QUANT)
                hist[k] = hist.get(k, 0) + 1
    if not hist:
        return None, None
    mk = max(hist, key=hist.get)
    mode = tuple(c * QUANT + QUANT // 2 for c in mk)

    xs, ys = [], []
    for y in ys_range:
        for x in xs_range:
            r, g, b = px[x, y]
            if (abs(r - mode[0]) <= TOL and abs(g - mode[1]) <= TOL
                    and abs(b - mode[2]) <= TOL):
                xs.append(x)
                ys.append(y)
    if len(xs) < MIN_HITS:
        return None, mode
    xs.sort()
    ys.sort()
    # THE 2ND AND 98TH PERCENTILES, NOT THE EXTREMES. One stray pixel of the
    # right colour on the other side of the search region would otherwise
    # stretch the rect across the whole frame, and the result would look
    # plausible in a printed number and absurd on the sheet.
    q = lambda a, f: a[int(f * (len(a) - 1))]                    # noqa: E731
    x0, x1 = q(xs, 0.02), q(xs, 0.98)
    y0, y1 = q(ys, 0.02), q(ys, 0.98)
    dx, dy = (x1 - x0) * INSET, (y1 - y0) * INSET
    return ((x0 + dx) / w, (y0 + dy) / h, (x1 - dx) / w, (y1 - dy) / h), mode


def draw(im: Image.Image, rect) -> Image.Image:
    """Stroke the rect and its type bands back onto the plate."""
    w, h = im.size
    d = ImageDraw.Draw(im)
    box = (rect[0] * w, rect[1] * h, rect[2] * w, rect[3] * h)
    d.rectangle(box, outline=(255, 40, 40), width=max(3, w // 270))
    for i in range(1, BANDS):
        yy = box[1] + (box[3] - box[1]) * i / BANDS
        d.line((box[0], yy, box[2], yy), fill=(255, 150, 40),
               width=max(2, w // 600))
    return im


def sheet(cells: list[tuple[str, Image.Image]], dest: str) -> str:
    cw = 840
    ch = round(cw * cells[0][1].size[1] / cells[0][1].size[0])
    cols = 2 if len(cells) > 1 else 1
    rows = (len(cells) + cols - 1) // cols
    out = Image.new("RGB", (cw * cols, (ch + 20) * rows), "black")
    dd = ImageDraw.Draw(out)
    for i, (lab, im) in enumerate(cells):
        x, y = (i % cols) * cw, (i // cols) * (ch + 20)
        out.paste(im.resize((cw, ch), Image.LANCZOS), (x, y + 20))
        dd.text((x + 6, y + 5), lab, fill="#ffdd99")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    out.save(dest)
    return dest


# The plates come from the tree's own gen_still, so aliases and flips resolve
# exactly as they will for the shoot -- one subprocess per tree, for the reason
# smoke.py sets out at length.
_PLATES = r"""
import json, os, sys
sys.path.insert(0, os.getcwd())
import gen_still, shot
out = {}
for sid in shot.CUT:
    try:
        out[sid] = gen_still.plate(sid)
    except SystemExit:
        out[sid] = None
json.dump(out, sys.stdout)
"""


def plates(folder: str) -> dict[str, str | None]:
    r = subprocess.run([sys.executable, "-c", _PLATES], cwd=folder,
                       capture_output=True, text=True)
    if r.returncode or not r.stdout.strip():
        sys.exit(f"FAIL: {os.path.basename(folder)} will not load -- "
                 f"`python smoke.py {os.path.basename(folder)}`\n"
                 f"  {(r.stderr or '').strip().splitlines()[-1:] or ['']}"[:400])
    # The last line only -- see the same note in contract.py.
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        sys.exit(f"FAIL: {os.path.basename(folder)} printed something this "
                 f"tool could not read where a plate list should have been.")


def tree(name: str) -> str:
    for label, folder in [("cold_open", parts.cold_open_dir() or ""),
                          ("show", parts.show_dir() or "")]:
        if name == label and folder:
            return folder
    for r in parts.sessions():
        if name == r["dir"]:
            return r["path"]
    sys.exit(f"FAIL: {name!r} is not a part of this season. "
             f"`python parts.py` lists them.")


def main() -> int:
    argv = sys.argv[1:]
    named = [a for a in argv if not a.startswith("-")]
    if not named:
        sys.exit(__doc__.strip().splitlines()[0]
                 + "\n\n  python surface.py <part> [beat ...] [--emit]"
                   "\n  python surface.py show --hint=teal --x-from=0.45")
    folder = tree(named[0])
    want = named[1:]

    def opt(flag: str, default: float) -> float:
        return next((float(a.split("=", 1)[1]) for a in argv
                     if a.startswith(flag)), default)

    hint = next((a.split("=", 1)[1] for a in argv
                 if a.startswith("--hint=")), "teal")
    # CHECKED BEFORE ANYTHING IS PRINTED. measure() refuses on an unknown hint
    # too, but by then the header has already claimed a search is underway.
    if hint not in HINTS:
        sys.exit(f"FAIL: no colour hint named {hint!r}. Known: "
                 f"{', '.join(sorted(HINTS))}\n"
                 f"  They are one-line predicates at the top of this file. If "
                 f"your season's\n"
                 f"  surface is not one of them, add it there rather than "
                 f"loosening one.")
    box = dict(x_from=opt("--x-from=", 0.0), x_to=opt("--x-to=", 1.0),
               y_from=opt("--y-from=", 0.0), y_to=opt("--y-to=", 1.0))

    got = plates(folder)
    sids = want or [s for s in got if got[s]]
    bad = [s for s in sids if s not in got]
    if bad:
        sys.exit(f"FAIL: {bad} are not beats of {named[0]}")
    if not sids:
        sys.exit(f"FAIL: no plate in {named[0]} yet -- run gen_still.py there. "
                 f"Measuring nothing and printing an empty table is not a pass.")

    rects: dict[str, tuple] = {}
    cells = []
    print(f"  {named[0]}   hint={hint}   search "
          f"x {box['x_from']:.2f}-{box['x_to']:.2f}  "
          f"y {box['y_from']:.2f}-{box['y_to']:.2f}\n")
    for sid in sids:
        p = got.get(sid)
        if not p:
            print(f"  {sid}  no plate yet")
            continue
        rect, mode = measure(p, hint, **box)
        im = Image.open(p).convert("RGB")
        if rect:
            rects[sid] = tuple(round(v, 4) for v in rect)
            im = draw(im, rect)
            lab = (f"{sid}  x {rect[0]:.3f}-{rect[2]:.3f}  "
                   f"y {rect[1]:.3f}-{rect[3]:.3f}   surface rgb{mode}")
        elif mode:
            lab = (f"{sid}  NOTHING BIG ENOUGH (modal {hint} {mode}) -- widen "
                   f"the search region")
        else:
            lab = f"{sid}  NO {hint.upper()} AT ALL -- wrong hint?"
        print(f"  {sid}  {rects.get(sid, lab.split('  ', 1)[1])}")
        cells.append((lab, im))

    if not cells:
        sys.exit("FAIL: nothing was measured.")

    dest = sheet(cells, os.path.join(folder, "out", "surface.png"))
    if rects:
        ws = [r[2] - r[0] for r in rects.values()]
        hs = [r[3] - r[1] for r in rects.values()]
        print(f"\n  width  {min(ws):.3f}-{max(ws):.3f} of frame")
        print(f"  height {min(hs):.3f}-{max(hs):.3f} of frame")
    # A COUNT OF WHAT WAS FOUND, NOT OF WHAT WAS LOOKED AT.
    print(f"\n  {len(rects)} of {len(cells)} plate(s) yielded a rect")
    print(f"  -> {dest}")
    print("\n  LOOK AT IT before pasting anything into shot.py. This finds the\n"
          "  SURFACE, not the USABLE AREA -- it cannot see the counter, the mug\n"
          "  or the hand in front of the lower third of it. That is what\n"
          "  TYPE_INSET_B is for and it can only be set by eye, off this sheet.")

    if "--emit" in argv:
        print("\nBOARD_RECT = {")
        for sid in sids:
            if sid in rects:
                print(f'    "{sid}": {rects[sid]},')
        print("}")
        missing = [s for s in sids if s not in rects]
        if missing:
            print(f"#  NOT FOUND, and therefore not in the table above: "
                  f"{missing}")
    return 0 if len(rects) == len(cells) else 1


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
