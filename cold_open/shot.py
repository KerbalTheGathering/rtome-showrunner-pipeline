"""The cold open's plates. Three wordless shots and the season title.

WHAT IS HERE IS AN EXAMPLE. The comments are the rules.

IT IS A PLACE, NOT A PERSON. The cold open exists to say what you are watching
before anybody speaks, and the cheapest way to get that wrong is to put the
protagonist in it -- at which point it is a scene, and the film has started
without its title. identity.py sets CHAR_LORA to "" on purpose.

NO LETTERING IN THE PLATE. The title is drawn at bake resolution in
assemble.py, over moving picture rather than over a frozen frame -- see its
docstring for why the obvious build reads as a still.
"""
from __future__ import annotations

import identity

# THE CONTENT BELOW IS THE TEMPLATE'S EXAMPLE, NOT YOUR FILM.
# preflight.py refuses to render while this line is here. Delete it when
# you have replaced the content -- and only then.
EXAMPLE_CONTENT = True


# IDENTITY IS IMPORTED, NEVER TYPED -- see identity.py.
NAME = identity.NAME

SESSION_NO = identity.SESSION_NO
TITLE = identity.TITLE            # the SEASON's title, not a local string
SLUG = identity.SLUG

SEED = identity.SEED

LATENT = identity.LATENT     # x2 VAE -> 2432x1664, same as every session

STYLE_LORA, STYLE_W = identity.STYLE_LORA, identity.STYLE_W

# NO CHARACTER LORA, AND IT IS THE REASON THE BOAT WOULD NOT GO AWAY.
#
# Beat 02 wants two silhouettes on a distant skiff. Asked for that with the
# a character LoRA at 0.9 it came back a medium two-shot TWICE, from two different
# angles -- the prompt was not the problem, the loader was. A character LoRA
# trained on portraits enforces a MINIMUM SUBJECT SCALE: it cannot render the
# thing it knows at thumbnail size, so it moves the camera instead.
#
# Nothing here needs it. Two of the three plates contain no people at all and
# the third wants shapes, not a face. gen_still.py omits the node entirely when
# this is None rather than running it at strength 0, so the VRAM goes too.
CHAR_LORA, CHAR_W = identity.CHAR_LORA or None, identity.CHAR_W

OBJ_NAME = NAME + "_obj"
OBJ = ""


def obj_prompt(_p: str) -> str:
    raise SystemExit("INTRO has no objective layer")


# The season's block, byte-identical to the films'. See the header.
_STYLE = (
    "Painted illustration in flat gouache and ink on textured paper, confident "
    "dark linework, visible brush marks. "
)

# A POSITIVE INVENTORY OF THE SURFACE, not a ban on text. See docs/02_traps.md:
# asking for "no lettering" is how lettering arrives.
_NOTEXT = "Every surface in the frame is plain, weathered and unmarked. "

_DAWN = (
    "First light. The sky is pale and low, brighter than the water, and "
    "nothing in the frame casts a hard shadow. "
)

_WATER = (
    "Flat open water running to a low horizon, grey-green and almost still. "
)

# EXAMPLE CONTENT -- replace all of it. Three shots is enough: somewhere, a
# detail of that somewhere, and a wider one to put the title over.
BEATS = [
    {
        "sid": "01",
        "what": "the water, before anything happens",
        "prompt": _STYLE + _NOTEXT + _DAWN + _WATER +
                  "A wide shot low to the surface, no land in sight.",
    },
    {
        "sid": "02",
        "what": "one made thing, and nobody near it",
        # NO SIDE IS NAMED. The example used to read "at the left of the
        # frame", which the assert at the bottom of this file forbids and
        # which is the exact thing that produced mirrored takes. Placement
        # that matters is fixed with PLATE_FLIP after the roll.
        "prompt": _STYLE + _NOTEXT + _DAWN + _WATER +
                  "A single weathered timber piling standing alone in the "
                  "shallows, a rusted cleat bolted to its top.",
    },
    {
        "sid": "03",
        "what": "the wide one the title comes up over",
        "prompt": _STYLE + _NOTEXT + _DAWN + _WATER +
                  "A wide shot of the open water with a low dark shoreline "
                  "along the far horizon and a great deal of pale sky above.",
    },
]

CUT = [b["sid"] for b in BEATS]
BEAT = {b["sid"]: b for b in BEATS}

# HOW LONG EACH SHOT RUNS, TYPED, BECAUSE THERE IS NO VOICE TO DERIVE IT FROM.
# This is the cold open's whole difference from a film tree: every other tree
# in the season sizes its clips off measured VO and refuses to guess, and there
# is nothing here to measure. See edit.py's docstring for why these three
# numbers are what they are -- it is the file that reads them, and the reasons
# are editorial, not mechanical.
#
# IT LIVES HERE AND NOT IN edit.py because edit.py derives FRAMES, SECS and
# TOKENS from it and a derived table must not also be the source. It was
# missing outright: edit.py imported shot.SECS, the assert below named it, and
# nothing in the tree could be imported at all.
SECS = {
    "01": 9.0,        # long enough to stop being a title background
    "02": 10.0,       # the longest; the only one with a made thing in it
    "03": 7.0,        # a beat too short on purpose -- the water closes
}

PLATE_SEED: dict[str, int] = {}
PLATE_FLIP: set[str] = set()

# TWO SHOTS THAT MUST MATCH NEED ONE PLATE, NOT TWO PROMPTS. Empty here -- the
# cold open's three shots are three different places on purpose -- but the
# mechanism exists in every tree now, so a cold open that opens and closes on
# the same water can say so instead of rolling it twice.
PLATE_ALIAS: dict[str, str] = {}

for _dst, _src in PLATE_ALIAS.items():
    assert _dst in BEAT, f"PLATE_ALIAS aliases unknown beat {_dst!r}"
    assert _src not in PLATE_ALIAS, f"alias chain: {_dst} -> {_src} -> ..."
for _src in PLATE_ALIAS.values():
    assert _src in BEAT, f"PLATE_ALIAS points at unknown beat {_src!r}"


def plate_seed(sid: str) -> int:
    return PLATE_SEED.get(sid, SEED)


# THE CAMERA LOOKS NORTH: shore on the RIGHT, Gulf and sun on the LEFT. The
# user's rule for the whole season -- the Gulf is west of this entire coast, so
# a camera facing north has the water on its left and there is no other
# arrangement that is true. Nothing here states a side, so nothing here can
# contradict it; if a plate comes back with the land on the left, flip it rather
# than writing LEFT into the prompt.
assert set(SECS) == set(CUT), "SECS and BEATS disagree"
for _b in BEATS:
    for _w in (" left", " right", "left-hand", "right-hand"):
        assert _w not in _b["prompt"].lower(), (
            f"beat {_b['sid']} names a side -- that is what produced #6's "
            "mirrored takes. Use PLATE_FLIP after the roll instead.")
