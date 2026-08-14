"""Audition candidate voices, and measure what can be measured.

I cannot hear these. What I CAN report is duration and pitch spread, which is
what separates "a drone" from "a performance" -- ~2 st is a drone, 4-5 ordinary
speech, 6+ animated (10th-to-90th percentile F0, never SD: one octave error
wrecks an SD). It ranks the takes for attention; the ear still decides.

Two candidates against the same three lines, so the comparison is a performance
rather than unrelated clips.
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import json
import math
import os
import struct
import subprocess
import sys
import urllib.request
import wave

from find_voice import key

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_audition")
FF = season_paths.FFMPEG

VOICES = {
    # "name": "<elevenlabs voice id>",
    "frederick": "uVKHymY7OYMd6OailpG5",  # Old Gnarly Narrator -- the control
}

# The candidate last line of the film, plus two carriers long enough to judge a
# voice on. A three-word line alone is not enough signal either to hear or to
# measure.
LINES = {
    "a_theline": "[dry] Eighteen, was it.",
    "b_longer": "[dry] You could have just asked. I am here every morning, "
                "and I have never once been difficult to find.",
    "c_flat": "[flat] It was never going to be more than twelve dollars. "
              "You knew that when you started.",
}

STYLE, STABILITY = 0.35, 0.5


def tts(voice_id: str, text: str, path: str, k: str) -> None:
    body = json.dumps({
        "text": text,
        "model_id": "eleven_v3",
        "voice_settings": {"stability": STABILITY, "similarity_boost": 0.75,
                           "style": STYLE, "use_speaker_boost": True},
    }).encode()
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        data=body, headers={"xi-api-key": k, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        open(path, "wb").write(r.read())


def to_wav(mp3: str, wav: str) -> None:
    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                    "-i", mp3, "-ac", "1", "-ar", "22050", wav], check=True)


def spread(wav_path: str) -> tuple[float, float, int]:
    """Duration, 10th-90th percentile F0 spread in semitones, voiced frames.

    Autocorrelation on 40 ms frames, energy-gated and voicing-gated. Reported
    with the frame count because a take with few voiced frames reads absurdly
    high -- two lines once came back at 12.8 and 21.9 st on ~100 frames and were
    octave artifacts, not liveliness.
    """
    with wave.open(wav_path) as w:
        sr, n = w.getframerate(), w.getnframes()
        pcm = struct.unpack(f"<{n}h", w.readframes(n))
    dur = n / sr
    fl, hop = int(sr * 0.040), int(sr * 0.010)
    lo, hi = int(sr / 300), int(sr / 70)          # 70-300 Hz search band
    rms = [math.sqrt(sum(v * v for v in pcm[i:i + fl]) / fl)
           for i in range(0, n - fl, hop)]
    if not rms:
        return dur, 0.0, 0
    gate = 0.25 * (sum(rms) / len(rms))
    f0 = []
    for j, i in enumerate(range(0, n - fl, hop)):
        if rms[j] < gate:
            continue
        f = [v / 32768.0 for v in pcm[i:i + fl]]
        e0 = sum(v * v for v in f) or 1e-9
        best, bl = 0.0, 0
        for lag in range(lo, min(hi, fl - 1)):
            s = sum(f[t] * f[t + lag] for t in range(fl - lag))
            nrm = s / e0
            if nrm > best:
                best, bl = nrm, lag
        if best > 0.35 and bl:                     # voicing gate
            f0.append(sr / bl)
    if len(f0) < 12:
        return dur, 0.0, len(f0)
    f0.sort()
    p10, p90 = f0[int(0.10 * len(f0))], f0[int(0.90 * len(f0)) - 1]
    return dur, 12 * math.log2(p90 / p10), len(f0)


def main() -> int:
    k = key()
    os.makedirs(OUT, exist_ok=True)
    print(f"  style {STYLE}  stability {STABILITY}  eleven_v3\n")
    for vname, vid in VOICES.items():
        for lname, text in LINES.items():
            mp3 = os.path.join(OUT, f"{vname}_{lname}.mp3")
            wav = os.path.join(OUT, f"{vname}_{lname}.wav")
            if not os.path.exists(mp3):
                tts(vid, text, mp3, k)
            to_wav(mp3, wav)
            d, st, nf = spread(wav)
            flag = "  <-- too few voiced frames to trust" if nf < 40 else ""
            print(f"  {vname:10s} {lname:10s} {d:5.2f}s   "
                  f"{st:5.2f} st  ({nf} voiced){flag}")
    print(f"\n  -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
