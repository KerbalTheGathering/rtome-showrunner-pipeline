"""Lip sync the six bounty reports on LOCAL Wav2Lip, and composite the mouth.

THIS REPLACES THE PAID KLING PASS, WHICH WAS MEASURED NOT TO WORK. Two reviewers
said the announcer's lips did not match. They were right, and the check that
proves it needs no metric: pull every frame where the VO is at TRUE SILENCE and
look at the mouth. Eight of ten were open. Half the peak-speech frames were shut.
Kling was animating a mouth, but not from this voice.

Three separate wins, and the first is the only one that matters:

    IT TRACKS THE VOICE.   Same silence test on the Wav2Lip pass: closed.
    IT IS FREE.            14c a call meant the paid version could never be
                           iterated -- every look cost money, so it shipped on
                           one look. This can be re-run until it is right.
    NO CHUNKS, NO SEAMS.   Kling takes 2-10s of video and the segments run
                           13.6-17.2s, so each was cut into pieces and rejoined.
                           Local Wav2Lip has no cap; a segment goes through
                           whole and there is nothing to seam.

TWO THINGS IT GETS WRONG, BOTH HANDLED HERE.

1. IT RUNS AT 25 FPS, ITS OWN, not the rate you hand it -- exactly the trap
   Kling set by returning 30. Feed it 24 and 48 frames come back as 50, every
   frame lands between two of yours, and a difference map lights up the hair and
   the jacket. So the picture goes over AT 25 and comes back to 24 afterwards.

2. IT ROUND-TRIPS THE WHOLE DETECTED FACE THROUGH 96x96, not just the mouth.
   The model only predicts the lower half, but the paste-back covers the entire
   face box, so the eyes and hair come back soft too. Hence the composite: only
   a feathered ellipse over the mouth is taken, and the rest of the picture is
   the original, untouched. Kling repainted 42.6% of the frame; this changes
   about 3%.

THE SOFTNESS THAT REMAINS IS INVISIBLE, and that is a fact about this show
rather than about Wav2Lip. The tube pass in crt.py limits luma bandwidth to 68%,
smears chroma to a sixth, and lays 480 scanlines over everything. A mouth
rebuilt from 96x96 has nothing left to lose by the time it reaches the viewer.
Checked side by side against Kling through the full grade before this was built.

    python w2l.py --probe      # locate the mouths, verify, write nothing else
    python w2l.py              # all six
    python w2l.py 03 05        # just these
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

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import shot

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "_work")
OUT = os.path.join(HERE, "out")
FF = season_paths.FFMPEG
HOST = season_paths.COMFY_URL
INPUT = season_paths.COMFY_INPUT
COMFY_OUT = season_paths.COMFY_OUTPUT

W, H = 1440, 1080
FPS = 24
W2L_FPS = 25                 # Wav2Lip's own rate. Not negotiable, so work with it.

# One crop for all six, generous on purpose: the detector wants context and a
# box that clips the chin is the classic way to make a face detector fail and
# then blame the model. Verified against every segment by --probe.
FACE = (0.15, 0.05, 0.65, 0.60)

MOUTHS = os.path.join(HERE, "_work", "mouths.json")


def crop_px() -> tuple[int, int, int, int]:
    x0, y0 = int(FACE[0] * W), int(FACE[1] * H)
    w, h = int((FACE[2] - FACE[0]) * W), int((FACE[3] - FACE[1]) * H)
    return x0, y0, w - w % 2, h - h % 2


def ff(*args: str) -> None:
    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error", *args],
                   check=True)


def read(path: str, w: int, h: int) -> np.ndarray:
    p = subprocess.run(
        [season_paths.ff("ffmpeg"), "-v", "error", "-i", path,
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=True).stdout
    a = np.frombuffer(p, np.uint8)
    n = len(a) // (w * h * 3)
    return a[:n * w * h * 3].reshape(n, h, w, 3)


def submit(g: dict) -> str:
    pid = json.load(urllib.request.urlopen(urllib.request.Request(
        f"{HOST}/prompt", json.dumps({"prompt": g}).encode(),
        {"Content-Type": "application/json"})))["prompt_id"]
    t0 = time.time()
    while True:
        time.sleep(5)
        h = json.load(urllib.request.urlopen(f"{HOST}/history/{pid}"))
        if pid in h:
            fs = [f for o in h[pid].get("outputs", {}).values()
                  for f in o.get("gifs", []) + o.get("videos", [])
                  + o.get("images", [])]
            if not fs:
                sys.exit(f"FAIL after {time.time()-t0:.0f}s:\n"
                         + json.dumps(h[pid].get("status", {}), indent=1)[:1500])
            return os.path.join(COMFY_OUT, fs[-1].get("subfolder", ""),
                                fs[-1]["filename"])
        if time.time() - t0 > 3600:
            sys.exit("FAIL: timed out waiting on Wav2Lip")


def run_w2l(sid: str, secs: float | None = None) -> tuple[str, str]:
    """Face crop -> Wav2Lip -> a 25fps clip. Returns (input, output) paths."""
    clean = os.path.join(WORK, f"clean_{sid}.mp4")
    vo = os.path.join(WORK, f"vo_{sid}.wav")
    for p in (clean, vo):
        if not os.path.exists(p):
            sys.exit(f"FAIL: {p} missing -- run `assemble.py --clean {sid}`")
    x0, y0, cw, ch = crop_px()
    vid = os.path.join(INPUT, f"w2l_{sid}.mp4")
    aud = os.path.join(INPUT, f"w2l_{sid}.wav")
    dur = ["-t", f"{secs:.3f}"] if secs else []
    ff(*dur, "-i", clean,
       "-vf", f"crop={cw}:{ch}:{x0}:{y0},fps={W2L_FPS}",
       "-an", "-c:v", "libx264", "-crf", "12", "-preset", "slow",
       "-pix_fmt", "yuv420p", vid)
    ff(*dur, "-i", vo, "-ac", "1", "-ar", "16000", aud)

    g = {
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
              "inputs": {"images": ["3", 0], "frame_rate": W2L_FPS,
                         "loop_count": 0, "filename_prefix": f"w2l/{sid}",
                         "format": "video/h264-mp4", "pingpong": False,
                         "save_output": True}},
    }
    return vid, submit(g)


def find_mouth(vid: str, got: str, cw: int, ch: int) -> tuple:
    """Where Wav2Lip ADDED motion. That is the mouth, and nothing else is.

    NOT "where the two clips differ" -- that was tried and it is wrong, because
    the 96x96 round trip changes the whole face box, so a difference map lights
    up the hair and the glasses too and any threshold on it picks the wrong
    region. What is specific to the mouth is MOTION: everywhere else Wav2Lip
    reproduces the input's own movement, and only at the mouth does it invent
    more. So the signal is the increase in temporal variation, not difference.
    """
    a = read(vid, cw, ch).astype(np.float32).mean(axis=3)
    b = read(got, cw, ch).astype(np.float32).mean(axis=3)
    n = min(len(a), len(b))
    extra = np.clip(b[:n].std(axis=0) - a[:n].std(axis=0), 0, None)
    # BLUR FIRST, NORMALISE AFTER. The other order silently fails: a small hot
    # spot normalised to 1.0 and then blurred has a peak well under any fixed
    # threshold, so nothing passes and the error reads as "no face found".
    extra = np.asarray(Image.fromarray(
        (extra / max(extra.max(), 1e-6) * 255).astype(np.uint8), "L")
        .filter(ImageFilter.GaussianBlur(9)), np.float32)
    extra /= max(extra.max(), 1e-6)
    ys, xs = np.nonzero(extra >= 0.45)
    if not len(xs):
        sys.exit("FAIL: Wav2Lip added no motion anywhere -- it did not find "
                 "the face. Look at the probe sheet.")
    cx, cy = (xs.min() + xs.max()) / 2.0, (ys.min() + ys.max()) / 2.0
    rx, ry = (xs.max() - xs.min()) / 2.0, (ys.max() - ys.min()) / 2.0
    return (cx / cw, cy / ch, max(rx / cw, 0.06) * 1.35,
            max(ry / ch, 0.06) * 1.35)


def mask_for(m: tuple, cw: int, ch: int) -> np.ndarray:
    cx, cy, rx, ry = m
    im = Image.new("L", (cw * 2, ch * 2), 0)
    ImageDraw.Draw(im).ellipse([(cx - rx) * cw * 2, (cy - ry) * ch * 2,
                                (cx + rx) * cw * 2, (cy + ry) * ch * 2], fill=255)
    im = im.resize((cw, ch), Image.LANCZOS).filter(ImageFilter.GaussianBlur(14))
    return (np.asarray(im, np.float32) / 255.0)[..., None]


def composite(sid: str, got: str, m: tuple) -> str:
    """Feathered mouth over the untouched original, colour-matched.

    THE COLOUR MATCH IS NOT COSMETIC. Wav2Lip returns the region a shade warmer
    and lighter than it went in, and a feathered blend of two different
    exposures leaves a soft bright patch the shape of the mask -- which reads as
    a smudge on the man's chin. Matched over the whole clip rather than per
    frame, so it corrects the offset without fighting the mouth's own changes.
    """
    x0, y0, cw, ch = crop_px()
    back = os.path.join(WORK, f"w2l24_{sid}.mp4")
    ff("-i", got, "-vf", f"fps={FPS}", "-an", "-c:v", "libx264", "-crf", "12",
       "-preset", "slow", "-pix_fmt", "yuv420p", back)

    src = read(os.path.join(WORK, f"clean_{sid}.mp4"), W, H)
    lip = read(back, cw, ch)
    n = min(len(src), len(lip))
    mask = mask_for(m, cw, ch)

    sel = mask[..., 0] > 0.5
    a = src[:n, y0:y0 + ch, x0:x0 + cw][:, sel].reshape(-1, 3).astype(np.float32)
    b = lip[:n][:, sel].reshape(-1, 3).astype(np.float32)
    shift = a.mean(axis=0) - b.mean(axis=0)

    dst = os.path.join(WORK, f"synced_{sid}.mp4")
    p = subprocess.Popen(
        [season_paths.ff("ffmpeg"), "-y", "-v", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-framerate", str(FPS), "-i", "-", "-an", "-c:v", "libx264",
         "-crf", "14", "-preset", "slow", "-pix_fmt", "yuv420p", dst],
        stdin=subprocess.PIPE)
    for i in range(n):
        f = src[i].astype(np.float32).copy()
        sub = f[y0:y0 + ch, x0:x0 + cw]
        f[y0:y0 + ch, x0:x0 + cw] = (
            np.clip(lip[i].astype(np.float32) + shift, 0, 255) * mask
            + sub * (1.0 - mask))
        p.stdin.write(np.clip(f, 0, 255).astype(np.uint8).tobytes())
    p.stdin.close()
    if p.wait():
        sys.exit("FAIL: encode of the composite failed")
    return dst


def main() -> int:
    want = [a for a in sys.argv[1:] if not a.startswith("-")] or list(shot.CUT)
    probe = "--probe" in sys.argv
    os.makedirs(WORK, exist_ok=True)
    x0, y0, cw, ch = crop_px()
    print(f"  face crop {cw}x{ch} at ({x0},{y0})   "
          f"{'PROBE -- 3s each, nothing composited' if probe else ''}")

    found = {}
    if os.path.exists(MOUTHS) and not probe:
        found = json.load(open(MOUTHS, encoding="utf-8"))

    sheet = []
    f = ImageFont.truetype(season_paths.font("arialbd.ttf"), 18)
    for sid in want:
        t0 = time.time()
        vid, got = run_w2l(sid, secs=3.0 if probe else None)
        m = find_mouth(vid, got, cw, ch)
        found[sid] = m
        print(f"  [{sid}] mouth at ({m[0]:.3f},{m[1]:.3f}) r=({m[2]:.3f},"
              f"{m[3]:.3f}) of the crop   {time.time()-t0:.0f}s", end="")

        # VERIFY BY DRAWING IT BACK ON THE PICTURE, always -- the numbers alone
        # have picked the wrong region twice on this project.
        im = Image.fromarray(read(got, cw, ch)[len(read(got, cw, ch)) // 2])
        d = ImageDraw.Draw(im)
        d.ellipse([(m[0] - m[2]) * cw, (m[1] - m[3]) * ch,
                   (m[0] + m[2]) * cw, (m[1] + m[3]) * ch],
                  outline=(255, 70, 60), width=3)
        d.text((6, 6), f"seg {sid}", font=f, fill=(255, 255, 255))
        sheet.append(im.resize((cw // 2, ch // 2), Image.LANCZOS))

        if probe:
            print()
            continue
        dst = composite(sid, got, m)
        print(f" -> {os.path.basename(dst)}")

    if sheet:
        g = Image.new("RGB", (sheet[0].width * min(3, len(sheet)),
                              sheet[0].height * ((len(sheet) + 2) // 3)),
                      (16, 16, 18))
        for i, im in enumerate(sheet):
            g.paste(im, ((i % 3) * im.width, (i // 3) * im.height))
        p = os.path.join(OUT, "w2l_mouths.png")
        g.save(p)
        print(f"  -> {p}   LOOK AT IT")
    with open(MOUTHS, "w", encoding="utf-8") as fh:
        json.dump(found, fh, indent=1)
    if not probe:
        print("  now: python assemble.py --synced")
    return 0


if __name__ == "__main__":
    sys.exit(main())
