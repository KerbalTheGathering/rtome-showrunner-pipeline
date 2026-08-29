"""The words, and who says them. Replace all of this; keep the rules.

WHAT IS HERE IS A THREE-BEAT EXAMPLE, invented for the template so you can see
the shape of a filled-in film. It is not anybody's script. Replace `LINES`
wholesale — `preflight.py` refuses to render while the example is still in
place.

THE RULES AROUND IT ARE NOT AN EXAMPLE. The asserts at the bottom encode things
that went wrong on real films, and they should survive your rewrite.

WRITE THE SCRIPT BEFORE THE PICTURE EXISTS, AND THEN CHECK IT AGAINST THE
PICTURE. Every duration in the film is derived from the MEASURED length of these
lines (see docs/01_process.md), so this file comes first — but a line that
asserts a number, a colour or a position is a claim about a plate that does not
exist yet. Re-read those lines against the rendered frame at full size. Changing
words is free; re-rolling a plate to match a number is not.

ONE TAG PER LINE, MAXIMUM. Each costs 0.4–0.6 s of runtime on eleven_v3, and a
tag that appears in more than about a third of the script is a habit rather than
a choice — repeated contour is what monotone actually sounds like.

    python script.py        # print the script with its tags and line ids
"""
from __future__ import annotations

import identity

# THE CONTENT BELOW IS THE TEMPLATE'S EXAMPLE, NOT YOUR FILM.
# preflight.py refuses to render while this line is here. Delete it when
# you have replaced the content -- and only then.
EXAMPLE_CONTENT = True


# WHO CAN SPEAK. From identity.py, so a clone cannot end up narrated by the
# previous film's voice. A line names a ROLE out of this table, never an id --
# see identity.VOICES for why.
VOICES = identity.VOICES
# `None` WHEN NOBODY IS CAST, NOT StopIteration. On a film with no voices at
# all -- picture and score, no spoken word -- `next(iter(VOICES))` raised at
# import and took this module down, and with it every module that imports it.
# A film that has a narrator still gets the same value it always did.
NARRATOR = next(iter(VOICES), None)    # the role that carries the film, if any

# ElevenLabs stability. Lower is more expressive and less repeatable.
STABILITY = 0.5

# (id, beat sid, ROLE, style, text)
#
# `style` is per-line expressiveness, not volume — the mix solves level per take
# (docs/03_audio.md). Push it up on the line the character is selling and down
# on the line where there is nothing to sell.
#
# TWO PEOPLE IN ONE BEAT IS JUST TWO LINES WITH THE SAME SID and different
# roles. edit.py lays them out in order with `extra` between them, make_vo.py
# renders each in its own voice, and `speakers(sid)` below tells anything that
# cares who is in the beat. What this repo cannot yet do is drive TWO MOUTHS in
# one shot -- see docs/04_lipsync.md, which is honest about where that stands.
LINES = [
    # EXAMPLE CONTENT — replace all of it.
    ("01", "01", NARRATOR, 0.45,
     "[dry] The light had been out for a week before anyone thought to walk up "
     "and look at it."),

    ("02", "02", NARRATOR, 0.40,
     "[thoughtful] Nothing was broken. That was the part that took the "
     "longest to explain."),

    ("03", "03", NARRATOR, 0.50,
     "[flat] I left it burning and went back down the hill."),
]

BY_ID = {ln[0]: ln for ln in LINES}


def voice_of(role: str) -> str:
    """The ElevenLabs id for a role. Refuses rather than returning nothing.

    EVERY LOOKUP GOES THROUGH HERE so a role that does not exist fails in one
    place with a sentence, rather than in four tools with a KeyError or -- far
    worse -- as an empty string that reaches the API and bills for a 400.
    """
    if role not in VOICES:
        raise SystemExit(
            f"FAIL: script.py gives a line to {role!r}, which identity.VOICES "
            f"does not have.\n  It knows: {sorted(VOICES)}")
    return VOICES[role]


def speakers(sid: str) -> list[str]:
    """Which roles speak in a beat, in the order they speak."""
    out = []
    for _lid, _sid, role, _style, _text in LINES:
        if _sid == sid and role not in out:
            out.append(role)
    return out


assert len(BY_ID) == len(LINES), "duplicate line id"

# EVERY ROLE A LINE NAMES EXISTS, CHECKED ON IMPORT. Without this the first
# thing that notices is make_vo.py, one line into a paid render.
for _lid, _sid, _role, _st, _t in LINES:
    assert _role in VOICES, (
        f"line {_lid} is spoken by {_role!r}, which identity.VOICES does not "
        f"have. It knows: {sorted(VOICES)}")
_used = {ln[2] for ln in LINES}
# A ROLE THAT IS CAST AND NEVER SPEAKS is contract.py's `cast` check, not a
# print from here. This was a `print()` at module level and it broke two tools
# in one go: anything that imports script.py in a subprocess and reads its
# stdout got a line of prose in front of the JSON. A module should not talk
# when it is imported.
assert all(t.count("[") <= 1 for _, _, _, _, t in LINES), \
    "a line carries more than one tag -- each costs 0.4-0.6s of runtime"

_tags = [t[t.index("[") + 1:t.index("]")] for _, _, _, _, t in LINES if "[" in t]
# THE SHARE IS OF THE SCRIPT, as the message says -- it divided by the
# TAGGED lines only (fault 133), so a ten-line film with two identical tags
# on otherwise-bare lines read as "100%" while the tag touched a fifth of
# the script, and a two-line film with two different tags failed outright.
# And a habit requires repetition: one use of a tag is a choice at any
# share, so nothing under three uses can trip this.
for _t in set(_tags):
    _n = _tags.count(_t)
    _share = _n / len(LINES)
    assert _n < 3 or _share < 0.40, (
        f"tag [{_t}] is on {_n} of the script's {len(LINES)} lines "
        f"({_share:.0%}) -- that is a habit, not a choice, and repeated "
        "contour is what monotone actually sounds like")

# PROVEN-SAFE TAGS ON eleven_v3: interpreted as direction, never spoken aloud.
# [serious] and [laughing] are PROVEN SPOKEN -- they come out of the actor's
# mouth as words -- and must never appear here. Add to this set only after
# hearing the take, never on the strength of the tag sounding plausible.
_SAFE = {"flat", "dry", "thoughtful", "warmly", "amused", "awed",
         "conspiratorial", "firmly", "excited", "cheerful", "delighted",
         "brightly"}
assert set(_tags) <= _SAFE, f"unverified tag: {set(_tags) - _SAFE}"

# IF A VOICE IS A SIGNATURE, ASSERT HOW OFTEN IT SPEAKS -- AND DECLARE IT.
#
# On the film this template came from, one character spoke exactly once, always
# last, and stayed a signature only while it stayed at one. That was written as
# `assert len(guest_lines) <= 1` in the machinery, which made "at most one" a
# fact about the TEMPLATE rather than about that film -- so a season that
# wanted a two-hander could not have one without deleting a guard.
#
# The cap is an editorial decision, so it is declared here, per role, and only
# for the roles that have one. A role with no entry is uncapped.
LINE_CAP: dict[str, int] = {
    # "keeper": 1,   # he speaks once, at the end, and that is the whole point
}
for _role, _cap in LINE_CAP.items():
    assert _role in VOICES, f"LINE_CAP names {_role!r}, which is not a role"
    _n = sum(1 for ln in LINES if ln[2] == _role)
    assert _n <= _cap, (
        f"{_role} speaks {_n} times against a declared cap of {_cap} -- either "
        f"the signature has become a character, or the cap is out of date. "
        f"Decide which, here.")

# A BEAT WITH NO LINE IS DELIBERATE OR IT IS A BUG, AND ONLY AN ASSERT KNOWS
# WHICH. A silence that is not written down is indistinguishable from a silence
# that was lost, and someone counting beats against lines will close the gap.
#
# THIS IS ALSO THE SWITCH FOR THE NON-NARRATED MODE. Every beat in this list
# takes its length from `edit.SILENT_SECS` instead of from measured takes --
# which is how a film with a wordless passage, or a whole film that is picture
# and score, gets timed at all. edit.py asserts the two lists match, so naming
# a beat here and forgetting to give it a length is a build failure rather than
# a beat that turns out to be lead + tail long.
#
# Example: SILENT = {"10"} for a beat whose whole point is that he says nothing.
SILENT: set[str] = set()
_sids = {ln[1] for ln in LINES}
assert not (SILENT & _sids), f"{sorted(SILENT & _sids)} is marked silent but has a line"


def main() -> int:
    print(f"  {len(LINES)} line(s), {len(_sids)} beat(s) with narration, "
          f"{len(_used)} of {len(VOICES)} role(s) speaking")
    if SILENT:
        print(f"  {len(SILENT)} beat(s) deliberately silent: "
              f"{', '.join(sorted(SILENT))} -- lengths in edit.SILENT_SECS")
    for lid, sid, role, style, text in LINES:
        print(f"\n  [{lid}] beat {sid}  {role}  style {style}")
        print(f"      {text}")
    multi = sorted(s for s in _sids if len(speakers(s)) > 1)
    if multi:
        print("\n  beats with more than one speaker:")
        for sid in multi:
            print(f"    {sid}  {' -> '.join(speakers(sid))}")
    return 0


if __name__ == "__main__":
    # -h/--help prints the docstring -- the usage has always lived
    # there; this makes it reachable without opening the file
    # (finding 146). Before main(), so no lock is taken and no
    # argument guard fires first.
    import sys as _hsys
    if "-h" in _hsys.argv or "--help" in _hsys.argv:
        print(__doc__ or "(no usage doc)")
        raise SystemExit(0)
    raise SystemExit(main())
