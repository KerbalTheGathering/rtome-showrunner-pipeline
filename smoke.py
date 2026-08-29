"""Import every module in every tree, each in its own process. Four seconds.

WHY THIS EXISTS. `preflight.py` asks "is any of this still the template's
example?" and every identity `check()` asks "is this season configured?" -- both
of which look at CONTENT. Nothing in this repo has ever looked at the MACHINERY,
so a season could pass `parts.py`, `preflight.py`, every identity check and
every content assert while being unable to shoot a single frame.

That is not hypothetical. A fork that took this template from clone to finished
feature found seven separate modules that could not be imported at all:

  * three copies of `h3_shoot.py` used `season_paths.COMFY_URL` at module level
    and never imported `season_paths`. `import edit` puts it in `sys.modules`,
    which is not the same thing as putting it in this module's namespace. Every
    one of them raised NameError on the first frame anybody tried to shoot.
  * `verify.py` used `shot.SLUG` without importing `shot` -- on the very line
    whose comment explains that the filename is DERIVED rather than typed.
  * four content files shipped examples that referenced names that were never
    defined, or asserted facts about a fifteen-beat film while carrying three
    beats. Which means the shipped template had not been executed end to end
    since those files were last edited, and nothing in the repo could tell.

A MODULE THAT CANNOT BE IMPORTED FAILS LATE AND EXPENSIVELY. It fails after the
plates are paid for, after the VO is recorded, at the moment somebody finally
runs the thing. This costs four seconds and it runs on a fresh clone, before
anything is configured.

WHY A SUBPROCESS PER FILE. Every tree owns an `identity.py`, a `script.py` and
a `shot.py`, and one interpreter can only hold one of each -- the second tree
would import the first tree's modules out of `sys.modules` and report a pass on
a file it never read. Each module is imported with the working directory set to
its own folder, which is exactly what `python <that file>` does, so the sys.path
this sees is the sys.path a real run sees.

TWO MODES, BECAUSE A FRESH CLONE AND A CONFIGURED SEASON FAIL DIFFERENTLY.

    python smoke.py --template    # a fresh clone. identity is STUBBED, so the
                                  # question is "does the example execute?"
    python smoke.py               # a configured season. the real identity.py
                                  # is used and everything must import for real
    python smoke.py show cold_open    # named trees only
    python smoke.py -v            # full traceback for every failure

WHAT --template STUBS AND WHY IT IS NOT A BACK DOOR. On a fresh clone
`season_identity.check()` exits at import, so every module in the repo dies on
the first line and the smoke test could only ever run on a season whose example
content has already been thrown away -- i.e. never on the files it most needs to
check. So in this mode, and only in this mode, a fake `season_identity` and a
fake per-tree `identity` are put in `sys.modules` of the CHILD PROCESS before
the target import. They exist for the length of one import and cannot be reached
from anywhere else, they are filled with values that are visibly not a season,
and nothing that spends money or writes a frame is ever called. The real
identity files are still imported unstubbed in this mode, and are expected to
REFUSE -- that refusal is itself checked.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import parts

ROOT = os.path.dirname(os.path.abspath(__file__))

# FILES THIS TOOL WILL NOT IMPORT, AND WHY -- printed, never silent. A file
# the checker skips is a fact about the file, and a skip nobody sees is how a
# tool reports "all clear" about work it did not do.
#
# Empty, and it should stay that way. The one entry it had was
# show/_probes/_open_strip.py, which did its whole job at module level with no
# `if __name__` guard, so importing it shelled out to ffmpeg sixty times. That
# was a fault in the file rather than a limit of this tool, and it was fixed
# by giving the probe a main().
NO_IMPORT: dict[str, str] = {}

# SEASON-ROOT FILES THAT ARE TREE-SCOPED: they live once at the root, each
# tree carries an importlib shim, and imported AT the root they refuse by
# design (findings 140/144). Their refusal there is a pass, not a fault --
# the real import is exercised through every tree's shim in the same run.
TREE_SCOPED = {"check_clip", "sheet"}


# --------------------------------------------------------------------------
# The stub, for --template mode
# --------------------------------------------------------------------------
#
# EVERY FIELD ANY FILE IN THE REPO READS OFF AN IDENTITY. Deliberately ugly
# values: if one of these ever turns up in a filename, a title card or a log
# line, it came from here and something is importing the stub for real.
def _stub(tree: str, session_no: int) -> dict:
    return {
        "season": {
            "SEASON": "SMOKE_SEASON", "SEASON_TITLE": "SMOKE",
            "SEASON_SLUG": "smoke", "N_SESSIONS": 6,
            "END_CARD": "SMOKE TEST.", "W": 1440, "H": 1080, "FPS": 24,
            "A_RATE": 48000, "CRF": 18, "I_TARGET": -16.0, "TP_TARGET": -1.5,
            "CEIL_DBFS": -2.0, "DELIVER": os.path.join(ROOT, "_smoke"),
            "SEASON_FOLDER": "", "EXTRA": "", "SHOW": True,
            # STUBBED AT THE TEMPLATE'S OWN DEFAULT, not at "" -- a stub that
            # dropped the eyebrow would make every title card in --template
            # mode a one-line card, which is not the shape a fresh clone has.
            "PART_LABEL": "SESSION #{n}",
            "SHOW_NAME": "SMOKE_SHOW",
            "FONT_DISPLAY": "arialbd.ttf",
            # the H3 shooter and the upscale read these at import
            "UPSCALE": None, "H3_UNET": "smoke.safetensors",
            "H3_ID_REFS": [], "H3_VOICE_REF": "", "H3_TAIL_FRAMES": 22,
        },
        "identity": {
            "NAME": "SMOKE_" + tree.upper().replace("/", "_"),
            "SESSION_NO": session_no,
            "TITLE": "SMOKE", "TITLE_SUPER": "SMOKE", "SLUG": "smoke",
            "SEED": 1, "LATENT": (1216, 832),
            "STYLE_LORA": "", "STYLE_W": 0.85,
            "CHAR_LORA": "", "CHAR_W": 0.9, "TRIGGER": "",
            # EVERY ROLE ANY TREE'S script.py NAMES. The stub cannot know what
            # a season calls its people, so it carries the two the template's
            # own examples use and nothing else -- a tree naming a third role
            # will fail here, loudly, which is the correct answer: smoke.py is
            # checking the example, and an example that names a role its own
            # identity.py does not declare is the fault, not the stub.
            "VOICES": {"narrator": "smoke", "host": "smoke"},
            "VOICE_IS_CLONE": False,
            "TRANSITION": "sweep", "TV": "heavy", "CLIPS": "",
            "TITLE_CARD": "plain", "TITLE_CARD_OPTS": {},
            "END_CARD_STYLE": "corner",
            # THE LOOK, THE FIT AND THE BUS, at their library defaults. These
            # are stubbed at the values a fresh clone carries rather than at
            # something exotic: smoke.py is asking whether the module imports,
            # and a stub that quietly names a grade the film would never use
            # would make `python identity.py` disagree with what was tested.
            "GRADE": "none", "GRADE_OPTS": {},
            "GRADED_AS": "flat", "GRADED_OPTS": {},
            "FIT": "crop", "FIT_OPTS": {},
            "MIX": "ducked", "MIX_OPTS": {},
            # `None` = defer to the season's PART_LABEL, which is what a film
            # that has not overridden its eyebrow carries.
            "LABEL": None,
        },
    }


# Runs in the child. Keep it small enough to read in a `-c`.
BOOT = r"""
import json, os, sys, types, traceback

mod, mode = sys.argv[1], sys.argv[2]

if mode == "template":
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
    # assemble.py calls this AT MODULE LEVEL to build the title card, so a
    # stub without it is an AttributeError on import and every checker
    # reports the tree as broken.
    ident.label = lambda: (
        spec["identity"]["LABEL"] if spec["identity"]["LABEL"] is not None
        else season.part_label(spec["identity"]["SESSION_NO"]))
    sys.modules["season_identity"] = season
    sys.modules["identity"] = ident

try:
    __import__(mod)
except SystemExit as e:
    # A guard that says no. `sys.exit("FAIL: ...")` is this repo's refusal
    # idiom, and refusing is not the same as breaking. The first line is
    # taken defensively: `"".splitlines()` is [] -- so a bare sys.exit(),
    # sys.exit(0) or sys.exit("") used to raise IndexError inside THIS
    # handler, and a clean early exit was reported as "FAIL no output"
    # (fault 119). A checker must not crash on the shapes of refusal.
    first = (str(e.code or "").splitlines() or ["(no message)"])[0]
    print("REFUSE " + first[:110])
    sys.exit(3)
except ModuleNotFoundError as e:
    # A third-party package that is not installed is a fact about this box.
    # A module that is IN THIS REPO and still not found is a fault in the
    # tree -- something is on the wrong sys.path -- so the two are told apart
    # against the list of every module the repo actually contains, not
    # against the one folder we happen to be standing in. Checking only the
    # cwd reported a whole folder of probes as "needs season_paths", which
    # is this repo's own module and was the fault.
    name = (e.name or "").split(".")[0]
    if name in json.loads(os.environ["SMOKE_OURS"]):
        traceback.print_exc()
        print("FAIL   ModuleNotFoundError: " + str(e)
              + "  (that module IS in this repo -- wrong sys.path)")
        sys.exit(1)
    print("NEEDS  " + name)
    sys.exit(4)
except BaseException as e:
    traceback.print_exc()
    print("FAIL   " + type(e).__name__ + ": " + str(e).splitlines()[0][:110])
    sys.exit(1)
print("OK")
"""


def trees() -> list[tuple[str, str]]:
    """(label, absolute path) for every folder holding modules, in build order.

    DISCOVERED, NOT LISTED. parts.py already works the sessions out from the
    disk; adding a fourth film must not mean editing this file.
    """
    out = [("root", ROOT)]
    for extra in ("_session_template", "cold_open", "show"):
        p = os.path.join(ROOT, extra)
        if os.path.isdir(p):
            out.append((extra, p))
    probes = os.path.join(ROOT, "show", "_probes")
    if os.path.isdir(probes):
        out.append(("show/_probes", probes))
    for r in parts.sessions():
        out.append((r["dir"], r["path"]))
    return out


def modules(folder: str) -> list[str]:
    return sorted(f[:-3] for f in os.listdir(folder)
                  if f.endswith(".py") and not f.startswith("__"))


def ours() -> list[str]:
    """Every module name this repo contains, anywhere. See the child's
    ModuleNotFoundError branch for what it is for."""
    names = set()
    for _, folder in trees():
        names.update(modules(folder))
    return sorted(names)


def session_no(label: str) -> int:
    """What SESSION_NO the stub should claim for this tree.

    The show and the cold open assert theirs is 0 and the films assert theirs
    is 1..N, so one number cannot serve both.
    """
    if label == "cold_open" or label == "show" or label.startswith("show/"):
        return 0
    return 1


def run(label: str, folder: str, mode: str, verbose: bool) -> tuple[int, int]:
    # _session_template IS NEVER CONFIGURED, BY DEFINITION. It is the scaffold
    # new_season.py copies to make a session folder, so its identity.py is
    # blank in a finished season exactly as it is in a fresh clone -- and it
    # still has to import, because every future film starts as a copy of it.
    if label == "_session_template":
        mode = "template"
    print(f"  {label}" + ("   [stubbed identity]" if mode == "template"
                          else ""))
    ok = bad = 0
    for mod in modules(folder):
        rel = os.path.relpath(os.path.join(folder, mod + ".py"), ROOT)
        if rel in NO_IMPORT:
            print(f"    {mod:<18} SKIP   {NO_IMPORT[rel]}")
            continue
        env = dict(os.environ)
        env["SMOKE_OURS"] = json.dumps(ours())
        if mode == "template":
            env["SMOKE_STUB"] = json.dumps(_stub(label, session_no(label)))
        # The real identity files are the one thing the stub must not shadow:
        # in --template mode their whole job is to refuse while blank, and a
        # stub standing in front of them would report that refusal as a pass.
        this_mode = "real" if mod in ("identity", "season_identity") else mode
        r = subprocess.run(
            [sys.executable, "-c", BOOT, mod, this_mode],
            cwd=folder, env=env, capture_output=True, text=True)
        verdict = (r.stdout or "").strip().splitlines()
        line = verdict[-1] if verdict else f"FAIL   no output (rc={r.returncode})"
        # A refusal is what a blank identity is SUPPOSED to do on a fresh clone,
        # and what a TREE-SCOPED season-root file does outside a tree -- and a
        # fault everywhere else. check_clip.py and sheet.py live once at the
        # season root and refuse when imported THERE (findings 140/144, by
        # design: they read a tree's shot.py); their import is genuinely
        # exercised through every tree's shim, which this tool also runs. The
        # first season shot on the shim layout had this tally count the two
        # designed refusals as import failures -- the label said REFUSE, the
        # verdict said FAIL, and the label was right (fault 148).
        if r.returncode == 3 and mode == "template" and this_mode == "real":
            line = "BLANK  " + line[7:]
        elif (r.returncode == 3 and mode != "template"
                and folder == ROOT and mod in TREE_SCOPED):
            line = "SCOPED " + line[7:]
            ok += 1
        elif r.returncode == 3 and mode != "template":
            bad += 1
        elif r.returncode in (0, 3, 4):
            ok += 1
        else:
            bad += 1
        if r.returncode not in (0, 4) or verbose:
            print(f"    {mod:<18} {line}")
        if r.returncode == 1 and verbose:
            for tl in (r.stderr or "").strip().splitlines()[-14:]:
                print(f"        {tl}")
    if not bad:
        print(f"    {len(modules(folder))} module(s), all import")
    return ok, bad


def main() -> int:
    argv = sys.argv[1:]
    verbose = "-v" in argv or "--verbose" in argv
    mode = "template" if "--template" in argv else "season"
    named = [a for a in argv if not a.startswith("-")]

    want = trees()
    if named:
        want = [t for t in want if t[0] in named or os.path.basename(t[1]) in named]
        if not want:
            sys.exit(f"FAIL: {named} matched no tree")

    print(f"  smoke: {mode} mode, {sys.executable}\n")
    total_bad = 0
    for label, folder in want:
        _, bad = run(label, folder, mode, verbose)
        total_bad += bad
        print()

    if total_bad:
        print(f"  FAIL: {total_bad} module(s) cannot be imported.\n"
              f"  Nothing downstream of one of these can run, and nothing else\n"
              f"  in this repo looks at whether a module executes -- preflight\n"
              f"  reads content, parts.py reads identity. Run with -v for the\n"
              f"  tracebacks.")
        return 1
    if mode == "template":
        print("  every module imports against a stubbed identity, and every\n"
              "  identity.py refuses while it is still blank. Both are what a\n"
              "  fresh clone should do.")
    else:
        print("  every module in every tree imports.")
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
    sys.exit(main())
