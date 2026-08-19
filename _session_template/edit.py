"""The timeline for Session #2, as a table -- every other length derives from it.

Same discipline as Session #1: the only numbers typed here are editorial (a
lead, a tail, a hold), and beat length, clip length to buy, score length and
subtitle timing are all computed from those plus the measured VO takes. A fixed
length under-runs a re-cut in total silence.

TWO THINGS THIS SESSION FORCED THAT #1 DID NOT:

  THE COLD-OPEN LEAD IS SHORTER (1.3s, against 2.2s). Line 01 came back at 9.36s
  after a style re-roll, and 2.2 + 9.36 + 0.7 is 12.26s of beat against a vendor
  duration slider that stops at TWELVE. The title card still lands over the
  opening, it just starts closer to the first word. Buying the length the beat
  needs only works while the beat fits inside the vendor's ceiling.

  THE LEADS ARE GENERALLY TIGHTER. This is the comedy session and it runs
  faster; a lead that reads as composure in an elegy reads as a gap in a joke.
  Tails are NOT tightened -- cutting away 0.35s after a line cuts before the
  audience has finished hearing it, and in a film whose comedy is entirely in
  the words that throws the joke away. Tails want 0.65-0.85s and ~1.3s on a
  button.
"""
from __future__ import annotations

# THE CONTENT BELOW IS THE TEMPLATE'S EXAMPLE, NOT YOUR FILM.
# preflight.py refuses to render while this line is here. Delete it when
# you have replaced the content -- and only then.
EXAMPLE_CONTENT = True


import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import math
import os
import subprocess
import sys

# identity, BECAUSE THE COMMENTED EXAMPLE BELOW USES IT. The TRANSITIONS
# example read `identity.TRANSITION` and this file did not import it, so
# uncommenting the one line the file tells you to uncomment was a
# NameError. An example that cannot be used is not an example.
import identity
import script

HERE = os.path.dirname(os.path.abspath(__file__))
VO = os.path.join(HERE, "_vo")
FF = season_paths.FFMPEG

CLIP_MARGIN = 1.2
CLIP_MIN, CLIP_MAX = 3, 12

# THE FLOOR ON A BEAT ITSELF, WHICH IS NOT CLIP_MIN. CLIP_MIN is what a vendor
# will sell; this is what a cut can hold. They are unrelated numbers and the
# gap between them is where a fault hides: `clip` is clamped UP to CLIP_MIN, so
# without this a beat of 0.4s buys three seconds of video, spends the money,
# and lands a four-frame shot in the film. Raise it if a season genuinely cuts
# faster than this -- but raise it deliberately, having looked at a cut that
# short.
BEAT_MIN = 1.2

# THE IN-POINT IS DERIVED, NOT FIXED. assemble.py enters each clip a little way
# in so the first frames (where a vendor sometimes settles) are not used. A
# constant 0.35s works everywhere except on a beat that has been pushed up
# against the vendor's 12s ceiling, where in-point + beat then runs past the end
# of the clip and extract silently yields short. Shrinking it only where the
# beat is tight makes an overrun impossible by construction rather than by an
# assertion catching it afterwards.
SS_MAX = 0.35
SS_GUARD = 0.08              # frames left spare at the tail of every clip

# TRANSITIONS COST RUNTIME AND IT COMES OUT OF THE INCOMING BEAT'S LEAD, so the
# device plays over silence and never covers a word. These three beats are the
# receiving end of a transition and carry a widened lead to pay for it.
TRANSITION_LEAD = 1.1

# --------------------------------------------------------------------------
# THE RUN-UP: SHOOT LONGER THAN THE BEAT AND THROW THE OPENING AWAY.
#
# A VIDEO MODEL CONDITIONED ON A STILL SPENDS ITS FIRST HALF SECOND GETTING UP
# TO SPEED, and the clip is exactly as long as the beat, so that half second is
# the cut's first half second. Measured on one shot across FOUR SEEDS: the
# opening eighth of each clip ran at 0.30, 0.32, 0.33 and 0.34 of that same
# clip's own peak frame-to-frame change. The consistency across independent
# draws is the finding -- it is a property of conditioning on a still, not a
# bad roll, and neither words nor seeds move it:
#
#   * "The movement is constant" was ALREADY in the shipped prompt and did
#     nothing. It describes a property, not the first frame.
#   * Rewriting it to "already at full speed in the very first frame" moved the
#     ramp 2.36x -> 2.01x. That is all.
#   * The best of four seeds still opened at 0.33 of its own peak.
#
# ON MOST BEATS THIS IS INVISIBLE OR CORRECT -- a man starts walking, a candle
# starts guttering, a banner starts to lift. It is a fault only where the beat
# must be ALREADY AT SPEED on the frame it cuts in on: a melee, a chase,
# anything cut into mid-action. So it is opt-in per beat and empty by default,
# the same shape as PLATE_ALIAS and MID_CARDS.
#
#     RUNUP = {"07": 1.0}       # seconds of clip shot and then discarded
#
#   as shipped          first eighth 1.39  peak 8.05  0.17 of peak  2.70x ramp
#   after a 1.0s runup  first eighth 7.54  peak 8.84  0.85 of peak  0.87x ramp
#
# IT IS ONE NUMBER AND BOTH ENDS READ IT. table() adds it to the clip LENGTH
# (so h3_shoot buys it) and to the IN-POINT (so assemble skips exactly what was
# bought). Typing the two separately is the bug this whole file is built to
# refuse -- a shooter that grew the clip while the assembler entered at the old
# mark would ship the run-up AND lose the tail.
#
# WHY IT LIVES HERE AND NOT IN motion.py, where the direction lives: it is a
# claim on the clip LENGTH, which is the same argument that put TRANSITIONS in
# this file rather than in the assembler. motion.py's docstring points back at
# it, because the beat that needs one is discovered while writing direction.
RUNUP: dict[str, float] = {}

# THE TRANSITION TABLE LIVES HERE, WITH THE TIMELINE, NOT IN THE ASSEMBLER.
# It was in assemble.py first and that put the knowledge in the wrong file: a
# transition needs the OUTGOING beat to supply live frames past the end of its
# own beat, which is a claim on the clip length -- an editorial fact, not a
# compositing one. Beat 01 duly failed at extract time with 7 tail frames
# against the 19 an 0.8s wipe needs, which is a bad place to find out. With the
# table here, table() prices the overrun in and main() refuses to print a
# budget that cannot be shot.
#
#   (from_sid, to_sid, kind, seconds)             or
#   (from_sid, to_sid, kind, seconds, {settings})
#
# THE FIFTH ELEMENT IS THAT DEVICE'S OWN SETTINGS and is optional. Device
# parameters are EDITORIAL -- the rect a portal starts in is read off a plate,
# the angle of a wipe is a choice about this cut -- so they belong with the
# timeline rather than in the assembler where they used to be.
#
# SESSION #3'S DEVICE IS THE HEADLIGHT SWEEP, used twice. A soft bar of light
# travels across the frame and the picture behind it has changed. It is
# deliberately unlike the two devices it follows -- #1's seam wipe is a hard
# cream diagonal, #2's row wipe is nine vertical bands snapping open -- because
# this one is single, soft, and it LIGHTS what it passes. A night film gets a
# transition only a night film could have.
#
# WHERE IT LANDS IS THE ENTIRE POINT. 09 -> 10 is the cut where he takes the
# ledger off her. A light goes past, and when it has gone he is already up the
# street with it under his arm. The film never shows the taking and never
# narrates it -- beat 10 is the silent one -- so the device is carrying a beat
# that has no words and no depicted action, which is the most work a transition
# has done in this season. 13 -> 14 is the drawer closing into first light: the
# same gesture pointed at the end of the night, so the device reads as a rhyme
# rather than as a trick used once.
# EVERY NAME HERE MUST BE IN ../devices.py. Nothing falls through to a default
# -- an `else` on this lookup is how one film rendered another film's device
# with nothing failing anywhere. contract.py refuses an unknown name, and an
# unknown SETTING, before anything is rendered.
#
#     python ../devices.py           # what is available and what it takes
#     python ../devices.py --sheet   # what each one looks like
#
# The film's own device is named once, in identity.TRANSITION. A device that
# only this film will ever want goes in a `devices_extra.py` beside this file.
#
# A DEVICE USED ONCE IS A TRICK; USED TWICE, POINTED THE OTHER WAY, IT IS A
# RHYME. Spend it on the two joins that earn it, not on every cut.
TRANSITIONS = [
    # ("01", "02", identity.TRANSITION, 0.70),
]
# A ROW MAY CARRY A FIFTH ELEMENT -- that transition's own device settings --
# so this slices rather than unpacking. Unpacking four names out of a
# five-element row is a ValueError at import, which is the good case; the bad
# case is a table where some rows have settings and some do not.
TRANS_EXTRA = {row[0]: row[3] for row in TRANSITIONS}

# (sid, [vo line ids], lead, tail, extra)
#
#   lead   silence before the first word of the beat
#   tail   silence after the last word
#   extra  additional gap between lines inside the beat
#
# NEVER TYPE A DURATION THAT MUST EQUAL ANOTHER NUMBER. A beat's length is
# computed from the MEASURED narration -- lead + Σ(line durations) + gap×(n−1)
# + tail -- so the sound and the picture cannot disagree. An edit written as two
# hand-typed tracks drifted 26 s apart on a real film, and every lip-sync window
# past the drift landed in the wrong shot.
#
# LEADS ARE THE FILM'S REGISTER, and they are worth setting deliberately. A
# comedy runs on 0.4 s leads because a lead that reads as composure in an elegy
# reads as a gap in a joke. Something slower sits at 0.5–0.6 with longer tails.
#
# EXAMPLE CONTENT -- replace it.
BEATS = [
    ("01", ["01"], 1.0, 0.80, 0.0),
    ("02", ["02"], 0.5, 0.90, 0.0),
    ("03", ["03"], 0.5, 1.20, 0.0),
]

# --------------------------------------------------------------------------
# THE OTHER MODE: A BEAT WITH NO VOICE.
#
# Everything above derives from measured narration, which is the best decision
# in this repo and is not a law of the universe. A film that is pure picture
# and score, or one with a wordless passage in it, has nothing to measure --
# and until now the only worked example of that was `cold_open/`, which types
# its lengths in `shot.SECS` because it has no `script.py` at all. That pattern
# is right; being a special case in one folder rather than a documented mode is
# what was wrong with it.
#
# SO A BEAT HAS ITS LENGTH ONE WAY OR THE OTHER, NEVER BOTH AND NEVER NEITHER:
#
#   lids is non-empty   ->   MEASURED. The beat is as long as its takes are.
#   lids is []          ->   TYPED. The beat is as long as SILENT[sid] says.
#
# Both still take lead/tail/extra on top, so a silent beat is still an
# editorial object rather than a raw number, and every consumer downstream --
# h3_shoot, make_music, assemble, storyboard -- is unchanged because they all
# read table().
#
# A TYPED LENGTH IS A CHOICE AND SHOULD READ LIKE ONE. `4.0  # long enough to
# stop feeling like a title background` is worth more than `4.0`, because the
# next person cannot re-measure it and has only the comment to argue with.
#
# WHICH BEATS ARE SILENT IS script.py'S FACT AND IS NOT REPEATED HERE. It is a
# decision about the writing -- `script.SILENT` -- and this table only says how
# long each of them runs, which is a decision about the timeline. The first
# draft of this had a `SILENT` in both files with different types, free to
# disagree, which is the exact bug the whole rest of this repo is built to
# refuse. The assert below is what makes the split safe.
SILENT_SECS: dict[str, float] = {
    # "04": 6.0,     # the walk, with nothing said over it
}


# THE SCORE'S CUE TABLE, HERE, BECAUSE WHERE THE MUSIC CHANGES IS AN EDIT.
#
# `CROSSOVER_SID = "11"` used to be declared SEPARATELY in assemble.py and in
# make_music.py, and the two were free to disagree -- which they did, at which
# point the cue was generated to change register at one moment and laid under
# the film at another. It only crashed because the beat one of them named did
# not exist; in a tree that HAS a beat of that number it is silent, and the
# score simply turns over in the wrong place.
#
#   (cue name, the sid it comes in on)
#
# The first entry enters at zero and each one runs until the next begins. A
# season with one cue writes one row; a season with four writes four. Nothing
# in the mixer or the generator counts them -- both read this table, which is
# what stops "two cues and one crossover" from being welded into the machinery.
CUES = [
    ("main", "01"),
    ("late", "03"),      # EXAMPLE: the beat where the film changes register
]


def cue_spans(rows: list[dict] | None = None) -> list[dict]:
    """(name, sid, start, secs) per cue, derived from the edit table.

    DERIVED, so a cue cannot be written to one length and laid under another.
    Both the generator and the mixer call this; neither works a start time out
    for itself.
    """
    rows = rows if rows is not None else table()
    starts, t = {}, 0.0
    for r in rows:
        starts[r["sid"]] = t
        t += r["beat"]
    out = []
    for name, sid in CUES:
        if sid not in starts:
            sys.exit(f"FAIL: score cue {name!r} comes in on beat {sid!r}, "
                     f"which is not in the edit table. That is another film's "
                     f"beat number left in this one's cue table.")
        out.append({"name": name, "sid": sid, "start": starts[sid]})
    out.sort(key=lambda c: c["start"])
    for i, c in enumerate(out):
        c["secs"] = (out[i + 1]["start"] if i + 1 < len(out) else t) - c["start"]
    return out


# NEVER BOTH, AND NEVER NEITHER. A beat that has copy AND a typed length has
# two sources of truth for one number, which is this repo's oldest bug; a beat
# with neither gets a length by accident. Checked here rather than in table()
# so a mistake fails on import instead of at the first render.
_SPOKEN = {sid for sid, lids, *_ in BEATS if lids}
_SIDS = [sid for sid, *_ in BEATS]
assert not (set(SILENT_SECS) & _SPOKEN), (
    f"{sorted(set(SILENT_SECS) & _SPOKEN)} has both copy and a typed length -- "
    f"the beat cannot be as long as its takes AND as long as somebody typed")
assert set(SILENT_SECS) <= set(_SIDS), (
    f"SILENT_SECS gives a length to {sorted(set(SILENT_SECS) - set(_SIDS))}, "
    f"which is not a beat of this film")
for _sid in _SIDS:
    assert _sid in _SPOKEN or _sid in SILENT_SECS, (
        f"beat {_sid} has no lines and no typed length -- see SILENT_SECS")
for _sid, _s in SILENT_SECS.items():
    assert _s > 0, f"beat {_sid} is typed at {_s}s of picture"

# AND THE TWO FILES AGREE ABOUT WHICH BEATS ARE SILENT. script.SILENT is the
# writing's declaration -- "this beat has no words and that is deliberate" --
# and SILENT_SECS is the timeline's answer to it. Either without the other is
# how a beat that was meant to play under nothing quietly acquires a line, or
# how a length gets typed for a beat that has one.
assert set(SILENT_SECS) == set(script.SILENT), (
    f"script.py and edit.py disagree about which beats are silent: "
    f"{sorted(set(SILENT_SECS) ^ set(script.SILENT))}. script.SILENT names "
    f"them; SILENT_SECS says how long each one runs.")

# AN UNSCORED FILM IS ALLOWED, AND UNTIL NOW IT WAS NOT. This asserted `CUES`
# was non-empty, on the grounds that make_music.py would have nothing to make.
# That was true of make_music.py and it was never true of the film: a piece
# carried by its voice and its room tone is an ordinary thing to want. The
# assert was standing in for the mixer, which built `amix=inputs=0` for an
# empty cue list -- an ffmpeg error at the end of a bake. ../mixes.py handles
# it by name now, so the only thing left to check is that a film which HAS a
# score does not start dry.
if CUES:
    assert CUES[0][1] == BEATS[0][0], (
        f"the first score cue comes in on beat {CUES[0][1]!r} but the film "
        f"starts on {BEATS[0][0]!r} -- the opening would play dry")
assert len(set(s for _n, s in CUES)) == len(CUES), \
    "two score cues come in on the same beat"
assert len(set(n for n, _s in CUES)) == len(CUES), \
    "two score cues have the same name -- they share a filename"


def vo_dur(lid: str) -> float:
    path = os.path.join(VO, f"{lid}.mp3")
    if not os.path.exists(path):
        sys.exit(f"FAIL: VO take {lid} missing -- run make_vo.py")
    out = subprocess.run(
        [season_paths.ff("ffprobe"), "-v", "error", "-show_entries",
         "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def table() -> list[dict]:
    rows = []
    for sid, lids, lead, tail, extra in BEATS:
        # MEASURED OR TYPED, AND THE FILE SAYS WHICH. This used to fall through
        # to `speech = 0` for a beat with no lines, so a beat that had simply
        # been forgotten came out as lead + extra + tail -- a plausible two
        # seconds of picture, arrived at by accident, in a pipeline whose whole
        # argument is that a silence should be a number somebody chose.
        if lids:
            speech = sum(vo_dur(l) for l in lids)
        elif sid in SILENT_SECS:
            speech = SILENT_SECS[sid]
        else:
            sys.exit(f"FAIL: beat {sid} has no lines and no typed length.\n"
                     f"  Give it copy in script.py and list the line ids in "
                     f"BEATS, or\n"
                     f"  name it in script.SILENT and give it a length in "
                     f"SILENT_SECS.\n"
                     f"  A beat that is as long as its lead plus its tail is "
                     f"an accident.")
        gaps = extra * (len(lids) - 1) if lids else 0.0
        beat = lead + speech + gaps + tail
        # AND IS IT A LENGTH A CAMERA COULD BE ASKED FOR? Everything above this
        # line checks that the number is CONSISTENT -- every beat has a source,
        # nothing is negative, the tables agree. None of it asks whether the
        # answer is SHOOTABLE, and those are different questions.
        #
        # A fork's beat tiler asserted its output covered the whole song
        # exactly, in order, with no gaps, summing to the duration -- four
        # asserts, all green, on a tiling whose last beat was THIRTY-TWO
        # SECONDS. Structural asserts are cheap and every one of them passes on
        # nonsense.
        #
        # Here the short end is the one that gets through: `clip` below is
        # clamped UP to CLIP_MIN, so a beat of 0.4s quietly buys three seconds
        # of video and puts a four-frame shot in the cut. The long end is
        # already caught, by the vendor-cap exit a few lines down.
        if beat < BEAT_MIN:
            sys.exit(
                f"FAIL: beat {sid} works out at {beat:.2f}s of picture, under "
                f"the {BEAT_MIN}s floor.\n"
                f"  lead {lead:.2f} + speech {speech:.2f} + gaps {gaps:.2f} + "
                f"tail {tail:.2f}.\n"
                f"  That is a real number and it is not a shot. Usually a "
                f"broken VO take\n"
                f"  measured near zero, or a SILENT_SECS entry typed in "
                f"frames instead of\n"
                f"  seconds. Fix the source, or fold this beat into its "
                f"neighbour.")
        # THE RUN-UP IS BOUGHT AND THEN SKIPPED, and both numbers come off this
        # one lookup so they cannot drift apart. See RUNUP above.
        runup = float(RUNUP.get(sid, 0.0))
        clip = min(CLIP_MAX,
                   max(CLIP_MIN, math.ceil(beat + runup + CLIP_MARGIN)))
        if clip < beat + runup:
            sys.exit(
                f"FAIL: beat {sid} needs {beat:.1f}s"
                + (f" plus a {runup:.1f}s run-up" if runup else "")
                + f" but the vendor caps at {CLIP_MAX}s -- shorten the line, "
                f"split the beat"
                + (", drop the run-up" if runup else "")
                + ".\n  CLIP_MAX is what a PAID vendor will sell in one call. "
                "A film shooting on local\n  h3_shoot.py has no such ceiling -- "
                "raise it here, with the reason beside it.")
        # A transition source has to hand the assembler live frames PAST the end
        # of its own beat, so its clip must cover in-point + beat + transition.
        trans = TRANS_EXTRA.get(sid, 0.0)
        # THE IN-POINT IS THE RUN-UP PLUS WHATEVER SETTLING FITS. The settle is
        # what is left over after the beat and the transition have been paid
        # for, capped at SS_MAX -- so a run-up never eats the frames the beat
        # itself needs. It cannot: the clip was bought `runup` longer above.
        ss = runup + max(0.0, min(SS_MAX,
                                  clip - runup - beat - trans - SS_GUARD))
        rows.append({"sid": sid, "lines": lids, "lead": lead, "tail": tail,
                     "extra": extra, "speech": speech, "beat": beat,
                     "clip": clip, "ss": ss, "trans": trans, "runup": runup})
    return rows


# SECS IS COMPUTED ON FIRST ACCESS, NOT ON IMPORT, and that is not a style
# preference. It used to be a module-level dict comprehension over table(),
# which shells out to ffprobe for every take -- so `import edit` REQUIRED the
# VO to have been recorded, and every module that imports edit (h3_shoot,
# assemble, verify, storyboard, make_video...) was unimportable on a fresh
# clone. Two of them had faults on the lines immediately after `import edit`
# and nothing could reach far enough to find them.
#
# A module-level __getattr__ (PEP 562) keeps `edit.SECS[sid]` reading exactly
# as it did, computes once, and caches into globals so the second lookup is a
# plain dict. The measurement still happens before anything is bought; it just
# happens when somebody ASKS, which is the point at which the VO must exist.
def __getattr__(name: str):
    if name == "SECS":
        globals()["SECS"] = v = {r["sid"]: r["clip"] for r in table()}
        return v
    # `FRAMES` IS HOW LONG THE BEAT IS ON SCREEN, IN DELIVERY FRAMES -- and it
    # is not the same number as SECS.
    #
    # SECS is how much CLIP to buy: the beat plus a margin, snapped up to a
    # whole second, because a vendor sells lengths and the assembler enters
    # each clip a little way in. FRAMES is what actually reaches the cut.
    #
    # IT EXISTS BECAUSE LIP SYNC ASKED FOR IT. italk.py renders at 25fps and
    # converts down, so it has to know exactly how many 24fps frames the
    # finished segment must be -- ask for one too few and the mouth runs out
    # before the bar does. show/edit.py has carried this for its own tree since
    # the reference season; a film tree could not answer the question at all,
    # which is one more way lip sync was welded to the show layer.
    if name == "FRAMES":
        fps = identity.season.FPS
        globals()["FRAMES"] = v = {r["sid"]: round(r["beat"] * fps)
                                   for r in table()}
        return v
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def main() -> int:
    rows = table()
    print(f"  {'#':>2} {'beat':>4} {'lines':<8} {'lead':>5} {'talk':>6} "
          f"{'tail':>5} {'beat':>6} {'buy':>4} {'run':>5} {'in':>5} "
          f"{'in+beat':>8}")
    bad = 0
    for i, r in enumerate(rows, 1):
        need = r["ss"] + r["beat"] + r["trans"]
        flag = "" if need <= r["clip"] else "  <-- OVERRUNS"
        bad += bool(flag)
        print(f"  {i:>2} {r['sid']:>4} {','.join(r['lines']) or '--':<8} "
              f"{r['lead']:>5.1f} {r['speech']:>6.2f} {r['tail']:>5.1f} "
              f"{r['beat']:>6.2f} {r['clip']:>3d}s "
              f"{r['runup'] or '':>5} {r['ss']:>5.2f} "
              f"{need:>7.2f}s{flag}")
    pic = sum(r["beat"] for r in rows)
    buy = sum(r["clip"] for r in rows)
    print(f"\n  picture {pic:.1f}s   |   buying {buy}s of clip ({buy/pic:.2f}x)")
    print(f"  Seedance 480p: ${buy/10*0.12:.2f}")
    if bad:
        sys.exit(f"FAIL: {bad} beat(s) overrun the clip they would buy -- "
                 "shorten a tail, or shorten the transition that beat feeds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
