"""Bake the cold open: three shots, one cue, and the season's title.

ONE MP4, which feature.py puts in front of everything else.

THE TITLE LANDS ON MOVING WATER, NOT ON A FROZEN FRAME. The obvious build is to
hold the last frame and draw type over it, and it is obvious because it is easy;
it also reads instantly as a still, because the water stops. So the title fades
up over the LAST FOUR SECONDS of shot 03 while the wake is still settling, and
the cut to the bounty show comes on the last frame. Nothing freezes.

IT MATCHES THE FILMS' TYPE, NOT THE BOUNTY SHOW'S. Impact, cream, ink stroke --
the same as every "SESSION #n" card in the season, because this card sits above
those and has to look like it belongs to them. The interstitials' board type is
deliberately the odd one out.

NO SPEECH ANYWHERE, asserted in motion.py. The first voice in the whole feature
is Dale's, four seconds after this ends.
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import concurrent.futures as cf
import math
import json
import re
import os
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import cards               # the card library, at the season root
import framing             # how a plate of one shape enters a frame of another
import grades              # the look library
import mixes               # the audio bus library
import edit
import identity
import shot

HERE = os.path.dirname(os.path.abspath(__file__))
FF = season_paths.FFMPEG

# The season's look, fit and bus, named once in identity.py. See ../grades.py,
# ../framing.py and ../mixes.py; each has a `--sheet` or a `--graph`.
GRADE, GRADE_OPTS = identity.GRADE, identity.GRADE_OPTS
FIT, FIT_OPTS = identity.FIT, identity.FIT_OPTS
MIX, MIX_OPTS = identity.MIX, identity.MIX_OPTS
for _lib in (grades, framing, mixes):
    _lib.load_extra(HERE)
WORK = os.path.join(HERE, "_work")
BAKED = os.path.join(HERE, "_baked")
OUT = os.path.join(HERE, "out")
MUSIC = os.path.join(HERE, "_music")
CLIPS = os.path.join(season_paths.COMFY_OUTPUT, f"{shot.NAME}_clips")

# THE SEASON'S OWN RENDER CANVASES, so a frame that came off the video model
# can be told from a plate by its exact size. See framing.unsqueeze().
CANVASES = season_paths.canvases(identity.season.W, identity.season.H)

# THE SEASON'S RATE, DERIVED. `24` was typed in eleven files beside a
# season_identity.FPS that already said so -- and feature.py asserts every
# part matches, so a season at another rate would have been caught only
# after every part was baked.
FPS = float(identity.season.FPS)
CRF = 18
# DERIVED FROM THE SEASON, NOT TYPED. It was `960, 1080` -- 4:3's answer
# written down in the one place that would silently letterbox a season that is
# not 4:3. feature.py asserts every part matches, so it would have caught the
# mismatch, but only after every part had been baked.
#
# THE RESULT IS UNCHANGED FOR A 4:3 SEASON: a 1024x768 clip scales by 1.40625
# either way, because pick_canvas() shoots at the delivery aspect and a clip at
# that aspect clears both floors at the same scale.
W_MIN, H_MIN = identity.season.W, identity.season.H
# The MIX BUS rate, which may be higher than delivery -- normalize() resamples
# to season.A_RATE at the end. Do not confuse the two: a sample count worked
# out at one rate and applied at the other cut this file in half once.
A_RATE = identity.season.A_RATE

FONT = season_paths.font(identity.season.FONT_DISPLAY)
CREAM = (247, 240, 224)
INK = (24, 20, 18)

# BOTH LINES COME FROM IDENTITY. The upper line was a typed string here, which
# is the same leak this template exists to close -- see identity.py.
TITLE_1, TITLE_2 = identity.TITLE_SUPER, shot.TITLE
T1_H, T2_H = 0.055, 0.115     # fractions of frame height, before fitting
TITLE_FADE = 1.0              # seconds to reach full

# WHICH CARD, FROM ../cards.py. The cold open used to hard-code a centred
# two-line stack, which is what `plain` does -- so this is the same picture by
# default and a season that wants its front door on flat colour, or in a lower
# third, now says so instead of rewriting draw_title().
TITLE_CARD = identity.TITLE_CARD
TITLE_OPTS = identity.TITLE_CARD_OPTS


def dims(sw: int, sh: int) -> tuple[int, int]:
    s = max(1.0, W_MIN / sw, H_MIN / sh)
    w, h = round(sw * s), round(sh * s)
    return w - w % 2, h - h % 2


def fit(text: str, px: int, cap: float) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(FONT, px)
    while px > 8 and f.getbbox(text)[2] > cap:
        px -= 2
        f = ImageFont.truetype(FONT, px)
    return f


def _text(im, text, font, cx, cy, stroke, anchor="mm", alpha=1.0):
    """One line, on its own RGBA layer so it fades as one thing.

    THE LAYER IS THE POINT AND IT IS WHY THIS TREE KEEPS ITS OWN RENDERER.
    Stroking straight onto the frame at partial alpha fades the fill and the
    stroke at different rates, and the type CRAWLS. Everything else about the
    card -- where the lines go, how many there are, what the card is called --
    comes from ../cards.py; only the ink is local.
    """
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x0, y0, x1, y1 = d.textbbox((0, 0), text, font=font,
                                stroke_width=stroke)
    x = (cx - (x1 - x0) // 2 - x0 if anchor[0] == "m"
         else cx - (x1 - x0) - x0 if anchor[0] == "r" else cx - x0)
    d.text((x, cy - (y1 - y0) // 2 - y0), text, font=font,
           fill=CREAM + (255,), stroke_width=stroke, stroke_fill=INK + (255,))
    if alpha < 1.0:
        lay.putalpha(lay.split()[3].point(lambda v: int(v * alpha)))
    return Image.alpha_composite(im.convert("RGBA"), lay).convert("RGB")


def draw_title(im: Image.Image, alpha: float) -> Image.Image:
    if alpha <= 0.002:
        return im
    w, h = im.size
    lay = cards.layout(TITLE_CARD, 2, TITLE_OPTS)
    # SIZED TO THE SPACE THE CARD'S OWN ANCHOR LEAVES. It was a flat 0.8w for
    # both lines regardless of where they sat, which is fine centred and wrong
    # anywhere else.
    fonts = [fit(t, round(h * ph), w * cards.limit(cx, anch, sl))
             for t, ph, (cx, _cy, anch, sl) in
             ((TITLE_1, T1_H, lay[0]), (TITLE_2, T2_H, lay[1]))]
    ctx = {"w": w, "h": h, "text": _text, "fonts": fonts,
           "stroke": max(2, round(fonts[1].size * 0.06)),
           "cream": CREAM, "ink": INK}
    im, off = cards.treat(TITLE_CARD, im, alpha, ctx, TITLE_OPTS)
    return cards.draw(TITLE_CARD, im, [TITLE_1, TITLE_2], ctx, alpha, off,
                      TITLE_OPTS)


def frames_of(sid: str) -> list[str]:
    got = sorted(f for f in os.listdir(CLIPS)
                 if f.startswith(f"s{sid}_") and f.endswith(".mp4")
                 and "_rej_" not in f)
    if not got:
        sys.exit(f"FAIL: no clip for shot {sid} -- run h3_shoot.py")
    d = os.path.join(WORK, f"src_{sid}")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                    "-i", os.path.join(CLIPS, got[-1]),
                    os.path.join(d, "f_%05d.png")], check=True)
    return [os.path.join(d, f) for f in sorted(os.listdir(d))]


# --------------------------------------------------------------------------
# TWO-STAGE LOUDNESS, BECAUSE ONE PASS OPENS EVERY PART TOO QUIET.
#
# ffmpeg's `loudnorm` in single-pass form is an ADAPTIVE normaliser with no
# lookahead over the file: it starts from a guess and converges. Measured on
# Session #3 by rendering the same graph with the filter replaced by `anull` and
# differencing the two short-term tracks, the gain it actually applied was
#
#     0-2s  +1.84 dB     2-5s  +2.88     5-10s  +3.90     10-121s  +3.9..+4.2
#
# -- the first two seconds ship 2.1 dB under the rest and ramp up over about
# five. The feature is thirteen separately-normalised parts joined end to end,
# so that is thirteen fade-ups, one at every cut. NO STATIC MEASUREMENT OF THE
# FINISHED FILE CAN SEE IT: the integrated number comes out correct either way,
# which is why thirteen parts measuring within 1.1 LU of each other still had it.
#
# Its effect on DYNAMICS was nearly nil -- short-term range 6.3 LU against 6.6
# un-normalised -- so the convergence was the whole problem.
#
# AND `linear=true` DOES NOT FIX IT. Asked for a static move, loudnorm refused
# and fell back to dynamic SILENTLY, reproducing the ramp exactly (-2.11 against
# -2.12). Its own analysis says why: Session #3's mix is -19.90 LUFS with a true
# peak of -3.69 dBTP, so the +3.90 dB needed for -16 would land the peak at
# +0.21 dBTP.
#
# So gain and ceiling are separated and made explicit: ONE static gain for the
# whole file, then a limiter that only touches what pokes through (0.29% of
# samples on Session #3). This is not "adding limiting" -- dynamic-mode loudnorm
# has a limiter inside it and was already using it. All that changes is that the
# gain in front of it stops converging: opening deficit -2.12 dB -> -0.55 dB.
# THESE WERE TYPED HERE, BESIDE A season_identity THAT ALREADY SAID SO -- the
# exact fault this repo records about `24` in eleven files and `impact.ttf` in
# three. Found by moving one: a season's loudness target was changed from -16
# to -14, the film was re-baked, and it came out at -16 with the build log
# printing the number it had ignored. A delivery spec that is declared in one
# file and obeyed in another is not a spec. See learnings.md 38.
#
# LRA stays local: it is a property of this normalisation method rather than of
# the season, and season_identity does not claim it.
I_TARGET = identity.season.I_TARGET
TP_TARGET = identity.season.TP_TARGET
LRA_TARGET = 11.0
CEIL_DBFS = -2.0          # sample-peak ceiling; leaves room for intersample
RATE = 48000              # ONE delivery rate for the whole season, see below


def measure(path: str) -> dict:
    r = subprocess.run(
        [season_paths.ff("ffmpeg"), "-v", "info", "-nostats", "-i", path,
         "-af", f"loudnorm=I={I_TARGET}:TP={TP_TARGET}:LRA={LRA_TARGET}:"
                f"print_format=json", "-f", "null", "-"],
        capture_output=True, text=True)
    m = re.search(r"\{[^{}]*input_i[^{}]*\}", r.stderr, re.S)
    if not m:
        sys.exit("FAIL: loudness analysis returned no JSON. Not falling back "
                 "to single-pass loudnorm -- that is the defect this replaces.")
    return json.loads(m.group(0))


def true_peak(path: str) -> float:
    r = subprocess.run(
        [season_paths.ff("ffmpeg"), "-v", "info", "-nostats", "-i", path,
         "-af", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True, text=True)
    m = re.search(r"Peak:\s*(-?\d+\.?\d*)", r.stderr[-2000:])
    return float(m.group(1)) if m else float("nan")


# AND THE MIX IS PINNED TO AN EXACT SAMPLE COUNT, WHICH IS A DIFFERENT BUG.
#
# `atrim=0:{total_s:.3f}` in the mix graph truncates the length to three
# decimals. On a film of 2918 frames the picture is 121.583333s and the mix came
# out 121.583000s -- SIXTEEN SAMPLES short. `-shortest` on the final mux then
# refuses to emit a video frame it cannot cover, so the file shipped with 2917
# frames of picture against a full-length soundtrack: video 41 ms SHORTER than
# audio, in every part whose frame count does not divide evenly into 24.
#
# One part like that is a dropped frame nobody sees. Thirteen concatenated is a
# drift that ACCUMULATES, and in the delivered feature it did: +70 ms into film
# 1, +160 ms into film 2, +232 ms into film 3, still climbing. No per-film check
# could see it, because inside any one film the audio is exactly right.
#
# So the length is set in SAMPLES against the picture, not in printed seconds,
# and asserted. Nothing downstream is allowed to round it.
def normalize(path: str, secs: float) -> None:
    d = measure(path)
    gain = I_TARGET - float(d["input_i"])
    ceil = 10 ** (CEIL_DBFS / 20)
    # `atrim=end_sample` COUNTS IN THE FILTER GRAPH'S RATE, NOT THE OUTPUT'S.
    # INTRO_src and BIGSHOT_src build their bus at A_RATE = 96000 while the six
    # films run at 48000, so a sample count worked out at 48k cut those two
    # files in HALF -- the cold open came back 13.77s of a 27.54s picture. The
    # assert below caught it; without it that would have shipped. Resampling
    # first makes the trim and the target the same units everywhere, and gives
    # the season one delivery rate instead of two.
    want = int(round(secs * RATE))
    tmp = path + ".norm.wav"
    subprocess.run(
        [season_paths.ff("ffmpeg"), "-y", "-v", "error", "-i", path,
         "-af", f"volume={gain:.2f}dB,"
                # NOTHING IN THIS CHAIN HAS A LOOKAHEAD, which is the whole
                # rule: measured on an impulse at 48 kHz, alimiter arrives 239
                # samples late and asoftclip and aresample arrive on time.
                f"asoftclip=type=hard:threshold={ceil:.4f}:oversample=1,"
                f"aresample={RATE},apad,atrim=end_sample={want}",
         "-ar", str(RATE), "-c:a", "pcm_s16le", tmp], check=True)
    if not os.path.exists(tmp):
        sys.exit("FAIL: normalise wrote nothing")
    got_n = int(subprocess.run(
        [season_paths.ff("ffprobe"), "-v", "error", "-select_streams",
         "a:0", "-show_entries", "stream=duration_ts", "-of", "csv=p=0", tmp],
        capture_output=True, text=True, check=True).stdout.strip().rstrip(","))
    if got_n != want:
        sys.exit(f"FAIL: mix is {got_n} samples against {want} wanted for "
                 f"{secs:.6f}s of picture -- the concat will drift")
    os.replace(tmp, path)
    got, tp = measure(path), true_peak(path)
    print(f"  loudness: {float(d['input_i']):+.1f} -> "
          f"{float(got['input_i']):+.1f} LUFS "
          f"(static {gain:+.2f} dB), true peak {tp:+.1f} dBTP")
    if abs(float(got["input_i"]) - I_TARGET) > 0.7:
        print(f"       !! landed {float(got['input_i']) - I_TARGET:+.1f} LU "
              f"off target -- the clip is doing more than shaving peaks")
    if tp > TP_TARGET + 0.3:
        print(f"       !! true peak {tp:+.1f} dBTP is above {TP_TARGET:+.1f} "
              f"-- lower CEIL_DBFS")


# --------------------------------------------------------------------------
# THE BAKE RUNS ON EVERY CORE.
#
# A REAL WORKER POOL HERE, not the self-slicing trick the film trees use, and
# the difference is the loop body. This one is a pure function of (index,
# source frame): it opens a file, resizes it, optionally draws the title card,
# and writes a numbered PNG. Nothing carries between frames and draw_title
# builds its own fonts, so there is nothing that has to survive a pickle --
# which is exactly what makes a pool possible on Windows, where processes are
# SPAWNED rather than forked. The film trees read neighbouring frames and close
# over FreeType objects, so they get sliced instead. See docs/07_performance.md.
#
# The one restructure it needs: every clip is exploded BEFORE the pool starts,
# rather than one shot at a time inside the loop. Workers must not race each
# other extracting and deleting the same directories -- that is the exact bug
# the film trees hit, where a child succeeds alone and dies in company. The
# explode dirs are removed once, after all the frames are baked.
JOBS = max(1, min(16, (os.cpu_count() or 4) - 2))

_CTX: dict = {}


def _bake_init(srcs: list[str], w: int, h: int, title_from: int) -> None:
    _CTX.update(srcs=srcs, w=w, h=h, title_from=title_from)


def _bake_one(i: int) -> int:
    c = _CTX
    im = Image.open(c["srcs"][i]).convert("RGB")
    # THE FIT AND THE LOOK ARE THE SEASON'S, NAMED. This was a bare `resize`,
    # which is `stretch` -- correct only for as long as the open is shot at
    # exactly the delivery aspect, and silently squashing the moment it is not.
    #
    # AND THE UN-SQUEEZE COMES BEFORE THE FIT. The video model squashes a plate
    # into an off-aspect canvas rather than cropping it, and `crop` keeps the
    # distortion while trimming the edges. Note what the old bare `resize` did
    # here: mapping the whole canvas onto the whole frame un-squeezed by
    # accident, so replacing it with a correct fit made this beat WORSE on a
    # scope season until this line existed. See framing.unsqueeze().
    im = framing.apply(FIT, framing.unsqueeze(im, c["w"], c["h"], CANVASES),
                       c["w"], c["h"], FIT_OPTS)
    im = grades.apply(GRADE, im, GRADE_OPTS)
    if i >= c["title_from"]:
        t = (i - c["title_from"]) / max(1.0, TITLE_FADE * FPS)
        im = draw_title(im, min(1.0, t))
    # compress_level=1: these exist for the length of one ffmpeg call and are
    # then deleted, so paying level 6 to shrink them is spent CPU.
    im.save(os.path.join(BAKED, f"b_{i:05d}.png"), compress_level=1)
    return i


def main() -> int:
    shutil.rmtree(BAKED, ignore_errors=True)
    os.makedirs(BAKED)
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)

    total = sum(edit.FRAMES.values())
    title_from = total - round(edit.TITLE_HOLD * FPS)

    srcs, dirs = [], []
    for sid in shot.CUT:
        got = frames_of(sid)
        dirs.append(os.path.dirname(got[0]))
        srcs += got[:min(len(got), edit.FRAMES[sid])]
    with Image.open(srcs[0]) as probe:
        w, h = dims(*probe.size)

    done = 0
    with cf.ProcessPoolExecutor(max_workers=JOBS, initializer=_bake_init,
                                initargs=(srcs, w, h, title_from)) as pool:
        for _ in pool.map(_bake_one, range(len(srcs)), chunksize=4):
            done += 1
            if done % 200 == 0:
                print(f"    baked {done}/{total}")
    for d in dirs:
        shutil.rmtree(d, ignore_errors=True)

    # NOT len(srcs) TAKEN ON TRUST. A worker that died would leave a hole in the
    # middle of the picture and the encode would paper over it silently.
    i = len([f for f in os.listdir(BAKED) if f.endswith(".png")])
    if i != len(srcs):
        sys.exit(f"FAIL: {i} frames baked against {len(srcs)} planned -- a "
                 f"worker died. Re-run with JOBS = 1 to see the error.")
    print(f"  baked {i} frames across {JOBS} processes")

    secs = i / FPS
    wav = os.path.join(WORK, "mix.wav")
    cue = os.path.join(MUSIC, "open.mp3")
    if not os.path.exists(cue):
        sys.exit("FAIL: no cue -- run make_music.py")
    # THE CUE IS PLACED HERE, THE BUS COMES FROM ../mixes.py -- which pads the
    # result up to the picture as well as trimming it down. This was an `atrim`
    # alone, so a cue file shorter than the open ended the audio early and
    # `-shortest` took the picture with it, with nothing anywhere to notice.
    bus, out = mixes.bus(MIX, [], ["[m0]"], {"total": secs, "spans": []},
                         MIX_OPTS)
    graph = ";".join(
        [f"[0:a]atrim=0:{secs:.3f},asetpts=PTS-STARTPTS,"
         f"afade=t=in:st=0:d=1.5,"
         f"afade=t=out:st={max(0.0, secs - 1.6):.3f}:d=1.6,"
         f"aformat=sample_rates={A_RATE}:channel_layouts=stereo[m0]"] + bus)
    subprocess.run(
        [season_paths.ff("ffmpeg"), "-y", "-v", "error", "-i", cue,
         "-filter_complex", graph, "-map", out,
         "-c:a", "pcm_s16le", wav], check=True)
    normalize(wav, secs)
    got = float(subprocess.run(
        [season_paths.ff("ffprobe"), "-v", "error", "-show_entries",
         "format=duration", "-of", "csv=p=0", wav],
        capture_output=True, text=True, check=True).stdout.strip())
    if abs(got - secs) > 0.10:
        sys.exit(f"FAIL: the open's audio is {got:.2f}s against {secs:.2f}s of "
                 f"picture -- `-shortest` will cut the open to the sound.")

    dst = os.path.join(OUT, "cold_open.mp4")
    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                    "-framerate", str(FPS),
                    "-i", os.path.join(BAKED, "b_%05d.png"), "-i", wav,
                    "-c:v", "libx264", "-crf", str(CRF), "-preset", "slow",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", dst],
                   check=True)
    print(f"\n  {i} frames  {secs:.2f}s  {w}x{h}  "
          f"title from {title_from/FPS:.2f}s  "
          f"{os.path.getsize(dst)/1e6:.1f} MB -> {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
