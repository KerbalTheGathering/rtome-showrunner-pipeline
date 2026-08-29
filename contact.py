"""Every plate in the season, in running order, on one sheet. Before the VO.

WHY THIS EXISTS AND storyboard.py DOES NOT COVER IT.

`storyboard.py` is the right sheet and it is drawn too late. It needs
`edit.table()` for its runtimes, `edit.table()` needs measured VO, and measured
VO is the first thing in this pipeline that costs money. So the one document
that shows you the whole season at once cannot be looked at until after you have
paid for the narration -- and it is per-film besides, so it never shows you the
SEASON.

Plates are the first thing that can be wrong in a way no assert catches. Not
wrong in the way a missing file is wrong: wrong in the way a room is wrong. The
same corner rendered as three different corners. A prop that came back generic
because the frame was too wide to hold it. A character in a landscape that was
meant to be empty. Every one of those renders cleanly, passes every check in
this repo, and is obvious in four seconds of looking -- next to the others.

On the fork this template came from, this sheet caught **six bad plates in one
look, three of which were prompt faults rather than seed faults** -- which is
the distinction that decides whether you re-roll or rewrite, and it is only
visible in comparison.

    python contact.py                 # every part, in running order
    python contact.py S3_HARBOUR show # named parts only
    python contact.py --cols=3        # bigger pictures, fewer per row
    python contact.py --cols=6        # a six-film season on one screen
    python contact.py --open          # print the path and nothing else

ONE SUBPROCESS PER PART, for the reason smoke.py sets out: every tree owns a
`shot.py` and one interpreter can only hold one of them. The work is in
contact_probe.py.

IT NEVER TOUCHES edit.py, WHICH IS THE WHOLE POINT. Nothing here needs a
duration, so nothing here waits on a take.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

import parts
import season_paths

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")
PROBE = os.path.join(ROOT, "contact_probe.py")

# SMALL TILES ON PURPOSE. This sheet answers "is that the same room?" and "is
# that the right prop?", which are comparison questions -- `sheet.py` is where
# you go to look at one plate at 1:1. A season of six films is ninety-nine
# plates, and a sheet nobody can scroll is a sheet nobody looks at.
#
# THE SHEET'S WIDTH IS FIXED AND THE TILE DERIVES FROM IT, so `--cols=3` means
# "bigger pictures" rather than "narrower document". The other way round makes
# the flag do the opposite of what its name says.
COLS = 4
SHEET_W = 1840
PAD = 14
CAP_H = 62
HEAD = 92
BAND = 46                       # the per-part heading strip

BG = (22, 20, 19)
INK = (238, 232, 220)
DIM = (150, 143, 133)
ACCENT = (226, 174, 90)
WARN = (232, 120, 96)
BAND_BG = (38, 34, 31)


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """A UI face, falling back rather than failing.

    season_paths.font() exits on a missing file, which is right for a title
    card that would otherwise ship a row of tofu boxes and wrong for a working
    document -- a contact sheet in the wrong typeface is still a contact sheet,
    and refusing to draw one because a font is missing helps nobody.
    """
    for n in (name, "segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        p = os.path.join(season_paths.FONT_DIR, n)
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def order() -> list[tuple[str, str]]:
    """(label, folder) for every part that makes plates, in running order.

    THE SAME ORDER THE FEATURE PLAYS IN, from parts.py, because a sheet in
    alphabetical order is a folder listing with pictures in it. `_session_
    template` is not in the season and is not here.
    """
    ss, _bad = parts.audit()
    out = []
    co = parts.cold_open_dir()
    if co:
        out.append(("COLD OPEN", co))
    sh = parts.show_dir()
    if sh:
        # ONE ENTRY, NOT ONE PER INTERSTITIAL. The show is a single tree with
        # one plate table; parts.running_order() lists it N times because it
        # delivers N mp4s, which is a different question from this one.
        out.append((f"THE SHOW ({parts.season.SHOW_NAME or 'show'})", sh))
    for r in ss:
        out.append((f"#{r['no']}  {r['title'] or r['dir']}", r["path"]))
    return out


def probe(folder: str) -> dict | None:
    r = subprocess.run([sys.executable, PROBE], cwd=folder,
                       capture_output=True, text=True)
    if r.returncode or not r.stdout.strip():
        return None
    # The last line only -- see the same note in contract.py.
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None


def caption(d: ImageDraw.ImageDraw, x: int, y: int, b: dict, fonts,
            tile_w: int) -> None:
    f_sid, f_what, f_meta = fonts
    d.text((x, y), b["sid"], font=f_sid, fill=ACCENT)
    what = b["what"] or "(no description)"
    while f_what.getlength(what) > tile_w - 42 and " " in what:
        what = what.rsplit(" ", 1)[0]
    d.text((x + 38, y + 2), what, font=f_what, fill=INK)

    bits = []
    if b["alias"]:
        bits.append(f"plate of {b['alias']}")
    if b["flip"]:
        bits.append("flipped")
    if b["graded"]:
        bits.append("flat grade")
    if b["takes"] > 1:
        bits.append(f"{b['takes']} takes")
    bits.append(f"seed {b['seed']}")
    d.text((x + 38, y + 24), "   ".join(bits), font=f_meta, fill=DIM)


def main() -> int:
    argv = sys.argv[1:]
    quiet = "--open" in argv
    cols = next((int(a.split("=", 1)[1]) for a in argv
                 if a.startswith("--cols=")), COLS)
    named = [a for a in argv if not a.startswith("-")]

    want = order()
    if named:
        want = [t for t in want if os.path.basename(t[1]) in named]
        if not want:
            sys.exit(f"FAIL: {named} matched no part. Known: "
                     f"{[os.path.basename(f) for _l, f in order()]}")
    if not want:
        sys.exit("FAIL: this season has no parts yet -- `python parts.py`")

    # EVERY PART IS PROBED BEFORE ANY OF IT IS DRAWN, because the sheet's
    # geometry depends on how many beats there are in total and a part that
    # will not load has to be a labelled row rather than a missing one.
    got = []
    for label, folder in want:
        m = probe(folder)
        got.append((label, folder, m))
        if m is None and not quiet:
            print(f"  {label:<34} will not load -- `python smoke.py "
                  f"{os.path.basename(folder)}`")

    live = [(l, f, m) for l, f, m in got if m]
    if not live:
        sys.exit("FAIL: no part could be loaded. Run `python smoke.py`.")

    probe_im = next((Image.open(b["plate"]) for _l, _f, m in live
                     for b in m["beats"] if b["plate"]), None)
    if probe_im is None:
        sys.exit("FAIL: not one beat in this season has a plate yet.\n"
                 "  Run gen_still.py in a part folder, then come back. A sheet\n"
                 "  of nothing is not an approval.")
    tile_w = (SHEET_W - (cols + 1) * PAD) // cols
    tile_h = round(tile_w * probe_im.height / probe_im.width)
    cell_h = tile_h + CAP_H

    blocks = []                                     # (label, meta, rows_of_beats)
    height = HEAD
    for label, folder, m in got:
        if m is None:
            blocks.append((label, "will not load -- run smoke.py", []))
            height += BAND + PAD
            continue
        bs = m["beats"]
        nrows = (len(bs) + cols - 1) // cols
        have = sum(1 for b in bs if b["plate"])
        meta = (f"{have} of {len(bs)} beat(s) have a plate"
                + ("" if have == len(bs)
                   else f"   -- missing "
                        f"{', '.join(b['sid'] for b in bs if not b['plate'])}"))
        blocks.append((label, meta, bs))
        height += BAND + nrows * (cell_h + PAD) + PAD

    width = cols * tile_w + (cols + 1) * PAD
    sheet = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(sheet)

    f_title = font("segoeuib.ttf", 34)
    f_sub = font("segoeui.ttf", 18)
    f_band = font("segoeuib.ttf", 24)
    fonts = (font("segoeuib.ttf", 24), font("segoeuib.ttf", 18),
             font("segoeui.ttf", 15))

    d.text((PAD + 4, 20), f"{parts.season.SEASON_TITLE or parts.season.SEASON}"
                          f"   --   every plate, in running order",
           font=f_title, fill=INK)

    y = HEAD
    drawn = total = 0
    for label, meta, bs in blocks:
        d.rectangle([0, y, width, y + BAND - 8], fill=BAND_BG)
        d.text((PAD + 4, y + 4), label, font=f_band, fill=INK)
        d.text((PAD + 4 + f_band.getlength(label) + 24, y + 11), meta,
               font=f_sub, fill=DIM if "will not load" not in meta
               and "missing" not in meta else WARN)
        y += BAND
        for i, b in enumerate(bs):
            total += 1
            cx = PAD + (i % cols) * (tile_w + PAD)
            cy = y + (i // cols) * (cell_h + PAD)
            if b["plate"]:
                with Image.open(b["plate"]) as im:
                    sheet.paste(im.convert("RGB")
                                .resize((tile_w, tile_h), Image.LANCZOS),
                                (cx, cy))
                drawn += 1
            else:
                d.rectangle([cx, cy, cx + tile_w - 1, cy + tile_h - 1],
                            fill=(34, 30, 28), outline=WARN, width=2)
                d.text((cx + 14, cy + tile_h // 2 - 10), "no plate yet",
                       font=fonts[1], fill=WARN)
            d.rectangle([cx, cy, cx + tile_w - 1, cy + tile_h - 1],
                        outline=(60, 55, 50), width=1)
            caption(d, cx, cy + tile_h + 8, b, fonts, tile_w)
        if bs:
            y += ((len(bs) + cols - 1) // cols) * (cell_h + PAD)
        y += PAD

    os.makedirs(OUT, exist_ok=True)
    dest = os.path.join(OUT, "contact.png")
    sheet.save(dest)

    if quiet:
        print(dest)
        return 0

    # A COUNT OF WHAT WAS DRAWN, NOT OF WHAT WAS ASKED FOR. This repo has
    # already shipped a reel whose log said "3 line(s) of type" over one line
    # of drawn type; a sheet that reports the beat count while showing gaps
    # would be the same lie with pictures.
    print(f"\n  {drawn} of {total} beat(s) drawn"
          + ("" if drawn == total else "   -- the rest have no plate yet"))
    print(f"  -> {dest}  ({width}x{height}, "
          f"{os.path.getsize(dest) / 1e6:.1f} MB)")
    print("\n  LOOK AT IT. The faults this catches are not the ones an assert\n"
          "  catches: the same location rendered as two locations, a prop that\n"
          "  fell back to a generic because the frame was too wide to hold it,\n"
          "  a figure in a landscape that was meant to be empty. All of them\n"
          "  render cleanly and all of them are obvious next to each other.")
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
