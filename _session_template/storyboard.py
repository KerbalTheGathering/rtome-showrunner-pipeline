"""One sheet showing the whole film: every plate in story order, with its beat,
its runtime and the line spoken over it.

WHY THIS EXISTS. A folder of fifteen PNGs is a set of pictures; a film is an
ORDER and a set of LENGTHS. Approving the former tells you almost nothing about
the latter -- Session #1's problems (a beat that ran past its clip, a title with
nothing paying it off) were all visible in the sequence and invisible in any
single frame.

Everything on it is DERIVED: plates come from the resolver, so a re-rolled beat
cannot leave a stale frame on the board; runtimes come from edit.table(), so the
board and the cut cannot disagree; lines come from script.py in the order
edit.py places them. Nothing here is typed twice.

Body type is a UI face rather than the film's Impact -- this is a working
document meant to be read, not a title card.
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import os
import sys

from PIL import Image, ImageDraw, ImageFont

import edit
import gen_still
import identity
import script
import shot

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

COLS = 3
TILE_W = 660
PAD = 18
CAP_H = 132
BG = (22, 20, 19)
INK = (238, 232, 220)
DIM = (150, 143, 133)
ACCENT = (226, 174, 90)

FONT_B = season_paths.font("segoeuib.ttf")
FONT_R = season_paths.font("segoeui.ttf")
FONT_I = season_paths.font("segoeuii.ttf")


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    for p in (path, FONT_R, season_paths.font("arial.ttf")):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def wrap(text: str, f: ImageFont.FreeTypeFont, limit: int, maxlines: int):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if f.getlength(t) <= limit:
            cur = t
            continue
        lines.append(cur)
        cur = w
        if len(lines) == maxlines:
            break
    if cur and len(lines) < maxlines:
        lines.append(cur)
    if len(lines) == maxlines and words:
        # Ellipsis only if something actually got dropped.
        joined = " ".join(lines)
        if len(joined) < len(text) - 1:
            while f.getlength(lines[-1] + " ...") > limit and " " in lines[-1]:
                lines[-1] = lines[-1].rsplit(" ", 1)[0]
            lines[-1] += " ..."
    return lines


def main() -> int:
    rows = edit.table()
    by_beat: dict[str, list[str]] = {}
    for r in rows:
        by_beat[r["sid"]] = r["lines"]

    probe = Image.open(gen_still.plate(rows[0]["sid"]))
    tile_h = round(TILE_W * probe.height / probe.width)
    cell_h = tile_h + CAP_H
    n = len(rows)
    nrows = (n + COLS - 1) // COLS
    head = 96
    W = COLS * TILE_W + (COLS + 1) * PAD
    H = head + nrows * cell_h + (nrows + 1) * PAD

    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)

    f_title = font(FONT_B, 40)
    f_sub = font(FONT_R, 20)
    f_num = font(FONT_B, 30)
    f_what = font(FONT_B, 21)
    f_line = font(FONT_I, 19)
    f_meta = font(FONT_R, 18)

    total = sum(r["beat"] for r in rows)
    buy = sum(r["clip"] for r in rows)
    _eyebrow = identity.label()
    d.text((PAD + 4, 22),
           f"{_eyebrow}:  {shot.TITLE}" if _eyebrow else shot.TITLE,
           font=f_title, fill=INK)
    # THIS FILM IS SHOT ON LOCAL H3, so there is no buy and no price. The old
    # line quoted a typed 0.12 -- the 480p Seedance rate -- which was already
    # half the real figure once the season moved to 720p, on the one sheet that
    # exists to be approved before money moves. Now it says what actually
    # happens: GPU time, no money.
    d.text((PAD + 6, 66),
           f"{n} beats   ·   {total:.0f}s   ·   {buy}s of clip, "
           f"shot on local H3 (6-step turbo) — $0.00   ·   "
           f"plates resolved live, runtimes from edit.table()",
           font=f_sub, fill=DIM)

    for i, r in enumerate(rows):
        sid = r["sid"]
        cx = PAD + (i % COLS) * (TILE_W + PAD)
        cy = head + PAD + (i // COLS) * (cell_h + PAD)

        im = Image.open(gen_still.plate(sid)).convert("RGB")
        sheet.paste(im.resize((TILE_W, tile_h), Image.LANCZOS), (cx, cy))
        d.rectangle([cx, cy, cx + TILE_W - 1, cy + tile_h - 1],
                    outline=(60, 55, 50), width=1)

        ty = cy + tile_h + 10
        d.text((cx, ty - 2), f"{i + 1:02d}", font=f_num, fill=ACCENT)
        what = shot.BEAT[sid]["what"].split(" -- ")[0]
        d.text((cx + 46, ty + 4), what, font=f_what, fill=INK)

        meta = f"beat {sid}   ·   {r['beat']:.1f}s   ·   buy {r['clip']}s"
        d.text((cx + 46, ty + 30), meta, font=f_meta, fill=DIM)

        lids = by_beat.get(sid, [])
        if not lids:
            d.text((cx, ty + 60), "(silent)", font=f_line, fill=DIM)
        else:
            y = ty + 58
            for lid in lids:
                _, _, role, _, text = script.BY_ID[lid]
                body = text[text.index("]") + 2:] if "]" in text else text
                # THE ROLE IS NAMED WHENEVER IT IS NOT THE ONE CARRYING THE
                # FILM. It used to say "GUEST" for a single hard-coded second
                # voice; a board for a scene between three people has to say
                # which of them is talking or it is not a board.
                who = "" if role == script.NARRATOR else f"{role.upper()}  "
                colour = ACCENT if who else INK
                for k, ln in enumerate(wrap(who + body, f_line, TILE_W, 2)):
                    d.text((cx, y), ln, font=f_line, fill=colour)
                    y += 22

    os.makedirs(OUT, exist_ok=True)
    # DERIVED, NOT TYPED. This read `storyboard_s03.png`, so every film in the
    # season wrote its board out under the third session's number -- the same
    # fault verify.py's own comment describes two files away, and the reason
    # every filename in this repo comes from identity.
    dest = os.path.join(OUT, f"storyboard_{shot.SLUG}.png")
    sheet.save(dest)
    print(f"  {n} beats, {total:.1f}s  ->  {dest}  ({W}x{H}, "
          f"{os.path.getsize(dest)/1e6:.1f} MB)")
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
