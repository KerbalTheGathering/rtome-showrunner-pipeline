"""Find the frame where the picture breaks, without watching all six segments.

WHY A WHOLE-FRAME AVERAGE MISSES IT. Segment 03 shipped with the announcer's
clasped hands swelling into a smooth pale blob for about five frames at 13.2s.
Averaged over the frame that is nothing -- the hands are a few percent of the
picture and the mean frame-to-frame difference put it below several ordinary
head turns. It only became obvious when the difference was measured PER BLOCK
and the worst block kept: a local catastrophe scores like a local catastrophe.

    worst 16x16 block of |frame[i] - frame[i-1]|, per frame

SCORED AGAINST THE CLIP'S OWN MEDIAN, never an absolute. How much a segment
moves depends on how animated that take is, and `mouth_open.py --check` already
taught this project that a score which cannot survive being pooled across
segments must not be thresholded across them either. So the unit here is
"multiples of this clip's median worst-block", and nothing is compared between
clips except that ratio.

    THE ROLL IS NOT A GLITCH. On a baked segment the tube rolls the picture for
    the first 14 frames, which is a deliberate tear and scores enormously. Those
    frames are skipped, and the number of skipped frames is printed so the skip
    can never quietly hide a real fault.

Validated on the two takes whose faults had already been SEEN: it puts the hand
blob at 4.4x and the webbed-finger flipper at 5.8x, both far clear of the ~2.5x
that ordinary gesture reaches.

TWO THINGS IT FLAGS THAT ARE NOT FAULTS, both confirmed by looking:

    THE BOARD TYPE LANDING. A line of type cutting in is a large change confined
    to a small block -- exactly the shape of a glitch. Segment 05's 5.3x peak is
    "$300" arriving on the felt. Check the flagged block against the type marks
    before believing it.

    A SEGMENT THAT BARELY MOVES. The ratio is against the clip's own median, so
    a still take has a tiny denominator: segment 06 sits at median 3.50 because
    he is silent most of it, and an ordinary mouth movement reads as 11.9x. The
    ratio is only meaningful where there is normal motion to be a multiple OF.
    Read the median column first; a low one means the ratios above it are soft.

    python glitch_scan.py                  # every synced segment
    python glitch_scan.py --shipped        # the baked bounty segments
    python glitch_scan.py 03 --sheet       # and draw the worst moments
"""
from __future__ import annotations

import os as _os, sys as _sys
# THREE DIRNAMES REACH THE SEASON ROOT FROM HERE, TWO ONLY REACH show/. This
# preamble was copied verbatim from show/*.py, which lives one level higher --
# so `import season_paths` failed outright and every probe in this folder was
# unrunnable. Nothing noticed, because nothing in this repo imported them.
_here = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:0] = [_os.path.dirname(_here),                     # show/ -- edit, script
                 _os.path.dirname(_os.path.dirname(_here))]   # the season root
import season_paths                                                # noqa: E402


import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import it_sync
import script

HERE = os.path.dirname(os.path.abspath(__file__))
FF = season_paths.FFMPEG
WORK = os.path.join(os.path.dirname(HERE), "_work")   # the SHOW tree's, not _probes' (fault 122)
OUT = os.path.join(os.path.dirname(HERE), "out")      # the SHOW tree's, not _probes' (fault 122)
FONT = season_paths.font("arialbd.ttf")

BLOCK = 16
SW, SH = 320, 240
ROLL_SKIP = 16          # the tube's roll is 14; two frames of margin
FLAG = 3.5              # multiples of the clip's own median worst-block


def score(path: str, skip: int):
    a = it_sync.frames_gray(path, SW, SH).astype(np.float32)
    d = np.abs(np.diff(a, axis=0))
    hh, ww = SH // BLOCK, SW // BLOCK
    blk = d[:, :hh * BLOCK, :ww * BLOCK].reshape(
        len(d), hh, BLOCK, ww, BLOCK).mean(axis=(2, 4))
    mx = blk.max(axis=(1, 2))
    where = [np.unravel_index(b.argmax(), b.shape) for b in blk]
    med = float(np.median(mx[skip:])) if len(mx) > skip else float(np.median(mx))
    return mx, np.array(where), med


def one(sid: str, shipped: bool) -> dict:
    path = (os.path.join(OUT, f"bounty_{sid}.mp4") if shipped
            else os.path.join(WORK, f"synced_{sid}.mp4"))
    if not os.path.exists(path):
        sys.exit(f"FAIL: {path} missing")
    skip = ROLL_SKIP if shipped else 1
    mx, where, med = score(path, skip)
    ratio = mx / max(1e-6, med)
    hits = [(i + 1, float(ratio[i]), tuple(where[i]))
            for i in range(skip, len(ratio)) if ratio[i] >= FLAG]
    hits.sort(key=lambda t: -t[1])
    return dict(sid=sid, path=path, med=med, ratio=ratio, skip=skip,
                hits=hits, peak=float(ratio[skip:].max()) if len(ratio) > skip
                else 0.0, peak_f=int(np.argmax(ratio[skip:])) + skip + 1)


def sheet(rows: list[dict]) -> None:
    picks = [(r, f) for r in rows for f, _, _ in r["hits"][:2]]
    if not picks:
        print("  nothing to draw")
        return
    CW = CH = 300
    f = ImageFont.truetype(FONT, 15)
    cols = min(6, max(1, len(picks)))
    n = len(picks) * 3
    rowsn = -(-n // cols)
    out = Image.new("RGB", (cols * (CW + 5) + 5, rowsn * (CH + 26) + 5),
                    (16, 16, 18))
    d = ImageDraw.Draw(out)
    k = 0
    for r, fr in picks:
        W, H = it_sync.size_of(r["path"])
        for off in (-3, 0, 3):
            i = max(0, fr + off)
            raw = subprocess.run(
                [season_paths.ff("ffmpeg"), "-v", "error", "-i", r["path"],
                 "-vf", f"select=eq(n\\,{i})", "-frames:v", "1", "-f",
                 "rawvideo", "-pix_fmt", "rgb24", "-"],
                capture_output=True, check=True).stdout
            im = Image.fromarray(
                np.frombuffer(raw, np.uint8).reshape(H, W, 3), "RGB")
            im = im.crop((int(W * .30), int(H * .28), int(W * .84),
                          int(H * .82))).resize((CW, CH), Image.LANCZOS)
            x = 5 + (k % cols) * (CW + 5)
            y = 5 + (k // cols) * (CH + 26)
            out.paste(im, (x, y))
            d.text((x + 3, y + CH + 4),
                   f"{r['sid']} f{i} {i/24:.2f}s{'  <-- PEAK' if off == 0 else ''}",
                   font=f, fill=(255, 90, 70) if off == 0 else (190, 190, 195))
            k += 1
    p = os.path.join(OUT, "glitch_scan.png")
    out.save(p)
    print(f"  -> {p}")


def main() -> int:
    shipped = "--shipped" in sys.argv
    want = [a for a in sys.argv[1:] if not a.startswith("-")] or list(script.SIDS)
    rows = []
    print(f"  {'seg':>4} {'median':>7} {'peak':>7} {'at':>7} {'time':>8} "
          f"{'over %.1fx':>10}   verdict" % FLAG)
    for sid in want:
        r = one(sid, shipped)
        rows.append(r)
        print(f"  {sid:>4} {r['med']:>7.2f} {r['peak']:>6.1f}x "
              f"{r['peak_f']:>7} {r['peak_f']/24:>7.2f}s {len(r['hits']):>10}   "
              f"{'LOOK' if r['hits'] else 'clean'}")
        for fr, v, wh in r["hits"][:4]:
            print(f"        f{fr} at {fr/24:.2f}s  {v:.1f}x  "
                  f"(block row {wh[0]}/{SH//BLOCK} col {wh[1]}/{SW//BLOCK})")
    if "--sheet" in sys.argv:
        sheet(rows)
    print(f"\n  skipped the first {rows[0]['skip']} frames "
          f"({'tube roll' if shipped else 'first-frame step'}).")
    print("  A ratio only says where to look. The frames decide.")
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
