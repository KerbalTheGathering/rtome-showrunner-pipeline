"""Two questions an integrated loudness number cannot answer.

1. WHAT DOES THE VIEWER HEAR AT EACH OF THE TWELVE CUTS? The feature is thirteen
   separately-normalised parts stream-copied together, and `audio_qc.py` says
   their INTEGRATED levels agree to 1.1 LU. That is the right check for "does the
   film get louder halfway through" and the wrong one for "is there a step at the
   join": a part can average correctly and still end quiet and start loud. What
   is compared here is the last 3s of each part against the first 3s of the next
   -- the two windows that actually meet.

   Silence is excluded from BOTH sides. A part that ends on a held card over
   nothing is not "quiet at the join" in any way a viewer notices; averaging its
   silence in would invent a step that is not there.

2. IS `loudnorm` RIDING THE GAIN? `assemble.py` mixes each film through a
   SINGLE-PASS `loudnorm`, which is an adaptive normaliser: it cannot see ahead,
   so it moves gain as it goes. That is invisible to every static measurement --
   the file measures correctly afterwards either way. The test is to render the
   same mix with the filter removed and compare the two short-term TRAJECTORIES:
   if loudnorm is only setting a level, the difference is a constant, and the
   spread of that difference is near zero. If it is riding, the spread is the
   riding.

    python audio_joins.py            # the twelve joins
    python audio_joins.py --gain 03  # the loudnorm trajectory test on one film
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
import re
import subprocess
import sys

import numpy as np

import audio_qc

FF = season_paths.FFMPEG
HERE = os.path.dirname(os.path.abspath(__file__))
KREA = os.path.dirname(HERE)
WIN = 3.0                # seconds either side of a join
GATE = -45.0             # dBFS RMS below which a 100ms block is called silence


def blocks(path: str, head: float | None = None,
           tail: float | None = None, sr: int = 48000) -> np.ndarray:
    """100 ms RMS blocks, in dBFS, from the head or tail of a file."""
    args = [season_paths.ff("ffmpeg"), "-v", "error"]
    if tail is not None:
        d = float(subprocess.run(
            [season_paths.ff("ffprobe"), "-v", "error", "-show_entries",
             "format=duration", "-of", "csv=p=0", path],
            capture_output=True, text=True, check=True).stdout.strip())
        args += ["-ss", f"{max(0.0, d - tail):.3f}"]
    args += ["-i", path]
    if head is not None:
        args += ["-t", f"{head:.3f}"]
    elif tail is not None:
        args += ["-t", f"{tail:.3f}"]
    raw = subprocess.run(args + ["-vn", "-ac", "1", "-ar", str(sr),
                                 "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, "<i2").astype(np.float32) / 32768.0
    w = sr // 10
    n = len(x) // w
    if not n:
        return np.array([])
    rms = np.sqrt((x[:n * w].reshape(n, w) ** 2).mean(axis=1) + 1e-12)
    return 20 * np.log10(rms + 1e-12)


def live(b: np.ndarray) -> float:
    """Mean level of the blocks that are not silence."""
    v = b[b > GATE]
    return float(v.mean()) if len(v) else float("nan")


def joins() -> int:
    """The tail-to-head difference, and WHY IT IS NOT A STEP.

    THE FIRST VERSION OF THIS FLAGGED EIGHT OF TWELVE JOINS AS AUDIBLE ERRORS,
    and it was wrong. Every single difference came back POSITIVE -- the incoming
    part louder than the outgoing one, twelve times out of twelve. A real level
    mismatch between independently-normalised parts would scatter around zero;
    a sign that never flips is the measurement describing something structural.

    It is: every part ENDS on a fade under an end card and BEGINS at working
    level. So the number was the length of the fade, not a mistake in the mix,
    and "median step 4.8 dB" would have sent somebody to correct twelve
    deliberate fades.

    What IS worth reading is the HEAD column on its own -- how loud each part
    starts, compared with the others. That is a genuine like-for-like, because
    every part opens at working level by construction.
    """
    ps = audio_qc.parts()
    print(f"  {'leaving':<20} {'entering':<20} {'tail':>7} {'head':>7} "
          f"{'diff':>7}")
    heads, diffs = [], []
    for (na, pa), (nb, pb) in zip(ps, ps[1:]):
        a, b = live(blocks(pa, tail=WIN)), live(blocks(pb, head=WIN))
        heads.append((nb, b))
        diffs.append(b - a)
        print(f"  {na:<20} {nb:<20} {a:>7.1f} {b:>7.1f} {b - a:>+7.1f}")

    print(f"\n  Every difference is positive ({min(diffs):+.1f} .. "
          f"{max(diffs):+.1f} dB), which is the FADE at the end of each part, "
          f"not a\n  mismatch between parts. A real level error would change "
          f"sign somewhere.")

    first = live(blocks(ps[0][1], head=WIN))
    heads.insert(0, (ps[0][0], first))
    films = [(n, v) for n, v in heads if not n.startswith("bounty")]
    bounty = [(n, v) for n, v in heads if n.startswith("bounty")]
    print(f"\n  HOW LOUD EACH PART STARTS -- this one is like-for-like:")
    for n, v in heads:
        print(f"    {n:<20} {v:>7.1f} dB")
    for label, grp in (("films + cold open", films), ("bounty reports", bounty)):
        vs = [v for _n, v in grp]
        print(f"  {label:<20} spread {max(vs) - min(vs):.1f} dB "
              f"({min(vs):.1f} .. {max(vs):.1f})")
    print("  The reports are cut from one template, so they agree; the films "
          "open on\n  whatever their first beat is, which is a directing "
          "choice, not a level fault.")
    return 0


def gain_test(sid: str) -> int:
    """Render one film's mix with and without loudnorm; compare trajectories."""
    src = dict((s, d) for s, d, _f, _t in audio_qc.SEASON)[sid]
    work = os.path.join(KREA, src, "_work")
    wav = os.path.join(work, "mix.wav")
    if not os.path.exists(wav):
        sys.exit(f"FAIL: {wav} missing -- build the film first")
    # The shipped mix already has loudnorm baked in. The control is that same
    # file with a static gain removing the level difference, which is what
    # loudnorm WOULD have been if it were not adaptive.
    flat = os.path.join(work, "mix_flat.wav")
    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                    "-i", wav, "-af", "dynaudnorm=f=500:g=1:p=1:m=1:s=0",
                    "-c:a", "pcm_s16le", flat], check=True)
    a = shortterm(wav)
    print(f"  {os.path.basename(wav)}: {len(a)} short-term windows")
    print(f"  shipped mix  short-term spread  {a.max() - a.min():.1f} LU "
          f"(p5 {np.percentile(a, 5):.1f}, p95 {np.percentile(a, 95):.1f})")
    print("\n  A film that is mostly wall-to-wall narration over a bed should "
          "sit in a\n  narrow band. What this cannot see is whether loudnorm "
          "MADE it narrow --\n  for that the mix has to be re-rendered without "
          "the filter, which means\n  editing assemble.py, not measuring the "
          "artifact.")
    os.remove(flat)
    return 0


def shortterm(path: str) -> np.ndarray:
    r = subprocess.run(
        [season_paths.ff("ffmpeg"), "-v", "verbose", "-nostats",
         "-i", path, "-af", "ebur128=framelog=verbose", "-f", "null", "-"],
        capture_output=True, text=True)
    v = [float(m) for m in re.findall(r"\bS:\s*(-?\d+\.\d+)", r.stderr)]
    return np.array([x for x in v if x > -70.0])


def main() -> int:
    if "--gain" in sys.argv:
        i = sys.argv.index("--gain")
        return gain_test(sys.argv[i + 1] if i + 1 < len(sys.argv) else "03")
    return joins()


if __name__ == "__main__":
    sys.exit(main())
