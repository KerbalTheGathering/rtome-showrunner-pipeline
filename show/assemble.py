"""Bake the six interstitials: board type, television grade, voice, sting.

ONE MP4 PER SEGMENT, not one reel. The feature cut interleaves these with six
films, so each has to stand alone and start and end clean. Concatenation is
feature.py's job and it should have nothing to fix up.

THE TYPE IS DRAWN HERE AND HAS ALWAYS BEEN GOING TO BE. Generated lettering
comes back as garbage on this stack -- it is why every session carries a _NOTEXT
block and why #2's campaign sign has a face and no words. So the plate leaves
the board blank, motion.py holds it blank for the full runtime, and the bounty
lands here at bake resolution where it is sharp and spelled correctly.

IT LANDS LINE BY LINE, ON THE WORD. Each of the three type lines appears at the
offset of the VO line that says it, taken from edit.offsets() so the two cannot
disagree. And it appears as a HARD CUT, not a fade: this is a felt letterboard,
somebody is slapping the letters on, and a dissolve would make it a graphic.

THE TELEVISION GRADE IS A FULL CRT PASS AND IT LIVES IN crt.py. It began as a
light touch -- fine scanlines, a one-pixel chroma smear, a vignette -- on the
argument that the flat studio LIGHT had already bought the interruption and
scanlines on top would be saying it twice. That was true of the argument and
false of the picture: at 1440x1080 a 5% scanline is invisible, so the segments
read as the same painted illustration as the films, only brighter.

What replaced it is a signal chain rather than an overlay -- bandwidth-limited
luma and chroma, lifted black, bloom, tube curvature with black corners,
scanlines and an aperture grille, a rolling hum bar. Compare presets on real
frames with tvtest.py before changing TV below; the two things this pass can
break are the legibility of the number and the shape of the glass, and its
detail sheet crops both at 1:1.

SEGMENT SIX DRAWS NOTHING, and it needs no special case. Its BOARD_TYPE is an
empty tuple, so the loop that draws type simply has nothing to iterate. The
board stays exactly as empty as the camera found it.

    python assemble.py            # all six
    python assemble.py 03 06      # just these
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402
import upscale                                                     # noqa: E402


import concurrent.futures as cf
import math
import json
import re
import os
import shutil
import struct
import subprocess
import sys
import wave

from PIL import Image, ImageDraw, ImageFont

import crt
import mixes                # the audio bus library, at the season root
import edit
import identity
import script
import shot

HERE = os.path.dirname(os.path.abspath(__file__))
FF = season_paths.FFMPEG
WORK = os.path.join(HERE, "_work")
BAKED = os.path.join(HERE, "_baked")
OUT = os.path.join(HERE, "out")
VO = os.path.join(HERE, "_vo")
MUSIC = os.path.join(HERE, "_music")
CLIPS = os.path.join(season_paths.COMFY_OUTPUT, f"{shot.NAME}_clips")

# THE SEASON'S RATE, DERIVED. `24` was typed in eleven files beside a
# season_identity.FPS that already said so -- and feature.py asserts every
# part matches, so a season at another rate would have been caught only
# after every part was baked.
FPS = float(identity.season.FPS)
CRF = 18

# Leave a couple of threads for ffmpeg and the machine. Above sixteen the PNG
# writes start contending for the disk rather than the CPU.
JOBS = max(1, min(16, (os.cpu_count() or 4) - 2))

# 96 kHz BECAUSE THAT IS WHAT THE SIX FILMS ARE, and feature.py concatenates
# these with them by stream copy. A 48 kHz interstitial would force the whole
# 14-minute cut to be re-encoded -- or worse, concatenate with a sample-rate
# mismatch the container does not complain about. Probed off the shipped films
# rather than assumed; 96 kHz is not a number anybody would have guessed.
A_RATE = 96000

# The same floor every film in the season bakes to, so the feature cut never
# has to rescale anything.
# DERIVED FROM THE SEASON, NOT TYPED. It was `960, 1080` -- 4:3's answer
# written down in the one place that would silently letterbox a season that is
# not 4:3. feature.py asserts every part matches, so it would have caught the
# mismatch, but only after every part had been baked.
#
# THE RESULT IS UNCHANGED FOR A 4:3 SEASON: a 1024x768 clip scales by 1.40625
# either way, because pick_canvas() shoots at the delivery aspect and a clip at
# that aspect clears both floors at the same scale.
W_MIN, H_MIN = identity.season.W, identity.season.H

FONT = season_paths.font(identity.season.FONT_DISPLAY)
CREAM = (247, 240, 224)
INK = (24, 20, 18)

# The two information lines are set at ONE size and the number is set bigger.
#
# NOT A HEIGHT PER LINE, WHICH IS WHAT THIS WAS AND WHY IT LOOKED WRONG. Asking
# for a fixed fraction of the board per line means a short line renders at the
# requested size and a long one gets shrunk to fit the width -- so "BIRD" came
# out LARGER than "$12 A HEAD", and the county line larger than the money. The
# number is the only thing anybody in this world is listening for and it has to
# be the biggest thing on the felt every single week.
#
# So both info lines take the SMALLER of their two fitted sizes (they match each
# other, which is what makes it look like a board rather than a poster), and the
# number is then set as large as its own width allows up to a multiple of them.
INFO_H = 0.19               # first guess at info-line height, board fractions
NUMBER_X = 1.9              # the number, relative to the info lines
LINE_GAP = 0.085

# Which television. The chain itself lives in crt.py; this is only the dial.
# Override for one run with --tv=NAME, which is how tvtest.py's answer gets
# turned into a bake without editing anything.
#
# THE DIAL LIVES IN identity.py AND IS READ, NOT RETYPED. This was
# `TV = "heavy"` typed here beside an identity.TV the identity's own comment
# claimed was the setting -- so a season that set identity.TV = "" (a show
# that is not on a television) shipped three segments through the heavy tube
# anyway, at the tube's cabinet geometry. A spec declared in one file and
# obeyed in another is not a spec; same class as fault 38's loudness target.
# ("heavy" itself was the user's choice off tvtest.py's 1:1 sheet on
# 2026-08-08 and stays recorded in identity.py, where the dial is.)
TV = identity.TV

# WHAT SITS UNDER WHAT, from ../mixes.py. The show's arrangement is fixed
# levels -- see identity.py. The `music` setting carries the sting's 0.42,
# which used to be a literal inside two separate filter chains in mix().
MIX, MIX_OPTS = identity.MIX, identity.MIX_OPTS
mixes.load_extra(HERE)


# --------------------------------------------------------------------------
# picture
# --------------------------------------------------------------------------

def dims(sw: int, sh: int) -> tuple[int, int]:
    s = max(1.0, W_MIN / sw, H_MIN / sh)
    w, h = round(sw * s), round(sh * s)
    return w - w % 2, h - h % 2


def fit(text: str, px: int, cap: float) -> ImageFont.FreeTypeFont:
    """Largest Impact that keeps `text` inside `cap` pixels, at most `px` tall."""
    f = ImageFont.truetype(FONT, px)
    while px > 8:
        if f.getbbox(text)[2] <= cap:
            return f
        px -= 2
        f = ImageFont.truetype(FONT, px)
    return f


def _layout(sid: str, bw: float, bh: float):
    """Fonts and line heights for one board. Same every frame, so cached."""
    key = (sid, round(bw), round(bh))
    got = _LAYOUT.get(key)
    if got is not None:
        return got
    lines = shot.BOARD_TYPE[sid]
    info = [fit(t, round(bh * INFO_H), bw) for t in lines[:2]]
    px = min(f.size for f in info) if info else round(bh * INFO_H)
    info = [ImageFont.truetype(FONT, px) for _ in lines[:2]]
    num = fit(lines[2], round(px * NUMBER_X), bw) if len(lines) > 2 else None
    fonts = info + ([num] if num else [])
    got = (fonts, [f.size for f in fonts])
    _LAYOUT[key] = got
    return got


_LAYOUT: dict[tuple, tuple] = {}


def draw_board(im: Image.Image, sid: str, shown: int) -> Image.Image:
    """Stamp the first `shown` lines of the bounty onto the board."""
    lines = shot.BOARD_TYPE[sid]
    if not lines or shown <= 0:
        return im
    w, h = im.size
    x0, y0, x1, y1 = shot.type_rect(sid)
    bx0, by0, bx1, by1 = x0 * w, y0 * h, x1 * w, y1 * h
    bw, bh = bx1 - bx0, by1 - by0

    fonts, sizes = _layout(sid, bw, bh)
    gap = bh * LINE_GAP
    # THE WHOLE BLOCK IS CENTRED IN THE BOARD, not hung from the top. Laying out
    # from by0 with fixed slots left the bottom half of the felt empty whenever
    # the lines got width-limited, which is most of them.
    block = sum(sizes) + gap * (len(sizes) - 1)
    y = by0 + (bh - block) / 2.0

    d = ImageDraw.Draw(im)
    for i, text in enumerate(lines):
        f, px = fonts[i], sizes[i]
        if i < shown:
            tw = f.getbbox(text)[2]
            # Right-aligned: he stands in front of the board's left edge, and it
            # is how a letterboard actually fills up.
            d.text((bx1 - tw, y), text, font=f, fill=CREAM,
                   stroke_width=max(2, round(px * 0.07)), stroke_fill=INK)
        y += px + gap
    return im


def clip_for(sid: str) -> str:
    got = sorted(f for f in os.listdir(CLIPS)
                 if f.startswith(f"s{sid}_") and f.endswith(".mp4")
                 and "_rej_" not in f)
    if not got:
        sys.exit(f"FAIL: no clip for segment {sid} in {CLIPS} -- run h3_shoot.py")
    return os.path.join(CLIPS, got[-1])


# The worker half of bake(). MODULE LEVEL AND NOT A CLOSURE, because Windows
# spawns rather than forks: every argument crosses to the child by pickle, and a
# nested function cannot make that trip. The context arrives once per worker
# through the initializer instead of once per frame.
_CTX: dict = {}


def _bake_init(frames_dir: str, names: list[str], sid: str, marks: list[int],
               plain: bool, w: int, h: int, tv: str) -> None:
    # TV TRAVELS EXPLICITLY. `--tv=` rebinds the module global in main(), and a
    # spawned worker re-imports this file from scratch -- it would have quietly
    # baked the default preset while the parent reported the requested one.
    _CTX.update(dir=frames_dir, names=names, sid=sid, marks=marks,
                plain=plain, w=w, h=h, tv=tv)


def _bake_one(i: int) -> int:
    c = _CTX
    im = Image.open(os.path.join(c["dir"], c["names"][i])).convert("RGB")
    im = im.resize((c["w"], c["h"]), Image.LANCZOS)
    # THE COVER SCALE OVERSHOOTS ON A SOURCE THAT IS NOT EXACTLY THE DELIVERY
    # ASPECT, AND ON A 4:3 SEASON THAT NEVER SHOWED. dims() scales UP to cover
    # both delivery floors and nothing here ever cropped: InfiniteTalk's
    # near-16:9 canvas came back 1920x1082 on a 16:9 season, and feature.py
    # (rightly) refused a part two rows taller than the films. On 4:3 the
    # numbers happen to land exact, which is why five seasons never saw it.
    if (c["w"], c["h"]) != (W_MIN, H_MIN):
        x0 = (c["w"] - W_MIN) // 2
        y0 = (c["h"] - H_MIN) // 2
        im = im.crop((x0, y0, x0 + W_MIN, y0 + H_MIN))
    if not c["plain"]:
        shown = sum(1 for m in c["marks"] if i >= m)
        im = draw_board(im, c["sid"], shown)
        # THE FRAME INDEX GOES IN because the tube is not a still filter -- the
        # hum bar drifts, and passing 0 every frame would nail it to one height
        # and turn a rolling band into a permanent bright stripe. AN EMPTY DIAL
        # SKIPS THE PASS -- identity.TV = "" is a show that is not on a
        # television, and crt.PRESETS has no "" entry to fall through to.
        if c["tv"]:
            im = crt.tube(im, c["tv"], i)
    im.save(os.path.join(BAKED, f"b_{i:05d}.png"), compress_level=1)
    return i


def board_marks(sid: str) -> list[int]:
    """The frame each line of board type lands on, from the VO offsets so the
    board and the voice cannot drift apart.

    IT IS A FUNCTION SO THE LOG CAN COUNT THE SAME THING THE BAKER DRAWS. This
    was two lines inside bake(), and main() then reported
    `len(shot.BOARD_TYPE[sid])` -- what was asked for -- while the baker
    stamped `len(marks)`, what there was room for. Three lines of type against
    one line of copy printed "3 line(s) of type" and drew one, on a delivered
    reel. shot.py now asserts the two can never differ; this makes it visible
    if they somehow do.
    """
    offs = [t for _, t in edit.offsets(sid)]
    return [round(t * FPS) for t in offs][:len(shot.BOARD_TYPE[sid])]


def bake(sid: str, src: str | None = None,
         plain: bool = False) -> tuple[int, int, int]:
    """Upscale, optionally stamp the board and grade it.

    `plain` is the pass that FEEDS Kling: same geometry, no type, no television
    treatment. Lip sync has to happen on the clean picture so the board type
    stays drawn at bake resolution rather than being re-encoded through a video
    model, and so Kling never sees the scanlines.

    `src` overrides the clip, which is how the second pass reads Kling's return
    instead of the raw H3 shoot.
    """
    shutil.rmtree(BAKED, ignore_errors=True)
    os.makedirs(BAKED)
    src = src or clip_for(sid)
    frames_dir = os.path.join(WORK, f"src_{sid}")
    shutil.rmtree(frames_dir, ignore_errors=True)
    os.makedirs(frames_dir)
    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                    "-i", upscale.clip(src), os.path.join(frames_dir, "f_%05d.png")],
                   check=True)

    got = sorted(os.listdir(frames_dir))
    want = edit.FRAMES[sid]
    n = min(len(got), want)
    # THE CLEAN PASS PADS A SHORT BASE UP TO THE SEGMENT. The H3 base clip is
    # capped (edit.BASE_FRAMES -- the latent budget cannot carry a long
    # talking hold), and the sync consumes exactly two things from this bake:
    # FRAME ZERO as its anchor image, and total_s as the length of the driver
    # audio. The repeated frames feed neither a viewer nor the model; they
    # exist so vo_XX.wav covers the whole segment. The FINAL pass never comes
    # through here short -- it bakes italk's full-length synced render.
    if plain and len(got) < want:
        got = got + [got[-1]] * (want - len(got))
        n = want

    marks = board_marks(sid)

    with Image.open(os.path.join(frames_dir, got[0])) as probe:
        w, h = dims(*probe.size)

    # ONE FRAME AT A TIME WAS COSTING TWENTY MINUTES A PASS ON A 16-CORE BOX.
    # The tube is the expensive part and it is a pure function of (frame, index)
    # -- no state carries between frames, the hum bar's phase comes from `i` --
    # so the loop was a serial bottleneck by accident rather than by necessity.
    # Measured at 126 frames/min on one core against 2257 frames a pass.
    #
    # `compress_level=1` on top of that: these PNGs exist for the length of one
    # ffmpeg call and are then deleted, so paying level 6 to make them smaller
    # is spending CPU on a file nobody keeps.
    ctx = (frames_dir, got, sid, marks, plain, w, h, TV)
    done = 0
    with cf.ProcessPoolExecutor(max_workers=JOBS, initializer=_bake_init,
                                initargs=ctx) as pool:
        for _ in pool.map(_bake_one, range(n), chunksize=4):
            done += 1
            if done % 200 == 0:
                print(f"    baked {done}/{n}")
    shutil.rmtree(frames_dir, ignore_errors=True)
    # WHAT WAS WRITTEN, NOT WHAT WAS SCALED. _bake_one centre-crops the cover
    # overshoot to the season's exact geometry; reporting the pre-crop pair
    # here is how a log says 1082 about a directory full of 1080s.
    return n, min(w, W_MIN), min(h, H_MIN)


# --------------------------------------------------------------------------
# sound
# --------------------------------------------------------------------------

_ENV: dict[str, tuple[float, float, float]] = {}


def env(lid: str) -> tuple[float, float, float]:
    """(file secs, leading silence, trailing silence) for a take."""
    if lid in _ENV:
        return _ENV[lid]
    wav = os.path.join(HERE, "_vo_wav", f"{lid}.wav")
    if not os.path.exists(wav):
        edit.speech(lid)                      # builds the wav as a side effect
    with wave.open(wav) as w:
        sr, n = w.getframerate(), w.getnframes()
        pcm = struct.unpack(f"<{n}h", w.readframes(n))
    total = n / sr
    win = int(sr * 0.010)
    k = n // win
    rms = [math.sqrt(sum(v * v for v in pcm[i * win:(i + 1) * win]) / win)
           / 32768.0 + 1e-12 for i in range(k)]
    live = [i for i, r in enumerate(rms) if 20 * math.log10(r) > -45.0]
    if not live:
        out = (total, 0.0, 0.0)
    else:
        out = (total, live[0] * 0.010, total - (live[-1] + 1) * 0.010)
    _ENV[lid] = out
    return out


_SPEECH_DB: dict[str, float] = {}


def speech_db(lid: str) -> float:
    """A take's loudness over its SPEECH only, in dBFS.

    Over the speech, not the file: a take that happens to arrive with two
    seconds of air in front of it would otherwise measure quiet and get boosted
    into the take beside it.
    """
    if lid in _SPEECH_DB:
        return _SPEECH_DB[lid]
    wav = os.path.join(HERE, "_vo_wav", f"{lid}.wav")
    if not os.path.exists(wav):
        edit.speech(lid)
    with wave.open(wav) as w:
        sr, n = w.getframerate(), w.getnframes()
        pcm = struct.unpack(f"<{n}h", w.readframes(n))
    win = int(sr * 0.010)
    rms = [math.sqrt(sum(v * v for v in pcm[i * win:(i + 1) * win]) / win)
           / 32768.0 + 1e-12 for i in range(n // win)]
    live = [r for r in rms if 20 * math.log10(r) > -45.0]
    out = (20 * math.log10(math.sqrt(sum(r * r for r in live) / len(live)))
           if live else -30.0)
    _SPEECH_DB[lid] = out
    return out


# "I CAN DISTINCTLY FEEL THE EDGES OF YOUR TAKES ON YOUR VO" -- the note from
# the 2026-08-08 review, and it is measurable: this reel's takes span 5.7 dB.
# The mix normalises the finished SEGMENT once and places every take at whatever
# level eleven_v3 happened to return, so each new line steps.
#
# MATCHED DOWNWARD, TO THE QUIETEST TAKE, NOT UP TO THE MEDIAN. These takes peak
# between -0.5 and -1.9 dBFS, so there is under 2 dB of headroom and the quiet
# ones physically cannot be raised to meet the loud ones without clipping.
# Attenuating instead is free -- the loudnorm at the end of the graph puts the
# whole segment back where it belongs, with the steps gone.
#
# Bounded, so one pathological take cannot drag the reel down with it.
MATCH_FLOOR_DB = 8.0


# THE FINAL 10ms MUST BEAT THE PRECEDING 100ms BY THIS MUCH to count as a
# transient. See _session_template/assemble.py's vo_tail() for the profile this
# came out of; the number is the same in both trees on purpose.
_TRANSIENT_RATIO = 2.0
_SPIKE: dict[str, bool] = {}


def tail_spike(lid: str) -> bool:
    """Does this take actually END on a transient? Peaks, not RMS.

    A 10ms spike barely moves the RMS of the window holding it, so env()'s
    silence measurement could not have seen one even if it had been looking --
    and it was not looking, because nothing was: the trim was applied to every
    take on the strength of make_vo.py's claim that eleven_v3 always produces
    one. A fork profiled 34 takes at sample level and found it in zero of them.
    """
    if lid in _SPIKE:
        return _SPIKE[lid]
    wav = os.path.join(HERE, "_vo_wav", f"{lid}.wav")
    if not os.path.exists(wav):
        edit.speech(lid)                      # builds the wav as a side effect
    with wave.open(wav) as w:
        sr, n = w.getframerate(), w.getnframes()
        pcm = struct.unpack(f"<{n}h", w.readframes(n))
    win = int(sr * 0.010)
    if n < 2 * win:
        _SPIKE[lid] = False
        return False
    last = max(abs(v) for v in pcm[-win:])
    before = max(abs(v) for v in pcm[max(0, n - 11 * win):n - win]) or 1
    _SPIKE[lid] = last > _TRANSIENT_RATIO * before
    return _SPIKE[lid]


def vo_tail(trailing: float, spike: bool) -> tuple[float, float]:
    """(trim, fade) for a take's end, measured rather than assumed.

    TWO MEASUREMENTS, AND THE FIRST ONE IS WHETHER THERE IS ANYTHING TO CUT.
    make_vo.py stated the trailing transient as a property of the vendor --
    "every eleven_v3 take" -- and this function only ever asked how much tail
    could be SPARED. A fork profiled all 34 of its takes against the actual
    signature and found it in none, where trimming 25ms from each would have
    discarded 850ms of real speech to solve a problem that was not there.

    What IS wrong on those takes is milder and wants a different tool: a file
    that stops while low-level energy is still present, butted against digital
    silence, CLICKS. That is a discontinuity, and a fade fixes a discontinuity
    without removing a single sample.

    The trailing-silence half still earns its place. FOURTEEN OF THIS REEL'S
    NINETEEN TAKES END ON A WORD with no trailing silence at all -- Dale Brinley
    simply stops -- so a trim that is warranted still has to be small enough not
    to land on speech, which is the defect that shipped once on Session #3's
    last line.
    """
    if not spike:
        return (0.0, 0.010)
    return (0.025, 0.050) if trailing >= 0.075 else (0.012, 0.020)


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
#
# AND THEN THE LIMITER CAME OUT AGAIN, BECAUSE A LIP-SYNCED PART CANNOT AFFORD
# ONE. `alimiter` works by looking ahead `attack` milliseconds, which means it
# DELAYS everything it passes -- measured at 239 samples for attack=5 at 48 kHz,
# and the file does not get longer, so the tail is simply lost. Every segment
# therefore shipped its whole soundtrack late against its own picture.
#
# Five milliseconds is an eighth of a frame, and on the six films that is
# genuinely nothing. On these six it is not nothing, because the mouths in
# synced_XX.mp4 were GENERATED from this waveform: the picture does not merely
# accompany the sound, it is a function of it, so any offset at all is a sync
# error by construction rather than a tolerance. Measured on the shipped
# segments: 04 +5.5 ms, 06 +4.1 ms, 05 +3.0 ms.
#
# Compensating for it worked -- those three read 0.0 ms once the head was
# trimmed back off -- and it is still the wrong answer, because it leaves a
# stage in the chain whose whole job is to move the audio and then subtracts
# what it moved. Get the correctness from the STRUCTURE instead: the only thing
# between the driver and the delivered file is now a scalar multiply, and a
# scalar cannot produce a lag.
#
# THE CEILING IS A HARD CLIP, WHICH IS THE ONLY KIND THAT CANNOT MOVE ANYTHING.
# Backing the gain off to fit the raw sample peak was tried first and it is too
# expensive: segment 06's driver peaks at 0.0 dBFS, so the whole part landed at
# -18.6 LUFS, 2.6 LU under the five around it. `asoftclip=type=hard` clamps the
# handful of samples that poke through and leaves every other sample bit for
# bit alone -- what a limiter does, minus the lookahead that was the bug.
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
QUIET_WARN = 1.5          # dB the ceiling may cost before it is worth saying
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


def peak_dbfs(path: str) -> float:
    """Sample peak, which is what a scalar gain has to fit under."""
    r = subprocess.run(
        [season_paths.ff("ffmpeg"), "-v", "info", "-nostats", "-i", path,
         "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True)
    m = re.search(r"max_volume:\s*(-?\d+\.?\d*) dB", r.stderr)
    if not m:
        sys.exit("FAIL: volumedetect returned no peak -- refusing to guess a "
                 "gain that could clip")
    return float(m.group(1))


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
    headroom = CEIL_DBFS - peak_dbfs(path)
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
         # NOTHING IN THIS CHAIN HAS A LOOKAHEAD. That is the whole design rule:
         # the mouths on screen were generated from these samples, so a stage
         # that delays what it passes is a lip sync error by construction.
         #
         # Measured on a single-sample impulse at 48 kHz, delay in samples:
         #     alimiter attack=5                      239   <- what was here
         #     asoftclip type=hard oversample=1          0
         # and asoftclip is bit-identical below its threshold (checked against
         # a -20 dBFS tone: zero differing samples out of 96000), so it is a
         # ceiling and not a grade. `aresample` measures zero too.
         "-af", f"volume={gain:.2f}dB,"
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
    if gain > headroom + QUIET_WARN:
        print(f"       !! {gain - headroom:.1f} dB of the gain is going "
              f"through the ceiling -- the clip is doing more than shaving "
              f"transients, check the VO for a bang")
    if tp > TP_TARGET + 0.3:
        print(f"       !! true peak {tp:+.1f} dBTP is above {TP_TARGET:+.1f} "
              f"-- lower CEIL_DBFS")


# --------------------------------------------------------------------------


def mix(sid: str, total_s: float, dest: str, vo_only: bool = False) -> None:
    """Voice at the scripted offsets, sting under the top.

    `vo_only` drops the sting, and that is what gets fed to Kling: the node
    wants "clearly distinguishable vocals", and a brass fanfare sitting under
    the first four seconds is the opposite of that. The film still gets the
    full mix -- this is only what the lip sync listens to.
    """
    # THE SHIPPED VOICE IS THE FILE THAT DROVE THE LIPS, NOT A RE-DERIVATION.
    #
    # `vo_{sid}.wav` is this same function's `vo_only` output, and it is what
    # italk.py handed to InfiniteTalk: every mouth position in synced_{sid}.mp4
    # was generated from those exact samples. Re-running the placement here to
    # build the full mix produced the same timeline in principle -- and measured
    # within 5 ms in practice -- but "in principle" is doing real work in that
    # sentence. Any later change to a take, to edit.offsets(), to the leading
    # silence trim or to a rounding rule would move the words and leave the lips
    # where they were, with nothing in the build to notice.
    #
    # So the driver is reused verbatim and the sting is laid over it. The words
    # cannot drift from the mouths, because they are the same samples. If the
    # driver is missing the function falls back to placing takes, which is how
    # `vo_only` bootstraps it in the first place.
    driver = os.path.join(WORK, f"synced_{sid}.wav")
    picture = os.path.join(WORK, f"synced_{sid}.mp4")
    if not vo_only and os.path.exists(picture):
        # THE VOICE COMES OUT OF THE RENDER, NOT OUT OF THE EDIT.
        #
        # italk.py writes synced_XX.mp4 and synced_XX.wav in one ffmpeg call
        # from one set of numbers. Reading the wav here means the sound in the
        # finished segment is the same timeline as the sound that made the
        # mouths, with no step in between that re-derives it -- and a re-roll
        # of a segment brings its audio along instead of leaving the old one
        # pointing at the new picture.
        if not os.path.exists(driver):
            sys.exit(f"FAIL: {os.path.basename(picture)} has no "
                     f"{os.path.basename(driver)} beside it.\n  Re-run "
                     f"`python italk.py {sid} --force` -- that is the only "
                     f"place the two are cut together, and baking from the "
                     f"edit instead is how the words come off the mouths.")
        if os.path.getmtime(driver) < os.path.getmtime(picture) - 1.0:
            sys.exit(f"FAIL: {os.path.basename(driver)} is older than "
                     f"{os.path.basename(picture)} -- the picture has been "
                     f"re-rendered since the voice was cut. Re-run italk.py "
                     f"for {sid}.")
        ins = ["-i", driver]
        parts = [f"[0:a]aformat=sample_rates=96000:"
                 f"channel_layouts=stereo[v0]"]
        labels, mlabels = ["[v0]"], []
        sting = os.path.join(MUSIC, "sting.mp3")
        if os.path.exists(sting):
            ins += ["-i", sting]
            parts.append(
                f"[1:a]atrim=0:{min(4.0, total_s):.3f},asetpts=PTS-STARTPTS,"
                f"afade=t=out:st={max(0.0, min(4.0, total_s) - 1.2):.3f}:d=1.2,"
                f"aformat=sample_rates=96000:channel_layouts=stereo[m]")
            mlabels.append("[m]")
        bus, out = mixes.bus(MIX, labels, mlabels,
                             {"total": total_s, "spans": []}, MIX_OPTS)
        graph = ";".join(parts + bus)
        subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error"]
                       + ins + ["-filter_complex", graph, "-map", out,
                                "-c:a", "pcm_s16le", dest], check=True)
        normalize(dest, total_s)
        print(f"       voice from {os.path.basename(driver)} "
              f"(the InfiniteTalk driver), sting over it")
        return

    ins, parts, labels, spans = [], [], [], []
    takes = edit.offsets(sid)
    lv = [speech_db(lid) for lid, _ in takes]
    med = sorted(lv)[len(lv) // 2]
    target = max(min(lv), med - MATCH_FLOOR_DB)
    for n, (lid, off) in enumerate(takes):
        d, lead, trail = env(lid)
        trim, fade = vo_tail(trail, tail_spike(lid))
        gain = min(0.0, target - lv[n])
        # LEADING SILENCE IS CUT, NOT PLACED AROUND. edit.py owns every pause in
        # this reel; a take that happens to arrive with 2.1s of air in front of
        # it (segment six's "Well.") would otherwise silently add its own.
        ss = max(0.0, lead - 0.03)
        end = max(0.05, d - trim)
        ins += ["-i", os.path.join(VO, f"{lid}.mp3")]
        parts.append(
            f"[{n}:a]atrim={ss:.3f}:{end:.3f},asetpts=PTS-STARTPTS,"
            f"volume={gain:.2f}dB,"
            f"afade=t=in:st=0:d=0.010,"
            f"afade=t=out:st={max(0.0, end - ss - fade):.3f}:d={fade:.3f},"
            f"adelay={int(off * 1000)}|{int(off * 1000)},"
            f"aformat=sample_rates=96000:channel_layouts=stereo[v{n}]")
        labels.append(f"[v{n}]")
        # Where the words are, for a bus that ducks by automation. The show's
        # `flat` bus ignores this; a show that switches to `under` needs it,
        # and deriving it here means it cannot drift from the placement above.
        spans.append((off, off + max(0.05, end - ss)))

    sting, mlabels = os.path.join(MUSIC, "sting.mp3"), []
    if os.path.exists(sting) and not vo_only:
        ins += ["-i", sting]
        si = len(labels)
        parts.append(
            f"[{si}:a]atrim=0:{min(4.0, total_s):.3f},asetpts=PTS-STARTPTS,"
            f"afade=t=out:st={max(0.0, min(4.0, total_s) - 1.2):.3f}:d=1.2,"
            f"aformat=sample_rates=96000:channel_layouts=stereo[m]")
        mlabels.append("[m]")

    # THE BUS IS ../mixes.py's, NOT THIS FILE'S. It was `amix, apad, atrim`
    # written out twice in this function and once more in italk_multi.py --
    # and the third copy had the length wrong, which is what a three-times
    # duplicated idiom is for. `flat` is the show's arrangement: the sting
    # sits at a fixed level and nothing moves, because the host is the show.
    bus, out = mixes.bus(MIX, labels, mlabels,
                         {"total": total_s, "spans": spans}, MIX_OPTS)
    graph = ";".join(parts + bus)
    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error"] + ins +
                   ["-filter_complex", graph, "-map", out,
                    "-c:a", "pcm_s16le", dest], check=True)
    normalize(dest, total_s)


def main() -> int:
    global TV
    for a in sys.argv[1:]:
        if a.startswith("--tv="):
            TV = a.split("=", 1)[1]
            if TV not in crt.PRESETS:
                sys.exit(f"FAIL: no tube preset {TV!r} -- "
                         f"have {sorted(crt.PRESETS)}")
    want = [a for a in sys.argv[1:] if not a.startswith("-")] or list(shot.CUT)
    bad = [s for s in want if s not in shot.CUT]
    if bad:
        sys.exit(f"FAIL: {bad} are not segments")
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)

    # --clean : picture only, no type, no grade, no sting -> feeds the lip sync
    # --raw   : bake the H3 take even though a lip-synced render exists
    #
    # THE LIP-SYNCED RENDER IS THE DEFAULT AND USED TO BE A FLAG, AND THAT COST
    # THE WHOLE SEASON. `--synced` was opt-in, so any rebuild that forgot it
    # baked the raw H3 clip instead -- same plate, same length, same framing,
    # same everything except that the mouth was never driven by the voice. All
    # six interstitials shipped that way and the defect reads as "the audio is
    # out of sync", which sent the hunt into the audio chain for two days. It is
    # not detectable in a frame grab and no assert in the build could see it.
    #
    # So the flag is inverted: if synced_XX.mp4 is on disk it IS the picture,
    # and going back to the raw take has to be asked for out loud. which_source.
    # py measures the delivered file against both candidates afterwards, because
    # a default is a habit and this needs a check.
    clean = "--clean" in sys.argv
    raw = "--raw" in sys.argv
    if "--synced" in sys.argv:
        print("  (--synced is the default now; the flag is ignored)")
    if clean and raw:
        sys.exit("FAIL: --clean builds the input; there is nothing raw about it")

    for sid in want:
        src = None
        if not clean and not raw:
            src = os.path.join(WORK, f"synced_{sid}.mp4")
            if not os.path.exists(src):
                sys.exit(f"FAIL: {src} missing.\n  Run `python italk.py {sid}` "
                         f"-- or `--raw` to deliberately bake the un-synced H3 "
                         f"take.")
        print(f"  [{sid}] {shot.BEAT[sid]['what']}"
              + ("   [clean, for lip sync]" if clean else
                 f"   [H3 RAW, NOT LIP SYNCED, tube={TV}]" if raw else
                 f"   [InfiniteTalk render, tube={TV}]"))
        n, w, h = bake(sid, src=src, plain=clean)
        total_s = n / FPS
        wav = os.path.join(WORK, f"{'vo' if clean else 'mix'}_{sid}.wav")
        mix(sid, total_s, wav, vo_only=clean)
        dst = (os.path.join(WORK, f"clean_{sid}.mp4") if clean
               else os.path.join(OUT, f"bounty_{sid}.mp4"))
        subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                        "-framerate", str(FPS),
                        "-i", os.path.join(BAKED, "b_%05d.png"),
                        "-i", wav,
                        "-c:v", "libx264", "-crf", str(CRF), "-preset", "slow",
                        "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "320k", "-shortest", dst],
                       check=True)
        # A COUNT IN A LOG LINE MUST BE A COUNT OF WHAT WAS DONE. This printed
        # `typed`, the length of the board table -- so a segment with three
        # lines of type and one line of copy reported "3 line(s) of type"
        # while drawing one, and a whole reel shipped that way. Nothing found
        # it until somebody grabbed a frame off the delivered mp4 and looked
        # at the felt. `drawn` is len(marks): one mark per line ACTUALLY
        # scheduled, which is what the baker stamps.
        typed, drawn = len(shot.BOARD_TYPE[sid]), len(board_marks(sid))
        note = "" if drawn == typed else "  <-- NOT ALL DRAWN"
        print(f"       {n} frames  {total_s:.2f}s  {w}x{h}  "
              f"{drawn} of {typed} line(s) of type drawn{note}  "
              f"{os.path.getsize(dst)/1e6:.1f} MB -> {os.path.basename(dst)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
