"""The show's plate and the type that lands on it. Replace the content.

WHAT IS HERE IS AN EXAMPLE. The comments are the rules.

ONE PLATE, SIX PARTS. The show is a single location shot once and reused, and
everything that distinguishes the six is words and drawn type. That is what
makes a wraparound affordable.

THE SURFACE THE TYPE LANDS ON IS DELIBERATELY BLANK IN THE PLATE. Generated
lettering comes back as garbage, so the plate leaves the board, sign or screen
empty, motion.py holds it empty for the full runtime, and assemble.py draws the
type at bake resolution where it is sharp and spelled correctly.

ONE PERSON, NOT TWO. A second figure in a locked-off medium shot is a second
identity for the model to confuse, and it will. If the season already has a
double act, the show is where you do not have one.

BLANKS CANNOT BE REQUESTED BY NEGATION -- see _NOTEXT below and
docs/02_traps.md. Compose around them.
"""
from __future__ import annotations

import identity
# WHICH SEGMENTS ARE THE FORMAT IS A FACT ABOUT THE WRITING, so it is read from
# script.py rather than restated as a literal here. script.py imports only
# identity, so there is no cycle -- and this file can therefore see both
# tables, which is where a check that spans them has to live.
import script

# THE CONTENT BELOW IS THE TEMPLATE'S EXAMPLE, NOT YOUR FILM.
# preflight.py refuses to render while this line is here. Delete it when
# you have replaced the content -- and only then.
EXAMPLE_CONTENT = True


# IDENTITY IS IMPORTED, NEVER TYPED -- see identity.py for the clone bugs
# that produced this rule.
NAME = identity.NAME

SESSION_NO = identity.SESSION_NO   # 0; not a session, the tissue between them
TITLE = identity.TITLE
SLUG = identity.SLUG

SEED = identity.SEED

LATENT = identity.LATENT     # x2 VAE -> 2432x1664, same as every session

STYLE_LORA, STYLE_W = identity.STYLE_LORA, identity.STYLE_W
CHAR_LORA, CHAR_W = identity.CHAR_LORA or None, identity.CHAR_W
# The films' character is not in this and must not arrive -- see identity.py.

# gen_still.py's --obj path renders a second flat layer. Nothing here uses it,
# but the module reads these at import, so they are defined and unused.
OBJ_NAME = NAME + "_obj"
OBJ = ""


def obj_prompt(_p: str) -> str:
    raise SystemExit("BIGSHOT has no objective layer -- --obj is not valid here")


# --------------------------------------------------------------------------
# THE LOOK. Same medium as the season, inverted lighting.
# --------------------------------------------------------------------------

# Every pigment word the season uses, and then the light turned all the way up
# and made even. "No deep shadow" is safe to state because the shadows ARE in
# frame in every reference the model has for a lit studio -- this constrains
# something present, it does not summon something absent.
_STYLE = (
    "Painted illustration in flat gouache and ink on textured paper, confident "
    "dark linework, visible brush marks. "
)

# ASK FOR BLANK STOCK, POSITIVELY. "An empty board with nothing written on it"
# invites writing; describing the SURFACE and what it is made of does not. This
# is the same rule as motion.py's -- a prohibition is not a position.
_NOTEXT = (
    "The board is a plain sheet of dark green felt in a wooden frame, evenly "
    "lit, its surface completely bare and unmarked from edge to edge. "
)

_FRAME = "A locked-off medium shot, square to the desk, flat even light. "

_SET = (
    "A cheap local television studio: a plain desk, a painted backdrop of a "
    "coastline, one potted palm at the edge of frame. "
)

_BOARD = (
    "The board stands on an easel to the right of the desk, angled slightly "
    "toward the camera and fully visible. "
)

_HOST = (
    "One man in his sixties sits behind the desk in a loud checked jacket and "
    "a knitted tie, hands resting on the desk, facing the camera. "
)

_BASE = _STYLE + _NOTEXT + _FRAME + _SET + _BOARD + _HOST

# WHAT IS DRAWN ON THE BOARD, PER PART, LINE BY LINE. Each line appears at the
# offset of the VO line that says it (assemble.py takes those from
# edit.offsets(), so the board and the voice cannot drift apart) and it appears
# as a HARD CUT, not a fade -- somebody is slapping letters onto felt, and a
# dissolve would make it a graphic.
#
# AN EMPTY TUPLE NEEDS NO SPECIAL CASE. The drawing loop simply has nothing to
# iterate, and the board stays as empty as the camera found it.
BOARD_TYPE = {
    "01": ("EXAMPLE COUNTY", "ONE ITEM", "$40 CASH"),
    "02": ("EXAMPLE COUNTY", "SECOND WEEK", "$40 CASH"),
    "03": ("EXAMPLE COUNTY", "RECOVERY", "$60 CASH"),
    "04": ("EXAMPLE COUNTY", "STANDING OFFER", "$200"),
    "05": ("EXAMPLE COUNTY", "INVENTORY", "NO FEE"),
    "06": (),
}

# ONE BOARD MARK IS DRAWN PER SPOKEN LINE and assemble.py has no way to say so.
# It takes `marks[:len(BOARD_TYPE[sid])]` off a list of offsets, so three lines
# of type against one line of copy draws ONE and logs "3 line(s) of type" --
# a count of what was asked for rather than of what was done. It rendered a
# whole reel that way and only a frame grab off the delivered mp4 found it.
#
# ASSERTED HERE BECAUSE THIS IS THE FILE THAT CAN SEE BOTH TABLES. script.py
# cannot import shot.py without a cycle; shot.py already imports script.
for _sid, _lines in BOARD_TYPE.items():
    _spoken = sum(1 for ln in script.LINES if ln[1] == _sid)
    assert len(_lines) <= _spoken, (
        f"segment {_sid} has {len(_lines)} line(s) of board type against "
        f"{_spoken} spoken line(s). Each mark is drawn at the offset of the "
        f"line that says it, so only the first {_spoken} would ever appear -- "
        f"and the log would report {len(_lines)}. Split the copy or cut the "
        f"board.")

# WHERE THE BOARD IS, PER SEGMENT, MEASURED. Run board_rect.py, LOOK at
# out/board_rect.png, then paste what `board_rect.py --emit` prints in here.
# Six numbers read off a contact sheet by eye are wrong by enough to push a
# line off the felt and onto the wooden frame, and it looks fine in the plate
# and wrong in the film.
#
# EMPTY UNTIL YOU HAVE MEASURED, and empty is a legal state -- the plates do
# not exist on a fresh clone. type_rect() refuses with the command to run
# rather than raising KeyError three files away. (This table did not exist at
# all: the module referenced it, and TYPE_INSET, and TYPE_INSET_L, and none of
# the three were ever defined, so show/ could not be imported.)
BOARD_RECT: dict[str, tuple[float, float, float, float]] = {}

# HOW FAR INSIDE THE MEASURED BOARD THE TYPE SITS, as a fraction of the box.
# The detector finds the SURFACE, not the USABLE AREA -- on a real reel the
# lower third of a correctly-detected board had a counter, a ledger and a mug
# in front of it. That is what TYPE_INSET_B is for and it can only be set by
# eye, off a drawn frame, not by a threshold.
TYPE_INSET = 0.06         # top, and both sides unless overridden
TYPE_INSET_L = 0.08       # the left edge; type reads better off the frame
TYPE_INSET_B = 0.06       # the bottom. RAISE IT if anything stands in front


def type_rect(sid: str) -> tuple[float, float, float, float]:
    """Where assemble.py may draw, in frame fractions. Clear of the presenter."""
    if sid not in BOARD_RECT:
        raise SystemExit(
            f"FAIL: segment {sid} has no measured board.\n"
            f"  Run `python board_rect.py`, LOOK at out/board_rect.png, then\n"
            f"  paste `python board_rect.py --emit` into BOARD_RECT in shot.py.")
    x0, y0, x1, y1 = BOARD_RECT[sid]
    w, h = x1 - x0, y1 - y0
    return (x0 + w * TYPE_INSET_L, y0 + h * TYPE_INSET,
            x1 - w * TYPE_INSET, y1 - h * TYPE_INSET_B)

# ONE ENTRY PER INTERSTITIAL, all from the same plate. `plate` names which
# beat's still this one renders from, so six parts cost one generation.
BEATS = [
    {"sid": sid,
     "what": f"interstitial {sid}",
     "prompt": _BASE}
    for sid in ("01", "02", "03", "04", "05", "06")
]

CUT = [b["sid"] for b in BEATS]
BEAT = {b["sid"]: b for b in BEATS}

PLATE_SEED: dict[str, int] = {}

# ONE PLATE, N SEGMENTS -- AS A MECHANISM RATHER THAN AS A HOPE.
#
# The header says the show is a single location shot once and reused, and that
# is the whole economic argument for having a wraparound at all. It was still
# generating one plate per segment, because gen_still.py in this tree had no
# alias branch (the one in _session_template always has) and this table did not
# exist. Six renders of the same room do not converge on the same room -- that
# is exactly what the films' shot.py says at the top and pays for twice.
#
#     PLATE_ALIAS = {s: CUT[0] for s in CUT[1:]}
#
# is the honest expression of "one plate, N segments": every segment takes the
# first one's picture, gen_still.py renders once, and nothing downstream knows.
# Left EMPTY here because the example still wants to show a per-segment roll
# and the flip below; turn it on as soon as the room is right.
PLATE_ALIAS: dict[str, str] = {}

for _dst, _src in PLATE_ALIAS.items():
    assert _dst in BEAT, f"PLATE_ALIAS aliases unknown segment {_dst!r}"
    assert _src not in PLATE_ALIAS, f"alias chain: {_dst} -> {_src} -> ..."
for _src in PLATE_ALIAS.values():
    assert _src in BEAT, f"PLATE_ALIAS points at unknown segment {_src!r}"

# A WHOLE-IMAGE MIRROR, APPLIED AFTER THE ROLL, to put the board on the same
# side in all six. 01 and 02 came back with the board on the LEFT while 03-06
# have it on the right, and a board that jumps across the frame between segments
# wrecks the one thing this reel is selling -- that it is the same set, every
# week, for six weeks.
#
# THIS IS THE SAFEST POSSIBLE USE OF THE MECHANISM. A mirror reverses text,
# which is why #6 asserts that flipped beats contain no signage, page or number.
# Here there is nothing to reverse BY CONSTRUCTION: the board is blank in every
# plate and the bounty type is drawn in post, i.e. AFTER the flip. No handed
# props, nothing read left-to-right, no geography to contradict.
#
# I TOOK THIS OUT ONCE, WRONGLY, and the way I did it is worth keeping. A coarse
# red-channel map put a big dark-teal slab on the LEFT of the flipped plates,
# which I read as "the board was already right-side, the flip broke it". It was
# not the board -- it was the SEA. Plates 01 and 02 have a darker overall
# palette (their painted water sits at R~85-91 against R~150 in 03-06), so a
# darkness threshold calibrated on the other four swept the ocean up with the
# felt. The verification sheet showed it immediately.
#
# SAME ERROR AS THE PITCH METRIC, ONE DAY APART: a fixed threshold, validated on
# some of the material, applied to all of it. When six samples differ in overall
# level, thresholds have to be found PER SAMPLE -- which is what board_rect.py
# now does, and why it draws its answer back onto the picture.
PLATE_FLIP: set[str] = {"01", "02"}


def plate_seed(sid: str) -> int:
    return PLATE_SEED.get(sid, SEED)


assert set(BOARD_TYPE) == set(CUT), "board type and beats disagree"
assert BOARD_TYPE["06"] == (), (
    "segment six's board must be empty -- it is the reason the reel has six "
    "slots instead of five")
assert all(len(v) == 3 for k, v in BOARD_TYPE.items() if k != "06"), \
    "segments 1-5 each carry three lines: where, what, how much"

# A FLIP IS ONLY SAFE WHILE THE BOARD IS EMPTY IN THE PLATE. The moment somebody
# asks the renderer for the bounty text instead of drawing it in post, every
# mirrored segment reverses its own numbers -- and it would look fine in the
# contact sheet, because a reversed board still reads as a board.
# THE CLAUSE IS NAMED ONCE AND CHECKED AGAINST ITSELF. This assert used to look
# for the literal "completely blank" while _NOTEXT said "completely bare and
# unmarked" -- so it fired on a prompt that was perfectly correct, which is the
# same fault as a typed duration next to a measured one. The phrase the plate
# actually asks for is the phrase that gets checked.
_BLANK_CLAUSE = "completely bare and unmarked"
assert _BLANK_CLAUSE in _NOTEXT, (
    "_NOTEXT no longer asks for a bare board -- the flip assert below reads "
    "this same phrase and would go green on a prompt that stopped asking")
assert not (set(PLATE_FLIP) & set(PLATE_ALIAS)), (
    f"{sorted(set(PLATE_FLIP) & set(PLATE_ALIAS))} is both aliased and "
    "flipped -- an aliased segment has no plate of its own to mirror, so the "
    "flip would silently apply to whatever it borrows")
for _sid in PLATE_FLIP:
    assert _sid in BEAT, f"PLATE_FLIP names unknown beat {_sid!r}"
    assert _BLANK_CLAUSE in BEAT[_sid]["prompt"], (
        f"beat {_sid} is flipped but no longer asks for a blank board -- a "
        "mirror reverses anything written in the plate. Either drop the flip "
        "or keep the type in post where it belongs.")

# THE BOARD TABLE IS CHECKED FOR SHAPE, NOT FOR COMPLETENESS. Completeness is
# checked by whoever is about to DRAW -- assemble.py, through type_rect() --
# because on a fresh clone there are no plates to measure and a module that
# cannot be imported until the plates exist cannot be smoke-tested at all.
for _sid, _r in BOARD_RECT.items():
    assert _sid in BEAT, f"BOARD_RECT measures unknown segment {_sid!r}"
    assert _r[0] < _r[2] and _r[1] < _r[3], f"board {_sid} rect is inside out"
    assert _r[0] > 0.40, (
        f"board {_sid} starts at x={_r[0]:.3f} -- that is left of the "
        "presenter, so the detector has found the painted sea again. Look at "
        "the verification sheet.")
