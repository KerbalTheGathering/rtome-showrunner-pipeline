"""Does the mouth stay shut inside the part of the clip the film actually uses?

WHY A WHOLE-CLIP VERDICT IS THE WRONG ONE. `assemble.py` enters every clip at
`ss` and takes `beat` seconds, so a take can open its mouth in the last second
and still be perfectly clean in the cut -- beat 04's first re-shoot did exactly
that at 8.75-9.5s against a window that ends at 8.77s. Judging the whole file
would have thrown away a usable take; judging only the window keeps the decision
honest in both directions.

THE UNIT IS THE CLIP'S OWN SHUT MOUTH, NEVER AN ABSOLUTE. mouth_open.py already
established that aperture does not compare across framings, so nothing here
thresholds a raw number. The baseline is this clip's own 20th percentile -- what
its face measures while resting -- and what is reported is how far the worst
moment rises above that. Ranking is between takes of the SAME beat, which is the
only comparison the metric supports.

    python mouth_scan.py 04              # every take on disk for this beat
    python mouth_scan.py 04 --all        # ignore the window, scan the whole clip
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import os
import subprocess
import sys

import numpy as np

# THIS SESSION'S MODULES FIRST, AND THE BORROWED PATH APPENDED, NEVER INSERTED.
# `sys.path.insert(0, BIGSHOT_src)` put another session's tree ahead of this one
# and `import edit` then resolved to BIGSHOT's timeline -- which has no `ss`
# field, so it raised instead of quietly measuring the wrong film's window.
# Every session numbers its beats 01-15 and every tree has an edit.py, so the
# lookup would have succeeded on any pair that happened to share a field name.
import edit                                          # noqa: E402
import make_video                                    # noqa: E402

# The aperture metric is season-level (../mouth.py, fault 149). It lived
# in show/ and was resolved by appending that folder to sys.path -- which
# crashed every film tree's scan on a SHOW = False season (no show/ at
# all), and on seasons WITH one, importing show/mouth_open.py from here
# bound THIS tree's shot.py where the show's was meant. The root is
# already first on sys.path.
import mouth as mouth_open                           # noqa: E402

FF = season_paths.FFMPEG
RATE = 8.0               # samples per second; a syllable is longer than 125 ms


def apertures(path: str) -> list[tuple[float, float | None]]:
    w, h = mouth_open.size_of(path)
    # THE HEIGHT IS COMPUTED ONCE AND HANDED TO FFMPEG, never predicted.
    # This asked for `scale=960:-2` and then re-derived the height with
    # round()+parity -- two implementations of one rounding rule, which
    # agreed on the 4:3 canvases the reference season shot and disagreed
    # on the first 16:9 season (554 predicted, 552 produced), so reshape
    # threw on a well-formed clip (fault 150; the fault-119 rule again --
    # the checker itself must not crash).
    sh = int(round(960 * h / w))
    sh += sh % 2
    raw = subprocess.run(
        [season_paths.ff("ffmpeg"), "-v", "error", "-i", path,
         "-vf", f"fps={RATE},scale=960:{sh}", "-f", "rawvideo",
         "-pix_fmt", "bgr24", "-"], capture_output=True, check=True).stdout
    ims = np.frombuffer(raw, np.uint8).reshape(-1, sh, 960, 3)
    return [(i / RATE, mouth_open.openness(im)) for i, im in enumerate(ims)]


def window(sid: str) -> tuple[float, float]:
    r = next(r for r in edit.table() if r["sid"] == sid)
    return r["ss"], r["ss"] + r["beat"]


def takes(sid: str) -> list[str]:
    d = make_video.outdir()
    return sorted(os.path.join(d, f) for f in os.listdir(d)
                  if f.startswith(f"s{sid}_") and f.endswith(".mp4"))


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        sys.exit("usage: python mouth_scan.py <beat sid> [--all]")
    sid = args[0]
    a, b = (0.0, 1e9) if "--all" in sys.argv else window(sid)
    print(f"  beat {sid}: judging {a:.2f}s..{b:.2f}s "
          f"({'whole clip' if b > 1e8 else 'the window assemble.py uses'})\n")
    print(f"  {'take':<34} {'rest':>6} {'worst':>6} {'over':>6}  when")
    rows = []
    for p in takes(sid):
        vals = [(t, ap) for t, ap in apertures(p) if ap is not None and a <= t < b]
        if len(vals) < 8:
            print(f"  {os.path.basename(p):<34}  no face in the window")
            continue
        v = np.array([ap for _, ap in vals])
        rest = float(np.percentile(v, 20))
        i = int(v.argmax())
        over = float(v[i] / max(1e-6, rest))
        rows.append((over, os.path.basename(p)))
        print(f"  {os.path.basename(p):<34} {rest:>6.3f} {v[i]:>6.3f} "
              f"{over:>5.2f}x  {vals[i][0]:.2f}s")
    if rows:
        rows.sort()
        print(f"\n  flattest in the window: {rows[0][1]}  ({rows[0][0]:.2f}x)")
    print("\n  A ratio only ranks takes of this beat against each other. "
          "The frames decide.")
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
