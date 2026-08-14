"""Is each VO line where the edit says it is, in the DELIVERED film?

THE GROUND TRUTH IS THE EDIT TABLE, NOT AN EARLIER BUILD. `edit.table()` says
where every line belongs; each take on disk is the exact signal that was placed
there. So the check is a correlation of the take against the film's own audio,
searched around the expected offset, and the answer is a lag in milliseconds.
That works without a reference build to compare against and it cannot be fooled
by the whole film shifting together.

WHY CORRELATION AND NOT SILENCE DETECTION. The score plays under the narration,
so the gaps between lines are not silent and an onset detector finds the music.
The take itself is the matched filter.

It correlates the ENVELOPE, not the waveform. The mix is the take plus a bed
plus a limiter, so sample-level phase is long gone; the 50 Hz amplitude envelope
survives all of that and is what "in sync" means to an ear anyway.

    python vo_placement.py            # every film
    python vo_placement.py S3_HARBOUR
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

import audio_qc

FF = season_paths.FFMPEG
KREA = audio_qc.KREA
ENV_HZ = 50.0            # envelope rate; 20 ms resolution
SEARCH = 2.0             # seconds either side of the expected offset


def env(x: np.ndarray, sr: int) -> np.ndarray:
    w = int(sr / ENV_HZ)
    n = len(x) // w
    if not n:
        return np.array([])
    e = np.sqrt((x[:n * w].reshape(n, w) ** 2).mean(axis=1) + 1e-12)
    return e - e.mean()


def load(path: str, sr: int = 16000) -> np.ndarray:
    raw = subprocess.run(
        [season_paths.ff("ffmpeg"), "-v", "error", "-i", path,
         "-vn", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(raw, "<i2").astype(np.float32) / 32768.0


def check(tree: str, film: str) -> list[tuple[str, float, float, float]]:
    sys.path.insert(0, os.path.join(KREA, tree))
    for m in ("edit", "script", "shot", "make_video", "assemble"):
        sys.modules.pop(m, None)
    import edit                                       # noqa: E402
    rows = edit.table()

    mix = env(load(os.path.join(KREA, tree, "out", film)), 16000)
    out = []
    t = 0.0
    for r in rows:
        off = t + r["lead"]
        for lid in r["lines"]:
            take = env(load(os.path.join(KREA, tree, "_vo", f"{lid}.mp3")),
                       16000)
            d = edit.vo_dur(lid)
            if len(take) < 10:
                continue
            lo = max(0, int((off - SEARCH) * ENV_HZ))
            hi = min(len(mix), int((off + SEARCH) * ENV_HZ) + len(take))
            seg = mix[lo:hi]
            if len(seg) < len(take) + 4:
                continue
            c = np.correlate(seg, take, mode="valid")
            k = int(np.argmax(c))
            found = (lo + k) / ENV_HZ
            peak = float(c[k])
            second = float(np.partition(c, -2)[-2]) if len(c) > 1 else 0.0
            sharp = peak / (abs(second) + 1e-9)
            out.append((lid, off, found - off, sharp))
            off += d
        t += r["beat"]
    sys.path.pop(0)
    return out


def main() -> int:
    want = [a for a in sys.argv[1:] if not a.startswith("-")]
    films = [(s, f) for _sid, s, f, _t in audio_qc.SEASON
             if not want or s in want]
    worst = []
    for tree, film in films:
        p = os.path.join(KREA, tree, "out", film)
        if not os.path.exists(p):
            continue
        rowsr = check(tree, film)
        lags = [lag for _l, _e, lag, _s in rowsr]
        print(f"\n  {tree}  ({len(rowsr)} lines)")
        print(f"    {'line':>5} {'expected':>9} {'lag ms':>8}")
        for lid, exp, lag, _sharp in rowsr:
            flag = "  <-- OFF" if abs(lag) > 0.060 else ""
            print(f"    {lid:>5} {exp:>8.2f}s {lag*1000:>+8.0f}{flag}")
        med = float(np.median(lags))
        print(f"    median {med*1000:+.0f} ms   worst "
              f"{max(lags, key=abs)*1000:+.0f} ms")
        worst.append((abs(med), tree, med))
    if worst:
        worst.sort(reverse=True)
        print(f"\n  Largest MEDIAN offset: {worst[0][2]*1000:+.0f} ms "
              f"({worst[0][1]})")
        print("  A median near zero with scatter is measurement noise. A median "
              "that is not\n  zero, and agrees across lines, is the film "
              "actually being out of step.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
