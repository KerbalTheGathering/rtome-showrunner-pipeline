"""WHO THIS SEASON IS. Fill this in first; nothing else reads a season name.

EVERY FILE IN THIS TEMPLATE THAT NEEDS TO KNOW WHAT SEASON IT IS IMPORTS FROM
HERE. That is the whole point of it. The season this template was extracted from
had its identity TYPED into five separate files per session tree, and every one
of those was a clone bug waiting: four sessions carried a title card reading
one film's title card over another film, one wrote its
output to another film's filename, and one rendered a different session's
transition device because the name it asked for was never implemented and the
`else` branch silently did something plausible.

None of those failed. They all rendered clean and exited 0.

SO: STATE IT ONCE, DERIVE IT EVERYWHERE, AND HARD-FAIL WHEN IT IS BLANK.
The asserts at the bottom fire on import, which means a half-configured clone
cannot get as far as spending money on a generation.

    python identity.py        # print what this season thinks it is
"""
from __future__ import annotations

import sys

import season_paths

# --------------------------------------------------------------------------
# THE SEASON
# --------------------------------------------------------------------------

# Short, filesystem-safe, no spaces. Used for the delivery folder, the feature
# filename and every log line that has to say which season it is.
SEASON = ""                      # e.g. "Harbour_Lights"

# What the feature is called on screen and on disk.
SEASON_TITLE = ""                # e.g. "NIGHT WORK"
SEASON_SLUG = ""                 # e.g. "harbour_lights"

# How many films. season.py builds this many session folders and refuses to
# join until every one of them has an out/ film.
N_SESSIONS = 0                   # e.g. 6

# THE LINE ABOVE THE TITLE, AS A TEMPLATE. `{n}` is the film's SESSION_NO.
#
# IT WAS `f"SESSION #{shot.SESSION_NO}"`, TYPED INTO assemble.py. "Session" is
# what the reference season happened to call its films, and it was welded into
# the machinery every season shares -- so an episode was a session, a chapter
# was a session, and a one-off music video with no numbered parts at all was
# "SESSION #1". Same fault as the transition that lived in an `if` and the
# grade that lived in a function: one season's vocabulary standing in for the
# structure.
#
# Set it to "EPISODE {n}", "CHAPTER {n}", "PART {n}", "A FILM IN {n} PARTS",
# anything. `{n}` is optional -- a constant string is fine.
#
# **"" MEANS NO LINE AT ALL**, and the title card becomes one line rather than
# two, which is what a film with a title and no series around it wants.
PART_LABEL = "SESSION #{n}"

# The line that closes every film. One string for the whole season, because it
# is a refrain -- if it differs between films it is not one.
END_CARD = ""                    # e.g. "SEE YOU NEXT WEEK."

# --------------------------------------------------------------------------
# DELIVERY -- THESE MUST MATCH ACROSS EVERY PART OR THE JOIN MISBEHAVES
# --------------------------------------------------------------------------
#
# feature.py concatenates thirteen parts by stream copy. A demuxer handed a
# mismatch does NOT fail: it produces a file that plays wrong somewhere in the
# middle. So these are asserted against every part before the join, and they
# live here rather than in eight separate files.
W, H = 1440, 1080                # 4:3. Every part bakes to exactly this.
FPS = 24                         # every part, no exceptions
# THE UPSCALE (../upscale.py): every H3 clip goes through this model once,
# cached beside the clips, before it is baked. H3 renders at 864x480 and a
# Lanczos stretch to delivery is what every season shipped until LOSS OF
# SIGNAL A/B'd it (learnings 58). Name a model under models/upscale_models;
# None is the plain stretch. Pick by DELIVERED scale: x2 for 480p -> 1080p
# (0.13 s/frame); x4plus paints four times the pixels you keep (0.67 s/frame).
UPSCALE = None                   # e.g. "RealESRGAN_x2plus.pth"
A_RATE = 48000                   # ONE delivery rate for the whole season
CRF = 18

# Loudness. See docs/03_audio.md -- in particular, NOTHING IN THE AUDIO CHAIN
# MAY HAVE LOOKAHEAD, which is why the ceiling is a hard clip and not a limiter.
I_TARGET = -16.0                 # LUFS, integrated
TP_TARGET = -1.5                 # dBTP
CEIL_DBFS = -2.0                 # sample-peak ceiling for the hard clip

# --------------------------------------------------------------------------
# THE TYPEFACE
# --------------------------------------------------------------------------
#
# The season's display face, by filename, resolved out of $SEASON_FONTS. Every
# card, every title and every drawn line of type in the season uses it.
#
# IT WAS `impact.ttf` TYPED INTO THREE assemble.py FILES, which is one season's
# look welded into shared machinery three times over -- and a font is about as
# far from a mechanism as a value gets. A season with a different look changes
# one line here.
#
# ANYTHING DRAWN AT BAKE RESOLUTION IS DRAWN IN THIS. If your type needs two
# faces -- a display face and something quieter for a caption -- add the second
# here rather than reaching for a name in the file that draws it.
FONT_DISPLAY = "impact.ttf"

# HOW HEAVY THE OUTLINE BEHIND THE TYPE IS, as a fraction of frame height.
#
# THIS BELONGS WITH THE FACE AND IT WAS `max(2, round(h * 0.014))` INSIDE
# assemble.py -- 15px at 1080. That is sized for a heavy display face, where the
# outline is thinner than the letter strokes. Put a light face in front of it --
# a season changing FONT_DISPLAY, which is the one line this file invites you to
# change -- and the outline is thicker than the letters, so the type stops
# reading as type and starts reading as a sticker. A considered typographic
# choice then arrives looking worse than the default it replaced, and the reason
# is in another file.
#
# 0.014 is what the reference season used with Impact. A light or monospaced
# face wants something nearer 0.003.
FONT_STROKE = 0.014

# --------------------------------------------------------------------------
# WHERE FINISHED WORK GOES
# --------------------------------------------------------------------------
# Where finished work is copied. Comes from season_paths, which reads
# $SEASON_DELIVER and otherwise uses a folder in your home directory -- the
# machine this was written on used a cloud-sync folder, which is a
# preference, not a fact about the pipeline.
DELIVER = season_paths.DELIVER
SEASON_FOLDER = ""               # e.g. "Harbour_Lights"; "" = DELIVER/<SEASON>
EXTRA = ""                       # a second folder every render is copied to, or ""

# --------------------------------------------------------------------------
# THE SHOW LAYER (optional)
# --------------------------------------------------------------------------
#
# The wraparound: a cold open, then an interstitial in front of every film.
# Set SHOW = False for a season that is just a cold open and N films, and
# season.py will not look for show/ at all.
SHOW = True
SHOW_NAME = ""                   # e.g. "NEWSDESK"; the show's own tree name



# --- THE H3 SHOOTER'S WEIGHTS AND REFERENCES (_session_template/h3_shoot.py) ---
# The ref2va HYBRID holds identity from reference pictures and is better at
# audio than fl2va (the ninth reference season, the operator's call) -- it shoots every
# beat, dialogue or not. H3_ID_REFS are two plates of the character, paths
# relative to ComfyUI/input, wired only when the beat has him alive in frame
# (not "nochar", not "norefs"). H3_VOICE_REF is recorded here and NOT wired:
# a voice reference alongside an anchored driver crashes the sampler (fault
# 51). H3_TAIL_FRAMES is the continuation anchor -- edit.RUNUP is derived
# from it, so they cannot disagree.
H3_UNET = "minimax_h3_ref2va_hybrid_b20-49_pruned_w4a8_mixed.safetensors"
H3_ID_REFS: tuple[str, ...] = ()     # e.g. ("probe/ref_hero.png", "probe/ref_visor.png")
H3_VOICE_REF = ""                    # recorded, never wired (fault 51)
H3_TAIL_FRAMES = 22                  # frames of the parent a continuation opens on
# H3_DRIVER: anchor an audio driver on every beat (the on-screen lines in
# place, silence elsewhere). True for a film that writes its words. False
# for a film whose sound is what H3 generates -- the driver would replace it
# with anchored silence, and did (fault 64).
H3_DRIVER = True


def check() -> None:
    """Refuse to run at all until this file has been filled in."""
    missing = [k for k in ("SEASON", "SEASON_TITLE", "SEASON_SLUG", "END_CARD")
               if not globals()[k]]
    if not N_SESSIONS:
        missing.append("N_SESSIONS")
    if SHOW and not SHOW_NAME:
        missing.append("SHOW_NAME (or set SHOW = False)")
    if missing:
        sys.exit("FAIL: season_identity.py is still blank (this season's root).\n"
                 "  Unfilled: " + ", ".join(missing) + "\n"
                 "  Read docs/00_READ_ME_FIRST.md before anything else. Do not\n"
                 "  work around this by hard-coding a name somewhere else --\n"
                 "  that is the exact bug this file exists to prevent.")


def part_label(n: int) -> str:
    """The eyebrow above a film's title. "" means the card is one line.

    THE FORMAT IS APPLIED HERE AND NOWHERE ELSE, so a season that writes
    `{n}` twice, or misspells it, fails once with a sentence rather than
    rendering `SESSION #{n}` across every title card in the season.
    """
    if not PART_LABEL:
        return ""
    try:
        return PART_LABEL.format(n=n)
    except (KeyError, IndexError) as e:
        sys.exit(f"FAIL: season_identity.PART_LABEL = {PART_LABEL!r} does not "
                 f"format: {e}.\n  The only field it may use is {{n}}, the "
                 f"film's SESSION_NO. A literal brace must be doubled.")


def folder() -> str:
    import os
    return os.path.join(DELIVER, SEASON_FOLDER or SEASON)


def claim_clips(clips: str, who: str) -> None:
    """Make sure this season's clip folder is not another season's.

    FOUND BY THIS TEMPLATE'S OWN TEST CLONE, which is the best argument for it
    existing. Every generator writes to `<ComfyUI>/output/<NAME>_clips`, and
    NAME is a short word like "INTRO" or "GROVE". Reuse one in a second season
    -- the natural thing to do, since parts are named after what they are --
    and the new build silently consumes the OLD season's clips. It renders. It
    is coherent. It is the wrong film.

    So the first part to use a clip folder stamps it, and anything finding a
    stamp with a different season on it refuses. A folder that already holds
    clips and has no stamp gets a warning rather than a refusal, because that
    is what a season built before this check looks like.

    Call it from anything that WRITES clips or READS them as a set.
    """
    import os
    if not clips:
        return
    tag = os.path.join(clips, ".season")
    if os.path.exists(tag):
        owner = open(tag, encoding="utf-8").read().strip()
        if owner != SEASON:
            raise SystemExit(
                f"FAIL: {clips}\n"
                f"  belongs to season {owner!r}, but this is {SEASON!r}.\n"
                f"  {who} would have generated into another season's clips --\n"
                f"  and read them back out again. Choose a different NAME in\n"
                f"  identity.py, or move the old folder aside.")
        return
    # STAMP ONLY WHAT IS OURS TO STAMP. An unstamped folder that already holds
    # clips is either a season built before this check or somebody else's work,
    # and this function cannot tell which -- so it says so and writes nothing.
    # (Writing anyway is what the first version did, and it put this season's
    # name into the reference season's clip folder during the template's own
    # test. A guard with a side effect on data it does not own is not a guard.)
    if os.path.isdir(clips) and any(f.endswith(".mp4")
                                    for f in os.listdir(clips)):
        print(f"  !! {clips}\n"
              f"     already holds clips and carries no season stamp. If they "
              f"are not\n"
              f"     this season's, {who} will read them as though they were. "
              f"Nothing\n"
              f"     was written. Rename NAME in identity.py, or drop a "
              f".season file\n"
              f"     containing {SEASON!r} in there to adopt them.")
        return
    os.makedirs(clips, exist_ok=True)
    with open(tag, "w", encoding="utf-8") as fh:
        fh.write(SEASON + "\n")


check()

if __name__ == "__main__":
    # -h/--help prints the docstring -- the usage has always lived
    # there; this makes it reachable without opening the file
    # (finding 146). Before main(), so no lock is taken and no
    # argument guard fires first.
    import sys as _hsys
    if "-h" in _hsys.argv or "--help" in _hsys.argv:
        print(__doc__ or "(no usage doc)")
        raise SystemExit(0)
    print(f"  season   {SEASON}  --  {SEASON_TITLE!r}")
    print(f"  films    {N_SESSIONS}" + (f" + show ({SHOW_NAME})" if SHOW else ""))
    print(f"  delivery {W}x{H} @{FPS}fps, {A_RATE} Hz, crf {CRF}")
    print(f"  end card {END_CARD!r}")
    print(f"  publish  {folder()}")
