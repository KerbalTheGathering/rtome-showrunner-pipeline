"""Measure the presenter's takes on things that are actually measurable.

THIS IS NOT THE COPIED VERSION AND DELIBERATELY SO. Every other tree's
measure_vo.py ranks takes by p10-p90 F0 spread. That metric is unreliable for
this voice by construction: its search band is 70-300 Hz, Dale Brinley's
fundamental sits near 100-130, and octave-DOUBLING errors land at 200-260 --
inside the band -- while octave-halving errors fall below 70 and get clipped.
Artefacts can only ever inflate it. Every audition take came back 6-17 st
against a scale whose own docstring calls 6+ "animated". Porting that here would
be shipping a number I already know is wrong.

WHAT IS MEASURED INSTEAD, all of it arithmetic on samples:

  speech / lead / tail   Where the words actually are inside the file. The mix
                         may destroy the last 75ms of a take to kill a trailing
                         transient, so a take with NO trailing silence can lose
                         real speech -- that shipped once, on the last line of
                         Session #3, and cost 15% of "Say it again". It applies
                         only to takes that MEASURE a transient now
                         (assemble.tail_spike), so a tight take is a warning
                         rather than a certainty.
  words per second       Pace. The one thing that separated the four audition
                         candidates, and the thing this part turns on.

A ONE-WORD LINE IS THE CASE THIS EXISTS FOR. "Well." came back at 3.44s. That is
either a very long delivery or half a second of speech in three seconds of room,
and those are different films. The number cannot tell you which is better; it
can tell you which one you have.

    python measure_vo.py
    python measure_vo.py --alt
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import math
import os
import struct
import subprocess
import sys
import wave

import script

HERE = os.path.dirname(os.path.abspath(__file__))
VO = os.path.join(HERE, "_vo_alt" if "--alt" in sys.argv else "_vo")
TMP = os.path.join(HERE, "_vo_wav")
FF = season_paths.FFMPEG

FLOOR_DB = -45.0             # same gate the mix's vo_tail() uses
TAIL_MIN = 0.075             # below this the mix has to shorten its own fade


def envelope(wav_path: str) -> tuple[float, float, float, float]:
    """(file secs, speech secs, leading silence, trailing silence)."""
    with wave.open(wav_path) as w:
        sr, n = w.getframerate(), w.getnframes()
        pcm = struct.unpack(f"<{n}h", w.readframes(n))
    total = n / sr
    win = int(sr * 0.010)
    k = n // win
    if not k:
        return total, 0.0, 0.0, total
    rms = [math.sqrt(sum(v * v for v in pcm[i * win:(i + 1) * win]) / win)
           / 32768.0 + 1e-12 for i in range(k)]
    live = [i for i, r in enumerate(rms) if 20 * math.log10(r) > FLOOR_DB]
    if not live:
        return total, 0.0, 0.0, total
    start, end = live[0] * 0.010, (live[-1] + 1) * 0.010
    return total, end - start, start, total - end


def main() -> int:
    os.makedirs(TMP, exist_ok=True)
    print(f"  {'ln':>3} {'seg':>3} {'sty':>4} {'file':>6} {'speech':>7} "
          f"{'lead':>6} {'tail':>6} {'w/s':>5}  note")

    tight, rows = [], []
    for lid, sid, voice, style, text in script.LINES:
        mp3 = os.path.join(VO, f"{lid}.mp3")
        if not os.path.exists(mp3):
            if "--alt" in sys.argv:
                continue
            sys.exit(f"FAIL: {mp3} missing -- run make_vo.py")
        wav = os.path.join(TMP, f"{lid}.wav")
        subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                        "-i", mp3, "-ac", "1", "-ar", "22050", wav], check=True)
        d, sp, lead, tail = envelope(wav)
        body = text[text.index("]") + 2:] if "]" in text else text
        wps = len(body.split()) / sp if sp > 0.05 else 0.0
        note = ""
        if tail < TAIL_MIN:
            note = "NO TAIL -- the mix's 75ms trim will eat speech"
            tight.append(lid)
        elif lead > 0.60:
            note = f"{lead:.2f}s of air before he speaks"
        rows.append((sid, sp))
        print(f"  {lid:>3} {sid:>3} {style:>4.2f} {d:>6.2f} {sp:>7.2f} "
              f"{lead:>6.2f} {tail:>6.2f} {wps:>5.2f}  {note}")

    if tight:
        print(f"\n  !! {len(tight)} take(s) end on a word with no room for the "
              f"fade: {', '.join(tight)}")
        print("     port vo_tail() from a film folder's assemble.py into this tree's "
              "mix, or re-roll those lines for a take that has a pad")
    else:
        print("\n  every take has room for the mix's tail fade")

    print()
    for sid in script.SIDS:
        s = sum(sp for g, sp in rows if g == sid)
        print(f"  segment {sid}: {s:5.2f}s of actual speech")
    return 0


if __name__ == "__main__":
    sys.exit(main())
