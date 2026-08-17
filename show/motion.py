"""What moves in each segment. Written after the plates existed, against them.

THE HARD PART HERE IS THAT ALMOST NOTHING SHOULD MOVE. This is a locked-off
studio camera on a man behind a desk, six times, and the whole value of the reel
is that it is unmistakably the same shot every week. Any camera drift, any
change of light, any wander in the set and it stops being a format and becomes
six similar scenes.

THE BOARD MUST STAY EMPTY FOR THE FULL RUNTIME, and this is the one that could
actually break the film. The bounty type is drawn over that felt in post; if H3
paints anything onto it -- a smudge that wants to be a letter, a chart, a
reflection that reads as writing -- the drawn type lands on top of somebody
else's marks. It is stated as a POSITIVE PROPERTY OF A SURFACE ("an unbroken
sheet of felt... the same flat colour from edge to edge") rather than as a ban
on writing, because naming writing is how writing arrives. Every session in this
season has paid for that lesson at least once.

HE TALKS THE WHOLE TIME AND THAT IS ALL HE DOES. H3 is generating from a first
frame with the gesture already in it, so the gesture does not need to be
performed from scratch -- it needs to be SUSTAINED. Each prompt says what the
hands are already doing and that they stay doing it, which is the "describe what
is conserved" rule pointed at a pose rather than at a landscape.

SEGMENT SIX IS THE ONE WITH NO WORDS UNDER MOST OF IT. Seven of its thirteen
seconds are silence, so the picture has to hold on a man not talking without
looking like a freeze frame. He gets breathing, a blink, one small shift -- and
explicitly no new business, because a model handed seven seconds of nothing will
invent something to fill them and what it invents will be a gesture that means
something.
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import direction                                                    # noqa: E402

import identity

import shot

# THE CONTENT BELOW IS THE TEMPLATE'S EXAMPLE, NOT YOUR FILM.
# preflight.py refuses to render while this line is here. Delete it when
# you have replaced the content -- and only then.
EXAMPLE_CONTENT = True


# THE SET IS THE FORMAT. Runs in all six, unchanged, for the same reason the
# style block runs in every beat of a session: the thing that must not vary is
# the thing that gets restated every time.
_STUDIO = (
    "Locked-off television studio camera, bolted to its tripod and completely "
    "static: it holds one fixed field of view for the whole segment, at the "
    "same distance and the same angle, and the four edges of the frame fall "
    "across exactly the same parts of the studio at the end as at the start. "
    "The flat even studio lighting stays exactly as bright and as even as it is "
    "in the first frame, and it is that same brightness and evenness in the "
    "last frame. The painted cloth backdrop behind him hangs still. "
)
# The count of people is stated ONCE, in _BODY. It used to be here as well
# ("He is the only person in the picture... and nobody else comes into the
# shot") and in _BODY, which is the same fact in two blocks free to disagree --
# the shape this repo refuses everywhere else.

# THE BOARD. Positive description of an intact surface -- see the header.
_BOARD = (
    "The big display board beside him stands exactly where it is on its easel, "
    "at the same angle, and it holds that exact position and angle for the "
    "whole shot. Its face stays one unbroken sheet of plain dark turquoise "
    "felt for the entire shot, the same flat colour from edge to edge and from "
    "the first frame to the last, an uninterrupted field of felt with the pale "
    "wooden frame around it unchanged. "
)

# The desk, for the same reason it is described in the plate: an empty surface
# that is not asserted gets furnished.
_DESK = (
    "The desktop in front of him stays one unbroken sheet of plain pale yellow "
    "laminate, bare and clear from edge to edge, for the whole shot. "
)

_HOLD = _STUDIO + _BOARD + _DESK

# ONE DIRECTION, REUSED BY EVERY PART. The show is the same shot six times;
# what differs is the words and the drawn type, not the movement.
#
# THE BOARD CLAUSE IS THE PART THAT COULD BREAK THE FILM, so _HOLD leads every
# segment. It did not: _STUDIO, _BOARD and _DESK were all written, concatenated
# into _HOLD -- and _HOLD was then never used. The assert at the bottom of this
# file looks for a phrase that lives in _BOARD, so it failed on import, in the
# one place a missing board clause could still be caught cheaply.
_BODY = """
BEATS
0-3s       The presenter settles, both hands resting on the desk, looking straight down the lens.
3-10s      He talks to camera with small natural movements of the head and hands, staying seated and square to the desk.
10-15s     He is still seated in the same place, hands still on the desk, in the last frame.

THE BOARD KEEPS ITS BARE SURFACE
The felt board on the easel is one clean unbroken sheet in the first frame, it stays that same clean unbroken sheet for every frame of the clip, and it is still one clean unbroken sheet in the last frame.

THE COUNT OF PEOPLE IS ONE
There is exactly one person in this picture and it is the presenter already seated in the first frame. He is the only figure in the frame at every moment, and he is still the only figure in the last frame.

THE FRAME IS LOCKED
The framing is identical in the first and last frame. It holds one fixed field of view for every frame of the segment, at the same distance and the same angle, and the edges of the frame fall in exactly the same places at the end as at the start.
"""

MOTION = {sid: _HOLD + _BODY for sid in shot.CUT}

SESSION = identity.NAME

assert SESSION == shot.NAME, (
    f"motion.py is {SESSION!r}'s table but shot.py is {shot.NAME!r} -- this "
    "file has been copied into the wrong tree")

assert set(MOTION) == set(shot.CUT), \
    f"motion/segment mismatch: {set(MOTION) ^ set(shot.CUT)}"

# THE BOARD CLAUSE IS NOT OPTIONAL IN ANY SEGMENT. The type is drawn over that
# felt in post; a segment that lets H3 decorate it has nowhere to put the
# bounty. Cheaper to assert than to notice at the mix.
for _sid, _p in MOTION.items():
    assert "unbroken sheet of plain dark turquoise felt" in _p, (
        f"segment {_sid} does not hold the board empty")

# And no segment may ASK for writing, which is how writing arrives.
for _sid, _p in MOTION.items():
    for _w in ("writes", "writing", "written", "letter", "word", "number",
               "chalk", "marker", "sign"):
        assert _w not in _p.lower(), (
            f"segment {_sid} mentions {_w!r} -- the board is filled in post, "
            "and naming writing is how the model paints some")

# A PROHIBITION IS NOT A POSITION, ENFORCED. This file's own docstring makes
# the argument better than most -- the board is "stated as a POSITIVE PROPERTY
# OF A SURFACE rather than as a ban on writing, because naming writing is how
# writing arrives" -- and then _STUDIO spent four clauses on what the camera
# does NOT do and _BODY's frame lock four more. The rule was understood
# perfectly and applied to one surface out of the shot. See ../direction.py.
direction.check(MOTION, what="segment")
