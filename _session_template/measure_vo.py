"""Rank the takes for attention before any video is bought.

MEASURE MONOTONE, DO NOT ADJUDICATE IT BY EAR I DO NOT HAVE. 10th-to-90th
percentile F0 spread in semitones: ~2 st is a drone, 4-5 ordinary speech, 6+
animated. Two caveats that must travel with every number quoted:

  - A take with FEW VOICED FRAMES reads absurdly high. Anything under ~40 voiced
    frames is an octave artifact, not liveliness, and is flagged rather than
    ranked. A one-second line is exactly this case, and so is any creaky
    voice -- period doubling breaks autocorrelation outright, which is why the
    audition numbers for Strig and Frederick were thrown away.
  - Pitch range measures MOVEMENT, not good phrasing. This ranks lines for a
    human to listen to. It does not decide anything.

INTUITION IS BACKWARDS HERE and that is the point of running it: on STEINHATCHEE
the three lines carrying the most feeling came back the FLATTEST while the arch
comedy beats were lively. THE WINDOW IN WHICH RE-ROLLING VO IS FREE IS NOW,
before a clip exists, because a take's duration sizes its beat and the beat
sizes the clip.
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import os
import subprocess
import sys

import script
from audition import spread

HERE = os.path.dirname(os.path.abspath(__file__))
VO = os.path.join(HERE, "_vo_alt" if "--alt" in sys.argv else "_vo")
TMP = os.path.join(HERE, "_vo_wav")
FF = season_paths.FFMPEG

LOW = 5.0                    # below this, worth a listen and maybe a re-roll


def main() -> int:
    os.makedirs(TMP, exist_ok=True)
    rows = []
    for lid, sid, role, style, text in script.LINES:
        mp3 = os.path.join(VO, f"{lid}.mp3")
        if not os.path.exists(mp3):
            if "--alt" in sys.argv:
                continue          # an alt folder holds only the candidates
            sys.exit(f"FAIL: {mp3} missing -- run make_vo.py")
        wav = os.path.join(TMP, f"{lid}.wav")
        subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                        "-i", mp3, "-ac", "1", "-ar", "22050", wav], check=True)
        d, st, nf = spread(wav)
        rows.append((lid, sid, style, d, st, nf, role))

    print(f"  {'line':>4} {'beat':>4} {'sty':>4} {'secs':>6} {'spread':>7}  note")
    ranked = []
    # THE ESTIMATOR IS TUNED TO ONE VOICE AND THERE MAY BE SEVERAL. Its
    # search band was chosen for the narrator; any OTHER role's number is
    # unreliable by construction rather than by measurement, and saying so is
    # the whole difference between a metric and a metric you can act on.
    main_role = script.NARRATOR
    for lid, sid, style, d, st, nf, role in rows:
        if nf < 40:
            note = f"too few voiced frames ({nf}) -- not measurable"
        elif role != main_role:
            note = f"{role}, outside the estimator's band -- number unreliable"
        elif st < LOW:
            note = "LOW -- listen to this one"
            ranked.append((st, lid))
        else:
            note = ""
            ranked.append((st, lid))
        print(f"  {lid:>4} {sid:>4} {style:>4.2f} {d:>6.2f} {st:>6.2f}st  {note}")

    if ranked:
        vals = [s for s, _ in ranked]
        print(f"\n  {len(vals)} measurable narrator lines, mean {sum(vals)/len(vals):.2f} st")
        low = sorted(ranked)[:3]
        print("  flattest: " + ", ".join(f"{lid} ({s:.2f})" for s, lid in low))
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
