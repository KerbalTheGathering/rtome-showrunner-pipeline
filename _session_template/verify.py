"""Look at the finished film where each device is supposed to fire, and measure
the mix. A device that silently did nothing looks exactly like a device that was
never written, and a mix fault is invisible in a picture.

Timestamps are DERIVED from the same edit table the film was cut from, so this
cannot drift out of step with the cut.
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import os
import subprocess
import sys

import edit
# NOT OPTIONAL, AND IT WAS MISSING. MP4 below reads shot.SLUG, and `import
# edit` only made `shot` reachable through sys.modules, not through this
# namespace -- so the verifier raised NameError the first time anybody tried to
# verify anything. A checker that cannot run has never disagreed with anything.
import shot

HERE = os.path.dirname(os.path.abspath(__file__))
FF = season_paths.FFMPEG
OUT = os.path.join(HERE, "_verify")
# DERIVED. This was a typed filename, which meant every clone verified the
# film it was copied from -- and passed, because that file existed.
MP4 = os.path.join(HERE, "out", f"{shot.SLUG}.mp4")


def starts() -> dict[str, float]:
    t, out = 0.0, {}
    for r in edit.table():
        out[r["sid"]] = t
        t += r["beat"]
    out["_end"] = t
    return out


def main() -> int:
    if not os.path.exists(MP4):
        sys.exit("FAIL: no film -- run assemble.py")
    s = starts()
    trans = {t: (f, k, sec) for f, t, k, sec in edit.TRANSITIONS}
    shots = [
        ("title, broken", 0.8),
        ("title, locked", 3.4),
        ("ROW WIPE 01>02", s["02"] + trans["02"][2] * 0.45),
        ("PORTAL out 03>04", s["04"] + trans["04"][2] * 0.45),
        ("flat grade (rally)", s["08"] + 3.0),
        ("the handshake", s["10"] + 2.0),
        ("PORTAL in 13>14", s["14"] + trans["14"][2] * 0.50),
        ("end card", s["_end"] - 1.2),
    ]
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    for i, (label, t) in enumerate(shots, 1):
        subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                        "-ss", f"{t:.2f}", "-i", MP4, "-frames:v", "1",
                        "-vf", "scale=620:-2",
                        os.path.join(OUT, f"_{i:02d}.png")], check=True)
        print(f"  {i}. {label:20s} @ {t:6.2f}s")
    dest = os.path.join(OUT, "devices.png")
    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                    "-i", os.path.join(OUT, "_%02d.png"), "-frames:v", "1",
                    "-vf", "tile=4x2:margin=6:padding=4:color=0x202020",
                    dest], check=True)
    for f in os.listdir(OUT):
        if f.startswith("_"):
            os.remove(os.path.join(OUT, f))
    print(f"  -> {dest}")

    r = subprocess.run([season_paths.ff("ffmpeg"), "-v", "info", "-i", MP4,
                        "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    for line in (r.stderr or "").splitlines():
        if "mean_volume" in line or "max_volume" in line:
            print("  " + line.split("] ")[-1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
