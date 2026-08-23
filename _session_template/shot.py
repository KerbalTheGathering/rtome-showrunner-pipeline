"""The plates: one prompt per beat, plus the look the whole season shares.

WHAT IS HERE IS A THREE-BEAT EXAMPLE, invented for the template. Replace every
prompt; preflight.py refuses to render while the example survives. The COMMENTS
are not an example -- they are the rules, and they should outlive your rewrite.

HOW A PROMPT IS BUILT: style block, then subject, then environment, then light,
then framing. THE LEADING BLOCK WINS TIES, so whatever must survive goes first.
The season's medium block leads every prompt in the season and is byte-identical
in all of them -- that is what makes six films look like one thing.

REUSABLE BLOCKS, NOT REPEATED SENTENCES. A character, a location or a lighting
state that appears in more than one beat gets a named constant. Retyping it is
how two beats that are meant to be the same place stop being the same place.

TWO SHOTS THAT MUST MATCH NEED ONE PLATE, NOT TWO PROMPTS. Two prompts will not
converge on the same room. Generate one plate and derive both framings from it,
or alias one beat to another's plate through PLATE_ALIAS below.

THE SEED IS THE RE-ROLL LEVER. Most shape failures -- a hand, a count, a pose --
are seed failures and cannot be argued away with more words. Change the seed
first; if the same fault returns at a second seed, then it is the prompt, and it
is more often a CAPACITY problem (too much asked of one frame) than a wording
one. Widen the frame before rewriting the sentence. See docs/05_prompting.md.

ANYTHING THAT MUST BE SPELLED CORRECTLY IS NOT GENERATED. Leave the surface
blank here and draw the type at bake resolution in assemble.py.
"""
from __future__ import annotations

import identity

# THE CONTENT BELOW IS THE TEMPLATE'S EXAMPLE, NOT YOUR FILM.
# preflight.py refuses to render while this line is here. Delete it when
# you have replaced the content -- and only then.
EXAMPLE_CONTENT = True


# IDENTITY IS IMPORTED, NEVER TYPED. Everything below that names this film reads
# from identity.py, which is the one file a clone edits. See its docstring for
# the four silent clone bugs that produced this rule.
NAME = identity.NAME

# WHO THIS FILM IS, IN ONE PLACE. The title card and the output filename were
# TYPED into assemble.py in every tree, so four sessions carried a card reading
# one film's title over another film, and wrote that film out under the first
# one's filename. Same clone bug as motion.py, same fix:
# state identity once and derive it everywhere.
SESSION_NO = identity.SESSION_NO
TITLE = identity.TITLE
SLUG = identity.SLUG

# NO BEAT IS FLAT-GRADED IN THIS FILM. The grade means "a place with nothing in
# it", and it was deliberately withheld from these empty 4am streets -- an empty
# street at night is already the thing the grade says, and spending it here
# would have said it twice. It went to #5's cleared land instead. assemble.py
# carried Session #2's rally beats {07,08,09,10} in every tree, which would have
# drained the bolero corner, the woman on the step and the reading room.
GRADED: list[str] = []

# WHERE A BEAT'S CROP COMES FROM, when the film's is wrong for it.
#
# identity.FIT_OPTS says how every plate is fitted into the frame. That is the
# right place for it and it is right for almost every beat -- but a crop is
# normally wrong on ONE of them: the shot where the subject sits low, or hard
# left, and the film's centre crop takes the head off. Overriding the film to
# fix one beat moves fourteen others.
#
# Keys are beat ids, values are settings for identity.FIT:
#     FIT_BEATS = {"07": {"anchor": (0.5, 0.2)}}
# `python ../framing.py --sheet` shows what each anchor keeps and loses.
FIT_BEATS: dict[str, dict] = {}

SEED = identity.SEED          # the seed the night test was proven on

LATENT = identity.LATENT     # x2 VAE -> 2432x1664 plate

STYLE_LORA, STYLE_W = identity.STYLE_LORA, identity.STYLE_W
CHAR_LORA, CHAR_W = identity.CHAR_LORA, identity.CHAR_W

# WHICH LOOK EACH BEAT TAKES, out of identity.REGISTERS. Empty means every
# beat takes STYLE_LORA. A beat listed here takes its register's style LoRA
# INSTEAD -- see identity.REGISTERS for why a film would want two.
REGISTER: dict[str, str] = {}


def style_for(sid: str) -> tuple[str, float]:
    """The (style LoRA, weight) this beat is painted with."""
    reg = REGISTER.get(sid)
    if reg is None:
        return STYLE_LORA, STYLE_W
    return identity.REGISTERS[reg]


def _check_registers() -> None:
    bad = sorted(r for r in set(REGISTER.values()) if r not in identity.REGISTERS)
    assert not bad, (f"shot.REGISTER names register(s) {bad} that "
                     f"identity.REGISTERS does not define")


_check_registers()

# --- the season spine, byte-identical across all three films -----------------

# --- the season's shared look ----------------------------------------------
#
# BYTE-IDENTICAL IN EVERY FILM OF THE SEASON. Copy this block between session
# folders unchanged, or the films stop looking like one another. If it needs to
# change, change it everywhere in the same commit.
_MEDIUM = (
    "Painted illustration in flat gouache and ink on textured paper over a "
    "visible pencil underdrawing, confident dark linework, visible brush "
    "marks. "
)

# WHAT THE FILM IS ABOUT, AS A VISUAL INSTRUCTION rather than a theme. It rides
# in every prompt so the season argues the same thing in every frame.
_THESIS = (
    "The place is doing something ordinary and nobody is watching it. "
)

# LIGHTING STATES. One per condition, not one per beat -- two beats in the same
# light must be handed the same string.
_LIGHT_NIGHT = (
    "Night. The only light is the lamp itself, cold and white, and it does not "
    "reach the ground. "
)
_LIGHT_DAWN = (
    "First light, low and grey, the sky brighter than the land. "
)

STYLE_NIGHT = _MEDIUM + _LIGHT_NIGHT + _THESIS
STYLE_DAWN = _MEDIUM + _LIGHT_DAWN + _THESIS
STYLE_MAIN = STYLE_NIGHT          # what a second-layer render defaults to

# --- recurring subjects ----------------------------------------------------
#
# AN IDENTITY BLOCK IS ALSO A SCALE INSTRUCTION. Specifying a coat's buttons and
# a beard's colour tells the model the figure must be close enough to show them,
# and it will walk the figure forward until it is. If you want a distant figure,
# describe a distant figure and move the detail into the environment.
_KEEPER = (
    "A lighthouse keeper in a heavy dark coat and a knitted cap, middle-aged, "
    "unhurried. "
)
_LIGHTHOUSE = (
    "A short white-painted stone lighthouse on a bare grass headland, its rail "
    "rusted, standing alone with no other building in sight. "
)

# --- the beats -------------------------------------------------------------
#
# EXAMPLE CONTENT. Replace all three and add your own.
#
# `sid` is a two-digit STRING and is the join between this file, script.py,
# motion.py and edit.py. `what` is the one-line intent, printed by every tool
# that lists beats. `caption` appears on the storyboard, not in the film.
BEATS = [
    {
        "sid": "01",
        "what": "THE WALK UP -- the light is out and somebody has to go and see",
        "caption": "EXAMPLE: BEAT 01",
        "prompt": (
            STYLE_NIGHT +
            "A wide low shot looking up a bare grass slope at night toward a "
            "dark headland. " + _LIGHTHOUSE +
            "The lamp room at the top is unlit and black against the sky. " +
            _KEEPER +
            "The keeper is small in the lower third of the frame, walking away "
            "from the camera up the slope with a lantern held low at his side."
        ),
    },
    {
        "sid": "02",
        "what": "THE LAMP ROOM -- nothing is broken, which is the problem",
        "caption": "EXAMPLE: BEAT 02",
        "prompt": (
            STYLE_NIGHT +
            "Interior of a small round lamp room, brass and glass, the great "
            "lens standing dark in the middle of the frame with the black sea "
            "beyond the windows. " + _KEEPER +
            "The keeper stands at the left of the frame with one hand on the "
            "brass rail, looking at the lens, framed from the waist up."
        ),
    },
    {
        "sid": "03",
        "what": "THE WALK DOWN -- he leaves it burning",
        "caption": "EXAMPLE: BEAT 03",
        "prompt": (
            STYLE_DAWN +
            "A wide shot of the same bare headland at first light, the sky "
            "grey and brightening, the sea flat below. " + _LIGHTHOUSE +
            "The lamp at the top is lit and pale against the dawn. " + _KEEPER +
            "The keeper is small at the right of the frame, walking down the "
            "slope away from the lighthouse, side-on to the camera."
        ),
    },
]

BEAT = {b["sid"]: b for b in BEATS}

ORDER = [b["sid"] for b in BEATS]        # story order
CUT = ORDER
VIDEO = {s: {"vendor": "seedance"} for s in CUT}

# --- second layer -----------------------------------------------------------
#
# NOT RENDERED, and this session does not use one at all. The flat grade means
# "a place with nothing in it" across the whole season -- it was built for
# Session #1's arithmetic and reused for #2's rally, and it is scheduled to come
# back later for another empty place. A street at four in the morning is empty
# but it is
# not nothing, and spending the device here would blunt it twice over. Withheld
# on purpose.
OBJ: list[str] = []
OBJ_NAME = NAME + "_OBJ"
OBJ_STYLE = STYLE_MAIN

# Any beat re-rolled with --seed= must be written down here. SEED is a film-wide
# DEFAULT and stays true right up until the first re-roll, after which it is a
# lie for those beats and nothing complains.
PLATE_SEED: dict[str, int] = {}

# THE BOLERO, MADE CERTAIN INSTEAD OF REQUESTED. Beat 07 does not get a plate of
# its own -- it uses beat 03's, so the second pass down the corner is the SAME
# PICTURE, not a similar one. Asking for that in words failed outright: same
# seed, byte-identical leading text, three different corners.
#
# Two clips bought off one still is not a saving dodge, it is the correct
# construction for this device. A musical repeat is literally the same bars
# again; the variation belongs in what MOVES, which is motion.py's job and costs
# nothing extra. gen_still.py skips an aliased beat and plate() resolves it.
# Example: {"07": "03"} makes beat 07 reuse beat 03's plate, which is how
# two beats in one unbroken location stay one location.
PLATE_ALIAS: dict[str, str] = {}


def plate_seed(sid: str) -> int:
    return PLATE_SEED.get(sid, SEED)


def obj_prompt(sid: str) -> str:
    raise AssertionError(
        "this session has no flat layer at all -- see the note above")


_caps = [b["caption"] for b in BEATS if b["caption"]]
assert len(_caps) == len(set(_caps)), f"a caption is repeated: {_caps}"
assert len(BEATS) == len(BEAT), "duplicate sid"

# THE BEAT COUNT IS NOT TYPED HERE. It used to read `assert len(BEATS) == 15`
# against a three-beat example, which is a fifteen-beat film's number left
# behind in a file that no longer describes one -- and it made this module
# impossible to import, so nothing downstream of it could be checked either.
#
# The count that matters is not a constant, it is AGREEMENT: script.py, this
# file, motion.py and edit.py must cover the same beats. That is checked where
# it can be seen, by contract.py, and repeating a literal here would only give
# it something else to disagree with. What IS asserted is the floor: a film
# with no beats is not a film.
assert BEATS, "no beats -- shot.py describes nothing"

# THE OLD ASSERT CHECKED THAT 03, 07 AND 12 SHARED THEIR LEADING TEXT, AND IT
# PASSED WHILE THE DEVICE FAILED. That is the worst kind of check: it verified
# the thing I controlled (the words) rather than the thing I wanted (the
# picture), so it went green on three visibly different corners. What replaced
# it constrains the actual outcome -- a beat cannot be a different corner from
# the one it repeats if it is not allowed to have a plate of its own:
#
#     assert PLATE_ALIAS.get("07") == "03", (
#         "beat 07 must alias beat 03's plate -- asking two renders to agree "
#         "on a composition does not work and was already tried")
#
# IT IS COMMENTED OUT BECAUSE IT NAMES BEATS THAT ONLY EXIST IN THE FILM THIS
# EXAMPLE CAME FROM. A two-digit sid resolves in every session, so an inherited
# one does not fail -- it quietly asserts something about the wrong beat, or
# refuses to import at all, which is what this line did. Write the version of
# it your film needs, against your own beat numbers.
for _dst, _src in PLATE_ALIAS.items():
    assert _dst in BEAT, f"PLATE_ALIAS aliases unknown beat {_dst!r}"
    assert _src not in PLATE_ALIAS, f"alias chain: {_dst} -> {_src} -> ..."
for _src in PLATE_ALIAS.values():
    assert _src in BEAT, f"PLATE_ALIAS points at unknown beat {_src!r}"


# --------------------------------------------------------------------------
# MID-FILM CARDS -- a card over a beat that is neither the first nor the
# last. TITLE_CARD and END_CARD_STYLE (identity.py) anchor to the film's
# START and END; this anchors to a BEAT, wherever it falls -- a "we'll be
# right back" or "and now, a word from our sponsor" card, for instance.
#
# Found missing on a real film: the beat's `what`/`caption` said what the
# card was SUPPOSED to say, and nothing ever drew it -- there was no
# machinery to draw a card anywhere but the start or the end. This is that
# machinery, added when the gap was noticed.
#
# {sid: (card name, [lines])} or {sid: (card name, [lines], {settings})} --
# the settings are the card's own, as TITLE_CARD_OPTS. EMPTY BY DEFAULT -- most films need no mid-
# film card at all. Clamped to the beat's own frame range in assemble.py, so
# a card cannot bleed into the beat before or after it.
#
#     MID_CARDS = {
#         "07": ("plain", ["AND NOW, A WORD FROM OUR SPONSOR"]),
#     }
#
# TEXT ONLY. It does not run the card's PICTURE treatment the way the title
# card does over the opening beat -- that needs neighbour-frame lookback
# (see assemble.py's `neighbour()` closure) that does not generalise to an
# arbitrary later beat without real extra machinery, and `break_diagonal` is
# the only card with a treatment at all, which is a season signature rather
# than something a quick mid-film aside would want. Add it here if a season
# ever needs one.
#
# IF A MID-CARD'S BEAT IS ALSO SILENT (script.SILENT / edit.SILENT_SECS),
# DERIVE ITS LENGTH FROM THE CARD RATHER THAN TYPING ONE. A typed length
# against whatever the card actually needs is the same bug that made a real
# film's opening beat fade its title out and then sit on the plain, undimmed
# picture for two and a half seconds before the cut -- the length and the
# card drifted apart because only one of them was a fact. In edit.py:
#
#     import cards
#     _mid_style, _ = MID_CARDS["07"]
#     SILENT_SECS = {"07": cards.seconds(_mid_style), ...}
MID_CARDS: dict[str, tuple[str, list[str]]] = {}

for _sid in MID_CARDS:
    assert _sid in BEAT, f"MID_CARDS names unknown beat {_sid!r}"
