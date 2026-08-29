"""Does the mouth ARTICULATE with the voice, or does the head just move?

it_sync.py measures motion energy in a box, which cannot tell those two apart:
a head that bobs on every stressed syllable scores exactly like a mouth that
opens on one. That ambiguity is what "off to the audio" usually is -- the timing
is fine and the lips are not doing the work.

So this measures the APERTURE instead, from the 106-point landmarks, which is
the thing itself rather than a stand-in. Two rules come with it:

    WITHIN A CLIP ONLY. mouth_open.py --check showed the score does not survive
    being pooled across segments -- a bigger face in the framing reads as a more
    open mouth -- so every number here is normalised inside its own segment and
    none of them are compared between segments as absolutes.

    LEVEL AGAINST LEVEL. Aperture and loudness are both levels, so they can be
    correlated directly. it_sync.py had to differentiate the envelope first
    because motion energy is already a derivative; none of that applies here,
    and the lag it reports is not biased early.

    python it_articulate.py            # all six
    python it_articulate.py 01 --step=2
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

import edit
import it_sync
import mouth_open
import script

HERE = os.path.dirname(os.path.abspath(__file__))
FF = season_paths.FFMPEG
WORK = os.path.join(os.path.dirname(HERE), "_work")   # the SHOW tree's, not _probes' (fault 122)
OUT = os.path.join(os.path.dirname(HERE), "out")      # the SHOW tree's, not _probes' (fault 122)
FONT = season_paths.font("arialbd.ttf")
FPS = 24.0
LAG = 12


def track(path: str, step: int = 1):
    """Per-frame mouth aperture. Frames with no face are carried forward."""
    w, h = mouth_open.size_of(path)
    raw = subprocess.run(
        [season_paths.ff("ffmpeg"), "-v", "error", "-i", path,
         "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
        capture_output=True, check=True).stdout
    ims = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)
    out, miss, last = [], 0, 0.0
    for i in range(0, len(ims), step):
        v = mouth_open.openness(ims[i])
        if v is None:
            miss += 1
            v = last
        last = v
        out.append(v)
    return np.array(out, np.float32), len(ims), miss


def one(sid: str, step: int) -> dict:
    path = os.path.join(WORK, f"synced_{sid}.mp4")
    ap, nf, miss = track(path, step)
    env_full = it_sync.envelope(sid, nf)
    env = env_full[::step][:len(ap)]
    sp_full, si_full, spans = it_sync.truth(sid, nf)
    sp, si = sp_full[::step][:len(ap)], si_full[::step][:len(ap)]

    # Normalised inside this clip, which is the only comparison the metric
    # supports. p5/p95 rather than min/max so one bad landmark frame cannot
    # set the scale.
    lo, hi = np.percentile(ap, 5), np.percentile(ap, 95)
    n = (ap - lo) / max(1e-6, hi - lo)

    rr = it_sync.lagged(n, env, -LAG // step or -1, LAG // step or 1)
    best = max(rr, key=lambda t: t[1])
    depth = float(n[sp].mean() - n[si].mean()) if si.any() and sp.any() else 0.0
    shut = float(n[si].mean())
    return dict(sid=sid, ap=ap, n=n, env=env, sp=sp, si=si, nf=nf, miss=miss,
                step=step, best=best, at0=dict(rr)[0], depth=depth, shut=shut,
                lag_s=best[0] * step / FPS)


def curves(rows: list[dict]) -> None:
    W, PH = 1180, 140
    f = ImageFont.truetype(FONT, 15)
    out = Image.new("RGB", (W, len(rows) * (PH + 34) + 10), (16, 16, 18))
    for j, r in enumerate(rows):
        y = 10 + j * (PH + 34)
        pw = W - 24
        pl = Image.new("RGB", (pw, PH), (26, 26, 30))
        pd = ImageDraw.Draw(pl)
        run = None
        for i, v in enumerate(np.append(r["sp"], False)):
            if v and run is None:
                run = i
            elif not v and run is not None:
                pd.rectangle([run * pw / len(r["n"]), 0,
                              i * pw / len(r["n"]), PH], fill=(38, 44, 38))
                run = None
        for s, col in ((r["env"], (90, 190, 255)), (r["n"], (255, 190, 80))):
            v = s - s.min()
            v = v / max(1e-9, v.max())
            pd.line([(k * pw / len(v), PH - 4 - t * (PH - 10))
                     for k, t in enumerate(v)], fill=col, width=1)
        out.paste(pl, (12, y + 22))
        ImageDraw.Draw(out).text(
            (12, y + 2),
            f"segment {r['sid']}   green = typed speech   blue = VO   "
            f"orange = MOUTH APERTURE   depth {r['depth']:+.2f}  "
            f"r={r['at0']:+.2f}@0  best {r['best'][1]:+.2f} @ "
            f"{r['lag_s']*1000:+.0f}ms", font=f, fill=(235, 232, 226))
    p = os.path.join(OUT, "it_articulate.png")
    out.save(p)
    print(f"  -> {p}")


def main() -> int:
    step = 1
    for a in sys.argv[1:]:
        if a.startswith("--step="):
            step = int(a.split("=", 1)[1])
    want = [a for a in sys.argv[1:] if not a.startswith("-")] or list(script.SIDS)
    rows = []
    print(f"  {'seg':>4} {'frames':>7} {'noface':>7} {'depth':>7} {'shut':>6} "
          f"{'r@0':>7} {'best r':>7} {'lag':>9}   verdict")
    for sid in want:
        r = one(sid, step)
        rows.append(r)
        bad = []
        if r["depth"] < 0.15:
            bad.append("FLAT-LIPS")
        if abs(r["lag_s"]) > 0.080:
            bad.append(f"LAG{r['lag_s']*1000:+.0f}ms")
        print(f"  {sid:>4} {r['nf']:>7} {r['miss']:>7} {r['depth']:>+7.2f} "
              f"{r['shut']:>6.2f} {r['at0']:>+7.2f} {r['best'][1]:>+7.2f} "
              f"{r['lag_s']*1000:>+7.0f}ms   {' '.join(bad) if bad else 'ok'}")
    curves(rows)
    print("\n  depth = how much wider the mouth is during speech than during "
          "the typed\n  silences, on this clip's own scale. Not comparable "
          "between segments.")
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
