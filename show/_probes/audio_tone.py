"""Is there an EQ move to make on the VO or the score? Measured on the stems.

MEASURED ON THE STEMS, NOT THE FILM. A finished mix is voice plus score plus a
sidechain, and its average spectrum is mostly whichever is louder. Anything read
off the delivered file and called "the voice is boxy" is really a statement about
the bed. So the voice is measured from `_vo/*.mp3` and the score from
`_music/*.mp3`, separately.

THIRD-OCTAVE, AND ENERGY PER OCTAVE RATHER THAN PER BAND. Summing raw FFT bins
into arbitrary bands makes a narrow band look quiet and a wide one look loud for
no reason but its width -- 200-500 Hz and 2-5 kHz differ by a factor of ten in
width, so comparing their sums says nothing about tone. Everything here is
normalised to energy per octave, which is what the ear approximately does.

THE LOUD HALF ONLY. Averaging a whole take includes its silences, which are
codec noise, and that moves the top and bottom bands more than any EQ under
consideration.

    python audio_tone.py            # voice and score, per film
    python audio_tone.py --mask     # where they compete
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
SR = 48000

# Third-octave centres from 31.5 Hz to 16 kHz.
CENTRES = [31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630,
           800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000,
           10000, 12500, 16000]


def octave_spectrum(x: np.ndarray) -> np.ndarray:
    """dB per octave of bandwidth, referenced to the take's own total."""
    win = 4096
    n = len(x) // win
    if not n:
        return np.full(len(CENTRES), np.nan)
    fr = x[:n * win].reshape(n, win)
    rms = np.sqrt((fr ** 2).mean(axis=1) + 1e-12)
    fr = fr[rms > np.median(rms)]
    if not len(fr):
        return np.full(len(CENTRES), np.nan)
    p = (np.abs(np.fft.rfft(fr * np.hanning(win), axis=1)) ** 2).mean(axis=0)
    freqs = np.fft.rfftfreq(win, 1 / SR)
    tot = p.sum() + 1e-20
    out = []
    for c in CENTRES:
        lo, hi = c / 2 ** (1 / 6), c * 2 ** (1 / 6)
        m = (freqs >= lo) & (freqs < hi)
        oct_frac = np.log2(hi / lo)
        out.append(10 * np.log10((p[m].sum() / tot) / oct_frac + 1e-20)
                   if m.any() else np.nan)
    return np.array(out)


def below(x: np.ndarray, hz: float) -> float:
    """Fraction of total energy under `hz`, as a percentage."""
    win = 4096
    n = len(x) // win
    fr = x[:n * win].reshape(n, win)
    p = (np.abs(np.fft.rfft(fr * np.hanning(win), axis=1)) ** 2).mean(axis=0)
    freqs = np.fft.rfftfreq(win, 1 / SR)
    return 100.0 * p[freqs < hz].sum() / (p.sum() + 1e-20)


def cutoff(x: np.ndarray) -> float:
    """Where the take stops -- the codec's lowpass, if it has one."""
    win = 4096
    n = len(x) // win
    fr = x[:n * win].reshape(n, win)
    p = (np.abs(np.fft.rfft(fr * np.hanning(win), axis=1)) ** 2).mean(axis=0)
    freqs = np.fft.rfftfreq(win, 1 / SR)
    peak = p[(freqs > 200) & (freqs < 4000)].max()
    live = freqs[p > peak * 1e-6]
    return float(live.max()) if len(live) else float("nan")


def stem(src: str, kind: str) -> np.ndarray:
    d = os.path.join(KREA, src, "_vo" if kind == "vo" else "_music")
    if not os.path.isdir(d):
        return np.array([])
    got = sorted(f for f in os.listdir(d) if f.endswith(".mp3"))
    if not got:
        return np.array([])
    return np.concatenate([audio_qc.pcm(os.path.join(d, f), SR) for f in got])


SHOW = [63, 80, 125, 250, 500, 1000, 2000, 4000, 8000, 12500]


def table(kind: str) -> dict[str, np.ndarray]:
    idx = [CENTRES.index(c) for c in SHOW]
    print(f"\n  {kind.upper()} -- dB per octave, relative to each film's own "
          f"total (loud half)")
    print(f"  {'film':<16}" + "".join(f"{c:>8g}" for c in SHOW)
          + f"{'<80Hz':>9}{'cutoff':>9}")
    got = {}
    for sid, src, _film, title in audio_qc.SEASON:
        x = stem(src, kind)
        if not len(x):
            continue
        s = octave_spectrum(x)
        got[title] = s
        print(f"  {title:<16}" + "".join(f"{s[i]:>8.1f}" for i in idx)
              + f"{below(x, 80):>8.2f}%{cutoff(x)/1000:>8.1f}k")
    return got


def main() -> int:
    vo = table("vo")
    mus = table("music")

    if vo:
        a = np.array(list(vo.values()))
        spread = np.nanmax(a, axis=0) - np.nanmin(a, axis=0)
        print(f"\n  VO agreement across the six films, per third-octave: "
              f"worst {np.nanmax(spread):.1f} dB at "
              f"{CENTRES[int(np.nanargmax(spread))]:g} Hz")
        print("  One voice, one model, one setting -- so a band that disagrees "
              "is a TAKE\n  difference and EQ on the bus would spread it, not "
              "fix it.")

    if "--mask" in sys.argv and vo and mus:
        v = np.nanmean(np.array(list(vo.values())), axis=0)
        m = np.nanmean(np.array(list(mus.values())), axis=0)
        print(f"\n  WHERE THEY COMPETE -- score minus voice, dB per octave")
        print(f"  {'Hz':>8} {'voice':>8} {'score':>8} {'score-voice':>12}")
        for c in SHOW:
            i = CENTRES.index(c)
            print(f"  {c:>8g} {v[i]:>8.1f} {m[i]:>8.1f} {m[i] - v[i]:>+12.1f}")
        print("\n  Positive where the bed is denser than the voice. The band "
              "that matters for\n  intelligibility is 1-4 kHz; a bed that is "
              "hotter than the voice THERE is what\n  a sidechain is covering "
              "for, and carving it is cheaper than ducking harder.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
