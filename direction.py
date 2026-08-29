"""The negation rule, as a check instead of a paragraph.

`motion.py` has taught this in capitals since the first season:

    A PROHIBITION IS NOT A POSITION. Naming a thing you do not want puts it in
    the frame's vocabulary; it does not reliably remove it, and it spends the
    words that could have specified what IS true.

It was a comment. Nothing read the prompts, and the rule is broken by accident
in the most natural phrasing English offers -- which is exactly the kind of rule
that belongs in an assert.

WHAT THAT COST, TWICE, IN THIS REPO'S OWN FILES:

  * A fork writing "constant pace" reached for *"moving NO faster at the end
    than at the beginning"* -- in the very file that states the rule, minutes
    after reading it. The guard refused the import; the phrase became "holding
    one even pace from the first frame to the last."
  * `cold_open/motion.py`'s example carried *"It does not rise, brighten,
    change colour or move."* Four prohibitions, in the tree copied verbatim into
    every new season, immediately below the file that forbids them. A fork
    copied that shape into an interior and H3 lit the bulb, then lit every arch
    in the hall like strip lighting, over five seconds, in a shot whose one job
    was to be dark. Nothing failed. The clip was beautiful and it was wrong.

THE REWRITE IS ALWAYS AVAILABLE and it is always the same three parts:

    what it is now, that it stays, and that it is STILL that way in the last
    frame.

    "no second person walks out of the door"
        -> "the count of people is one, from the first frame to the last...
            he is still the only figure in the picture in the last frame"
    "the doorways stay empty"
        -> "every doorway keeps exactly what it has in the first frame: the lit
            ones stay lit, the dark ones stay dark"
    "no dialogue, no whispering"
        -> describe the room tone (docs/04_lipsync.md)

WHY IT IS ONE FILE AND NOT THREE COPIES. `docs/10_fork_report.md` fault 8: a
three-branch `draw_text` was correct in `cold_open/assemble.py` the whole time
and the fix never reached `_session_template`, which is the copy that gets
cloned. A bug fixed in one of three copies is not fixed, and a RULE enforced in
one of three copies is not enforced.

    python direction.py        # the list, and the check checking itself
"""
from __future__ import annotations

import sys

# THE LIST IS DELIBERATELY SHORT AND DELIBERATELY BLUNT.
#
# `docs/06_verification.md`: a check that refuses correct work costs as much as
# one that passes wrong work, because the response to it is to widen it until it
# stops complaining. So this catches the phrasings that have actually produced a
# wrong clip in this project and stops there. It is not a grammar checker and it
# is not trying to be.
#
# THE SPACES IN " no " AND " not " ARE LOAD-BEARING: without them this fires on
# "cannot", "another", "nothing" inside "note", and every one of those false
# positives is a step toward somebody deleting the guard.
BANNED = (" no ", " not ", "n't", " never", "nothing", "without",
          "empty of", "free of", " absent", "neither", "none of")

# HOW MUCH OF THE SENTENCE TO QUOTE BACK. A bare "beat 07 contains ' not '" is
# a riddle in a 300-word prompt; the phrase in context is the fix.
_CONTEXT = 44


def _flat(text: str) -> str:
    """One line, lowercased, single-spaced, padded -- so " no " matches a
    "No voice" that happens to start a line."""
    return " " + " ".join(str(text).split()).lower() + " "


def negations(text: str) -> list[tuple[str, str]]:
    """Every banned phrase in `text`, with the words around it."""
    flat = _flat(text)
    out = []
    for word in BANNED:
        at = flat.find(word)
        while at >= 0:
            lo = max(0, at - _CONTEXT)
            hi = min(len(flat), at + len(word) + _CONTEXT)
            out.append((word.strip(), ("..." if lo else "") + flat[lo:hi].strip()
                        + ("..." if hi < len(flat) else "")))
            at = flat.find(word, at + 1)
    return out


def check(table: dict, what: str = "beat") -> None:
    """Refuse a direction table that tells the model what NOT to do.

    Called at IMPORT from every motion.py, which is the point of it: the fork
    that first ran this was refused while writing the offending sentence, not
    after shooting a clip from it.
    """
    for sid in sorted(table):
        found = negations(table[sid])
        if not found:
            continue
        lines = "\n".join(f"      {w!r:12} in  ...{c}..." for w, c in found[:6])
        more = (f"\n      ({len(found) - 6} more)" if len(found) > 6 else "")
        raise AssertionError(
            f"{what} {sid} tells the model what NOT to do:\n{lines}{more}\n"
            f"    A PROHIBITION IS NOT A POSITION. Naming a thing you do not "
            f"want puts it in\n    the frame's vocabulary; it does not reliably "
            f"remove it. Say what IS true,\n    that it stays, and that it is "
            f"still true in the LAST frame:\n"
            f"      'he does not turn'   -> 'he keeps his back to the camera, "
            f"and it is still\n                              turned away in the "
            f"last frame'\n"
            f"    docs/05_prompting.md has the table. direction.BANNED is the "
            f"list.")


# --------------------------------------------------------------------------
# the check, checking itself
# --------------------------------------------------------------------------
#
# `docs/06_verification.md`: give a check a self-test where it can have one --
# the glyph detector refuses to vouch for a font unless a known-absent glyph
# looks absent to it. A negation checker that silently matched nothing would
# vouch for every prompt in the repo, which is the exact "resolver matched zero
# files and still printed a pass" failure this project keeps finding.
_MUST_CATCH = (
    "He walks away and does not turn.",
    "There are no boats on the water.",
    "The doorways stay empty and nothing enters them.",
    "It never brightens.",
    "Moving no faster at the end than at the beginning.",
    "The room is free of furniture.",
    "He doesn't speak.",
)
_MUST_PASS = (
    "He keeps his back to the camera and is still turned away in the last frame.",
    "The water is unbroken from edge to edge in the first frame, in every frame "
    "between, and in the last.",
    "He holds one even pace from the first frame to the last.",
    # THE FALSE POSITIVES THIS LIST MUST NOT HAVE. Each of these contains a
    # banned string as a SUBSTRING and is ordinary direction.
    "He cannot be seen behind the door, which is another matter entirely.",
    "Note the lantern: it holds its exact brightness throughout.",
)


def selftest() -> int:
    bad = 0
    for s in _MUST_CATCH:
        if not negations(s):
            print(f"  MISSED   {s!r}")
            bad += 1
    for s in _MUST_PASS:
        got = negations(s)
        if got:
            print(f"  FALSE +  {s!r} -> {[w for w, _ in got]}")
            bad += 1
    print(f"  {len(_MUST_CATCH)} must-catch, {len(_MUST_PASS)} must-pass: "
          + ("all correct" if not bad else f"{bad} WRONG"))
    return 1 if bad else 0


def main() -> int:
    print(f"  {len(BANNED)} banned phrase(s), matched case-insensitively "
          f"against one flattened line:\n")
    print("    " + "  ".join(repr(b) for b in BANNED))
    print("\n  Every motion.py calls direction.check(MOTION) at import.\n")
    return selftest()


if __name__ == "__main__":
    # -h/--help prints the docstring -- the usage has always lived
    # there; this makes it reachable without opening the file
    # (finding 146). Before main(), so no lock is taken and no
    # argument guard fires first.
    import sys as _hsys
    if "-h" in _hsys.argv or "--help" in _hsys.argv:
        print(__doc__ or "(no usage doc)")
        raise SystemExit(0)
    sys.exit(main())
