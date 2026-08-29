"""Refuse to render while this season is still the template's example.

WHAT THIS CATCHES. The content files in a fresh folder are a WORKING EXAMPLE,
not a blank scaffold -- they carry an invented three-beat film so you can see
the shape of a filled-in `LINES`, `BEATS` and `MOTION` before you write your
own. That is the right trade and it has exactly one failure mode: rendering
before the content has been replaced.

Nothing else in the pipeline can see that. Every check downstream asks "is this
consistent?" and a wholly-inherited film is perfectly consistent.

So this asks the one question none of them ask: IS ANY OF THIS STILL MINE?

HOW IT KNOWS. Each content file declares `EXAMPLE_CONTENT = True` near the top.
That is a deliberate sentinel rather than a guess at which words look
template-ish: keyword matching flagged the DOCSTRINGS -- which are the part
meant to survive -- and a check that cries wolf gets ignored, which is worse
than no check at all. Delete the line when you have replaced the content, and
only then.

    python preflight.py             # from the season root, checks everything
    python preflight.py S3_HARBOUR  # one folder
"""
from __future__ import annotations

import ast
import os
import sys

import parts

ROOT = os.path.dirname(os.path.abspath(__file__))

# Files whose content is meant to be replaced wholesale. Everything else in a
# folder is machinery and is meant to be inherited unchanged.
#
# make_music.py IS ON THIS LIST AND WAS NOT. Its cue prompts decide what the
# film sounds like, which is content by any definition worth having -- but it
# did not LOOK like content, so a fork shipped a Cuban bolero, a 1978 brass
# sting and a Gulf-coast trumpet under a season that was none of those things,
# and preflight said "yours" about every folder.
#
# THIS LIST IS THE WHOLE OF WHAT preflight CAN SEE, which is also its limit:
# it reads content and nothing else. What the modules DO is smoke.py's
# question, and whether their tables agree is contract.py's.
# `verify.py` IS ON THIS LIST. It names beats, devices and the moments they
# are expected to fire -- one film's claims about one film -- and it was left
# off because a verifier did not look like content. See learnings.md 37.
# `vo_candidates.py` joined the list with fault 130: its CANDIDATES are one
# film's closing line, it spends ElevenLabs credit the moment it runs, and
# --install overwrites a real take -- content by any measure.
CONTENT = ("script.py", "shot.py", "motion.py", "edit.py", "make_music.py",
           "verify.py", "vo_candidates.py")

# AND THE SEASON ROOT HAS CONTENT OF ITS OWN. `credits.py` is the only file in
# this repo that names PEOPLE -- the author, the cast, whoever trained each
# LoRA. Every other example ships a wrong cue or a wrong beat and costs a
# re-render; this one credits a stranger for someone else's work. It is
# checked here, at the root, because that is where it lives.
ROOT_CONTENT = ("credits.py",)


def still_example(path: str) -> bool:
    """Is `EXAMPLE_CONTENT = True` still declared at module level?

    Parsed, not grepped, so a mention of the name in a comment or a docstring
    does not count and commenting the line out actually works.
    """
    try:
        tree = ast.parse(open(path, encoding="utf-8").read(), path)
    except SyntaxError:
        return False
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if (isinstance(t, ast.Name) and t.id == "EXAMPLE_CONTENT"
                        and isinstance(node.value, ast.Constant)
                        and node.value.value is True):
                    return True
    return False


def scan(folder: str) -> list[str]:
    return [f for f in CONTENT
            if os.path.exists(os.path.join(folder, f))
            and still_example(os.path.join(folder, f))]


def main() -> int:
    named = [a for a in sys.argv[1:] if not a.startswith("-")]
    ss, bad = parts.audit()
    folders = [r["path"] for r in ss]
    for extra in ("cold_open", "show"):
        p = os.path.join(ROOT, extra)
        if os.path.isdir(p):
            folders.append(p)
    if named:
        folders = [p for p in folders if os.path.basename(p) in named]
        if not folders:
            sys.exit(f"FAIL: {named} matched no folder")

    if bad and not named:
        print("  the season does not describe itself consistently:")
        for b in bad:
            print(f"    {b}")
        print()

    total = 0
    for p in folders:
        left = scan(p)
        total += len(left)
        name = os.path.basename(p)
        print(f"  {name:<20} " + (f"still the example: {', '.join(left)}"
                                  if left else "yours"))

    # The root's own content, checked whenever the whole season is (naming a
    # folder asks about that folder). credits.py is optional: a season with no
    # credit roll has nothing to get wrong.
    if not named:
        root_left = [f for f in ROOT_CONTENT
                     if os.path.exists(os.path.join(ROOT, f))
                     and still_example(os.path.join(ROOT, f))]
        total += len(root_left)
        print(f"  {'(season root)':<20} " +
              (f"still the example: {', '.join(root_left)}" if root_left
               else "yours"))

    print()
    if total:
        print(f"  FAIL: {total} file(s) still carry the template's example "
              f"content.\n"
              f"  Those are the files that decide what the film IS -- the "
              f"words, the\n"
              f"  plates, the motion and the timeline. Replace them, then "
              f"delete the\n"
              f"  `EXAMPLE_CONTENT = True` line at the top of each.\n\n"
              f"  Keep the docstrings and the asserts around them. They are "
              f"the reasons\n"
              f"  the guards exist, and they cost nothing to carry.")
        return 1
    print("  no example content left in the files that define the films.")
    # THE EXIT CODE SAYS ONLY WHAT WAS SAID. Naming a folder asks about that
    # folder, and the season-level findings are suppressed above -- but the
    # return still counted them, so `preflight.py S3_X` on a clean folder
    # printed success and exited 1 with no stated reason (fault 118). A
    # guard that fails without saying why is half a guard; the season-wide
    # run is where those findings print, so it is where they fail.
    return 1 if (bad and not named) else 0


if __name__ == "__main__":
    sys.exit(main())
