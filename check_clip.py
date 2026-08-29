"""Pull a filmstrip out of a clip so motion can be judged across the whole thing.

ONE FILE, NOT THREE COPIES (finding 140). This was byte-identical in
`_session_template/`, `show/` and `cold_open/` -- and a template copy
multiplies per film, so a fix in one of eight copies is not a fix.
`direction.py` set the precedent. Each tree keeps a thin shim with the
same name, so `python check_clip.py 03` and `import check_clip` work
unchanged inside a tree; the tree is resolved through the `shot` module
the shim puts first on sys.path.

JUDGE MOTION ON SIX FRAMES SPREAD ACROSS THE CLIP, NEVER ONE. Two clips once
looked perfect at whatever frame a filmstrip happened to sample and were broken
by halfway -- a galaxy that darkened into a black rag, birds that grew into
foreground creatures. Sampling evenly is the whole point.

IT IS RUN FOR YOU. h3_shoot.py writes a strip for every clip it lands, because
a review step you have to remember is a review step that gets skipped -- and the
thing it catches is invisible in the first frame, which is the only frame
anybody looks at by default. `--no-strip` turns it off.

IT RESOLVES THE CLIP ITSELF rather than through make_video.py. That import made
this file depend on the PAID path in a repo whose default generator is the free
one, and it meant h3_shoot.py could not call it without a cycle.

    python check_clip.py            # every beat that has a clip
    python check_clip.py 03 07      # just these
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import season_paths                                                # noqa: E402


import os
import subprocess
import sys

try:
    import shot  # noqa: E402  -- the TREE'S shot, via the shim's sys.path
except ModuleNotFoundError:
    sys.exit("FAIL: check_clip.py reads a film tree's shot.py -- run it from "
             "inside a film folder (each tree carries a shim), not at the "
             "season root.")

# THE TREE IS WHERE `shot` CAME FROM, not where this file lives.
HERE = os.path.dirname(os.path.abspath(shot.__file__))
OUT = os.path.join(HERE, "_strips")
CLIPS = os.path.join(season_paths.COMFY_OUTPUT, f"{shot.NAME}_clips")
FF = season_paths.FFMPEG
N = 6


def existing(sid: str) -> list[str]:
    """Every live take for a beat, oldest first. `_rej_` is skipped explicitly:
    "highest number wins" has carried a worse re-roll into a film."""
    if not os.path.isdir(CLIPS):
        return []
    return sorted(f for f in os.listdir(CLIPS)
                  if f.startswith(f"s{sid}_") and f.endswith(".mp4")
                  and "_rej_" not in f)


def clip(sid: str) -> str:
    got = existing(sid)
    if not got:
        sys.exit(f"FAIL: no clip for beat {sid} in {CLIPS} -- shoot it first")
    return os.path.join(CLIPS, got[-1])


def probe(path: str) -> float:
    out = subprocess.run(
        [season_paths.ff("ffprobe"), "-v", "error", "-show_entries",
         "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def strip(sid: str) -> str:
    src = clip(sid)
    d = probe(src)
    os.makedirs(OUT, exist_ok=True)
    # Evenly spaced, first and last pulled just inside the ends so neither is a
    # black or duplicated frame.
    times = [d * (i + 0.5) / N for i in range(N)]
    tiles = []
    # `tile` consumes ONE input stream of N frames -- handing it N separate -i
    # inputs silently tiles only the first and pads the rest with black, which
    # looks like five dead frames rather than like a broken command. So the
    # grabs are written as a numbered SEQUENCE and read back as one stream.
    for i, t in enumerate(times):
        p = os.path.join(OUT, f"_{sid}_{i + 1:02d}.png")
        subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                        "-ss", f"{t:.2f}", "-i", src, "-frames:v", "1",
                        "-vf", "scale=640:-2", p], check=True)
        tiles.append(p)
    dest = os.path.join(OUT, f"strip_{sid}.png")
    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                    "-i", os.path.join(OUT, f"_{sid}_%02d.png"),
                    "-frames:v", "1",
                    "-vf", f"tile={N // 2}x2:margin=6:padding=4:color=0x202020",
                    dest], check=True)
    for p in tiles:
        os.remove(p)
    print(f"  [{sid}] {os.path.basename(src)}  {d:.2f}s  -> {dest}")
    return dest


def main() -> int:
    # DEFAULTS TO THE BEATS THIS FILM HAS, not to whatever filenames are in the
    # clip folder. A clip directory can hold another season's work -- that is
    # what season_identity.claim_clips() exists for -- and stripping those
    # would review a film that is not this one.
    sids = [a for a in sys.argv[1:] if not a.startswith("-")]
    bad = [s for s in sids if s not in shot.CUT]
    if bad:
        sys.exit(f"FAIL: {bad} are not beats of this film ({list(shot.CUT)})")
    sids = sids or [s for s in shot.CUT if existing(s)]
    if not sids:
        sys.exit(f"FAIL: no clips in {CLIPS} for any beat of this film. "
                 f"A strip of nothing is not a pass.")
    for sid in sids:
        strip(sid)
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
