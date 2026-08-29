"""Free local lip sync on a face crop, to see whether it can beat the paid one.

WHY THIS EXISTS. Kling was measured, observationally, not to track the voice on
these segments: eight of ten frames at TRUE SILENCE have the mouth open, and
half the peak-speech frames are nearly shut. Two reviewers independently called
it out. Kling also repaints the entire frame -- the difference map between the
clean picture and the synced one lights up the desk edge, the board frame and
the palm fronds, none of which have a mouth -- so the painted linework is being
softened everywhere to fix one small region.

Wav2Lip is installed, local, and free, which is the whole argument for trying
it: a paid pass costs 14c per attempt and cannot be iterated, and this can.

TWO THINGS THIS TEST HAS TO ANSWER, in order:

    1. Does the face detector FIND a painted 2D face at all? S3FD is trained on
       photographs. If it misses, everything downstream is moot and the answer
       is worth knowing for the price of two seconds of video.
    2. Is the mouth SHUT when nobody is speaking? That is the specific defect,
       and it is the one thing a still cannot hide.

IT RUNS ON A CROP, NOT THE FRAME, for two reasons that happen to agree. A whole
segment as an IMAGE batch is 413 x 1080 x 1440 x 3 float32 -- about 7.7 GB, and
this card has 24. And compositing a crop back through a feathered mask is what
keeps the rest of the picture pristine, which is exactly what the paid pass
failed to do.

    python wav2lip_test.py
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


import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(os.path.dirname(HERE), "_work")   # the SHOW tree's, not _probes' (fault 122)
OUT = os.path.join(os.path.dirname(HERE), "out")      # the SHOW tree's, not _probes' (fault 122)
FF = season_paths.FFMPEG
HOST = season_paths.COMFY_URL
INPUT = season_paths.COMFY_INPUT
COMFY_OUT = season_paths.COMFY_OUTPUT

# The head, with room around it -- a detector wants context, and a crop that
# clips the chin is the classic way to make one fail and blame the model.
FACE = (0.20, 0.10, 0.62, 0.52)
SEG = "01"
A_S, DUR = 4.0, 2.0            # frames 96-143, mid-sentence
FPS = 24


def build(vid: str, aud: str, prefix: str) -> dict:
    return {
        "1": {"class_type": "VHS_LoadVideo",
              "inputs": {"video": os.path.basename(vid), "force_rate": 0,
                         "custom_width": 0, "custom_height": 0,
                         "frame_load_cap": 0, "skip_first_frames": 0,
                         "select_every_nth": 1, "format": "None"}},
        "2": {"class_type": "LoadAudio",
              "inputs": {"audio": os.path.basename(aud)}},
        "3": {"class_type": "Wav2Lip",
              "inputs": {"images": ["1", 0], "mode": "sequential",
                         "face_detect_batch": 8, "audio": ["2", 0]}},
        "4": {"class_type": "VHS_VideoCombine",
              "inputs": {"images": ["3", 0], "frame_rate": FPS,
                         "loop_count": 0, "filename_prefix": prefix,
                         "format": "video/h264-mp4", "pingpong": False,
                         "save_output": True, "audio": ["3", 1]}},
    }


def run(g: dict) -> str:
    body = json.dumps({"prompt": g}).encode()
    pid = json.load(urllib.request.urlopen(urllib.request.Request(
        f"{HOST}/prompt", body, {"Content-Type": "application/json"})))["prompt_id"]
    t0 = time.time()
    while True:
        time.sleep(4)
        h = json.load(urllib.request.urlopen(f"{HOST}/history/{pid}"))
        if pid in h:
            st = h[pid].get("status", {})
            files = [f for o in h[pid].get("outputs", {}).values()
                     for f in o.get("gifs", []) + o.get("videos", [])
                     + o.get("images", [])]
            if not files:
                sys.exit(f"FAIL after {time.time()-t0:.0f}s:\n"
                         + json.dumps(st, indent=1)[:2000])
            f = files[-1]
            return os.path.join(COMFY_OUT, f.get("subfolder", ""), f["filename"])
        if time.time() - t0 > 900:
            sys.exit("FAIL: timed out")


def main() -> int:
    clean = os.path.join(WORK, f"clean_{SEG}.mp4")
    vo = os.path.join(WORK, f"vo_{SEG}.wav")
    for p in (clean, vo):
        if not os.path.exists(p):
            sys.exit(f"FAIL: {p} missing")

    vid = os.path.join(INPUT, "w2l_face.mp4")
    aud = os.path.join(INPUT, "w2l_face.wav")
    x0, y0, x1, y1 = FACE
    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                    "-ss", f"{A_S:.3f}", "-t", f"{DUR:.3f}", "-i", clean,
                    "-vf", f"crop=iw*{x1-x0}:ih*{y1-y0}:iw*{x0}:ih*{y0}",
                    "-an", "-c:v", "libx264", "-crf", "12", "-preset", "slow",
                    "-pix_fmt", "yuv420p", vid], check=True)
    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                    "-ss", f"{A_S:.3f}", "-t", f"{DUR:.3f}", "-i", vo,
                    "-ac", "1", "-ar", "16000", aud], check=True)
    print(f"  face crop {os.path.getsize(vid)/1e6:.1f} MB, {DUR}s from {A_S}s")

    got = run(build(vid, aud, "w2l_test/seg01"))
    dst = os.path.join(OUT, "w2l_test.mp4")
    shutil.copy2(got, dst)
    print(f"  -> {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
