"""Measure whether the lip sync actually lands, instead of squinting at it.

TWO REVIEWERS SAID THE MOUTH DOES NOT MATCH and the picture alone cannot settle
why, because "the sync is late", "the sync is right but the shapes are mush" and
"the sync is right and the HEAD motion underneath is fighting it" all look the
same in a frame grab. So this measures three separate things:

    WHERE   Kling only repaints what it changed, so the mean absolute difference
            between the clean picture and the synced one IS the mouth. Nothing
            is hand-placed; the region is found per segment and drawn back out
            for verification, the same discipline as board_rect.py.

    WHEN    Openness per frame inside that region against the VO envelope, and
            the correlation swept across lag. A peak away from zero is timing; a
            weak peak AT zero is shapes.

    HOW BIG How much the sync moved the mouth at all, compared with how much the
            underlying H3 clip was already moving it. If H3's own talking is
            larger than Kling's correction, the sync is being worn rather than
            applied -- which is the specific failure "flappy lips" describes.

    python sync_qc.py 01          # one segment
    python sync_qc.py             # all six
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


import math
import os
import struct
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import assemble
import edit
import shot

HERE = os.path.dirname(os.path.abspath(__file__))
FF = season_paths.FFMPEG
WORK = os.path.join(os.path.dirname(HERE), "_work")   # the SHOW tree's, not _probes' (fault 122)
OUT = os.path.join(os.path.dirname(HERE), "out")      # the SHOW tree's, not _probes' (fault 122)

FPS = 24.0
SMALL_W, SMALL_H = 360, 270          # for the difference map; plenty for a box
FONT = season_paths.font("arialbd.ttf")


def frames(path: str, w: int, h: int, gray: bool = False) -> np.ndarray:
    """Decode a whole clip into memory at a working size."""
    fmt = "gray" if gray else "rgb24"
    n = 1 if gray else 3
    p = subprocess.run(
        [season_paths.ff("ffmpeg"), "-v", "error", "-i", path,
         "-vf", f"scale={w}:{h}:flags=bilinear", "-f", "rawvideo",
         "-pix_fmt", fmt, "-"],
        capture_output=True, check=True).stdout
    a = np.frombuffer(p, np.uint8)
    return a.reshape(-1, h, w, n) if not gray else a.reshape(-1, h, w)


def envelope(sid: str, nf: int) -> np.ndarray:
    """Per-frame VO loudness, from the vo-only mix Kling was actually given."""
    wav = os.path.join(WORK, f"vo_{sid}.wav")
    if not os.path.exists(wav):
        assemble.mix(sid, nf / FPS, wav, vo_only=True)
    with wave.open(wav) as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        pcm = np.frombuffer(w.readframes(n), np.int16).astype(np.float32)
    if ch > 1:
        pcm = pcm.reshape(-1, ch).mean(axis=1)
    out = np.zeros(nf, np.float32)
    step = sr / FPS
    for i in range(nf):
        a, b = int(i * step), int((i + 1) * step)
        seg = pcm[a:b]
        if seg.size:
            out[i] = math.sqrt(float(np.mean(seg * seg))) / 32768.0
    return out


def lagged(x: np.ndarray, y: np.ndarray, lo: int = -12, hi: int = 12):
    """Pearson r between two per-frame signals, swept over frame lag."""
    def r(a, b):
        a = a - a.mean()
        b = b - b.mean()
        d = float(np.sqrt((a * a).sum() * (b * b).sum()))
        return float((a * b).sum() / d) if d else 0.0
    out = []
    for k in range(lo, hi + 1):
        if k >= 0:
            out.append((k, r(x[k:], y[:len(y) - k] if k else y)))
        else:
            out.append((k, r(x[:k], y[-k:])))
    return out


def one(sid: str) -> dict:
    clean = os.path.join(WORK, f"clean_{sid}.mp4")
    synced = os.path.join(WORK, f"synced_{sid}.mp4")
    for p in (clean, synced):
        if not os.path.exists(p):
            sys.exit(f"FAIL: {p} missing")

    a = frames(clean, SMALL_W, SMALL_H, gray=True).astype(np.float32)
    b = frames(synced, SMALL_W, SMALL_H, gray=True).astype(np.float32)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]

    # WHERE -- everything Kling touched, as a heat map, then a box around the
    # hottest connected mass. A generous threshold: the point is to bound the
    # mouth, not to trace it.
    heat = np.abs(a - b).mean(axis=0)
    thr = heat.max() * 0.35
    ys, xs = np.nonzero(heat >= thr)
    if not len(xs):
        sys.exit(f"FAIL: segment {sid} -- clean and synced are identical")
    box = (xs.min() / SMALL_W, ys.min() / SMALL_H,
           (xs.max() + 1) / SMALL_W, (ys.max() + 1) / SMALL_H)

    # WHEN / HOW BIG -- openness inside the box. In this painted style an open
    # mouth is a dark hole, so the dark fraction tracks it. The moustache is a
    # constant offset and drops out of a correlation.
    x0, y0, x1, y1 = (int(box[0] * SMALL_W), int(box[1] * SMALL_H),
                      int(box[2] * SMALL_W), int(box[3] * SMALL_H))
    ca, cb = a[:, y0:y1, x0:x1], b[:, y0:y1, x0:x1]
    lo = np.percentile(cb, 12)
    open_c = (ca < lo).mean(axis=(1, 2))
    open_s = (cb < lo).mean(axis=(1, 2))

    env = envelope(sid, n)
    rc = lagged(open_c, env)
    rs = lagged(open_s, env)
    best_c = max(rc, key=lambda t: t[1])
    best_s = max(rs, key=lambda t: t[1])
    at0_s = dict(rs)[0]

    # How much each version moves the mouth frame to frame.
    mv_c = float(np.abs(np.diff(open_c)).mean())
    mv_s = float(np.abs(np.diff(open_s)).mean())
    # And how much of the picture Kling actually repainted.
    area = (box[2] - box[0]) * (box[3] - box[1])

    return dict(sid=sid, n=n, box=box, heat=heat, area=area,
                open_c=open_c, open_s=open_s, env=env,
                best_c=best_c, best_s=best_s, at0_s=at0_s,
                mv_c=mv_c, mv_s=mv_s)


def sheet(rows: list[dict]) -> None:
    """The heat map and the two curves, drawn so the numbers can be checked."""
    W, H = 1200, 260
    f = ImageFont.truetype(FONT, 18)
    out = Image.new("RGB", (W, H * len(rows)), (16, 16, 18))
    for j, r in enumerate(rows):
        y = j * H
        hm = r["heat"] / max(1e-6, r["heat"].max())
        im = Image.fromarray((hm * 255).astype(np.uint8), "L").convert("RGB")
        im = im.resize((300, 225), Image.NEAREST)
        d = ImageDraw.Draw(im)
        b = r["box"]
        d.rectangle([b[0] * 300, b[1] * 225, b[2] * 300, b[3] * 225],
                    outline=(255, 80, 60), width=2)
        out.paste(im, (8, y + 30))

        # curves: VO envelope, then synced openness, over the same frames
        pw, ph = 860, 200
        pl = Image.new("RGB", (pw, ph), (24, 24, 28))
        pd = ImageDraw.Draw(pl)
        for series, col in ((r["env"], (90, 190, 255)),
                            (r["open_s"], (255, 190, 80)),
                            (r["open_c"], (120, 120, 130))):
            s = series - series.min()
            s = s / max(1e-9, s.max())
            pts = [(k * pw / len(s), ph - 6 - v * (ph - 14))
                   for k, v in enumerate(s)]
            pd.line(pts, fill=col, width=1)
        out.paste(pl, (320, y + 30))
        ImageDraw.Draw(out).text(
            (8, y + 6),
            f"{r['sid']}  synced r={r['best_s'][1]:+.2f} @ lag {r['best_s'][0]:+d}f "
            f"(r={r['at0_s']:+.2f} at 0)   clean r={r['best_c'][1]:+.2f} @ "
            f"{r['best_c'][0]:+d}f   motion clean {r['mv_c']:.4f} -> synced "
            f"{r['mv_s']:.4f}   blue=VO  orange=synced  grey=clean",
            font=f, fill=(235, 232, 226))
    p = os.path.join(OUT, "sync_qc.png")
    out.save(p)
    print(f"  -> {p}")


def main() -> int:
    want = [a for a in sys.argv[1:] if not a.startswith("-")] or list(shot.CUT)
    rows = []
    print(f"  {'seg':>4} {'frames':>7} {'repaint':>8} {'r@0':>7} {'best r':>7} "
          f"{'lag':>5} {'clean r':>8}  {'mouth motion clean->synced':>28}")
    for sid in want:
        r = one(sid)
        rows.append(r)
        print(f"  {sid:>4} {r['n']:>7} {r['area']*100:>7.1f}% "
              f"{r['at0_s']:>+7.2f} {r['best_s'][1]:>+7.2f} "
              f"{r['best_s'][0]:>+5d} {r['best_c'][1]:>+8.2f}  "
              f"{r['mv_c']:>12.4f} -> {r['mv_s']:.4f}")
    sheet(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
