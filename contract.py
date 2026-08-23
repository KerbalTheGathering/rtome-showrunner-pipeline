"""Assert the facts that live in more than one file. The gate before a render.

THE IDENTITY LAYER PROVED SOMETHING AND ONLY HALF-APPLIED IT.

`state it once, derive it everywhere, hard-fail when blank` killed an entire
bug class for NAMES -- nine parts, zero identity bugs, in a fork that found
seventeen faults everywhere else. It was never extended to SHAPE, and shape is
where the rest of them were:

  * `CROSSOVER_SID` was declared separately in assemble.py and make_music.py.
    They disagreed. The cue was generated to change register at 19.4s and the
    mix was told to lay it under a beat that does not exist. It crashed only
    because the beat was absent -- in a tree that HAS that beat number, the cue
    is written for one moment and laid under another, silently, forever.
  * `assemble.py` took one board mark per SPOKEN line and drew
    `[:len(BOARD_TYPE[sid])]` of them, so three lines of type against one line
    of copy drew ONE and logged "3 line(s) of type". A whole reel shipped that
    way and it was found by grabbing a frame off the delivered mp4.
  * `edit.TRANSITIONS` named a device `assemble.py` had never implemented, and
    the `else` branch rendered the PREVIOUS season's device.

Every one of those is TWO FILES DISAGREEING, and every one of them is checkable
before a single frame is rendered.

WHY IT IS NOT AN ASSERT INSIDE THE FILES. Some of these facts span files that
cannot import each other -- script.py cannot import shot.py without a cycle --
and the ones that can are checked there already (shot.py asserts the board/copy
count, because it is the file that can see both). What is left is what nothing
can see from the inside, so it is checked from the outside, per tree, in that
tree's own process for the same sys.modules reason as smoke.py.

    python contract.py            # every tree
    python contract.py show       # one tree
    python contract.py -v         # print what passed as well as what failed

RUN IT AFTER edit.py AND BEFORE ANYTHING IS GENERATED. season.py runs it for
you. It is the last check that costs nothing.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import smoke

ROOT = os.path.dirname(os.path.abspath(__file__))

# Runs inside the tree. Every check returns a list of sentences; an empty list
# is a pass. Nothing here raises on a missing module -- a cold open has no
# script.py and a film has no board, and "this tree does not have one" is a
# different answer from "this tree is wrong".
CHECKS = r'''
import importlib, json, os, sys

def load(name):
    try:
        return importlib.import_module(name)
    except BaseException as e:
        return e

shot = load("shot")
script = load("script")
edit = load("edit")
motion = load("motion")
assemble = load("assemble")

bad, ran, skipped = [], [], []


def broken(*mods):
    """Any of these that will not import, as a sentence."""
    out = [f"{m}" for m, v in mods if isinstance(v, BaseException)]
    return out


def check_beats():
    """shot, motion and edit must cover the same beats, in the same order.

    THE COUNT IS NOT THE POINT, THE AGREEMENT IS. shot.py used to assert
    `len(BEATS) == 15` -- a number from the film it was copied from, typed
    into the file that is supposed to define the beats. A literal cannot
    disagree with anything; three tables can, and do.
    """
    if broken(("shot", shot), ("edit", edit)):
        return ["shot.py or edit.py will not import -- run smoke.py"]
    out = []
    cut = list(getattr(shot, "CUT", []))
    if not cut:
        return ["shot.CUT is empty -- this tree describes no beats"]

    if not isinstance(motion, BaseException):
        m = set(getattr(motion, "MOTION", {}))
        if m != set(cut):
            out.append(f"motion covers {sorted(m ^ set(cut))} differently "
                       f"from the cut")

    rows = getattr(edit, "BEATS", None)
    if rows is not None:
        esids = [r[0] for r in rows]
        if esids != cut:
            out.append(f"edit.BEATS is {esids} but shot.CUT is {cut} -- the "
                       f"timeline and the plates disagree about the film")

    if not isinstance(script, BaseException):
        sids = getattr(script, "SIDS", None)
        if sids is not None and list(sids) != cut:
            out.append(f"script.SIDS is {list(sids)} but shot.CUT is {cut}")
        lines = getattr(script, "LINES", None)
        if lines is not None:
            orphan = sorted({ln[1] for ln in lines} - set(cut))
            if orphan:
                out.append(f"script has copy for {orphan}, which is not in "
                           f"the cut -- those lines are never heard")
    return out


def check_lengths():
    """Every beat is either MEASURED or TYPED, and the two files agree which.

    edit.py asserts this against its own tables on import. What it cannot see
    is script.py: a beat listed with line ids that script.py does not have is
    measured against nothing, and a beat that script.py HAS copy for but that
    edit.py never lists never plays at all. Both need a file that can see both.
    """
    if isinstance(edit, BaseException):
        return None
    rows = getattr(edit, "BEATS", None)
    if rows is None:
        return None                      # this tree types its lengths in shot
    silent = getattr(edit, "SILENT_SECS", {})
    out = []
    known = ({ln[0] for ln in getattr(script, "LINES", ())}
             if not isinstance(script, BaseException) else None)
    placed = set()
    for sid, lids, *_rest in rows:
        placed |= set(lids)
        if not lids and sid not in silent:
            out.append(f"beat {sid} has no lines and no typed length")
        if lids and sid in silent:
            out.append(f"beat {sid} has copy and a typed length -- one number, "
                       f"two sources")
        if known is not None:
            for lid in lids:
                if lid not in known:
                    out.append(f"beat {sid} is timed off line {lid!r}, which "
                               f"script.py does not have")
    if known is not None:
        for lid in sorted(known - placed):
            out.append(f"line {lid!r} is written but no beat plays it -- it is "
                       f"recorded, paid for, and never heard")
    return out


def check_cast():
    """Every role that speaks has a voice, and every voice declared is used.

    script.py asserts a line's role EXISTS on import. What it cannot do is
    notice a role declared in identity.VOICES that no line ever uses -- a voice
    id left behind from the previous film, sitting in the table, resolving
    perfectly, waiting for somebody to give it a line.
    """
    if isinstance(script, BaseException):
        return None
    voices = getattr(script, "VOICES", None)
    if voices is None:
        return None                      # this tree has no words
    out = []
    used = {ln[2] for ln in getattr(script, "LINES", ())}

    # THE NON-NARRATED FILM, CHECKED WHERE IT CAN ACTUALLY BE CHECKED.
    #
    # identity.py used to refuse an empty VOICES outright, while telling you
    # what a film with nobody in it needs -- a requirement it had no way to
    # verify, because it cannot import the two files that answer it. That made
    # the mode unreachable except by casting a narrator who never speaks. The
    # refusal moved here, where both files are already loaded.
    #
    # A film may have no voices. What it may not be is silent BY ACCIDENT: no
    # cast, no lines, and beats nobody gave a length to is not a film that is
    # picture and score, it is a film whose script was never written.
    if not voices:
        if used:
            out.append("identity.VOICES is empty but script.LINES has lines "
                       "-- cast the roles or delete the lines")
        silent = set(getattr(script, "SILENT", ()) or ())
        cut = set(getattr(shot, "CUT", ()) or ())
        loose = sorted(cut - silent)
        if loose:
            out.append(
                f"this film has no voices, so every beat must be in "
                f"script.SILENT with a length in edit.SILENT_SECS -- "
                f"{loose} are in neither")
        return out
    for role in sorted(used - set(voices)):
        out.append(f"{role!r} has lines but no voice in identity.VOICES")
    for role in sorted(r for r in voices if not voices[r]):
        out.append(f"role {role!r} is declared with an empty voice id")
    # NOT AGAINST A STUBBED IDENTITY. _session_template is never configured, so
    # its VOICES come from smoke.py's stand-in, which carries every role any
    # tree's example uses. "declared and never speaks" would then be a fact
    # about the stub rather than about the film -- and a finding that is always
    # there is a finding nobody reads.
    if not os.environ.get("SMOKE_STUB"):
        for role in sorted(set(voices) - used):
            out.append(f"role {role!r} is cast and never speaks -- either a "
                       f"line is missing or the role is the previous film's")
    return out


def check_marks():
    """One line of drawn type per line of spoken copy, at most.

    assemble.py schedules marks from edit.offsets() -- one per VO line -- and
    then takes len(BOARD_TYPE[sid]) of them. More type than copy is silently
    truncated AND reported as though it had all been drawn.
    """
    board = getattr(shot, "BOARD_TYPE", None) if not isinstance(
        shot, BaseException) else None
    if board is None:
        return None                      # this tree draws no board
    if isinstance(script, BaseException):
        return ["there is a board but script.py will not import"]
    out = []
    for sid, lines in board.items():
        spoken = sum(1 for ln in getattr(script, "LINES", ()) if ln[1] == sid)
        if len(lines) > spoken:
            out.append(f"segment {sid}: {len(lines)} line(s) of board type "
                       f"against {spoken} spoken line(s) -- only the first "
                       f"{spoken} would ever be drawn")
    return out


def check_devices():
    """Every transition the edit asks for has a branch in the assembler.

    AND THE ASSEMBLER'S OWN REGISTRY MATCHES ITS OWN DISPATCH. A declared list
    that can drift from the code it describes is the same fault one level up,
    so DEVICES is checked against the `kind == "..."` literals in the source
    rather than trusted.
    """
    trans = getattr(edit, "TRANSITIONS", None) if not isinstance(
        edit, BaseException) else None
    if trans is None:
        return None
    if isinstance(assemble, BaseException):
        return ["there are transitions but assemble.py will not import"]
    import devices
    devices.load_extra(os.getcwd())
    known = set(devices.DEVICES)
    out = []
    cut = set(getattr(shot, "CUT", ()))
    for row in trans:
        f, t, kind, secs = row[:4]
        opt = row[4] if len(row) > 4 else {}
        if kind not in known:
            out.append(f"transition {f}->{t} is {kind!r}, which is not in the "
                       f"device library (it has {sorted(known)})")
        else:
            # THE SETTINGS ARE CHECKED TOO. A setting the device does not have
            # is silently ignored otherwise, and you would spend the render
            # wondering why the angle did nothing.
            spare = sorted(set(opt) - set(devices.DEVICES[kind]["defaults"]))
            if spare:
                out.append(f"transition {f}->{t} passes {spare} to {kind!r}, "
                           f"which does not take "
                           f"{'them' if len(spare) > 1 else 'it'}")
        for sid in (f, t):
            if cut and sid not in cut:
                out.append(f"transition {f}->{t} names beat {sid!r}, which is "
                           f"not in the cut")
        if secs <= 0:
            out.append(f"transition {f}->{t} runs {secs}s")
    return out


def check_cards():
    """The named title, end and mid-film cards exist, and their settings are
    theirs."""
    ident = load("identity")
    if isinstance(ident, BaseException):
        return None
    name = getattr(ident, "TITLE_CARD", None)
    if name is None:
        return None                      # this tree draws no card
    import cards
    out = []
    for label, n, opt in ((name, 2, getattr(ident, "TITLE_CARD_OPTS", {})),
                          (getattr(ident, "END_CARD_STYLE", "corner"), 1, {})):
        if label not in cards.CARDS:
            out.append(f"identity names card {label!r}, which is not in the "
                       f"library ({sorted(cards.CARDS)})")
            continue
        try:
            cards.settings(label, opt)
            cards.layout(label, n, opt)
        except SystemExit as e:
            out.append(str(e).splitlines()[0].removeprefix("FAIL: "))

    # MID-FILM CARDS -- shot.MID_CARDS, checked the same way, plus the one
    # thing title/end do not need checked: that the beat it names actually
    # exists. shot.py's own import-time assert catches a MID_CARDS beat this
    # film never had; this catches the same class of fault contract.py
    # exists for everywhere else -- a name that resolves cleanly against the
    # wrong thing rather than refusing.
    if not isinstance(shot, BaseException):
        cut = set(getattr(shot, "CUT", ()) or ())
        for sid, entry in (getattr(shot, "MID_CARDS", {}) or {}).items():
            # (style, lines) or (style, lines, opts): the third is optional
            style, lines, *rest = entry
            mid_opt = rest[0] if rest else {}
            if sid not in cut:
                out.append(f"MID_CARDS names beat {sid!r}, which is not in "
                          f"shot.CUT")
            if style not in cards.CARDS:
                out.append(f"MID_CARDS[{sid!r}] names card {style!r}, which "
                          f"is not in the library ({sorted(cards.CARDS)})")
                continue
            try:
                cards.settings(style, mid_opt)
                cards.layout(style, len(lines), mid_opt)
            except SystemExit as e:
                out.append(str(e).splitlines()[0].removeprefix("FAIL: "))
    return out


def check_look():
    """The named grade, fit and mix exist, and their settings are theirs.

    THE NAMES ARE CHECKED BEFORE ANYTHING IS BAKED, which is the whole point:
    `GRADED_AS = "flatt"` is a typo that costs a full render to discover
    otherwise, and it fails on the LAST frame the grade is asked for rather
    than the first thing anybody runs.

    A GRADE THAT NEVER RUNS IS ALSO REPORTED. `shot.GRADED` naming beats while
    `GRADED_AS` is "none" is a contradiction between two files -- somebody
    turned the look off and left the list behind, or wrote the list and never
    named the look. Either way the film does not do what one of them says.
    """
    ident = load("identity")
    if isinstance(ident, BaseException):
        return None
    out = []
    for mod_name, attrs in (("grades", ("GRADE", "GRADED_AS")),
                            ("framing", ("FIT",)), ("mixes", ("MIX",))):
        names = [a for a in attrs if getattr(ident, a, None) is not None]
        if not names:
            continue
        lib = __import__(mod_name)
        lib.load_extra(os.getcwd())
        for attr in names:
            name = getattr(ident, attr)
            opts = getattr(ident, attr.replace("GRADED_AS", "GRADED")
                           + "_OPTS", {})
            try:
                lib.settings(name, opts)
            except SystemExit as e:
                out.append(f"identity.{attr}: "
                           + str(e).splitlines()[0].removeprefix("FAIL: "))
    graded = list(getattr(shot, "GRADED", ())) if not isinstance(
        shot, BaseException) else []
    if graded and getattr(ident, "GRADED_AS", None) == "none":
        out.append(f"shot.GRADED names {len(graded)} beat(s) but "
                   f"identity.GRADED_AS is \"none\" -- the list does nothing")
    # AND THE PER-BEAT CROPS ARE SETTINGS THE FIT ACTUALLY TAKES. A beat-level
    # override is the most likely place for a stale key: it is written once,
    # for one shot, and never looked at again.
    fit = getattr(ident, "FIT", None)
    beats = getattr(shot, "FIT_BEATS", None) if not isinstance(
        shot, BaseException) else None
    if fit is not None and beats:
        import framing
        for sid, opt in beats.items():
            try:
                framing.settings(fit, dict(getattr(ident, "FIT_OPTS", {}),
                                           **opt))
                framing.anchor_xy(opt.get("anchor", "centre"))
            except SystemExit as e:
                out.append(f"shot.FIT_BEATS[{sid!r}]: "
                           + str(e).splitlines()[0].removeprefix("FAIL: "))
    return out


def check_cues():
    """One owner for where the score changes, and a prompt for every cue."""
    cues = getattr(edit, "CUES", None) if not isinstance(
        edit, BaseException) else None
    if cues is None:
        return None
    out = []
    cut = list(getattr(shot, "CUT", ()))
    for name, sid in cues:
        if cut and sid not in cut:
            out.append(f"score cue {name!r} comes in on beat {sid!r}, which "
                       f"is not in the cut")
    mm = load("make_music")
    if isinstance(mm, BaseException):
        out.append("edit.CUES exists but make_music.py will not import")
        return out
    prompts = getattr(mm, "PROMPTS", None)
    if prompts is None:
        out.append("make_music.py has no PROMPTS table keyed by cue name")
        return out
    for name, _sid in cues:
        if name not in prompts:
            out.append(f"score cue {name!r} has no prompt in make_music.py")
    for name in sorted(set(prompts) - {n for n, _s in cues}):
        out.append(f"make_music.py has a prompt for {name!r}, which is not a "
                   f"cue in edit.CUES -- it will never be generated")
    return out


def check_plates():
    """Every plate table points at beats this film has."""
    if isinstance(shot, BaseException):
        return ["shot.py will not import"]
    cut = set(getattr(shot, "CUT", ()))
    out = []
    for name in ("PLATE_SEED", "PLATE_ALIAS", "PLATE_FLIP", "GRADED",
                 "FIT_BEATS", "BOARD_RECT", "BOARD_TYPE"):
        tbl = getattr(shot, name, None)
        if tbl is None:
            continue
        for sid in tbl:
            if sid not in cut:
                out.append(f"shot.{name} names beat {sid!r}, which is not in "
                           f"the cut")
    return out


for name, fn in (("beats", check_beats), ("lengths", check_lengths),
                 ("cast", check_cast), ("marks", check_marks),
                 ("devices", check_devices), ("cards", check_cards),
                 ("look", check_look),
                 ("cues", check_cues), ("plates", check_plates)):
    try:
        got = fn()
    except BaseException as e:
        got = [f"the check itself raised {type(e).__name__}: {e}"]
    if got is None:
        skipped.append(name)
    else:
        ran.append(name)
        bad += [f"[{name}] {s}" for s in got]

json.dump({"bad": bad, "ran": ran, "skipped": skipped}, sys.stdout)
'''


# `registry_matches_source()` USED TO LIVE HERE and is gone with the thing it
# checked. assemble.py declared a DEVICES tuple beside a four-branch `if kind
# ==` chain, and the two could drift -- so this read the branches back out of
# the source and compared them. Now there is no chain: devices.py IS the
# registry, and a device that is in it is a device that runs. A check that
# exists because two things can disagree should go away when they cannot.


def check(label: str, folder: str, verbose: bool) -> list[str]:
    env = dict(os.environ)
    args = [sys.executable, "-c", CHECKS]
    if label == "_session_template":
        env["SMOKE_STUB"] = json.dumps(smoke._stub(label, 1))
        args = [sys.executable, "-c", _STUB + CHECKS]
    r = subprocess.run(args, cwd=folder, env=env, capture_output=True,
                       text=True)
    if r.returncode or not r.stdout.strip():
        tail = (r.stderr or "").strip().splitlines()[-1:] or ["no output"]
        return [f"the tree will not load: {tail[0]}  -- run smoke.py"]
    # THE LAST LINE, NOT THE WHOLE STREAM. A tree that prints anything at
    # import -- a note, a warning, a deprecation from a dependency -- lands it
    # in front of the JSON, and the tool then dies with a decode error that
    # says nothing about the actual cause. One of this repo's own script.py
    # files did exactly that.
    try:
        got = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return [f"the tree printed something this tool could not read: "
                f"{r.stdout.strip().splitlines()[:1]}"]
    bad = got["bad"]
    if verbose:
        print(f"    ran: {', '.join(got['ran']) or 'nothing'}"
              + (f"   not applicable here: {', '.join(got['skipped'])}"
                 if got["skipped"] else ""))
    return bad


_STUB = r'''
import json, os, sys, types
spec = json.loads(os.environ["SMOKE_STUB"])
season = types.ModuleType("season_identity")
season.__dict__.update(spec["season"])
season.check = lambda: None
season.claim_clips = lambda *a, **k: None
season.folder = lambda: spec["season"]["DELIVER"]
season.part_label = lambda n: (spec["season"]["PART_LABEL"].format(n=n)
                               if spec["season"]["PART_LABEL"] else "")
ident = types.ModuleType("identity")
ident.__dict__.update(spec["identity"])
ident.season = season
ident.check = lambda: None
ident.claim_clips = season.claim_clips
ident.label = lambda: (spec["identity"]["LABEL"]
                       if spec["identity"]["LABEL"] is not None
                       else season.part_label(spec["identity"]["SESSION_NO"]))
sys.modules["season_identity"] = season
sys.modules["identity"] = ident
'''


def main() -> int:
    argv = sys.argv[1:]
    verbose = "-v" in argv or "--verbose" in argv
    named = [a for a in argv if not a.startswith("-")]

    # THE PROBES ARE NOT PART OF THE PIPELINE and have no tables of their own.
    want = [t for t in smoke.trees()
            if t[0] not in ("root", "show/_probes")]
    if named:
        want = [t for t in want if t[0] in named
                or os.path.basename(t[1]) in named]
        if not want:
            sys.exit(f"FAIL: {named} matched no tree")

    total = 0
    for label, folder in want:
        print(f"  {label}")
        bad = check(label, folder, verbose)
        total += len(bad)
        for b in bad:
            print(f"    {b}")
        if not bad:
            print("    the tables agree")
        print()

    if total:
        print(f"  FAIL: {total} disagreement(s) between files.\n"
              f"  Every one of these renders. That is the problem with them --\n"
              f"  a table that resolves against the wrong film does not raise,\n"
              f"  it just produces a coherent film that is not yours.")
        return 1
    print("  every cross-file fact agrees with itself.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
