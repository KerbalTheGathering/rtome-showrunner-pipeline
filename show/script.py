"""What the host says in each interstitial. Replace all of it.

WHAT IS HERE IS A SIX-PART EXAMPLE, invented for the template, one interstitial
in front of each film. preflight.py refuses to render while it survives.

THE SHOW IS SHOT IN ONE TAKE OF A SINGLE LOCATION and everything that changes
between parts is words and drawn type. That is what makes it cheap enough to run
six times, and it is why the plate deliberately leaves the surface the type goes
on BLANK -- see shot.py.

THE HOST DOES NOT KNOW ABOUT THE FILMS. He announces; the films answer. A
presenter who comments on the outcome collapses the joke into one voice.

AND THE LAST ONE IS DIFFERENT. Whatever pattern the first five establish, spend
the sixth breaking it -- that is the slot the whole structure is paying for.

ON NAMES: invent them, and check that what you invented is not somebody. A name
that sounds regionally right is exactly the kind that belongs to a real person
in that region. See docs/01_process.md on claims.

    python script.py
"""
from __future__ import annotations

import identity

# THE CONTENT BELOW IS THE TEMPLATE'S EXAMPLE, NOT YOUR FILM.
# preflight.py refuses to render while this line is here. Delete it when
# you have replaced the content -- and only then.
EXAMPLE_CONTENT = True


HOST_BRIEF = "the presenter, in one line, for casting"

# WHO CAN SPEAK, from identity.py, so a clone cannot inherit the previous
# show's voice. A line names a ROLE out of this table, never an id.
VOICES = identity.VOICES
HOST = "host"                # the role, not the id -- see voice_of() below


def voice_of(role: str) -> str:
    """The ElevenLabs id for a role. Refuses rather than returning nothing.

    EVERY LOOKUP GOES THROUGH HERE so a role that does not exist fails in one
    place with a sentence, rather than as an empty string that reaches the API
    and bills for a 400.
    """
    if role not in VOICES:
        raise SystemExit(
            f"FAIL: script.py gives a line to {role!r}, which identity.VOICES "
            f"does not have.\n  It knows: {sorted(VOICES)}")
    return VOICES[role]


def speakers(sid: str) -> list[str]:
    """Which roles speak in a segment, in the order they speak.

    ONE ON-CAMERA SPEAKER IS A LIMIT OF THE LIP SYNC, NOT OF THIS FUNCTION --
    a second role can speak off camera today. See docs/04_lipsync.md.
    """
    out = []
    for _lid, _sid, role, _style, _text in LINES:
        if _sid == sid and role not in out:
            out.append(role)
    return out


STABILITY = 0.5              # v3 accepts 0.0/0.5/1.0 only; 0.5 stops it wandering

# (id, part sid, ROLE, style, text)
#
# EXAMPLE CONTENT -- replace all of it.
# THREE LINES PER SEGMENT, ONE PER LINE OF BOARD TYPE -- where, what, how much.
# That is not decoration: assemble.py lands each board mark on the offset of
# the VO line that says it, so a board line with no line of copy under it is
# never drawn. shot.py asserts the relationship, because it is the file that
# can see both tables. The example used to run one line per segment against a
# three-line board, which is exactly the fault, shipped as the worked example.
LINES = [
    ("01a", "01", HOST, 0.50,
     "[brightly] Good morning. Example County again this week."),
    ("01b", "01", HOST, 0.50,
     "One item on the board, and it is not a difficult one."),
    ("01c", "01", HOST, 0.50,
     "Forty dollars cash, on delivery."),

    ("02a", "02", HOST, 0.50,
     "[cheerful] Example County, and this one you have seen before."),
    ("02b", "02", HOST, 0.50,
     "Second week running, which tells you something."),
    ("02c", "02", HOST, 0.50,
     "Still forty dollars."),

    ("03a", "03", HOST, 0.45,
     "[conspiratorial] Example County. Now this one you will want to write "
     "down."),
    ("03b", "03", HOST, 0.45,
     "A recovery, and they are not fussy about how."),
    ("03c", "03", HOST, 0.45,
     "Sixty dollars."),

    ("04a", "04", HOST, 0.55,
     "[excited] Example County, and I have been waiting to read this one "
     "out."),
    ("04b", "04", HOST, 0.55,
     "A standing offer, open until somebody takes it."),
    ("04c", "04", HOST, 0.55,
     "Two hundred dollars. Biggest number on this board all year."),

    ("05a", "05", HOST, 0.40,
     "[dry] Example County, one more time."),
    ("05b", "05", HOST, 0.40,
     "An inventory this week, rather than a job."),
    ("05c", "05", HOST, 0.40,
     "No fee. They are asking all the same."),

    ("06", "06", HOST, 0.40,
     "[flat] Well. Nothing this week."),
]

BY_ID = {ln[0]: ln for ln in LINES}
SIDS = ["01", "02", "03", "04", "05", "06"]

# WHICH SEGMENTS KEEP THE FORMAT, AND WHICH ONE BREAKS IT.
#
# "the last one is different" used to be written as `sid == "06"` in edit.py,
# as `k != "06"` in shot.py, as `SIDS[:5]` in make_vo.py and as `rows[5]` in
# edit.main(). Four files each holding their own copy of one editorial fact,
# and every one of them silently means something else in a reel that is not
# six segments long -- `rows[5]` is an IndexError on a three-segment reel and
# `sid == "06"` is simply never true.
#
# WHICH SEGMENTS ARE THE FORMAT IS A FACT ABOUT THE WRITING, so it is stated
# once here, where the writing is, and edit.py, shot.py, motion.py and
# make_vo.py all read it. Everything not in FORMAT_SIDS is the break.
FORMAT_SIDS = ["01", "02", "03", "04", "05"]
BREAK_SIDS = [s for s in SIDS if s not in FORMAT_SIDS]

assert set(FORMAT_SIDS) <= set(SIDS), \
    f"FORMAT_SIDS names segments that do not exist: {set(FORMAT_SIDS) - set(SIDS)}"
assert BREAK_SIDS, (
    "every segment keeps the format, so nothing breaks it -- that slot is the "
    "structural event the whole reel is paying for. See the docstring.")

assert len(BY_ID) == len(LINES), "duplicate line id"

# EVERY ROLE A LINE NAMES EXISTS, CHECKED ON IMPORT.
for _lid, _sid, _role, _st, _t in LINES:
    assert _role in VOICES, (
        f"line {_lid} is spoken by {_role!r}, which identity.VOICES does not "
        f"have. It knows: {sorted(VOICES)}")
assert [ln[1] for ln in LINES] == sorted(ln[1] for ln in LINES), \
    "lines are out of segment order -- the reel plays in this order"
assert set(ln[1] for ln in LINES) == set(SIDS), "a segment has no copy"

assert all(t.count("[") <= 1 for *_, t in LINES), \
    "a line carries more than one tag -- each one costs 0.4-0.6s of runtime"

_tags = [t[t.index("[") + 1:t.index("]")] for *_, t in LINES if "[" in t]
for _t in set(_tags):
    _share = _tags.count(_t) / len(_tags)
    assert _share < 0.40, (
        f"tag [{_t}] is {_share:.0%} of the script -- that is a habit, not a "
        "choice, and repeated contour is what monotone actually sounds like")

# Proven-safe on eleven_v3: interpreted as direction, never spoken aloud.
# [serious] and [laughing] are PROVEN SPOKEN and must never appear here.
_SAFE = {"flat", "dry", "thoughtful", "warmly", "amused", "awed",
         "conspiratorial", "firmly", "excited", "cheerful", "delighted",
         "brightly"}
assert set(_tags) <= _SAFE, f"unverified tag: {set(_tags) - _SAFE}"

# --------------------------------------------------------------------------
# THE SHOW DOES NOT KNOW ABOUT THE SEASON, AND THAT IS LOAD-BEARING.
#
# The moment it names the protagonist or their world it stops being separate and
# starts being a narrator -- and a narrator that knows how each job turns out
# cannot deliver these numbers straight. It also must not refer to a previous
# week, because six segments that acknowledge each other become a subplot, and
# the only structural event in this reel is the sixth board being empty.
_ALL = " ".join(t.lower() for *_, t in LINES)
# THE SHOW DOES NOT NAME THE FILMS' WORLD. It announces; the films answer. The
# moment it names the protagonist, the vehicle or the animal it stops being a
# separate broadcast and becomes narration. List the words your show must not
# contain and assert their absence -- an intention in a comment gets edited away.
_FORBIDDEN: tuple[str, ...] = ()
for _w in _FORBIDDEN:
    assert _w not in _ALL, f"the show names {_w!r}; it is not supposed to know"


# A WORD THAT IS ALLOWED EXACTLY ONCE gets counted rather than banned. This
# slot held `assert _ALL.count("bird") == 1` -- true of the reel this example
# was lifted from and false of the example itself, so show/script.py could not
# be imported and neither could the eighteen modules downstream of it. A
# constraint copied out of another season is not a constraint, it is a fault
# that happens to be spelled like one.
#
#     assert _ALL.count("<the word>") == 1, "<why once and no more>"

# ASSERT THE CONSTRAINT, DO NOT COMMENT IT. If a name, a place or a claim in
# this show must not appear -- because it belongs to somebody real -- write the
# check here rather than a note. A comment is a hope; an assert is a build
# failure, and it survives an editor who never knew the constraint existed.
#
# Example, from the season this came from: an invented presenter's name was one
# word away from a real broadcaster's, so the script asserted the real name was
# absent and the invented one present.
#
#     assert "<the real name>" not in _ALL, "that is a real person"
#     assert "<the invented name>" in _ALL, "the presenter introduces himself"

# NO TITLE IS EVER SPOKEN -- the user's call. Titles are drawn type only.
# NOR THE FILMS' TITLES. The show introduces a number, not a story.
_TITLES: tuple[str, ...] = ()
for _t in _TITLES:
    assert _t not in _ALL, f"the show says {_t!r}, which is a film's title"


# THE NUMBERS ARE THE SPINE and each has to actually be said in its own
# segment. Keyed off SIDS rather than typed as a run of literals, so a segment
# that stops existing takes its entry with it instead of asserting about a
# neighbour. EXAMPLE CONTENT -- these are the example's own numbers, and they
# match the board in shot.py because a board and a voice that disagree about a
# figure is the one mistake this reel cannot survive.
SPINE = {
    "01": "forty dollars",
    "02": "forty dollars",
    "03": "sixty dollars",
    "04": "two hundred dollars",
    "05": "no fee",
}

_BY_SID: dict[str, str] = {}
for _, _sid, _, _, _t in LINES:
    _BY_SID[_sid] = _BY_SID.get(_sid, "") + " " + _t.lower()
for _sid, _n in SPINE.items():
    assert _sid in _BY_SID, f"SPINE names segment {_sid!r}, which has no copy"
    assert _n in _BY_SID[_sid], f"segment {_sid} never says {_n!r}"
assert not set(SPINE) & set(BREAK_SIDS), (
    f"SPINE gives {sorted(set(SPINE) & set(BREAK_SIDS))} a number, but that is "
    "the segment with nothing to announce")

# AND THE BREAK SEGMENT HAS NO NUMBER AT ALL. This is the one that matters, and
# it is found through BREAK_SIDS rather than by naming "06" -- the reel is not
# always six long and the break is not always last.
for _sid in BREAK_SIDS:
    for _w in ("dollar", "county", "paying", "pays", "cash", "job", "bounty",
               "hundred", "twelve", "forty", "sixty"):
        assert _w not in _BY_SID[_sid], (
            f"segment {_sid} says {_w!r} -- it has nothing to announce, and "
            "that emptiness is the reason the slot exists")
