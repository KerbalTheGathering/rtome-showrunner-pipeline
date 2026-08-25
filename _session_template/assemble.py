"""Cut Session #2: fifteen beats, two new devices, two carried, VO and score.

MP4 ONLY, 24fps NATIVE, one clock. Every compositing decision is resolved
against its own segment's length in plan() and baked into the per-frame record;
the baker only reads the plan. Recomputing any of it against a strided index is
the two-clocks bug and on a travelling seam it shows up as the seam jumping.

DEVICE DISCIPLINE IS THE POINT. Session #1 established a vocabulary -- a
travelling cream seam, a hard-edged register break, a flat grade that means "a
place with nothing in it". This session KEEPS the grammar and spends two NEW
sentences in it, and deliberately drops the triptych and the inset box. A film
that runs every device is a device demo and none of them mean anything.

  THE ROW WIPE (new, once, 01 -> 02). The grove is rows, so the incoming shot
  arrives in vertical bands staggered left to right, like passing trunks. It is
  Session #1's single seam played as a chord -- same instrument, evolved. It
  fires on the one cut where the film leaves the water and goes inland, which is
  this session's whole structural job.

  THE SIGN PORTAL (new, twice, opposite directions). A rectangle that grows or
  shrinks between shots. Forward at 03 -> 04, the printed face on the sign grows
  off its board until it IS the next shot. Reverse at 13 -> 14, the world shrinks
  back down and lands as one of the trampled signs in the mud. The picture
  becomes the place; the place becomes a picture again, face down. Two uses in
  opposite directions is what made Session #1's wipe an argument rather than a
  flourish, and it is the same construction here.

  THE DIAGONAL TITLE FIX (carried). The season's title convention: the frame
  opens broken along a hard diagonal, slipped, out of sync and drained of
  colour, and all three faults resolve as the type lands. A season needs a
  signature that recurs.

  THE FLAT GRADE (carried, new meaning). Its established sense is "a place with
  nothing in it", so it runs across the four rally beats. A rally for eleven
  people is exactly that. Same grammar, new sentence. WHICH beats is shot.GRADED;
  WHAT the look is is identity.GRADED_AS, out of ../grades.py -- the grade was a
  function in this file and so was one season's only possible answer.

TRANSITIONS ARE PAID FOR OUT OF THE INCOMING BEAT'S LEAD, so a device always
plays over silence and never covers a word -- see TRANSITION_LEAD in edit.py.
The outgoing beat supplies live frames for the duration (not a freeze), which is
why plan() extracts beat + transition seconds for a source beat: the clip has
that margin already and a frozen under-layer reads as a hitch.
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402
import upscale                                                     # noqa: E402  the clip, upscaled once


import json
import math
import os
import re
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import cards                # the title/end card library, at the season root
import devices              # the transition library, at the season root
import framing              # how a plate of one shape enters a frame of another
import grades               # the look library
import mixes                # the audio bus library
import edit
import identity
import make_video
import script
import shot

HERE = os.path.dirname(os.path.abspath(__file__))
FF = season_paths.FFMPEG
WORK = os.path.join(HERE, "_work")
BAKED = os.path.join(HERE, "_baked")
OUT = os.path.join(HERE, "out")
VO = os.path.join(HERE, "_vo")
MUSIC = os.path.join(HERE, "_music")

# THE SEASON'S RATE, DERIVED. `24` was typed in eleven files beside a
# season_identity.FPS that already said so -- and feature.py asserts every
# part matches, so a season at another rate would have been caught only
# after every part was baked.
FPS = float(identity.season.FPS)

# THE BAKE CANVAS. DERIVED FROM THE SEASON, NOT FROM ANY ONE CLIP. It was
# `960, 1080` once -- 4:3's answer written down in the one place that would
# silently letterbox a season that is not 4:3 -- and it was also, for a
# while, computed by calling a since-removed `dims()` helper on the FIRST
# beat's plate and using THAT as the canvas for the whole film. That worked
# exactly as long as every beat's plate shared the delivery aspect, which
# local H3's per-beat VRAM-driven canvas shrinking does not guarantee: one
# real film's plates ranged from 2.400:1 to 2.545:1 against a declared
# 2.392:1, and whichever beat happened to be first in story order silently
# set the size of every frame in the film -- 1444px wide against a declared
# 1440, not even a multiple of 16. See main()'s own note beside where the
# canvas gets fixed.
#
# EVERY GEOMETRY CONSTANT IN THIS FILE IS A FRACTION OF W OR H, so the
# title cards, the box device and the caption type all scale in both
# directions from this pair alone; nothing else here is tuned to a number.
# framing.apply()'s crop resizes UP as readily as down, so a plate smaller
# than this canvas is not a problem the canvas has to solve.
W_MIN, H_MIN = identity.season.W, identity.season.H
CRF = 18

FONT = season_paths.font(identity.season.FONT_DISPLAY)
CREAM, INK = (247, 240, 224), (24, 20, 18)
FLOOR = 15

# THE GRADED RUN IS DERIVED FROM THE SESSION, NOT TYPED HERE. This was Session
# #2's rally -- {"07","08","09","10"} -- in every tree, so it drained a quarter
# of Session #6 to nothing before anyone noticed. shot.GRADED is the one place
# the decision is made, and this session declares it EMPTY: an empty street at
# 4am already IS "a place with nothing in it", so spending the grade here would
# have said the same thing twice.
FLAT_BEATS = set(shot.GRADED)

# WHICH beats is above; WHAT the look is comes from identity, out of the
# library at ../grades.py. `flatten()` used to be a function in this file, and
# the whole of a season's look lived in its six lines -- so a film that wanted
# to go cold rather than warm edited the assembler that every other film in
# every other season shares. Same shape as the transition ladder, same fix.
GRADE, GRADE_OPTS = identity.GRADE, identity.GRADE_OPTS
GRADED_AS, GRADED_OPTS = identity.GRADED_AS, identity.GRADED_OPTS
grades.load_extra(HERE)

# HOW A PLATE ENTERS THE FRAME. Was a centre crop with the 2 written into the
# expression; is now a named fit with a named anchor, overridable per beat in
# shot.FIT_BEATS because a crop is normally wrong on one beat and not on a film.
FIT, FIT_OPTS = identity.FIT, identity.FIT_OPTS
FIT_BEATS = getattr(shot, "FIT_BEATS", {})
framing.load_extra(HERE)

# WHAT SITS UNDER WHAT. mix() built one graph; the arrangement is now named.
MIX, MIX_OPTS = identity.MIX, identity.MIX_OPTS
mixes.load_extra(HERE)

# THE MIX GRAPH NO LONGER NORMALISES. See normalize() below for why, and keep
# this a constant rather than welding a filter into the f-string: it is what
# made the single-pass behaviour measurable in the first place (render the same
# graph with `anull`, difference the two short-term tracks).
LOUDNORM = "anull"

# TWO-PASS LOUDNESS, BECAUSE ONE PASS OPENS EVERY PART TOO QUIET.
#
# ffmpeg's `loudnorm` in single-pass form is an ADAPTIVE normaliser with no
# lookahead over the file: it starts from a guess and converges. Measured on
# this film by rendering the same graph with the filter replaced by `anull` and
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
# Its effect on DYNAMICS turned out to be nearly nil -- short-term range 6.3 LU
# against 6.6 un-normalised -- so the convergence was the whole problem, and
# nothing here is trying to fix pumping that was not happening.
#
# Two passes: measure, then apply the measured values with `linear=true`, which
# is one static gain over the whole file. Nothing converges and the target is hit
# to about 0.1 LU. `linear` is not always granted -- if the move needed would
# clip, loudnorm silently falls back to dynamic -- so pass two is asked what it
# did and says so out loud.
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


#     AND `linear=true` IS NOT GRANTED HERE -- THE GUARD CAUGHT IT.
#
# Asking loudnorm for a static move was refused and it fell back to dynamic
# silently, reproducing the ramp exactly (-2.11 dB over the first two seconds
# against -2.12 before). The reason is in its own analysis: this mix measures
# -19.90 LUFS with a true peak of -3.69 dBTP, so the +3.90 dB needed to reach
# -16 would land the peak at +0.21 dBTP. loudnorm will not do that, and it does
# not tell you it declined unless asked.
#
# So the gain and the ceiling are separated and done explicitly: ONE static gain
# for the whole file, then a limiter that only touches what pokes through.
# Measured on this film, +3.90 dB puts 0.29% of samples over -1.5 dBFS -- a
# limiter working on three samples in a thousand, which is what a mastering
# chain does anyway.
#
# THIS IS NOT "ADDING LIMITING". Dynamic-mode loudnorm has a limiter inside it
# and was already using it; all that changes is that the gain in front of it
# stops converging. Same amount of peak control, no fade-up at every join.
CEIL_DBFS = identity.season.CEIL_DBFS   # sample-peak ceiling; leaves
                                        # room for intersample. As above.
RATE = identity.season.A_RATE           # ONE delivery rate, season-wide


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
# `atrim=0:{total_s:.3f}` in the graph above truncates the length to three
# decimals. On a film of 2918 frames the picture is 121.583333s and the mix came
# out 121.583000s -- SIXTEEN SAMPLES short. `-shortest` on the final mux then
# refuses to emit a video frame it cannot cover, so the file shipped with 2917
# frames of picture against a full-length soundtrack: video 41ms SHORTER than
# audio, in every part whose frame count does not divide evenly into 24.
#
# One part like that is a dropped frame nobody sees. Thirteen of them
# concatenated is a drift that ACCUMULATES, and measured in the delivered
# feature it did: +70ms into film 1, +160ms into film 2, +232ms into film 3 and
# still climbing. That is the whole "the VO is off" report, and no per-film
# check could see it because inside any one film the audio is exactly right.
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

# THE CUE TABLE LIVES IN edit.py. `CROSSOVER_SID = "11"` used to be declared
# here AND in make_music.py, free to disagree -- see edit.CUES.
TRANSITIONS = edit.TRANSITIONS      # the table lives with the timeline

# THE DEVICES ARE A LIBRARY, NOT A LADDER. `../devices.py` holds them and
# `edit.TRANSITIONS` asks for one by name with its own settings. This file used
# to carry a four-branch `if kind ==` chain plus the masks and constants each
# branch needed, which meant adding a device was editing the assembler --
# shared machinery, in every season that ever clones this template, in order to
# say that your film wipes diagonally.
#
# A FILM WITH A DEVICE NOBODY ELSE WANTS drops a `devices_extra.py` in its own
# folder and registers it there. Loaded here, once, before anything asks.
devices.load_extra(HERE)

# THE CARD IS PICKED BY NAME TOO, AND `plain` IS THE DEFAULT. See ../cards.py.
# The season names its choice in identity.py, so the look travels with the
# film's identity rather than living in shared machinery.
#
# EVERY GEOMETRY NUMBER THE CARD NEEDS IS THE CARD'S. What used to be here --
# the diagonal's slope, the slip, the skew, and three separate line positions
# seventy lines from the fit that had to agree with them -- is one layout()
# declaration in cards.py that the drawing, the fit and the on-frame check all
# read.
TITLE_CARD = identity.TITLE_CARD
TITLE_OPTS = identity.TITLE_CARD_OPTS
END_STYLE = identity.END_CARD_STYLE
# THE END CARD TAKES SETTINGS TOO. The title card had TITLE_CARD_OPTS from the
# day cards.py existed; the end card had none, so a film that needed its last
# line moved off the one thing in the last frame (a reel ending on a single
# lit LED, with the card landing exactly on it) had no way to say so.
# getattr so an identity.py written before this line still runs.
END_OPTS = getattr(identity, "END_CARD_OPTS", {}) or {}
TITLE_FIX = cards.settings(TITLE_CARD, TITLE_OPTS)["fix"]
TITLE_OUT = cards.settings(TITLE_CARD, TITLE_OPTS)["out"]
TITLE_SECS = cards.seconds(TITLE_CARD, TITLE_OPTS)

# THE CARD IS DERIVED, NOT TYPED. Four sessions once carried a title card
# reading one film's title over another film,
# because this line held a string instead of a lookup.
# THE CARD'S LINES, AND HOW MANY THERE ARE, ARE BOTH DERIVED.
#
# This read `f"SESSION #{shot.SESSION_NO}"`. See season_identity.PART_LABEL for
# why that was wrong: "session" was one season's word for a film, hard-coded in
# the assembler every season shares.
#
# AN EMPTY LABEL DROPS THE LINE RATHER THAN DRAWING A BLANK ONE. The number of
# lines feeds cards.layout(), so a one-line card is laid out as a one-line card
# -- centred on the card's own cy instead of sitting where the top half of a
# two-line stack would have been.
TITLE_LINES = [t for t in (identity.label(), shot.TITLE) if t]
assert TITLE_LINES, "the title card has no lines -- shot.TITLE is empty"
END_CARD = identity.season.END_CARD    # one refrain for the whole season

# THE FIT LIMIT IS DERIVED FROM THE ANCHOR, NOT TYPED NEXT TO IT -- and both
# now live in cards.py, because the anchor does.
#
# fit() takes a width CAP, and a cap only binds on a string long enough to
# reach it. Short titles never do, so for two sessions the fact that the caps
# did not agree with the anchor positions seventy lines away was invisible --
# until one long title hit its 0.90w cap exactly and rendered a block 0.90w
# wide centred at 0.60w. That spans 0.15w to 1.05w: the last letter was off the
# frame, and the register slip pushed it further off, on the very first thing
# anybody sees.
#
# `cards.layout()` is now the one declaration, and `cards.limit()` and
# `cards.span()` both read it. Three sets of numbers that had to agree became
# one that everything derives from.
TYPE_MARGIN = 0.03                   # frame edge kept clear, as a fraction of w


# --------------------------------------------------------------------------
# layers


def graded(im: Image.Image) -> Image.Image:
    """The film's own look. `none` by default, and then this costs nothing."""
    return grades.apply(GRADE, im, GRADE_OPTS)


def flatten(im: Image.Image) -> Image.Image:
    """The look a shot.GRADED beat gets INSTEAD of the film's.

    THE NAME IS KEPT because it is half of a contract: cards.py reads
    `ctx["flatten"]` when a card's picture treatment wants to resolve out of
    the objective layer as the type lands, and the sheet in that file stubs it
    the same way. What it DOES is now identity.GRADED_AS, out of ../grades.py.

    Its old body -- saturation to about half, a lifted black, a five per cent
    warm wash -- is `flat` in the library, tuned exactly as it was, with every
    number that used to be a literal here now a setting there.
    """
    return grades.apply(GRADED_AS, im, GRADED_OPTS)


def fit(lines, start, limit, stroke):
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    for size in range(start, FLOOR - 1, -1):
        f = ImageFont.truetype(FONT, size)
        if all(probe.textbbox((0, 0), ln, font=f, stroke_width=stroke)[2]
               - probe.textbbox((0, 0), ln, font=f, stroke_width=stroke)[0] <= limit
               for ln in lines):
            return f
    raise SystemExit(f"FAIL: {lines!r} will not fit above the {FLOOR}px floor.")


def draw_text(im, text, font, cx, cy, stroke, anchor="mm", alpha=1.0):
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = d.textbbox((0, 0), text, font=font, stroke_width=stroke)
    # THREE ANCHORS, NOT TWO. This read:
    #
    #     x = cx - (x1-x0)//2 - x0 if anchor[0] == "m" else cx - (x1-x0) - x0
    #
    # -- centre, or else RIGHT. There was no left branch, so a LEFT-anchored
    # card ("lm", which is what cards._lower_third returns) was drawn
    # right-aligned on its own cx: the block ENDED 8% into the frame and ran
    # off the left edge. On a 1440px delivery that put all but the last glyph
    # of "UNEXPECTED ITEM" outside the picture.
    #
    # WHAT MAKES THIS THE HOUSE FAULT RATHER THAN A TYPO: cards.limit() and
    # cards.span() get the same anchor and read it CORRECTLY, three branches,
    # left included. So the fitter sized the type to the space a left-anchored
    # block would have, and assemble.py printed
    #
    #     TITLE_1  0.080..0.395  (margins 0.080 / 0.605)
    #
    # -- a report of comfortably on-frame type, computed from the anchor
    # convention, over a bake in which the words were off the screen. The
    # check measured the intent and the renderer did something else. Nothing
    # failed, nothing was clipped by an assert, and the film played.
    #
    # Only left-anchored cards were affected, which is why it survived: the
    # reference season used `plain` (mm) and `corner` (rm), and "r" happened
    # to land in the else branch that was already right-aligned.
    if anchor[0] == "m":
        x = cx - (x1 - x0) // 2 - x0
    elif anchor[0] == "r":
        x = cx - (x1 - x0) - x0
    else:
        x = cx - x0
    y = cy - (y1 - y0) // 2 - y0
    if alpha >= 0.999:
        d.text((x, y), text, font=font, fill=CREAM,
               stroke_width=stroke, stroke_fill=INK)
        return im
    layer = Image.new("RGB", im.size, (0, 0, 0))
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(layer).text((x, y), text, font=font, fill=CREAM,
                               stroke_width=stroke, stroke_fill=INK)
    ImageDraw.Draw(mask).text((x, y), text, font=font, fill=int(255 * alpha),
                              stroke_width=stroke, stroke_fill=int(255 * alpha))
    return Image.composite(layer, im, mask)


# --------------------------------------------------------------------------
# plan


def explode(path, ss, dur, dest, tag):
    # A SLICE CHILD READS; IT DOES NOT EXTRACT. Sixteen processes each wiping
    # and re-filling this directory delete each other's source frames mid-read.
    # The parent has already done this work by the time any child starts.
    if SLICE is not None:
        got = sorted(f for f in os.listdir(dest) if f.endswith(".png"))
        if not got:
            sys.exit(f"FAIL: {tag}: no frames in {dest} for a slice child to "
                     f"read -- the parent never extracted them")
        return [os.path.join(dest, f) for f in got]
    shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(dest)
    cmd = [season_paths.ff("ffmpeg"), "-v", "error"]
    if ss is not None:
        cmd += ["-ss", str(ss)]
    if dur is not None:
        cmd += ["-t", str(dur)]
    path = upscale.clip(path)        # the cached RealESRGAN twin, or the clip itself
    cmd += ["-i", path, os.path.join(dest, "f_%05d.png")]
    subprocess.run(cmd, check=True)
    got = sorted(f for f in os.listdir(dest) if f.endswith(".png"))
    if not got:
        sys.exit(f"FAIL: {tag} yielded no frames -- in-point past the clip end?")
    return [os.path.join(dest, f) for f in got]


def plan():
    if SLICE is None:
        shutil.rmtree(WORK, ignore_errors=True)
    rows = edit.table()
    # SLICED, NOT UNPACKED. A row may carry a fifth element -- that device's
    # own settings -- and `for f, t, k, s in TRANSITIONS` is a ValueError the
    # moment one does.
    src_of = {r[0]: (r[1], r[2], r[3]) for r in TRANSITIONS}
    dst_of = {r[1]: (r[0], r[2], r[3]) for r in TRANSITIONS}

    frames, tails, starts = [], {}, {}
    for r in rows:
        sid, want = r["sid"], round(r["beat"] * FPS)
        extra = r["trans"]
        got = explode(make_video.clip(sid), r["ss"], r["beat"] + extra,
                      os.path.join(WORK, sid), f"beat {sid}")
        # A RUN-UP MAKES THIS EXACT RATHER THAN APPROXIMATE, and it has to.
        # h3_shoot.py SKIPS a beat that already has a clip, so adding a run-up
        # to a beat that was already shot moves the in-point later into a clip
        # nobody lengthened -- and 0.9 is loose enough to ship a beat most of a
        # second short without a word. The clip is only short because it
        # predates the run-up, so the message says to re-shoot it.
        if r["runup"] and len(got) < want:
            sys.exit(f"FAIL: beat {sid} has a {r['runup']:.2f}s run-up and its "
                     f"clip yielded {len(got)} frames against the {want} the "
                     f"beat needs.\n  The clip on disk was shot before the "
                     f"run-up existed and h3_shoot.py skipped it:\n"
                     f"    python h3_shoot.py --rej=runup {sid}")
        if len(got) < want * 0.9:
            sys.exit(f"FAIL: beat {sid} yielded {len(got)} frames, wanted "
                     f"~{want} -- in-point {r['ss']}s + {r['beat']:.2f}s runs "
                     "past the clip end")
        body, tail = got[:want], got[want:]
        tails[sid] = tail
        starts[sid] = len(frames)
        last = max(1, len(body) - 1)
        for j, p in enumerate(body):
            frames.append({"src": p, "sid": sid, "flat": sid in FLAT_BEATS,
                           "fix": None, "trans": None, "card": None,
                           "mid": None})
        print(f"  [{sid}] {len(body):4d} frames ({r['beat']:5.2f}s)"
              + (f"  +{len(tail)} tail for transition" if tail else ""))

    # THE CARD'S PICTURE TREATMENT, on whichever beat opens the film. Zero
    # frames for a card that has none, which is most of them.
    o0 = shot.ORDER[0]
    n_fix = round(TITLE_FIX * FPS)
    b0, blen0 = starts[o0], sum(1 for f in frames if f["sid"] == o0)
    for j in range(min(n_fix, blen0)):
        frames[b0 + j]["fix"] = (j / max(1, n_fix - 1), b0, blen0, j)

    # THE TRANSITIONS, laid over the head of the incoming beat.
    for row in TRANSITIONS:
        # A FIFTH ELEMENT IS THAT TRANSITION'S OWN SETTINGS and is optional --
        # ("03", "04", "wipe", 0.7, {"angle": 20.0}). Device parameters are
        # editorial (the rect a portal starts in is read off a plate), so they
        # live with the timeline rather than in the assembler.
        from_sid, to_sid, kind, secs = row[:4]
        opt = row[4] if len(row) > 4 else {}
        n = round(secs * FPS)
        under = tails[from_sid]
        if len(under) < n:
            sys.exit(f"FAIL: beat {from_sid} has {len(under)} tail frames for a "
                     f"{secs}s transition needing {n} -- raise CLIP_MARGIN")
        base = starts[to_sid]
        for j in range(n):
            # THE OUTGOING BEAT'S ID, NOT A BOOLEAN ABOUT IT. This used to
            # carry `from_sid in FLAT_BEATS`, which was everything the bake
            # needed to know about the beat under a transition until the crop
            # became per-beat too. One id answers both questions and cannot
            # answer them about different beats.
            frames[base + j]["trans"] = (kind, j / max(1, n - 1), under[j],
                                         from_sid, opt)

    total = len(frames)
    title_n = round(TITLE_SECS * FPS)
    for i in range(min(title_n, total)):
        frames[i]["card"] = ("title", min(1.0, i / (0.35 * FPS),
                                          (title_n - i) / (TITLE_OUT * FPS)))
    end_n = round(3.2 * FPS)
    for i in range(max(0, total - end_n), total):
        k = i - (total - end_n)
        frames[i]["card"] = ("end", min(1.0, k / (0.7 * FPS)))

    # MID-FILM CARDS -- shot.MID_CARDS, each anchored to ITS OWN BEAT'S frame
    # range rather than to the start or end of the whole film, which is what
    # TITLE_CARD/END_CARD_STYLE anchor to. Clamped to `min(mid_n, mblen)` so a
    # card cannot bleed into the beat before or after it -- the title card's
    # own fix-window is clamped the same way, against blen0. Same alpha shape
    # as the title card (a short fixed fade-in, a hold, a fade-out sized by
    # the card's own `out` setting), so an announcement mid-film reads like
    # the same vocabulary as the one at the start rather than a new one.
    for mid_sid, mid_entry in shot.MID_CARDS.items():
        mid_style = mid_entry[0]
        mid_opt = (mid_entry[2] if len(mid_entry) > 2 else {}) or {}
        mid_out = cards.settings(mid_style, mid_opt)["out"]
        mid_n = round(cards.seconds(mid_style, mid_opt) * FPS)
        mb0 = starts[mid_sid]
        mblen = sum(1 for f in frames if f["sid"] == mid_sid)
        n = min(mid_n, mblen)
        for j in range(n):
            # THE FRAME INDEX RIDES ALONG so the render can hand the card's
            # treat() its progress within the fix phase (fault 84).
            frames[mb0 + j]["mid"] = (mid_sid, min(
                1.0, j / (0.35 * FPS), (n - j) / max(1e-6, mid_out * FPS)), j)

    print(f"  total {total} frames ({total/FPS:.2f}s at {FPS:g}fps)")
    return frames, rows


# --------------------------------------------------------------------------
# bake


# THE SEASON'S OWN RENDER CANVASES, so a frame that came off the video model
# can be told from a plate and from a bake frame by its exact size. See
# framing.unsqueeze() and season_paths.canvases().
CANVASES = season_paths.canvases(identity.season.W, identity.season.H)


def fit_aspect(im, w, h, sid: str | None = None):
    """A plate into the frame, the film's way, and this beat's way if it has one.

    THE CROP USED TO BE THE ONLY ANSWER and it was written `(sw - cw) // 2` --
    a centre crop with the 2 inside the expression, in the file every season
    shares. See ../framing.py. `sid` is optional so the QC tools and the
    devices' `ctx["fit"]`, which are fitting a picture rather than placing a
    beat, can call this without inventing one.

    THE UN-SQUEEZE COMES FIRST AND IT IS NOT OPTIONAL. A video model handed a
    plate at a canvas whose ratio is not the delivery's SQUASHES it -- measured
    8 of 8 against both crops -- and every frame comes back compressed by that
    difference. A crop cannot undo it: it trims the edges and keeps the
    distortion, which is how a 2.40 season shipped 2.56% squeezed with every
    check green. See season_paths.canvases() for the five seasons that did not
    notice.

    IT IS HERE BECAUSE THIS IS THE CHOKE POINT. Every path that puts a picture
    in a frame -- the beat, the flat layer, a device's `ctx["fit"]`, the QC
    tools -- comes through this one function, and `docs/02_traps.md` is explicit
    that one choke point beats per-site checks: a `unsqueeze()` call at each
    site is only as good as whoever added the last one.
    """
    opt = FIT_OPTS
    if sid is not None and sid in FIT_BEATS:
        opt = dict(FIT_OPTS, **FIT_BEATS[sid])
    return framing.apply(FIT, framing.unsqueeze(im, w, h, CANVASES), w, h, opt)


# THE MASKS AND THE PANEL PASTE MOVED TO ../devices.py, which is where the
# devices that use them are. What was here -- a diagonal mask, a travelling
# soft edge built out of a resized one-pixel row, nine staggered bands, a rect
# lerp and a bordered paste -- was six helpers serving four hard-coded
# branches. They are the library's now, and the library generalised two of them
# on the way: the travelling edge takes an ANGLE (the row trick only ever
# worked left to right) and the bands take a count and a direction.


# A SOFT CLIP GETS ITS LINEWORK BACK, AND NOTHING ELSE.
#
# Ported from Session #1, where the same problem arrived from the other
# direction: one beat still coming from a smaller source than its neighbours,
# blown up further to reach the same bake. Here it is beat 12, generated on
# InfiniteTalk at the 480p model's 768x576 so that the character can say the line --
# against 896 and 1024 for every other beat and a 1440 bake.
#
# The threshold is a LINE BETWEEN THE STOCKS IN THIS FILM and has to be put
# there on purpose: 768 is 0.53 of the bake, 896 is 0.62, 1024 is 0.71. At 0.85
# -- the first value tried in Session #1 -- it sits above all three and quietly
# unsharps the entire film. Hence 0.60, and hence the check below, which runs
# before a single frame is written rather than reporting after the bake.
#
# Only the unsharp is ported. Session #1's version also carried a half-strength
# grade and moving grain, and the grain was the part that did not work: it read
# as one clip going wrong rather than as a change of stock.
SOFT_UNDER = 0.60         # source width below this fraction of bake width
SOFT_SHARP = 55           # unsharp percent, radius 1.8, threshold 4


def sharpened(im: Image.Image) -> Image.Image:
    return im.filter(ImageFilter.UnsharpMask(radius=1.8, percent=SOFT_SHARP,
                                             threshold=4))


# THE BAKE RUNS ON EVERY CORE, BY SLICING ITSELF. See patch_parbake.py for why
# it is done this way round; the short version is that the loop below reads
# neighbouring frames and draws with font objects, neither of which survives the
# pickle that a worker pool on Windows would need.
#
# `--bake-slice=k/N` is the child form and is not meant to be typed by hand.
# `--jobs=N` caps the fan-out; --jobs=1 restores the old serial behaviour, which
# is what to use when a bake is misbehaving and the output needs to be read.
JOBS = max(1, min(16, (os.cpu_count() or 4) - 2))
SLICE: tuple[int, int] | None = None
for _a in sys.argv[1:]:
    if _a.startswith("--bake-slice="):
        _k, _n = _a.split("=", 1)[1].split("/")
        SLICE = (int(_k), int(_n))
    elif _a.startswith("--jobs="):
        JOBS = max(1, int(_a.split("=", 1)[1]))


def fan_out(n_frames: int) -> int:
    """Run this script once per core over disjoint frames, then count them."""
    args = [a for a in sys.argv[1:] if not a.startswith("--jobs=")]
    kids = [subprocess.Popen(
        [sys.executable, os.path.abspath(__file__),
         f"--bake-slice={k}/{JOBS}", *args],
        stdout=subprocess.DEVNULL) for k in range(JOBS)]
    dead = [k for k, p in enumerate(kids) if p.wait() != 0]
    if dead:
        sys.exit(f"FAIL: bake slice(s) {dead} of {JOBS} exited nonzero -- the "
                 f"film would have holes in it. Re-run with --jobs=1 to see "
                 f"the error.")
    # NOT `>= n_frames`. A stale PNG left over from a longer edit would pass
    # that, and the encode would silently make a film of the wrong length.
    got = len([f for f in os.listdir(BAKED) if f.endswith(".png")])
    if got != n_frames:
        sys.exit(f"FAIL: {got} frames on disk against {n_frames} planned")
    print(f"  baked {got} frames across {JOBS} processes")
    return n_frames


def bake(frames, w, h):
    # The children must not wipe the directory their siblings are filling.
    if SLICE is None:
        shutil.rmtree(BAKED, ignore_errors=True)
        os.makedirs(BAKED)
    # THE OUTLINE IS A PROPERTY OF THE FACE, so it is declared beside the
    # face in season_identity.py rather than fixed here: a weight sized for
    # a heavy display face buries a light one. See the note there.
    stroke = max(1, round(h * identity.season.FONT_STROKE))

    width_of = {}
    for rec in frames:
        width_of.setdefault(rec["sid"], Image.open(rec["src"]).width)
    soft_sids = {s for s, sw in width_of.items() if sw < w * SOFT_UNDER}
    print("  source widths: "
          + ", ".join(f"{s}:{sw}" for s, sw in sorted(width_of.items())))
    print(f"  sharpening beat(s) {', '.join(sorted(soft_sids)) or 'none'} "
          f"-- under {round(w * SOFT_UNDER)}px of {w}")
    if len(soft_sids) == len(width_of):
        sys.exit("FAIL: every beat reads as soft. SOFT_UNDER is a line BETWEEN "
                 "the stocks in the film, not a global grade -- set it against "
                 "the widths above.")

    # THE TYPE IS SIZED TO THE SPACE ITS OWN ANCHOR LEAVES, and the anchor is
    # the card's. cards.limit() charges each line for the card's slip as well,
    # because a treatment's displacement is worst on frame one -- which is
    # exactly where the clipping showed.
    ctx = {"w": w, "h": h, "text": draw_text, "stroke": stroke,
           "cream": CREAM, "ink": INK, "fit": fit_aspect, "flatten": flatten,
           "neighbour": None, "fonts": []}

    def cap(entry) -> float:
        cx, _cy, anchor, slip = entry
        return w * cards.limit(cx, anchor, slip, TYPE_MARGIN)

    # THE EYEBROW IS THE SMALL ONE AND THE TITLE IS THE BIG ONE -- unless the
    # eyebrow is not there, in which case the title is the only one and keeps
    # its own size. Sizes are per LINE COUNT, not per index, so a one-line card
    # does not silently render its title at the eyebrow's height.
    px = (0.070, 0.105) if len(TITLE_LINES) == 2 else (0.105,)
    lay = cards.layout(TITLE_CARD, len(TITLE_LINES), TITLE_OPTS)
    elay = cards.layout(END_STYLE, 1, END_OPTS)
    tfonts = [fit([t], round(h * p), cap(e), stroke)
              for t, p, e in zip(TITLE_LINES, px, lay)]
    tend = fit([END_CARD], round(h * 0.062), cap(elay[0]), stroke)
    ctx["fonts"] = tfonts

    # MID-FILM CARDS -- fitted the same way as END_CARD (one modest size,
    # each line independently capped by its own anchor), keyed by beat so the
    # render loop can hand cards.draw() the right layout/fonts for whichever
    # beat it is currently on.
    # A MID CARD IS (style, lines) OR (style, lines, opts). The third is the
    # card's own settings, as TITLE_CARD_OPTS is for the title: a card that
    # shares the lower third with burned-in captions on a vertical delivery
    # has to be able to move, and could not.
    mid_cards = {sid: (e[0], e[1], (e[2] if len(e) > 2 else {}) or {})
                 for sid, e in shot.MID_CARDS.items()}
    mid_lay = {sid: cards.layout(style, len(lines), opt)
              for sid, (style, lines, opt) in mid_cards.items()}
    mid_fonts = {sid: [fit([ln], round(h * 0.05), cap(e), stroke)
                       for ln, e in zip(lines, mid_lay[sid])]
                for sid, (style, lines, _opt) in mid_cards.items()}

    print(f"  card: {TITLE_CARD} ({TITLE_SECS:.1f}s), end {END_STYLE}; "
          f"type {'/'.join(str(f.size) for f in tfonts)}px title, "
          f"{tend.size}px end"
          + (f"; mid {', '.join(f'{s}:{f[0].size}px' if f else f'{s}:treat-only' for s, f in mid_fonts.items())}"
             if mid_fonts else ""))   # a card with no lines has no type to report

    # AND THEN MEASURE WHAT WAS ACTUALLY DRAWN. cards.limit() constrains the
    # fit, but the fit and the draw are still two separate statements, and this
    # is precisely the seam the last bug came through. Refusing to bake beats
    # discovering it in the finished film.
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    checks = [(f"TITLE_{i + 1}", t, f, e) for i, (t, f, e)
              in enumerate(zip(TITLE_LINES, tfonts, lay))]
    checks.append(("END_CARD", END_CARD, tend, elay[0]))
    for sid, (_style, lines, _opt) in mid_cards.items():
        checks += [(f"MID_{sid}_{i + 1}", ln, f, e) for i, (ln, f, e)
                  in enumerate(zip(lines, mid_fonts[sid], mid_lay[sid]))]
    for label, txt, f, (cx, _cy, anch, sl) in checks:
        bb = probe.textbbox((0, 0), txt, font=f, stroke_width=stroke)
        lo, hi = cards.span(cx, anch, sl, (bb[2] - bb[0]) / w)
        if lo < 0.0 or hi > 1.0:
            sys.exit(f"FAIL: {label} spans {lo:+.3f}..{hi:+.3f} of the frame "
                     f"-- it runs off the edge. Move its centre in the card's "
                     f"settings, or lower its start size.")
        print(f"    {label:8s} {lo:.3f}..{hi:.3f}  "
              f"(margins {lo:.3f} / {1 - hi:.3f})")

    soft = 0
    if SLICE is None and JOBS > 1:
        return fan_out(len(frames))

    for i, rec in enumerate(frames):
        if SLICE is not None and i % SLICE[1] != SLICE[0]:
            continue
        im = fit_aspect(Image.open(rec["src"]).convert("RGB"), w, h, rec["sid"])
        # Before the type, the cards and the devices, so those are drawn at bake
        # resolution onto a finished picture rather than sharpened with it.
        if rec["sid"] in soft_sids:
            im = sharpened(im)
            soft += 1
        # NO DISPLACEMENT UNLESS A CARD ASKS FOR ONE. It was `None`, which
        # every card with a picture treatment overwrote and every card
        # without left for cards.draw() to unpack.
        slip = (0.0, 0.0)

        # ONE GRADE PER FRAME, EVER. A shot.GRADED beat gets GRADED_AS INSTEAD
        # of the film's look, not on top of it -- `bleach` under `flat` gives
        # you neither, and a film where that happened would be very hard to
        # read back to a cause. `graded()` is free when GRADE is "none", which
        # is the default, so the else costs nothing on a film with no look.
        im = flatten(im) if rec["flat"] else graded(im)

        if rec["fix"] is not None:
            # THE CARD'S OWN PICTURE TREATMENT, over the head of the opening
            # beat. Most cards have none and this is a no-op returning (0, 0).
            prog, bstart, blen, j = rec["fix"]

            def neighbour(dj, _b=bstart, _l=blen, _j=j):
                """The opening beat's frame `dj` away, fitted. Clamped: a card
                that reads ahead must not read past the beat it is over."""
                k = max(0, min(_l - 1, _j + dj))
                return fit_aspect(
                    Image.open(frames[_b + k]["src"]).convert("RGB"), w, h,
                    frames[_b + k]["sid"])

            ctx["neighbour"] = neighbour
            im, slip = cards.treat(TITLE_CARD, im, prog, ctx, TITLE_OPTS)

        if rec["trans"] is not None:
            kind, t, under_path, under_sid, opt = rec["trans"]
            # THE OUTGOING BEAT IS FITTED AND GRADED AS ITSELF, not as the beat
            # it is going into. `under` is read straight off disk and so never
            # passed through the `rec["flat"]` test that grades a beat's own
            # frames. On Session #5 that made the outgoing beat pop from flat
            # to full saturation across the WHOLE FRAME the instant a
            # transition began -- the colour came back before the device did.
            # The crop has exactly the same failure now that it is per beat.
            under = fit_aspect(Image.open(under_path).convert("RGB"), w, h,
                               under_sid)
            under = (flatten(under) if under_sid in FLAT_BEATS
                     else graded(under))
            # SMOOTHSTEP, HERE, ONCE. Every device gets an eased `e` rather than
            # each one easing for itself -- which is what makes two devices in
            # one film feel like one vocabulary.
            im = devices.apply(kind, im, under, t * t * (3 - 2 * t), ctx, opt)

        if rec["card"]:
            kind, a = rec["card"]
            a = max(0.0, min(1.0, a))
            if a > 0.01:
                if kind == "title":
                    im = cards.draw(TITLE_CARD, im, TITLE_LINES, ctx,
                                    a, slip, TITLE_OPTS)
                else:
                    im = cards.draw(END_STYLE, im, [END_CARD],
                                    dict(ctx, fonts=[tend]), a,
                                    opt=END_OPTS)

        # MID-FILM CARDS. Text only -- no picture treatment, no `slip`; see
        # shot.py's note on MID_CARDS for why. A beat can carry a "card" (the
        # title, if this is beat 01) AND a "mid" entry at once only if a
        # season declares a mid-card on the same beat the title lands on,
        # which would be an odd choice but is not refused here -- both would
        # simply draw, title first.
        if rec["mid"] is not None:
            mid_sid, a, mj = rec["mid"]
            a = max(0.0, min(1.0, a))
            mid_style, mid_lines, mid_opt = mid_cards[mid_sid]
            # THE PICTURE TREATMENT RUNS FOR MID CARDS TOO. The note in
            # shot.py said "text only" and held for five seasons -- until
            # the first card that is ALL treatment and no type (a season's
            # ink stamp, fault 84). e ramps across the card's own fix
            # phase; a card with no treat is identity here and nothing
            # changes for any prior season.
            _fix = cards.settings(mid_style, mid_opt)["fix"]
            _e = 1.0 if _fix <= 0 else min(1.0, mj / max(1e-6, _fix * FPS))
            im, _ = cards.treat(mid_style, im, _e, ctx, mid_opt)
            if a > 0.01 and mid_lines:
                im = cards.draw(mid_style, im, mid_lines,
                                dict(ctx, fonts=mid_fonts[mid_sid]), a,
                                opt=mid_opt)

        im.save(os.path.join(BAKED, f"b_{i:05d}.png"))
        if i % 300 == 0:
            print(f"    baked {i}/{len(frames)}")
    print(f"  sharpened {soft}/{len(frames)} frames")
    if SLICE is not None:
        sys.exit(0)                    # a slice child stops before the mix
    return len(frames)


# --------------------------------------------------------------------------
# sound


def has_audio(path: str) -> bool:
    """Does this clip carry an audio stream? Asked before it is wired in.

    An `-i` with no audio stream makes `[n:a]` an ffmpeg error at the end of
    the bake, which is the place this file has learned not to find things
    out. A paid vendor's clip has none; H3's has one; the upscaled twin of
    either has none. So the assembler asks, and a beat without sound simply
    places nothing -- a silent beat on the diegetic bus, and nothing at all
    on every other.
    """
    r = subprocess.run([season_paths.ff("ffprobe"), "-v", "error",
                        "-select_streams", "a", "-show_entries",
                        "stream=codec_type", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    return "audio" in (r.stdout or "")


def vo_offsets(rows):
    out, t = [], 0.0
    for r in rows:
        cur = t + r["lead"]
        for lid in r["lines"]:
            out.append((lid, cur))
            cur += edit.vo_dur(lid) + r["extra"]
        t += r["beat"]
    return out



# HOW MUCH OF A VO TAKE'S TAIL MAY BE DESTROYED, MEASURED PER TAKE.
#
# THE TRIM USED TO BE UNCONDITIONAL AND THE PROPERTY IT ASSUMED IS NOT A
# PROPERTY OF THE VENDOR. make_vo.py stated it flatly -- "every eleven_v3 take
# has a transient glued to its final milliseconds" -- and this function's whole
# question was how much tail could be SPARED, never whether there was anything
# there to cut. A fork profiled all 34 of its takes at sample level, against the
# actual signature (peak in the final 10ms over peak in the preceding 100ms) and
# found it in ZERO of them. Trimming 25ms from every take would have thrown away
# 850ms of real speech across that film to solve a problem it did not have.
#
# The observation the rule came from was real: 12 of 20 takes on one film, tails
# sitting at 0.06-0.10 amplitude with the last 10ms spiking to 0.29. That is a
# 3-5x ratio and it is worth cutting. It is a thing SOME takes do, and the fix
# is to look rather than to assume.
#
# AND THE FAULT THAT SURVIVES ON THE OTHER TAKES NEEDS A DIFFERENT TOOL. Several
# takes end while low-level energy is still present, and a file that stops at
# 0.09 butted against digital silence CLICKS. That is a discontinuity, not a
# transient, and the fix for a discontinuity is a FADE -- which removes no
# samples at all. Trimming was solving the wrong half of it.
#
# The trailing-silence measurement below is kept and still earns its place: it
# is what stops a trim landing on speech. In Session #3 both closing takes
# measured ZERO trailing silence, and the film's last line -- 0.51s of speech in
# a 0.64s file -- lost its final 75ms and came out clipped.
#
#   transient, ends in silence   trim 25ms, fade 50ms    (the old behaviour)
#   transient, ends on a word    trim 12ms, fade 20ms    (only enough)
#   no transient                 trim  0,   fade 10ms    (the click, and nothing
#                                                         else, is the problem)
_TAIL: dict[str, tuple[float, float]] = {}
_TAIL_WHY: dict[str, str] = {}

# THE FINAL 10ms MUST BEAT THE PRECEDING 100ms BY THIS MUCH to count as a
# transient. Speech decays into its own ending, so a last window LOUDER than the
# hundred before it is anomalous by construction; 2.0 sits well under the 3-5x
# the real ones measured and well over anything ordinary word-final energy does.
_TRANSIENT_RATIO = 2.0


def vo_tail(lid: str, d: float) -> tuple[float, float]:
    """(trim, fade) seconds to apply to this take's end, measured not assumed."""
    if lid in _TAIL:
        return _TAIL[lid]
    raw = subprocess.run(
        [season_paths.ff("ffmpeg"), "-v", "error",
         "-i", os.path.join(VO, f"{lid}.mp3"),
         "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
        capture_output=True, check=True).stdout
    x = np.frombuffer(raw, "<i2").astype(np.float32) / 32768.0
    sr, win = 16000, 160                                     # 10ms windows
    out, why = (0.0, 0.010), "no transient"

    # THE SIGNATURE, ON PEAKS RATHER THAN RMS. A 10ms spike barely moves the RMS
    # of the window it is in, which is why the old silence-based test could not
    # have seen one even if it had been looking.
    tail = np.abs(x[-win:]) if len(x) >= win else np.abs(x)
    before = np.abs(x[-11 * win:-win]) if len(x) >= 11 * win else np.abs(x[:-win])
    spike = (len(tail) and len(before)
             and tail.max() > _TRANSIENT_RATIO * max(before.max(), 1e-6))

    if spike:
        out, why = (0.025, 0.050), "transient"
        k = len(x) // win
        if k:
            rms = np.sqrt((x[:k * win].reshape(k, win) ** 2).mean(axis=1) + 1e-12)
            live = np.nonzero(20 * np.log10(rms) > -45.0)[0]
            if len(live):
                silence = len(x) / sr - (live[-1] + 1) * win / sr
                if silence < 0.075:
                    # Nothing to spare: cut the transient and get out.
                    out, why = (0.012, 0.020), "transient, no pad"
    _TAIL[lid], _TAIL_WHY[lid] = out, why
    return out


def mix(rows, total_s, dest):
    """The takes and the cues placed; identity.MIX decides what sits under what.

    THIS FUNCTION PLACES; IT NO LONGER ARRANGES. Everything below is about
    where a take starts and how long a cue runs -- facts that come out of
    edit.py and cannot be anybody's stylistic choice. The bus that sums them,
    which IS a choice, is one name in identity.py out of ../mixes.py.

    SOME eleven_v3 takes have a transient glued to their last few milliseconds
    -- an audible click on a timeline, and it makes the line sound cut off.
    Measured per take in vo_tail() and trimmed only where it is actually there;
    everything else gets a 10ms fade, which removes no samples. The raw takes
    stay archived untouched either way.
    """
    offs = vo_offsets(rows)
    cues = edit.cue_spans(rows)

    ins, parts, labels, spans = [], [], [], []
    for n, (lid, off) in enumerate(offs):
        d = edit.vo_dur(lid)
        trim, fade = vo_tail(lid, d)
        ins += ["-i", os.path.join(VO, f"{lid}.mp3")]
        parts.append(
            f"[{n}:a]atrim=0:{max(0.05, d - trim):.3f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d=0.010,"
            f"afade=t=out:st={max(0.0, d - trim - fade):.3f}:d={fade:.3f},"
            f"adelay={int(off * 1000)}|{int(off * 1000)},"
            f"aformat=sample_rates=48000:channel_layouts=stereo[v{n}]")
        labels.append(f"[v{n}]")
        # WHERE THE WORDS ACTUALLY ARE, for a bus that ducks by automation
        # rather than by signal. Same numbers the placement above uses, so the
        # dip cannot drift from the take that caused it.
        spans.append((off, off + max(0.05, d - trim)))
    nvo = len(offs)

    # WHAT THE TAIL MEASUREMENT ACTUALLY DECIDED, PRINTED BEFORE THE BAKE'S
    # OUTPUT SCROLLS. docs/06_verification.md: make a check print what it
    # measured, not just its verdict. This one replaced a rule that was applied
    # to every take without looking, so the count of takes it now leaves alone
    # is the whole point -- and a run where it suddenly trims everything, or
    # nothing, is the first sign the threshold has stopped discriminating.
    if offs:
        tally: dict[str, int] = {}
        for lid, _off in offs:
            tally[_TAIL_WHY[lid]] = tally.get(_TAIL_WHY[lid], 0) + 1
        cut = sum(vo_tail(lid, 0)[0] for lid, _ in offs)
        print("  vo tails: " + ", ".join(f"{n} {why}"
                                         for why, n in sorted(tally.items()))
              + f"  ({cut * 1000:.0f} ms trimmed in total)")

    # ONE BRANCH PER CUE, FROM edit.CUES. This was two hand-written branches
    # named m0 and m1 with a single crossover between them, so a season with
    # one cue -- or four -- had to edit the mixer. Every number below is the
    # same number the two-cue version used; nothing about the sound changes,
    # it just no longer counts to two.
    #
    # EACH CUE RUNS ITS OWN SPAN PLUS THE OVERLAP, is delayed to its own start,
    # and fades out into the next. The last one gets the long 3s resolve into
    # the end of the picture; the first gets the slow 1.5s open.
    fade, out_fade = 2.0, 3.0
    mlabels = []
    for n, c in enumerate(cues):
        last = n == len(cues) - 1
        ins += ["-i", os.path.join(MUSIC, f"{c['name']}.mp3")]
        idx = nvo + n
        span = total_s - c["start"] if last else c["secs"]
        off = out_fade if last else fade
        chain = [f"[{idx}:a]"]
        if not last:
            # Trimmed to its span plus the crossover, so the file's own tail
            # never plays under the cue that replaced it.
            chain.append(f"atrim=0:{c['secs'] + fade:.3f},")
        chain.append("asetpts=PTS-STARTPTS,")
        chain.append(f"afade=t=in:st=0:d={1.5 if n == 0 else fade},")
        chain.append(f"afade=t=out:st={max(0.0, span - off):.3f}:d={off},")
        # THE SCORE'S LEVEL IS THE BUS'S, NOT THE CUE'S. It was `volume=0.55`
        # here, on every cue, which is the same number said N times: a season
        # dropping its score edited it once per cue and a season adding a cue
        # inherited whatever the last one happened to say. It is mixes.py's
        # `music` setting now. Linear gain, so 0.55*(a+b) is what it always was.
        if c["start"] > 0:
            ms = int(c["start"] * 1000)
            chain.append(f"adelay={ms}|{ms},")
        chain.append(f"aformat=sample_rates=48000:channel_layouts=stereo[m{n}]")
        parts.append("".join(chain))
        mlabels.append(f"[m{n}]")

    # AND THE ARRANGEMENT, BY NAME. What was here -- a VO sum, a music sum, a
    # padded key and a sidechain -- is `ducked` in ../mixes.py, built from the
    # same numbers. It is no longer the only thing this template can do, and
    # the two shapes it silently could not do (a film with no cues, a film with
    # no takes) are refused there by name instead of arriving as
    # `amix=inputs=0` a hundred lines into a filter graph at the end of a bake.
    # THE CLIPS' OWN SOUND, PLACED EXACTLY WHERE THEIR FRAMES WENT. One
    # input per beat, from the same clip `plan()` exploded (make_video.clip,
    # NOT the upscaled twin -- RealESRGAN writes no audio stream), trimmed
    # from the same in-point to the same length, delayed to the same start.
    # It is placed for EVERY bus and only `diegetic` sums it; the others
    # ignore ctx["clips"], which is how nine seasons of narrated films keep
    # sounding the way they did. The 5 ms fades are against the click of a
    # hard cut between two unrelated room tones; they remove no samples.
    #
    # THE START IS THE SAME RUNNING TOTAL vo_offsets() USES, so a clip's
    # sound and a take over it cannot disagree about where the beat begins.
    clabels, t = [], 0.0
    for r in rows:
        src = make_video.clip(r["sid"])
        if has_audio(src):
            idx = len(ins) // 2
            ins += ["-i", src]
            a, d = float(r["ss"] or 0.0), float(r["beat"])
            ms = int(round(t * 1000))
            parts.append(
                f"[{idx}:a]atrim={a:.3f}:{a + d:.3f},asetpts=PTS-STARTPTS,"
                f"afade=t=in:st=0:d=0.005,"
                f"afade=t=out:st={max(0.0, d - 0.005):.3f}:d=0.005,"
                f"adelay={ms}|{ms},"
                f"aformat=sample_rates=48000:channel_layouts=stereo"
                f"[c{len(clabels)}]")
            clabels.append(f"[c{len(clabels)}]")
        t += r["beat"]

    bus, out = mixes.bus(MIX, labels, mlabels,
                         {"total": total_s, "spans": spans, "clips": clabels},
                         MIX_OPTS)
    parts += bus
    parts.append(f"{out}{LOUDNORM}[final]")

    # THE GRAPH GOES IN A FILE, NOT ON THE COMMAND LINE. An 84-beat film
    # (84 clip tracks + 72 takes + 18 cues) pushed the inline filter_complex
    # past Windows' 32K CreateProcess limit and died with WinError 206 --
    # a fault no film under ~60 beats can ever hit (fault 83).
    fcs = os.path.join(WORK, "mix_graph.txt")
    with open(fcs, "w", encoding="utf-8") as fh:
        fh.write(";\n".join(parts))
    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error"] + ins +
                   ["-filter_complex_script", fcs, "-map", "[final]",
                    "-c:a", "pcm_s16le", dest], check=True)
    # Second stage on the finished bus: static gain, then the length pinned to
    # the picture in samples.
    normalize(dest, total_s)
    got = float(subprocess.run(
        [season_paths.ff("ffprobe"), "-v", "error", "-show_entries",
         "format=duration", "-of", "csv=p=0", dest],
        capture_output=True, text=True, check=True).stdout.strip())
    if abs(got - total_s) > 0.10:
        sys.exit(f"FAIL: mix is {got:.2f}s against {total_s:.2f}s of picture -- "
                 "`-shortest` will silently truncate the film. Something in the "
                 "audio graph is bounded by a stream that ends early.")
    where = ", ".join(f"{c['name']}@{c['start']:.1f}s" for c in cues)
    print(f"  audio: {MIX} bus, {nvo} takes, {len(cues)} cue(s) [{where}], "
          f"{len(clabels)} clip track(s), {got:.2f}s (picture {total_s:.2f}s)")


# --------------------------------------------------------------------------


def main() -> int:
    keep = "--keep-frames" in sys.argv
    rows = edit.table()
    if keep:
        baked = [f for f in os.listdir(BAKED) if f.endswith(".png")]
        n = len(baked)
        want = sum(round(r["beat"] * FPS) for r in rows)
        if abs(n - want) > len(rows):
            sys.exit(f"FAIL: {n} baked frames against ~{want} wanted -- the "
                     "edit changed; re-run without --keep-frames")
        # A COUNT IS NOT A RECIPE, AND THIS ONE ONLY CHECKED THE COUNT.
        # Re-render a clip, re-grade a beat, or swap a plate, and the frame
        # count does not move -- so `--keep-frames` happily re-bakes the OLD
        # picture at exactly the right length, and every check downstream
        # passes because length is all any of them measure.
        #
        # The severe version of this is not a stale clip, it is a REHEARSAL:
        # a fork validated its whole assembly chain against placeholder
        # sources before the real ones existed, and every later run reused
        # that cache and would have shipped the animatic -- right length,
        # right order, all green.
        #
        # So: if anything the bake was made FROM is newer than the frames
        # themselves, the cache is stale and says so.
        # THE SOURCE IS THE CLIP EACH BEAT EXPLODES, which is what plan()
        # reads and therefore the only honest thing to compare against. An
        # earlier draft of this check compared `r["src"]/r["clip"]/r["plate"]`
        # -- keys that either do not exist on a row or, in `clip`'s case, hold
        # an INT number of seconds. It would have found nothing, ever, and
        # reported success: the exact vacuous check this repo keeps writing
        # about. Resolve the real path or do not claim to have checked.
        newest = max((os.path.getmtime(os.path.join(BAKED, f))
                      for f in baked), default=0.0)
        srcs = []
        for r in rows:
            try:
                p = make_video.clip(r["sid"])
            except SystemExit:
                # A missing clip is not this check's business -- reusing frames
                # is legitimate after the clips have been cleared away.
                continue
            if os.path.exists(p):
                srcs.append(p)
        fresher = sorted({p for p in srcs if os.path.getmtime(p) > newest})
        if fresher:
            sys.exit(
                f"FAIL: {len(fresher)} source(s) are newer than the baked "
                f"frames --\n  " + "\n  ".join(
                    os.path.basename(p) for p in fresher[:6])
                + ("\n  ..." if len(fresher) > 6 else "")
                + f"\n  The frame COUNT still matches, which is why this is "
                f"not caught by\n  the check above and why it would have "
                f"baked the old picture at the\n  right length. Re-run "
                f"without --keep-frames.")
        w, h = Image.open(os.path.join(BAKED, "b_00000.png")).size
        print(f"  reusing {n} baked frames at {w}x{h}")
    else:
        frames, rows = plan()
        # THE CANVAS IS THE SEASON'S DECLARED SIZE, NOT WHATEVER a clip's
        # own plate happens to be. It used to be `sw, sh = Image.open(
        # frames[0]["src"]).size; w, h = dims(sw, sh)` -- fine while every
        # beat's plate shared the delivery aspect, and silently wrong the
        # moment it stopped being true. Local H3 shrinks canvas per beat
        # for VRAM, so different beats can land at different NATIVE
        # aspects, and whichever beat happened to be FIRST in story order
        # set the canvas for the ENTIRE FILM, because every other frame
        # gets fit into that SAME (w, h) afterwards. Found on a real film:
        # beat 01 was 2.400:1 against a declared 2.392:1, height-bound,
        # producing a width 4px over the declared one and not even a
        # multiple of 16. fit_aspect()'s crop already handles an arbitrary
        # source size fitting into a FIXED target; the canvas itself must
        # be that fixed target, unconditionally.
        w, h = W_MIN - W_MIN % 2, H_MIN - H_MIN % 2
        n = bake(frames, w, h)

    os.makedirs(OUT, exist_ok=True)
    total_s = n / FPS
    wav = os.path.join(WORK, "mix.wav")
    os.makedirs(WORK, exist_ok=True)
    mix(rows, total_s, wav)

    # THE FILENAME IS THE SLUG, EXACTLY. parts.py looks for <slug>.mp4, so a
    # prefix added here would make the season unable to find its own film.
    # Put any prefix you want into identity.SLUG.
    mp4 = os.path.join(OUT, f"{shot.SLUG}.mp4")
    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                    "-framerate", str(FPS),
                    "-i", os.path.join(BAKED, "b_%05d.png"), "-i", wav,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(CRF),
                    "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-movflags", "+faststart", mp4], check=True)
    print(f"\n  {total_s:.2f}s, {w}x{h} at {FPS:g}fps, {n} frames")
    print(f"  MP4 {os.path.getsize(mp4)/1e6:.2f} MB  -> {mp4}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
