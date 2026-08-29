"""Copy this template into a new season folder, and add session folders to one.

RUN THIS RATHER THAN COPYING BY HAND. A hand copy brings the previous season's
_work/, _baked/ and out/ with it -- gigabytes of the wrong film, and worse, a
`--keep-frames` rebuild that silently bakes it.

    python new_season.py --to D:\\Projects\\MY_SEASON
    python new_season.py --to ..\\MY_SEASON --sessions 6

Then, inside the new season:

    python new_season.py --session S1_HARBOUR        # add one more film folder
    python parts.py                                  # see what is still blank

WHAT IS COPIED AND WHAT IS NOT. Scripts, docs and identity files are copied.
Anything that is OUTPUT or CACHE is not: _work, _baked, out, _vo, _vo_wav,
_vo_alt, _music, _verify, __pycache__. That list is deny-by-default -- a
directory whose name starts with `_` and is not `_session_template` is assumed
to be data and skipped, so a new cache directory added later cannot leak into a
clone just because nobody updated this file.
"""
from __future__ import annotations

import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Copied. Everything else at the top level is data or a session folder.
KEEP_FILES = (".py", ".md")
# `_probes` IS ON THIS LIST BECAUSE THE DOCS SEND YOU TO IT. docs/09_scripts.md
# says to read one when you are about to re-litigate the decision it records --
# and the deny-by-default rule below (a leading underscore means data) was
# quietly dropping the whole folder, so a new season could be told to go and
# read files it did not have. `_probes_out`, which is where they WRITE, stays
# in NEVER.
KEEP_DIRS = ("docs", "show", "cold_open", "_session_template", "_probes")
NEVER = {"_work", "_baked", "out", "_vo", "_vo_wav", "_vo_alt", "_music",
         "_verify", "_probes_out", "__pycache__", ".git"}


def is_data(name: str) -> bool:
    return name in NEVER or (name.startswith("_") and name not in KEEP_DIRS)


def copy_tree(src: str, dst: str) -> int:
    n = 0
    os.makedirs(dst, exist_ok=True)
    for e in sorted(os.listdir(src)):
        s, d = os.path.join(src, e), os.path.join(dst, e)
        if os.path.isdir(s):
            if is_data(e):
                continue
            n += copy_tree(s, d)
        elif os.path.splitext(e)[1] in KEEP_FILES:
            shutil.copy2(s, d)
            n += 1
    return n


def new_season(to: str, n_sessions: int) -> int:
    if os.path.exists(to) and os.listdir(to):
        sys.exit(f"FAIL: {to} exists and is not empty. Refusing to copy over "
                 f"a season that may already have work in it.")
    n = 0
    os.makedirs(to, exist_ok=True)
    for e in sorted(os.listdir(HERE)):
        s, d = os.path.join(HERE, e), os.path.join(to, e)
        if os.path.isdir(s):
            if is_data(e):
                continue
            n += copy_tree(s, d)
        elif os.path.splitext(e)[1] in KEEP_FILES:
            shutil.copy2(s, d)
            n += 1
    print(f"  copied {n} files -> {to}")

    for i in range(1, n_sessions + 1):
        made = add_session(to, f"S{i}_UNNAMED", session_no=i, quiet=True)
        print(f"    session folder S{i}_UNNAMED ({made} files)")

    print(f"""
  NEXT, IN ORDER -- and do not skip the first one, everything imports it:

    1. edit {os.path.join(to, 'season_identity.py')}
    2. rename each S*_UNNAMED folder to something meaningful and fill its
       identity.py (NAME, SESSION_NO, TITLE, SLUG, SEED, TRANSITION)
    3. cd {to} && python parts.py        -- says what is still blank
    4. read docs/00_READ_ME_FIRST.md and docs/01_process.md

  The scripts REFUSE TO RUN until the identity files are filled. That is
  deliberate: a half-configured clone that renders is how a season ships with
  another season's title card on it.""")
    return 0


def add_session(root: str, folder: str, session_no: int | None = None,
                quiet: bool = False) -> int:
    src = os.path.join(root, "_session_template")
    if not os.path.isdir(src):
        sys.exit(f"FAIL: {src} is missing -- is {root} a season folder?")
    dst = os.path.join(root, folder)
    if os.path.exists(dst):
        sys.exit(f"FAIL: {dst} already exists")
    n = copy_tree(src, dst)
    if session_no is not None:
        p = os.path.join(dst, "identity.py")
        s = open(p, encoding="utf-8").read()
        s = s.replace("SESSION_NO = 0  ", f"SESSION_NO = {session_no}  ", 1)
        open(p, "w", encoding="utf-8", newline="\n").write(s)
    if not quiet:
        print(f"  {folder}: {n} files. Now fill {folder}/identity.py.")
    return n


def main() -> int:
    a = sys.argv[1:]
    if "--to" in a:
        to = os.path.abspath(a[a.index("--to") + 1])
        n = int(a[a.index("--sessions") + 1]) if "--sessions" in a else 0
        return new_season(to, n)
    if "--session" in a:
        return 0 if add_session(HERE, a[a.index("--session") + 1]) else 1
    print(__doc__)
    return 1


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
