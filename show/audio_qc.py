"""What the season's audio actually measures, part by part, before anybody EQs.

WHY PER PART AND NOT ON THE FEATURE. `feature.py` joins thirteen finished files
with the concat demuxer and stream-copies the audio, so the feature has no mix of
its own: it inherits thirteen independent normalisations. A single number for the
whole 14 minutes would average exactly the thing worth finding, which is whether
a viewer has to touch the volume when a part changes.

WHAT IS MEASURED AND WHY EACH ONE

    LUFS-I   integrated loudness, the number a platform matches on. Differences
             under ~1 LU are inaudible; 3+ LU is a reach for the remote.
    LRA      loudness range. On narration this reads as "how even is the read";
             a big number over a whole part usually means the score is moving,
             not the voice.
    TP       true peak, measured with 4x oversampling. Above -1.0 dBTP an AAC or
             Opus transcode can clip on playback even though the PCM never does.
    SHORT    the loudest and quietest 3s windows INSIDE the part, which is what
             catches a single beat sitting low rather than a whole film.

NOTHING HERE IS A VERDICT ON TONE. Loudness meters are deaf to EQ -- two takes
can measure identically and one still be boxy. The spectrum pass is separate and
it compares LIKE WITH LIKE (voice against voice), because a film's average
spectrum is mostly its music.

    python audio_qc.py              # the thirteen parts
    python audio_qc.py --spectrum   # and the VO band balance, per film
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import json
import os
import re
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KREA = os.path.dirname(HERE)
FF = season_paths.FFMPEG
OUT = os.path.join(HERE, "out")

SEASON: list[tuple] = [
    # Filled from parts.py rather than typed -- see feature.py for why a
    # second list of what the season is turns into two lists that disagree.
]
COLD_OPEN = os.path.join(KREA, "INTRO_src", "out", "cold_open.mp4")


def parts() -> list[tuple[str, str]]:
    got = [("COLD OPEN", COLD_OPEN)]
    for sid, src, film, title in SEASON:
        got.append((f"bounty {sid}", os.path.join(OUT, f"bounty_{sid}.mp4")))
        got.append((title, os.path.join(KREA, src, "out", film)))
    return [(n, p) for n, p in got if os.path.exists(p)]


def ebur128(path: str) -> dict:
    """Integrated, range and true peak, from one pass of the real meter."""
    r = subprocess.run(
        [season_paths.ff("ffmpeg"), "-v", "info", "-nostats", "-i", path,
         "-af", "ebur128=peak=true:framelog=verbose", "-f", "null", "-"],
        capture_output=True, text=True)
    tail = r.stderr[-3000:]
    def grab(label: str) -> float:
        m = re.search(rf"{label}:\s*(-?\d+\.?\d*)", tail)
        return float(m.group(1)) if m else float("nan")
    return {"I": grab("I"), "LRA": grab("LRA"), "TP": grab("Peak")}


def shorts(path: str) -> tuple[float, float]:
    """Loudest and quietest 3s windows, from the meter's own short-term track.

    `-v verbose`, NOT `-v info`. `framelog=verbose` prints the per-frame lines at
    AV_LOG_VERBOSE, so at info the summary still arrives and the frame track is
    silently absent -- which reads as "this file has no short-term data" rather
    than as a wrong flag. It returned NaN for all thirteen parts before this.
    """
    r = subprocess.run(
        [season_paths.ff("ffmpeg"), "-v", "verbose", "-nostats",
         "-i", path, "-af", "ebur128=framelog=verbose", "-f", "null", "-"],
        capture_output=True, text=True)
    v = [float(m) for m in re.findall(r"\bS:\s*(-?\d+\.\d+)", r.stderr)]
    v = [x for x in v if x > -70.0]          # drop the meter's warm-up and gaps
    if len(v) < 10:
        return float("nan"), float("nan")
    return max(v), float(np.percentile(v, 5))


def pcm(path: str, sr: int = 48000) -> np.ndarray:
    raw = subprocess.run(
        [season_paths.ff("ffmpeg"), "-v", "error", "-i", path,
         "-vn", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(raw, "<i2").astype(np.float32) / 32768.0


BANDS = [(20, 80, "rumble"), (80, 200, "chest"), (200, 500, "boxy"),
         (500, 2000, "body"), (2000, 5000, "presence"),
         (5000, 9000, "sibilance"), (9000, 16000, "air")]


def spectrum(x: np.ndarray, sr: int = 48000) -> dict[str, float]:
    """Band energy in dB relative to the whole, on the LOUD half only.

    THE QUIET HALF IS NOT THE VOICE. Averaging a whole take includes its
    silences, which are room and encoder noise, and that drags the top and
    bottom bands around by more than any EQ move being considered. Only frames
    above the take's own median RMS are counted.
    """
    win = 2048
    n = len(x) // win
    f = np.abs(np.fft.rfft(x[:n * win].reshape(n, win) * np.hanning(win),
                           axis=1)) ** 2
    rms = np.sqrt((x[:n * win].reshape(n, win) ** 2).mean(axis=1) + 1e-12)
    loud = f[rms > np.median(rms)]
    if not len(loud):
        loud = f
    p = loud.mean(axis=0)
    freqs = np.fft.rfftfreq(win, 1 / sr)
    tot = p.sum() + 1e-20
    return {name: 10 * np.log10(p[(freqs >= lo) & (freqs < hi)].sum() / tot
                                + 1e-20)
            for lo, hi, name in BANDS}


def vo_concat(src: str) -> np.ndarray:
    """Every VO take of one film, end to end, as the model rendered it."""
    d = os.path.join(KREA, src, "_vo")
    if not os.path.isdir(d):
        return np.array([])
    got = sorted(f for f in os.listdir(d) if f.endswith(".mp3"))
    return np.concatenate([pcm(os.path.join(d, f)) for f in got]) if got \
        else np.array([])


def main() -> int:
    ps = parts()
    print(f"  {'part':<20} {'LUFS-I':>7} {'LRA':>6} {'TP dB':>7} "
          f"{'loud 3s':>8} {'quiet 3s':>9}")
    rows = []
    for name, p in ps:
        m = ebur128(p)
        hi, lo = shorts(p)
        rows.append((name, m["I"], m["LRA"], m["TP"], hi, lo))
        print(f"  {name:<20} {m['I']:>7.1f} {m['LRA']:>6.1f} {m['TP']:>7.1f} "
              f"{hi:>8.1f} {lo:>9.1f}")

    ints = [r[1] for r in rows if not np.isnan(r[1])]
    tps = [r[3] for r in rows if not np.isnan(r[3])]
    print(f"\n  integrated spread: {max(ints) - min(ints):.1f} LU "
          f"({min(ints):.1f} .. {max(ints):.1f})")
    print(f"  worst true peak:   {max(tps):+.1f} dBTP")
    print("  under ~1 LU is inaudible; 3+ LU is a reach for the remote. "
          "Above -1.0 dBTP\n  a lossy transcode can clip on playback.")

    if "--spectrum" in sys.argv:
        print(f"\n  VO BAND BALANCE, dB relative to each film's own total "
              f"(loud half only)")
        print(f"  {'film':<16}" + "".join(f"{n:>11}" for _, _, n in BANDS))
        ref = None
        for sid, src, film, title in SEASON:
            x = vo_concat(src)
            if not len(x):
                continue
            s = spectrum(x)
            if ref is None:
                ref = s
            print(f"  {title:<16}" + "".join(f"{s[n]:>11.1f}"
                                             for _, _, n in BANDS))
        print("\n  These are the RAW ElevenLabs takes -- one voice, one model, "
              "so the six\n  rows should agree closely. A row that does not is "
              "a take problem, not an EQ\n  problem, and EQ applied to the bus "
              "would spread it to the other five.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
