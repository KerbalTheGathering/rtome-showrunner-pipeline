"""What moves in the cold open. A few wordless shots, half a minute, no event.

WHAT IS HERE IS AN EXAMPLE. The comments and the asserts are the rules.

NOTHING HERE IS ALLOWED TO BECOME AN EVENT. A cold open with no dialogue is
carried entirely by the picture staying still enough to be looked at, and the
failure mode is a model handed ten seconds of water deciding to fill them --
with weather, with a bird arriving, with the camera drifting somewhere more
interesting. Every prompt below is mostly a list of things that stay true.

THE LIGHT IS THE ONE THING THAT MUST NOT MOVE. If the shots are meant to cut
together as one continuous minute, every one of them has to defend the medium
and the hour. A clip that was correct in every particular asked for turned into
bright daylight by five seconds, because nothing in the prompt defended it. So
the hold block runs on ALL of them, not only the ones with travel in them.

A SUN, A LAMP OR A MOON IS EXACTLY THE SORT OF THING A VIDEO MODEL LIKES TO
RAISE. If one is in frame, pin it: it stays where it is and stays the size it
is. Never make a light source the subject of a verb -- what moves is the surface
the light is lying on.
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


# THE SHARED HOLD. "A place doing nothing" is a harder thing to ask for than it
# sounds. The direction says what CONTINUES, at length, and says it is still
# true in the last frame -- a prohibition is not a position (docs/05_prompting).
_HOLD = """
THE FRAME IS LOCKED
The framing is identical in the first and last frame. The camera is bolted down on a tripod and holds one fixed field of view for the whole clip, at the same distance, the same height and the same angle, and the four edges of the frame fall across exactly the same parts of the location at the end as at the start.

THE LIGHT IS THE SAME AT THE END AS AT THE START
The hour, the colour and the direction of the light are exactly as they are in the first frame for every frame of the clip, and they are exactly the same in the last frame. The sun holds the position it has and holds the size it has, and it is in that same position at that same size in the last frame.
"""

# THE PLACE, STATED AS WHAT IT HOLDS. This block used to read "There are no
# people, no boats and no animals..." -- which is the exact example
# docs/05_prompting.md uses for the trap ("'No boats' does not remove boats"),
# sitting in the tree that is copied into every new season. The count is a
# positive property and reads as one now.
_EMPTY = """
THE PLACE KEEPS EXACTLY WHAT IT HAS
Everything in this picture is already in the first frame: the water, the light and the built things standing in it, and that is the complete list for every frame of the clip. The count of people in the frame is zero from the first frame to the last, the count of boats is zero, the count of animals is zero, and all three counts are still zero in the last frame. The four edges of the frame stay closed for the whole clip.
"""

# THE AUDIO CHANNEL, OCCUPIED. An omni-modal model invents a soundtrack when you
# do not describe one, and an invented soundtrack in a wordless cold open is the
# one thing it cannot have. See docs/04_lipsync.md.
_AUDIO = """
AUDIO
The soundtrack of this clip is one continuous quiet ambience, at the same steady level from the first frame to the last: moving water and distant air, and that pair is the complete contents of the audio track. That flat ambience is the whole of the soundtrack, it runs unbroken for the entire length of the clip, and it is the only thing on the track in the last frame as in the first.
"""

MOTION = {
    # EXAMPLE CONTENT -- replace it.
    "01": _HOLD + _EMPTY + _AUDIO + """
BEATS
0-10s      The water moves in long slow swells across the whole frame and the small surface texture travels with them.
""",
    "02": _HOLD + _EMPTY + _AUDIO + """
BEATS
0-10s      Small waves break against the base of the piling and run back down it. The piling itself stands rigid and vertical in the first frame and is still rigid and vertical in the last.
""",
    "03": _HOLD + _EMPTY + _AUDIO + """
BEATS
0-12s      The water moves in long slow swells. The far shoreline holds its exact shape, its exact darkness and its exact distance from the camera for the whole clip.
""",
}

SESSION = identity.NAME

assert SESSION == shot.NAME, (
    f"motion.py is {SESSION!r}'s table but shot.py is {shot.NAME!r}")
assert set(MOTION) == set(shot.CUT), \
    f"motion/beat mismatch: {set(MOTION) ^ set(shot.CUT)}"

# EVERY BEAT SAYS WHAT ITS LIGHT DOES, AND THIS NO LONGER ASSUMES THE ANSWER IS
# "NOTHING".
#
# It read `assert "The sun stays where it is" in _p`. That is a sentence out of
# ONE season's outdoor cold open, and it was the guard for every cold open the
# template will ever produce. A fork whose cold open was an interior -- a stone
# hall, no sun in it anywhere -- had two options: carry a sentence pinning a
# light source that is not in the frame, which pins nothing while still passing,
# or DELETE THE GUARD. The docs tell you to keep the asserts. This one made
# that impossible to do honestly.
#
# It also could not express a cold open where the light is MEANT to change. The
# same fork wanted a bulb to come up, deliberately, as the whole content of the
# shot, and the only way to have it was to remove the check.
#
# So the guard now verifies the thing that actually matters -- that the beat
# DECLARED something about its light, either way -- and leaves the answer to
# the film. What it is defending against is an UNDIRECTED light, which is what
# an omni-modal model fills in for itself: on the fork that found this, an
# undirected hall lit its own arches like strip lighting over five seconds and
# every check in the tree passed.
for _sid, _p in MOTION.items():
    assert "THE LIGHT" in _p, (
        f"beat {_sid} says nothing about what its light does. Say it holds or "
        f"say it changes, but say it -- an undirected light gets invented.")

# NOBODY SPEAKS IN THE COLD OPEN. If a mouth moves here, the cut to the first
# interstitial stops being the first voice in the feature, which is the whole
# shape of the thing.
#
# NOTE WHAT THIS CHECK IS AND IS NOT. It asks whether the PROMPT names speech,
# because naming it is how it arrives -- it is a guard on the words, not on the
# clip, and the clip still has to be listened to. That is also why it reads as
# a list of forbidden words while direction.check() below refuses forbidden
# words in the prompt: one is a rule about what the text may MENTION, the other
# a rule about how the text may PHRASE what it wants.
for _sid, _p in MOTION.items():
    for _w in ("speak", "says", "talking", "mouth moves", "lips"):
        assert _w not in _p.lower(), f"beat {_sid} has somebody speaking"

# A PROHIBITION IS NOT A POSITION, ENFORCED. This tree is where the rule was
# most broken: `_HOLD` opened with six ("No push in, no pull back, no drift, no
# handheld tremor, no reframing, no zoom") and `_EMPTY` was three more of the
# exact phrasing docs/05_prompting.md uses as its worked example of the trap --
# in the folder that is copied verbatim into every new season. Fault 3 in
# learnings.md fixed this file's LIGHT guard and left its prompts alone.
direction.check(MOTION)
