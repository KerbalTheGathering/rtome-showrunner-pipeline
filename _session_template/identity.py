"""WHO THIS SESSION IS. The only file you edit when you clone a session folder.

READ THE SEASON-LEVEL identity.py FIRST -- this one is the per-film half of the
same idea, and it exists because the season it came from had these values typed
into five separate files per tree. Two of the resulting bugs FAILED SILENTLY:

  * `shot.py` and `assemble.py` each held the title, so a clone rendered
    film #2's title card over film #3, and wrote film #3 out under
    film #2's filename.
  * `motion.py` held its own SESSION name and the previous film's beat
    durations, so a checker reported "these beats need longer clips" -- which
    reads as "go and buy longer clips" and would have cost real money.
  * `edit.TRANSITIONS` named a device (`sweep`) that `assemble.py` had never
    implemented, and the `else` branch rendered the PREVIOUS season's device.
    Nothing failed. See the transition assert in assemble.py.
  * A missing SECS entry crashed AFTER the balance check, i.e. after the money.

So: state it once here, import it everywhere, and let check() refuse to run.

    python identity.py        # print what this session thinks it is
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import os
import sys

# THE TWO FILES HAVE DIFFERENT NAMES ON PURPOSE. A script's own directory is
# sys.path[0], so if the season-level file were also called identity.py, every
# `import identity` inside a session folder would find the SESSION's copy and
# the season values would silently be whatever this file happens to define.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import season_identity as season                                   # noqa: E402

# --------------------------------------------------------------------------
# THE FILM
# --------------------------------------------------------------------------

# Short, uppercase, filesystem-safe. Becomes the ComfyUI output folder
# (`<season_paths.COMFY>\output\<NAME>_clips`) and every log prefix.
NAME = ""                        # e.g. "LIGHTHOUSE"

SESSION_NO = 0                   # 1..season.N_SESSIONS; feeds PART_LABEL's {n}
TITLE = ""                       # e.g. "THE LIGHTHOUSE" -- the on-screen card
SLUG = ""                        # e.g. "the_lighthouse" -- the output filename

# THE LINE ABOVE THE TITLE ON THIS FILM'S CARD.
#
# `None` takes the season's `PART_LABEL` and is what almost every film wants --
# the eyebrow is a series fact, not a per-film one. Set a string to override it
# for this film alone (a prologue in a numbered season), or "" to give this one
# film a title card of one line.
LABEL: str | None = None


def label() -> str:
    """This film's eyebrow line, resolved. "" means the card is one line."""
    return season.part_label(SESSION_NO) if LABEL is None else LABEL

# --------------------------------------------------------------------------
# THE LOOK
# --------------------------------------------------------------------------

# The plate seed the night test was proven on. A seed is the re-roll lever;
# changing prompt words to fix a shape that is wrong in the plate is the
# expensive way round. See docs/05_prompting.md.
SEED = 0

LATENT = (1216, 832)             # x2 VAE -> 2432x1664 plate

# LoRAs. "" means none, and gen_still.py builds a shorter chain rather than
# loading a no-op -- so a film with neither still works.
#
# A STYLE LORA MAY HAVE NO TRIGGER WORD. Check the tensors before inventing one:
# a unet-only LoRA has nothing to trigger with, and typing a trigger anyway
# spends prompt weight on a token the model does not know.
STYLE_LORA, STYLE_W = "", 0.85
CHAR_LORA, CHAR_W = "", 0.9
TRIGGER = ""                     # "" if the character LoRA has no trigger token

# --------------------------------------------------------------------------
# THE VOICE
# --------------------------------------------------------------------------
#
# A CLIENT DELIVERABLE MUST NOT CARRY A CLONED VOICE OR A LIKENESS LORA. If this
# film is going to anyone who holds no licence to either, use a PREMADE
# ElevenLabs voice and no character LoRA -- make_vo.py asserts the category.
# WHO SPEAKS IN THIS FILM, BY ROLE. A table, not two slots.
#
# It was `VOICE_ID` and `VOICE_ID_2` -- one narrator plus an optional second
# voice -- and script.py asserted the second one spoke at most once. That is
# the right shape for a narrated object-film and it is a wall for anything
# else: a scene between three people cannot be expressed at all, and the cap
# was welded into the machinery rather than declared by the season that wanted
# it.
#
# THE KEY IS A ROLE AND script.LINES NAMES THE ROLE, NOT THE ID. A line that
# says `"keeper"` is readable, survives recasting, and cannot be a voice id
# from another film that happens to still resolve at the API. An empty id is a
# hard failure at the one place it is looked up rather than a 400 on the first
# render.
VOICES: dict[str, str] = {
    "narrator": "",              # ElevenLabs voice id
    # "keeper": "",
}
VOICE_IS_CLONE = False           # True only for personal work

# --------------------------------------------------------------------------
# THE DEVICE
# --------------------------------------------------------------------------
#
# WHAT THIS FILM'S TRANSITIONS ARE CALLED. Every name must be in the library at
# ../devices.py, and nothing falls through to another season's device: an
# unknown name is refused by contract.py before anything is rendered and by
# assemble.py if it somehow gets that far.
#
# `python ../devices.py` lists what is available and what each one takes;
# `--sheet` renders every one of them so you can look rather than guess.
TRANSITION = ""                  # e.g. "wipe", "iris", "sweep", "rows", "push"

# --------------------------------------------------------------------------
# THE GRADE
# --------------------------------------------------------------------------
#
# WHAT THE PICTURE LOOKS LIKE, from the library at ../grades.py.
#
# `GRADE` is every beat. `GRADED_AS` is what the beats named in `shot.GRADED`
# get INSTEAD -- shot.py says WHICH, this says WHAT, and they do not stack.
#
# The defaults reproduce the template's old behaviour exactly: no look on the
# film, and the carried `flat` grade on whichever beats shot.GRADED names. A
# film with an empty GRADED never runs either.
#
# `python ../grades.py --sheet` draws all of them on a chart with a ramp, six
# swatches and a skin tone in it, which is the only way to see what a number
# like `contrast=0.9` actually costs.
GRADE = "none"
GRADE_OPTS: dict = {}
GRADED_AS = "flat"
GRADED_OPTS: dict = {}           # e.g. {"wash": (228, 236, 250)} -- cold flat

# --------------------------------------------------------------------------
# THE FRAME
# --------------------------------------------------------------------------
#
# HOW A PLATE OF ONE SHAPE GETS INTO A FRAME OF ANOTHER, from ../framing.py.
#
# `crop` fills the frame and loses the overflow, anchored where you say;
# `pad` keeps the whole picture and puts bars round it; `stretch` distorts.
# The anchor is a name or a pair of fractions of the leftover space, so
# `{"anchor": (0.5, 0.3)}` keeps a little above centre -- which is where faces
# are, and is the setting a vertical delivery cut from horizontal plates
# usually wants.
#
# A crop that is wrong is normally wrong on ONE beat, not on the film. Override
# it there, in shot.FIT_BEATS, rather than moving the whole picture.
FIT = "crop"
FIT_OPTS: dict = {}              # e.g. {"anchor": "top"}

# --------------------------------------------------------------------------
# THE MIX
# --------------------------------------------------------------------------
#
# WHAT SITS UNDER WHAT, from ../mixes.py. `ducked` sidechains the score to the
# voice and is right for anything narrated; `flat` sums at fixed levels;
# `under` drops the score by automation instead, which does not pump and does
# not care how loud the take was.
#
# All three cope with a film that has no cues and with one that has no takes.
# The hand-built graph this replaced produced `amix=inputs=0` for either, a
# hundred lines into a filter chain at the end of a bake.
MIX = "ducked"
MIX_OPTS: dict = {}              # e.g. {"music": 0.42}

# --------------------------------------------------------------------------
# THE CARDS
# --------------------------------------------------------------------------
#
# `python ../cards.py` lists them; `--sheet` draws them.
#
# `plain` is the default and does the obvious thing -- the type fades up over
# the opening shot, holds, fades out. The template used to offer exactly one
# card, a diagonal break with a slip and a desaturation resolving as the type
# lands, which is one season's signature and was welded into the assembler. It
# is still here as `break_diagonal`; it is just no longer everybody's.
TITLE_CARD = "plain"
TITLE_CARD_OPTS: dict = {}       # e.g. {"cy": 0.44} -- see the card's settings
END_CARD_STYLE = "corner"
END_CARD_OPTS: dict = {}         # the end card's own settings, same keys as its card


def check() -> None:
    season.check()
    missing = [k for k in ("NAME", "TITLE", "SLUG", "TRANSITION")
               if not globals()[k]]
    for k in ("SESSION_NO", "SEED"):
        if not globals()[k]:
            missing.append(k)
    if missing:
        sys.exit(f"FAIL: {os.path.basename(os.path.dirname(os.path.abspath(__file__)))}"
                 f"/identity.py is still blank.\n"
                 "  Unfilled: " + ", ".join(missing) + "\n"
                 "  Read ../docs/01_process.md. Every other file in this folder\n"
                 "  imports these values -- do not type a name anywhere else.")
    if not 1 <= SESSION_NO <= season.N_SESSIONS:
        sys.exit(f"FAIL: SESSION_NO {SESSION_NO} is outside 1..{season.N_SESSIONS} "
                 f"(season identity says the season has {season.N_SESSIONS} films)")
    # AN EMPTY `VOICES` IS ALLOWED. IT USED TO BE A HARD REFUSAL HERE, AND
    # THAT MADE A DOCUMENTED MODE UNREACHABLE.
    #
    # The old text named exactly the right conditions -- "a film with nobody
    # in it needs script.SILENT covering every beat and edit.SILENT_SECS
    # giving each one a length" -- and then exited anyway, because THIS FILE
    # CANNOT CHECK EITHER OF THEM. identity.py does not import script.py or
    # edit.py and must not: they import IT. So the guard could only state the
    # requirement and refuse.
    #
    # The result was a non-narrated mode that edit.SILENT_SECS supports,
    # mixes.py has a bus for, docs/01_process.md explains, and nothing could
    # actually enter. The only way past was to cast a narrator who never
    # speaks -- and on a season with no ElevenLabs in it at all, that means
    # writing down a voice id for a film that never calls the API, i.e.
    # recording something untrue to satisfy a check.
    #
    # The requirement is real and it spans two files, so it belongs to
    # contract.py (`check_cast`), which loads both and can see the answer.
    # Found by a purely local music video: eleven beats, no spoken word, a
    # song generated on the machine.
    # AN EMPTY ID FAILS HERE, NOT AT THE FIRST RENDER. A role in the table with
    # no voice behind it is the same shape as a blank NAME: it resolves all the
    # way to the API and comes back a 400 with the money already spent on the
    # lines before it.
    blank = sorted(r for r, v in VOICES.items() if not v)
    if blank:
        sys.exit(f"FAIL: role(s) {blank} in VOICES have no voice id.\n"
                 f"  `python find_voice.py <name>` looks one up, or "
                 f"`python audition.py`\n  casts one. Delete the role if the "
                 f"film does not have it.")
    if CHAR_LORA and not VOICE_IS_CLONE:
        print("  note: a character LoRA is set on a film using a non-clone "
              "voice -- check this is not a client deliverable")


CLIPS = (os.path.join(season_paths.COMFY_OUTPUT, f"{NAME}_clips")
         if NAME else "")

check()

# THE CLIP FOLDER IS CLAIMED FOR THIS SEASON, not merely named. See
# season_identity.claim_clips() -- a NAME reused between seasons otherwise makes
# a new build read the old season's clips, coherently and silently.
season.claim_clips(CLIPS, f"{__name__}")

if __name__ == "__main__":
    print(f"  session  #{SESSION_NO}  {NAME}  --  {TITLE!r}")
    print(f"  file     {SLUG}.mp4")
    print(f"  plate    seed {SEED}, latent {LATENT}")
    print(f"  loras    style={STYLE_LORA or '(none)'} char={CHAR_LORA or '(none)'}")
    print(f"  device   {TRANSITION}")
    print(f"  look     {GRADE} (graded beats: {GRADED_AS}), fit {FIT}"
          f"{' ' + str(FIT_OPTS) if FIT_OPTS else ''}")
    print(f"  cards    {TITLE_CARD} / {END_CARD_STYLE}, mix {MIX}")
    print(f"  clips    {CLIPS}")
