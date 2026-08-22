"""What this season is made of, discovered rather than typed.

THE RUNNING ORDER USED TO BE A LIST OF FOLDER NAMES IN TWO FILES. season.py had
one and feature.py had another, and they were free to disagree -- which is the
same shape as every other bug this template guards against, one level up.

So it is worked out ONCE, here, by looking at the disk:

  * a session is any sub-folder holding an identity.py that declares a
    SESSION_NO of 1 or more
  * the show, if this season has one, is show/
  * the order is [cold open] then [interstitial n] [film n] for n in 1..N

IDENTITY IS READ WITH A REGEX, NOT AN IMPORT, and that is deliberate: a session
identity.py hard-fails on import while it is still blank, so importing them here
would mean a half-built season could not even be LISTED. This module has to be
able to say "session 3 is not configured yet" without dying.

THE SEASON FILE IS READ THE SAME WAY, FOR THE SAME REASON, and it did not used
to be. `import season_identity` at the top of this file meant a fresh clone
could not run `parts.py`, could not run `preflight.py` (which imports this) and
could not run `smoke.py` -- all three died on season_identity's blank guard
instead of saying what THEY had to say. A module whose whole job is to describe
a half-built season must not require a built one.

    python parts.py           # print the running order and what is missing
    python parts.py --json    # the same facts, machine-readable

WHY --json EXISTS. This repo is operated by agent sessions, and a session
re-entering a half-built season used to re-derive "what exists" by parsing the
prose above -- every time, at the cost of its own context. The JSON is the same
discovery (regex off the files, existence off the disk, imports of nothing), so
it stays runnable on a season too blank to import. Counts come with the path
they were counted in, so a zero can be told from a wrong NAME: a `*_clips`
folder that does not exist yet and a folder being looked for in the wrong
place print identically as 0 without the path beside them.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SKIP = {"docs", "show", "cold_open", "__pycache__", "_session_template"}
SEASON_FILE = os.path.join(ROOT, "season_identity.py")


def _field(path: str, name: str) -> str | None:
    """Read `NAME = "value"`, `NAME = 3` or `NAME = True` without importing it."""
    try:
        s = open(path, encoding="utf-8").read()
    except OSError:
        return None
    m = re.search(rf'^{name}\s*=\s*'
                  rf'(?:"([^"]*)"|\'([^\']*)\'|(\d+)|(True|False))\s*(?:#.*)?$',
                  s, re.M)
    if not m:
        return None
    return next((g for g in m.groups() if g is not None), "")


class _Season:
    """The season fields this module needs, read off the file rather than run.

    Deliberately NOT the season_identity module: this one is allowed to be
    blank. `blank` is the flag audit() reports on, so a caller gets the same
    sentence season_identity.check() would have given it -- as a finding rather
    than as an exit.
    """

    def __init__(self, path: str) -> None:
        self.SEASON = _field(path, "SEASON") or ""
        self.SEASON_TITLE = _field(path, "SEASON_TITLE") or ""
        self.SEASON_SLUG = _field(path, "SEASON_SLUG") or ""
        self.END_CARD = _field(path, "END_CARD") or ""
        self.N_SESSIONS = int(_field(path, "N_SESSIONS") or 0)
        self.SHOW = (_field(path, "SHOW") or "False") == "True"
        self.SHOW_NAME = _field(path, "SHOW_NAME") or ""

    @property
    def blank(self) -> list[str]:
        missing = [k for k in ("SEASON", "SEASON_TITLE", "SEASON_SLUG",
                               "END_CARD") if not getattr(self, k)]
        if not self.N_SESSIONS:
            missing.append("N_SESSIONS")
        if self.SHOW and not self.SHOW_NAME:
            missing.append("SHOW_NAME (or set SHOW = False)")
        return missing


season = _Season(SEASON_FILE)


def sessions() -> list[dict]:
    """Every session folder on disk, in running order, configured or not."""
    out = []
    for d in sorted(os.listdir(ROOT)):
        p = os.path.join(ROOT, d)
        if not os.path.isdir(p) or d in SKIP or d.startswith("."):
            continue
        idp = os.path.join(p, "identity.py")
        if not os.path.exists(idp):
            continue
        no = _field(idp, "SESSION_NO")
        if no is None or int(no) < 1:
            continue
        out.append({"dir": d, "path": p, "no": int(no),
                    "name": _field(idp, "NAME") or "",
                    "title": _field(idp, "TITLE") or "",
                    "slug": _field(idp, "SLUG") or ""})
    out.sort(key=lambda r: r["no"])
    return out


def cold_open_dir() -> str | None:
    """The cold open, if this season has one. Delete the folder if it does not."""
    p = os.path.join(ROOT, "cold_open")
    return p if os.path.isdir(p) and os.path.exists(
        os.path.join(p, "assemble.py")) else None


def show_dir() -> str | None:
    p = os.path.join(ROOT, "show")
    return p if season.SHOW and os.path.isdir(p) else None


def audit() -> tuple[list[dict], list[str]]:
    """The sessions, and everything wrong with the set of them."""
    ss = sessions()
    bad = []
    if season.blank:
        bad.append("season_identity.py is still blank: "
                   + ", ".join(season.blank))
    nos = [r["no"] for r in ss]
    for n in range(1, season.N_SESSIONS + 1):
        if n not in nos:
            bad.append(f"no session folder declares SESSION_NO = {n}")
    for n in set(nos):
        if nos.count(n) > 1:
            dupes = ", ".join(r["dir"] for r in ss if r["no"] == n)
            bad.append(f"SESSION_NO {n} is claimed by {nos.count(n)} folders: "
                       f"{dupes}")
    for r in ss:
        if r["no"] > season.N_SESSIONS:
            bad.append(f"{r['dir']} is session {r['no']} but the season "
                       f"declares only {season.N_SESSIONS}")
        for k in ("name", "title", "slug"):
            if not r[k]:
                bad.append(f"{r['dir']}/identity.py has no {k.upper()}")
    if season.SHOW and not show_dir():
        bad.append("SHOW is True but there is no show/ folder")
    return ss, bad


def running_order() -> list[tuple[str, str, str]]:
    """(label, mp4, PCM mix) for the finished feature, in order.

    THE MIX PATH TRAVELS WITH THE PICTURE PATH, in one tuple, because
    feature.py builds the season's audio from the mixes rather than from the
    parts' AAC (see its own comments on encoder priming). Working the wav out
    separately from the mp4 is exactly the kind of second derivation that lets
    a whole part's sound end up under the wrong film.

    Paths, not existence -- feature.py reports what is missing, because
    "that film has not been built" is more useful than a KeyError here.
    """
    ss, _ = audit()
    sh = show_dir()
    out = []
    co = cold_open_dir()
    if co:
        out.append(("COLD OPEN",
                    os.path.join(co, "out", "cold_open.mp4"),
                    os.path.join(co, "_work", "mix.wav")))
    for r in ss:
        if sh:
            out.append((f"interstitial {r['no']:02d}",
                        os.path.join(sh, "out", f"bounty_{r['no']:02d}.mp4"),
                        os.path.join(sh, "_work", f"mix_{r['no']:02d}.wav")))
        out.append((r["title"] or r["dir"],
                    os.path.join(r["path"], "out", f"{r['slug']}.mp4"),
                    os.path.join(r["path"], "_work", "mix.wav")))
    # THE END CREDITS ARE A PART, AND AN OPTIONAL ONE (../credits.py). Present
    # only if it has been rendered, so a season without credits joins exactly
    # as it did before, and a season with them gets the same mix-vs-picture
    # check and the same dip-to-black handover as every other part.
    cr = os.path.join(ROOT, "out", "credits.mp4")
    if os.path.exists(cr):
        out.append(("CREDITS", cr, os.path.join(ROOT, "_work", "credits.wav")))
    return out


def state() -> dict:
    """Everything a session needs to resume, importing nothing per-tree."""
    ss, bad = audit()
    sys.path.insert(0, ROOT)
    import season_paths
    parts = []
    for label, mp4, wav in running_order():
        parts.append({"label": label, "mp4": mp4,
                      "built": os.path.exists(mp4),
                      "mtime": os.path.getmtime(mp4)
                      if os.path.exists(mp4) else None})
    trees = []
    for r in ss:
        clips = (os.path.join(season_paths.COMFY_OUTPUT, f"{r['name']}_clips")
                 if r["name"] else None)
        vo = os.path.join(r["path"], "_vo")

        def _n(d, ext):
            if not d or not os.path.isdir(d):
                return 0
            return len([f for f in os.listdir(d)
                        if f.endswith(ext) and "_rej_" not in f])
        trees.append({**{k: r[k] for k in ("dir", "no", "name", "title",
                                           "slug")},
                      "clips_dir": clips, "clips": _n(clips, ".mp4"),
                      "vo_takes": _n(vo, ".mp3") + _n(vo, ".wav"),
                      "baked": _n(os.path.join(r["path"], "_baked"), ".png"),
                      "out_mp4": os.path.exists(
                          os.path.join(r["path"], "out", f"{r['slug']}.mp4"))
                      if r["slug"] else False})
    return {"season": {"SEASON": season.SEASON,
                       "SEASON_TITLE": season.SEASON_TITLE,
                       "N_SESSIONS": season.N_SESSIONS,
                       "blank": season.blank},
            "problems": bad, "sessions": trees, "running_order": parts}


def main() -> int:
    if "--json" in sys.argv:
        import json
        print(json.dumps(state(), indent=1))
        return 0
    ss, bad = audit()
    print(f"  {season.SEASON}  --  {season.SEASON_TITLE!r}")
    print(f"  {len(ss)} session folder(s) of {season.N_SESSIONS} declared"
          + (f", plus the show" if show_dir() else ", no show layer"))
    print()
    for r in ss:
        print(f"    #{r['no']}  {r['dir']:<20} {r['name']:<10} {r['title']}")
    if bad:
        print("\n  PROBLEMS:")
        for b in bad:
            print(f"    {b}")
        return 1
    print("\n  running order:")
    for label, mp4, wav in running_order():
        mark = " " if os.path.exists(mp4) else "*"
        print(f"   {mark} {label:<28} {mp4}")
    print("\n  (* = not built yet)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
