"""How far has the delivered sound moved off the file that drove the lips?

THE DRIVER IS `_work/vo_XX.wav`. italk.py resamples it to 16k mono, hands it to
WanInfiniteTalkToVideo as node 9, and the mouths in the render are a function of
THAT waveform starting at t=0. Anything downstream that shifts a sample shifts
the words off the mouth, and nothing downstream is allowed to.

So this measures the one number that matters: the lag, in milliseconds, between
the driver and whatever sound actually ships. Zero is the only passing value --
not "small", zero -- because every stage between them is either a scalar gain or
a straight copy, and a pure gain cannot produce a lag.

Correlation runs on the ENERGY ENVELOPE, not the waveform. The delivered mix is
a different gain, a different sample rate and has a brass sting under the head,
so sample-wise correlation is meaningless; the envelope of the speech survives
all three. The sting window is excluded for the same reason -- it is music the
driver never had, and it would drag the peak toward itself.

    python sync_probe.py                  # all six, driver vs shipped segment
    python sync_probe.py --feature        # ... and vs the assembled feature
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import os
import subprocess
import sys

import numpy as np

import edit
import shot

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "_work")
OUT = os.path.join(HERE, "out")
FF = season_paths.FFMPEG

SR = 1000                 # envelope rate: 1 ms per bin, finer than any lip cue
HOP = 0.010               # 10 ms envelope frames
SKIP_HEAD = 4.5           # the sting sits under the first four seconds
MAX_LAG = 1.0             # search +/- one second


def pcm(path: str, ss: float = 0.0, t: float | None = None) -> np.ndarray:
    """Mono float samples at SR Hz."""
    cmd = [season_paths.ff("ffmpeg"), "-v", "error"]
    if ss:
        cmd += ["-ss", f"{ss:.3f}"]
    if t:
        cmd += ["-t", f"{t:.3f}"]
    cmd += ["-i", path, "-map", "a:0", "-ac", "1", "-ar", str(SR * 16),
            "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def envelope(x: np.ndarray, rate: int) -> np.ndarray:
    n = int(HOP * rate)
    m = len(x) // n
    e = np.sqrt((x[:m * n].reshape(m, n) ** 2).mean(axis=1) + 1e-12)
    e = np.log10(e)
    return e - e.mean()


def lag_ms(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Lag of b behind a, in ms, and the peak correlation."""
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    a = a / (np.linalg.norm(a) + 1e-12)
    b = b / (np.linalg.norm(b) + 1e-12)
    k = int(MAX_LAG / HOP)
    c = np.correlate(b, a, mode="full")
    mid = len(c) // 2
    win = c[mid - k:mid + k + 1]
    i = int(np.argmax(win))
    # Parabolic interpolation, so a sub-frame offset is not rounded to 10 ms.
    if 0 < i < len(win) - 1:
        y0, y1, y2 = win[i - 1], win[i], win[i + 1]
        d = (y0 - y2) / (2 * (y0 - 2 * y1 + y2) + 1e-12)
    else:
        d = 0.0
    return (i - k + d) * HOP * 1000.0, float(win[i])


def main() -> int:
    rate = SR * 16
    print(f"  {'seg':>4} {'target':>28} {'lag':>9} {'r':>6}")
    worst = 0.0
    for sid in shot.CUT:
        drv = os.path.join(WORK, f"vo_{sid}.wav")
        if not os.path.exists(drv):
            print(f"  {sid:>4}  no driver")
            continue
        secs = edit.FRAMES[sid] / 24.0
        a = envelope(pcm(drv, SKIP_HEAD, secs - SKIP_HEAD), rate)
        for label, path, ss in (
                ("synced_XX.mp4 (render)",
                 os.path.join(WORK, f"synced_{sid}.mp4"), SKIP_HEAD),
                ("mix_XX.wav (normalised)",
                 os.path.join(WORK, f"mix_{sid}.wav"), SKIP_HEAD),
                ("bounty_XX.mp4 (shipped)",
                 os.path.join(OUT, f"bounty_{sid}.mp4"), SKIP_HEAD)):
            if not os.path.exists(path):
                continue
            has_a = subprocess.run(
                [season_paths.ff("ffprobe"), "-v", "error",
                 "-select_streams", "a", "-show_entries", "stream=index",
                 "-of", "csv=p=0", path],
                capture_output=True, text=True).stdout.strip()
            if not has_a:
                continue
            b = envelope(pcm(path, ss, secs - SKIP_HEAD), rate)
            ms, r = lag_ms(a, b)
            worst = max(worst, abs(ms) if r > 0.3 else 0.0)
            note = "" if r > 0.3 else "   (r too low to trust)"
            print(f"  {sid:>4} {label:>28} {ms:>+8.1f}ms {r:>6.2f}{note}")
        print()
    print(f"  worst trusted lag: {worst:+.1f} ms "
          f"({worst * 24 / 1000:.2f} frames at 24fps)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
