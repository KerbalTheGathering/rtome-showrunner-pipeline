"""What moves in each beat. The direction, not the description.

WHAT IS HERE IS A THREE-BEAT EXAMPLE. Replace every entry; preflight.py refuses
to render while the example survives. The COMMENTS and the shared blocks are the
rules and should outlive the rewrite.

THE MODEL CAN ALREADY SEE THE FRAME. It is handed the plate as its first frame,
so describing what is in the picture is wasted weight at best and an instruction
to REDRAW it at worst. Say what happens to it.

A PROHIBITION IS NOT A POSITION. This is the load-bearing rule of the whole
file. Naming a thing you do not want puts it in the frame's vocabulary; it does
not reliably remove it, and it spends the words that could have specified what
IS true. Every constraint below is written as three parts:

    what it is now, that it stays, and that it is still that way in the LAST
    frame.

"No second person walks out of the door"  ->  "the count of people is one, from
the first frame to the last ... he is still the only figure in the picture in
the last frame."

THE OTHER RULES, all learned the expensive way (docs/05_prompting.md):

  * Naming what a character LOOKS AT rotates them toward it.
  * Head turns drag the body. Say the shoulders stay square if they must.
  * NEVER name the camera in a travelling shot -- mentioning it at all is a
    strong pull toward moving it. Say the FRAME is locked, not that the camera
    does not move.
  * A light is never the subject of a verb. What moves is the wet surface the
    light is lying on. Naming a light source as a moving thing puts a sun in a
    flat sky.
  * OCCUPY THE AUDIO CHANNEL. Some video models are omni-modal -- picture and
    sound decode from one latent -- so undirected audio gets INVENTED, and an
    invented voice moves the mouth. Describe room tone. See docs/04_lipsync.md.

A BEAT THAT MUST BE AT SPEED ON ITS FIRST FRAME CANNOT BE WRITTEN INTO THIS
FILE. The model is conditioned on a still and spends its opening half second
climbing out of it -- measured at 0.30-0.34 of the clip's own peak across four
independent seeds, and "already at full speed in the very first frame" moved it
2.36x -> 2.01x and no further. It is a property of the conditioning, not a
wording failure, so the fix is structural and lives in edit.RUNUP: shoot the
beat longer and throw the opening away. Reach for it only on a beat cut into
mid-action; on a beat that STARTS something the ramp is what you wanted.
"""
from __future__ import annotations

import identity
import shot

# THE CONTENT BELOW IS THE TEMPLATE'S EXAMPLE, NOT YOUR FILM.
# preflight.py refuses to render while this line is here. Delete it when
# you have replaced the content -- and only then.
EXAMPLE_CONTENT = True


_HEAD = """{secs}s | 4:3 | 24fps | painted 2D illustration, gouache and ink, visible brush texture -- NOT photoreal, NOT 3D, NOT CGI, NOT anime

FIRST FRAME
The supplied first frame is the complete and final composition, palette and painting style. Do not redesign it, do not recompose it, and do not add anything that is not already in it.

STYLE LOCK
Hold the painted surface of the first frame for the whole clip: visible brush and palette-knife texture, flat layered colour, ink linework, slightly stepped tonal banding. Never resolve toward photography, never smooth into a 3D render, never add photographic depth of field, bloom, glare or lens flare.
"""

# THE FRAME, HELD. Runs in every beat of the film unchanged, for the same
# reason the style block runs in every prompt in shot.py: the thing that must
# not vary is the thing that gets restated every time.
#
# THE CAMERA IS NEVER NAMED. Mentioning it at all is a strong pull toward
# moving it, so this describes the FRAMING as a property that is conserved.
# (This block was referenced by all three example beats and never defined --
# a NameError on import, in the file that teaches the rule.)
_LOCK = """
THE FRAME
The framing is identical in the first frame and the last frame. It does not push in, does not pull back, does not drift and does not reframe at any point, and no more of the location comes into view than is already in the first frame."""

# AMBIENT BLOCKS. One per condition, shared by every beat in that condition --
# two beats in the same weather must be handed the same string, or they are not
# the same weather.
_NIGHT = """
THE NIGHT
The air is still and the grass moves only where the wind touches it. The lamp keeps its exact brightness and its exact colour. The dark beyond the headland stays dark and nothing brightens it."""

_DAWN = """
THE MORNING
The sky brightens very slowly and evenly from the horizon up. The sea below holds its flat grey and moves only in long slow swells."""

# THE AUDIO CHANNEL, OCCUPIED. Written as what the soundtrack IS, continuously,
# because a list of things it must not contain buys mumbling rather than
# silence. Verified by transcribing the returned audio -- see docs/04_lipsync.md.
_AUDIO = """
AUDIO
The soundtrack of this clip is one continuous quiet room tone and nothing else, at the same steady level from the first frame to the last: wind over grass, the small sounds of the building, and still air. That flat ambience is the entire soundtrack and it never stops, never changes and is never interrupted. No voice, no dialogue, no whispering, no muttering, no singing and no music at any point."""

MOTION: dict[str, str] = {

    # EXAMPLE CONTENT -- replace all of it.
    #
    # `secs` is filled in from edit.py so the direction and the timeline cannot
    # disagree about how long the beat is.
    "01": _HEAD.format(secs="10.0") + _LOCK + _NIGHT + """
BEATS
0-4s       The keeper walks steadily away from the camera up the slope, his lantern swinging a little at his side. The grass moves around his boots.
4-8s       He keeps walking at the same pace and does not turn. He is smaller in the frame and still walking away.
8-10s      He is still walking away up the slope in the last frame.

THE COUNT OF PEOPLE IS ONE
There is exactly one person in this picture and it is the keeper already on the slope in the first frame. He is the only figure in the frame at every moment of the clip, and he is still the only figure in the picture in the last frame.

THE LAMP ROOM STAYS DARK
The lamp room at the top of the tower is unlit and black in the first frame, it stays unlit and black for the whole clip, and it is still unlit and black in the last frame.""",

    "02": _HEAD.format(secs="9.0") + _LOCK + _NIGHT + """
BEATS
0-3s       The keeper stands at the rail with his hand on it, looking at the lens. Nothing else in the room moves.
3-7s       He takes his hand off the rail and lets it fall to his side. His shoulders stay square to the lens and his feet do not move.
7-9s       He is still standing in the same place with his hand at his side in the last frame.

THE LENS KEEPS ITS POSITION
The great lens stands exactly where it is in the first frame, at the same angle, and it does not rotate, tilt or move at any point. It is in the same position in the last frame.""",

    "03": _HEAD.format(secs="11.0") + _LOCK + _DAWN + """
BEATS
0-4s       The keeper walks down the slope away from the tower, side-on to the camera, unhurried.
4-9s       He continues down at the same pace, crossing the frame from right to left, getting no closer to the camera.
9-11s      He is still walking down and to the left in the last frame.

THE LAMP STAYS LIT
The lamp at the top of the tower is lit in the first frame, it holds exactly that brightness and colour for the whole clip, and it is still lit in the last frame.""",
}


# --------------------------------------------------------------------------
# THE MOUTH, UNDER NARRATION -- AND WHY THE "BOTH OF THEM" CLAUSE IS GONE.
#
# It was appended to beat 04 because that shot once had TWO people in it and the
# clause protecting the man left the woman behind the table talking through the
# whole of the narration. Correct diagnosis, and the rule it was written for
# still stands: an instruction that names a person protects that person only.
#
# BUT THE PLATE CHANGED UNDER IT. The take that fixed the woman removed her, and
# the shot has been one man since; the clause was never revisited. So beat 04
# spent its last render carrying "Both of them keep their mouths closed" over a
# picture containing one person -- a sentence that ASSERTS a second person into a
# frame this file elsewhere works hard to keep at one. He then talked anyway,
# because three prohibitions ("does not speak", "his mouth stays closed", "both
# of them ... neither of them speaks") are still three ways of telling a face to
# do nothing, and an unoccupied face fills itself.
#
# Replaced in the beat itself by an EXPRESSION the closed mouth is part of, which
# is the only thing that has ever worked on this failure. Nothing is appended
# here any more: a clause bolted on after the fact is a clause nobody re-reads
# when the shot it was written for stops existing.


# --------------------------------------------------------------------------
# WHICH FILM THIS TABLE IS FOR.
#
# Session #2's motion.py was copied into four other trees when they were
# scaffolded and never replaced. Because every session numbers its beats 01-15,
# `MOTION[sid]` resolved cleanly for all fifteen -- so no lookup failed, no
# count came out wrong, and every check in the pipeline passed while Session #6
# was bought for $3.88 against a film about a dead citrus grove.
#
# A KEY THAT EXISTS IN EVERY SESSION IS NOT AN IDENTIFIER.
SESSION = identity.NAME   # NOT typed -- a stale copy of this cost a false "buy longer clips"

assert SESSION == shot.NAME, (
    f"motion.py is Session {SESSION!r}'s table but shot.py is {shot.NAME!r} -- "
    "this file has been copied into the wrong session's tree. Every session "
    "numbers its beats 01-15, so nothing else in the pipeline can tell the "
    "difference, and the clips come back describing the wrong film.")

assert set(MOTION) == set(shot.CUT), (
    f"motion covers {sorted(set(MOTION) ^ set(shot.CUT))} differently from the "
    "cut -- every beat that is shot needs direction and only beats that are "
    "shot should have any")
