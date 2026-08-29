"""How long each segment runs, derived from the takes rather than chosen.

THE SAME RULE AS EVERY SESSION: a line's measured duration sizes its segment and
the segment sizes the clip. Nothing here is typed except the AIR -- the lead
before he starts, the gaps between lines, and the tail after he stops.

SPEECH, NOT FILE LENGTH. Segment six's first take is 3.44s of file containing
1.06s of "Well." and 2.12s of silence in front of it. That pause is exactly
right and it arrived by accident, which is the one thing this project does not
allow a silence to be. So the takes are measured to their actual speech, the
leading air is trimmed at mix time along with the trailing transient, and every
pause in the reel is a number in this file.

SEGMENT SIX GETS ITS OWN AIR AND THAT IS THE POINT. Five segments run tight
because a man selling something does not leave gaps. Six runs slow because there
is nothing to sell, and the format staying exactly the same length while its
content evaporates is the joke. Its gaps are more than three times the others'.
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

import identity
import script

HERE = os.path.dirname(os.path.abspath(__file__))
VO = os.path.join(HERE, "_vo")
TMP = os.path.join(HERE, "_vo_wav")
FF = season_paths.FFMPEG

# THE SEASON'S RATE, DERIVED. `24` was typed in eleven files beside a
# season_identity.FPS that already said so -- and feature.py asserts every
# part matches, so a season at another rate would have been caught only
# after every part was baked.
FPS = identity.season.FPS
FLOOR_DB = -45.0

# (lead, gap, tail) in seconds. He is a pitchman; he does not leave room.
AIR = (0.40, 0.35, 1.20)
# The break segment. The dead air IS the content, so it is the largest number
# here. WHICH segment that is comes from script.FORMAT_SIDS -- it used to be
# `sid == "06"`, a literal that is simply never true on a reel that is not six
# long, and the format's own air would then have been used for the break.
AIR_EMPTY = (1.00, 1.40, 2.00)


def _speech(lid: str) -> float:
    """Seconds of actual speech in a take, ignoring silence at either end."""
    mp3 = os.path.join(VO, f"{lid}.mp3")
    if not os.path.exists(mp3):
        sys.exit(f"FAIL: VO take {lid} missing -- run make_vo.py")
    os.makedirs(TMP, exist_ok=True)
    wav = os.path.join(TMP, f"{lid}.wav")
    if not os.path.exists(wav) or os.path.getmtime(wav) < os.path.getmtime(mp3):
        subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                        "-i", mp3, "-ac", "1", "-ar", "22050", wav], check=True)
    with wave.open(wav) as w:
        sr, n = w.getframerate(), w.getnframes()
        pcm = struct.unpack(f"<{n}h", w.readframes(n))
    win = int(sr * 0.010)
    k = n // win
    if not k:
        return n / sr
    rms = [math.sqrt(sum(v * v for v in pcm[i * win:(i + 1) * win]) / win)
           / 32768.0 + 1e-12 for i in range(k)]
    live = [i for i, r in enumerate(rms) if 20 * math.log10(r) > FLOOR_DB]
    if not live:
        return n / sr
    return (live[-1] + 1 - live[0]) * 0.010


_CACHE: dict[str, float] = {}


def speech(lid: str) -> float:
    if lid not in _CACHE:
        _CACHE[lid] = _speech(lid)
    return _CACHE[lid]


def grid(seconds: float) -> int:
    """H3's 17k+5 frame grid at 24fps. Always UP -- a clip one frame short of
    its segment is a black frame in the reel."""
    n = max(5, round(seconds * FPS))
    return n + (5 - (n % 17)) % 17


def table() -> list[dict]:
    rows = []
    for sid in script.SIDS:
        lids = [ln[0] for ln in script.LINES if ln[1] == sid]
        lead, gap, tail = AIR if sid in script.FORMAT_SIDS else AIR_EMPTY
        sp = sum(speech(l) for l in lids)
        seg = lead + sp + gap * (len(lids) - 1) + tail
        rows.append({"sid": sid, "lines": lids, "lead": lead, "gap": gap,
                     "tail": tail, "speech": sp, "seg": seg,
                     "clip": grid(seg) / FPS, "frames": grid(seg)})
    return rows


# THE H3 BASE CLIP IS NOT THE SEGMENT, AND ON A TALKATIVE SHOW IT CANNOT BE.
#
# A desk that talks 22-27s a segment needs a 600-670 frame hold, which is
# over the 2.80M latent budget at every canvas the aspect offers -- and past
# the budget H3 does not fail, it thrashes. What saves it is what the sync
# actually consumes: italk.py takes FRAME ZERO of the clean bake as its
# anchor image and regenerates the whole segment at FRAMES length from the
# voice; every base frame after zero is discarded. So the base shoot is
# capped here and the clean bake pads the remainder by repeating the last
# frame (see assemble.bake), which keeps the driver audio full length. On a
# reel whose segments fit under the cap, BASE_FRAMES == FRAMES and nothing
# changes.
#
# 294 frames is the H3 grid at ~12s -- the longest clip the reference season
# proved on the measured card.
BASE_CAP_F = 294


# COMPUTED ON FIRST ACCESS, NOT ON IMPORT. These were two module-level
# comprehensions over table(), which decodes every VO take -- so `import edit`
# required the reel to have been recorded, and everything downstream of edit
# was unimportable (and unverifiable) until it had been. See the same note in
# _session_template/edit.py. `edit.SECS[sid]` and `edit.FRAMES[sid]` are
# unchanged for every caller; they are just no longer paid for at import.
def __getattr__(name: str):
    if name in ("SECS", "FRAMES", "BASE_SECS", "BASE_FRAMES"):
        rows = table()
        globals()["SECS"] = {r["sid"]: r["clip"] for r in rows}
        globals()["FRAMES"] = {r["sid"]: r["frames"] for r in rows}
        # The base shoot: capped, still on the 17k+5 grid by construction.
        globals()["BASE_FRAMES"] = {r["sid"]: min(r["frames"], BASE_CAP_F)
                                    for r in rows}
        globals()["BASE_SECS"] = {s: f / FPS
                                  for s, f in globals()["BASE_FRAMES"].items()}
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def offsets(sid: str) -> list[tuple[str, float]]:
    """(line id, start offset in seconds) within a segment."""
    r = next(x for x in table() if x["sid"] == sid)
    out, t = [], r["lead"]
    for lid in r["lines"]:
        out.append((lid, t))
        t += speech(lid) + r["gap"]
    return out


def main() -> int:
    rows = table()
    print(f"  {'seg':>4} {'lines':>6} {'speech':>7} {'air':>6} {'segment':>8} "
          f"{'clip':>7} {'frames':>7}")
    for r in rows:
        air = r["seg"] - r["speech"]
        print(f"  {r['sid']:>4} {len(r['lines']):>6} {r['speech']:>7.2f} "
              f"{air:>6.2f} {r['seg']:>8.2f} {r['clip']:>7.2f} "
              f"{r['frames']:>7}")
    tot = sum(r["clip"] for r in rows)
    print(f"\n  reel {tot:.1f}s over {len(rows)} slot(s), "
          f"{sum(r['frames'] for r in rows)} frames to shoot")
    # SLICED BY NAME, NOT BY POSITION. `rows[:5]` and `rows[5]` were an
    # IndexError on any reel that is not exactly six long -- and worse, on a
    # seven-segment reel they would have quietly compared the wrong five.
    body = [r["seg"] for r in rows if r["sid"] in script.FORMAT_SIDS]
    if body:
        print(f"  the format ({len(body)} segment(s)) spans "
              f"{min(body):.2f}-{max(body):.2f}s "
              f"({max(body)-min(body):.2f}s apart)")
    for r in rows:
        if r["sid"] in script.BREAK_SIDS:
            print(f"  segment {r['sid']} is {r['seg'] - r['speech']:.2f}s of "
                  f"air around {r['speech']:.2f}s of speech")
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
