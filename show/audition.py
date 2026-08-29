"""Audition candidates on their OWN copy, at their OWN settings.

I CANNOT HEAR THESE AND WILL NOT PRETEND TO. What can be measured is duration
and pitch spread, and here that measurement is unusually well aimed: the brief
is `older southern american man, warm, broadcast energy`, and pitch spread is
exactly what separates a calm audiobook reader from somebody selling you
something. Most of the shared library's older Southern men are tagged
`narrative_story` and will read this copy like a bedtime story. ~2 st is a
drone, 4-5 ordinary speech, 6+ animated (10th-to-90th percentile F0, never SD --
one octave error wrecks an SD). The numbers rank them for attention. The ear
decides, and the ear is the user's.

THREE LINES, CHOSEN TO SPAN THE PART rather than to be representative, and
DERIVED FROM script.py RATHER THAN TYPED:

  intro   the first line of the reel -- the first thing in the whole feature.
          If this does not sound like television, nothing downstream can fix it.
  peak    the line scripted at the highest style. The most exposed moment in
          the reel; the joke is that he means it.
  empty   a line from the break segment, at its much lower style. The same man
          with nothing to sell. A voice that can only do enthusiasm fails here,
          and this is the take that decides it.

WHY THEY ARE DERIVED. They were three typed line ids -- `{"intro": "01",
"peak": "03", "empty": "17"}` -- and 17 is a line id from a reel that had
seventeen of them. A line id either resolves in this season or it does not
resolve at all; this one did not, and the audition raised KeyError on import
before it could render a single take. A key that exists in every season is not
an identifier, and neither is one that exists in only the last one.

EACH LINE IS RENDERED AT THE STYLE IT WILL SHIP AT. Auditioning three lines at
one averaged style would compare a performance nobody is going to hear -- and
style is the energy lever for this character, running 0.85 down to 0.25 across
the reel.
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

import script
from find_voice import key

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_audition")
FF = season_paths.FFMPEG

# Four ways of being an older Southern man, deliberately not four of the same.
# CANDIDATES. Paste voice ids from the ElevenLabs library here -- four ways of
# being the same character, deliberately not four of the same thing. Widen the
# net before narrowing it: on the season this came from, the winning read was a
# preacher's cadence, on the argument that it IS a pitchman's.
VOICES: dict[str, str] = {
    # "name": "<elevenlabs voice id>",
}

# Pulled from script.py so the audition cannot drift from the shipping copy --
# and WORKED OUT rather than typed, so it cannot name a line this reel does not
# have. See the header.
def picks() -> dict[str, str]:
    """(role -> line id), from the shape of this season's own script."""
    lines = script.LINES
    out = {"intro": lines[0][0],
           "peak": max(lines, key=lambda ln: ln[3])[0]}
    empty = [ln[0] for ln in lines if ln[1] in script.BREAK_SIDS]
    if empty:
        out["empty"] = empty[0]
    return out


PICKS = picks()
LINES = {k: (script.BY_ID[lid][4], script.BY_ID[lid][3])
         for k, lid in PICKS.items()}

assert len(set(PICKS.values())) == len(PICKS), (
    f"the audition would render the same line twice: {PICKS} -- this reel is "
    "too short, or too flat in style, for three lines to span the part")

STABILITY = script.STABILITY


def tts(voice_id: str, text: str, style: float, path: str, k: str) -> None:
    body = json.dumps({
        "text": text,
        "model_id": "eleven_v3",
        "voice_settings": {"stability": STABILITY, "similarity_boost": 0.75,
                           "style": style, "use_speaker_boost": True},
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

    Reported WITH the frame count because a take with few voiced frames reads
    absurdly high -- two lines once came back at 12.8 and 21.9 st on ~100 frames
    and were octave artifacts, not liveliness.
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
    # A CHECKER THAT MATCHES ZERO ITEMS AND PRINTS A PASS IS THE FAULT THIS
    # REPO KEEPS FINDING. VOICES ships empty on purpose -- paste your own
    # candidates in -- and the run below would otherwise render nothing,
    # tabulate nothing and end on a cheerful "0 voices x 3 lines".
    if not VOICES:
        sys.exit("FAIL: VOICES is empty, so there is nobody to audition.\n"
                 "  Paste candidate ids into VOICES at the top of this file --\n"
                 "  `python _probes/cast.py` searches the shared library by\n"
                 "  demographic if you do not have any yet.")
    k = key()
    os.makedirs(OUT, exist_ok=True)
    force = "--force" in sys.argv
    print(f"  brief: {script.HOST_BRIEF}")
    print(f"  eleven_v3, stability {STABILITY}, style per line as scripted\n")
    for lname, (text, style) in LINES.items():
        print(f"  [{lname}] style {style}  {text}")
    print()

    rows: dict[str, list] = {}
    for vname, vid in VOICES.items():
        for lname, (text, style) in LINES.items():
            mp3 = os.path.join(OUT, f"{vname}_{lname}.mp3")
            wav = os.path.join(OUT, f"{vname}_{lname}.wav")
            if force or not os.path.exists(mp3):
                try:
                    tts(vid, text, style, mp3, k)
                except Exception as e:                           # noqa: BLE001
                    print(f"  {vname:9s} {lname:6s} FAILED: {e}")
                    continue
            to_wav(mp3, wav)
            d, st, nf = spread(wav)
            rows.setdefault(vname, []).append((lname, d, st, nf))

    print(f"  {'voice':10s} {'line':7s} {'secs':>6s} {'w/s':>6s}  {'spread':>9s}")
    pace: dict[str, dict] = {}
    for vname, rs in rows.items():
        for lname, d, st, nf in rs:
            wps = len(LINES[lname][0].split()) / d if d else 0.0
            pace.setdefault(vname, {})[lname] = wps
            print(f"  {vname:10s} {lname:7s} {d:6.2f} {wps:6.2f}  "
                  f"{st:6.2f} st?")
        print()

    # THE RANKING IS ON PACE, NOT ON PITCH SPREAD -- see _f0check.py. The spread
    # column above is printed with a question mark and must not be used: at
    # 70-300 Hz the estimator lets octave DOUBLING through on voices whose
    # fundamental sits near 85-120, which is all four of these men, and every
    # take came back off the top of the metric's own scale.
    #
    # What survives is duration, which involves no estimation at all. And the
    # useful question it can answer is exactly the one the part turns on: DOES
    # HE CHANGE PACE between the line he is selling and the line where there is
    # nothing to sell? A presenter who reads segment six at pitch speed has not
    # played it, and that is the failure this casting most needs to avoid.
    print("  PACE RANGE -- words/sec on the pitch vs words/sec on the empty "
          "line.\n  Higher means he actually slows down when the board is "
          "empty.\n")
    ranked = sorted(pace.items(),
                    key=lambda kv: -(kv[1].get("peak", 0)
                                     / max(1e-6, kv[1].get("empty", 1))))
    for vname, p in ranked:
        if "peak" not in p or "empty" not in p:
            continue
        r = p["peak"] / p["empty"]
        note = ("reads both at one speed -- has not played segment six"
                if r < 1.10 else "some change" if r < 1.35 else "real range")
        print(f"  {vname:10s} pitch {p['peak']:.2f} w/s -> empty "
              f"{p['empty']:.2f} w/s   x{r:.2f}   {note}")

    print(f"\n  -> {OUT}   ({len(VOICES)} voices x {len(LINES)} lines)")
    print("  LISTEN TO THEM. Pace range says he can do both halves of the part."
          "\n  It cannot say whether he sounds like a man who believes in the "
          "show,\n  and that is the thing actually being cast.")
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
