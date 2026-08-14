"""Search the shared library BY DEMOGRAPHIC, not by name.

find_voice.py matches on the voice's NAME, which is the right tool when you know
who you are looking for -- "Strig Narrator" was asked for by name. Casting a new
character is the opposite problem: the brief is `older southern american man,
warm, broadcast energy` and nothing in it is a name. The shared-voices endpoint
takes gender / age / accent / use_case filters, so this asks the question the
brief actually poses.

    python cast.py                       # the brief, several ways
    python cast.py --q="radio announcer" # one free-text probe

The key is read from .env at runtime and sent as a header -- never on a command
line, never in shell history.
"""
from __future__ import annotations

# show/ HOLDS find_voice.py; a probe is one level below it and does not get it
# for free. This file had no path preamble at all and could not be imported.
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import sys
import urllib.parse

from find_voice import get, key                                    # noqa: E402

# EACH PROBE IS A DIFFERENT WAY OF ASKING, because one query is one sample. A
# presenter is not a narrator: `narrative_story` will return calm audiobook
# readers all day and this man has to sound like he is selling something.
PROBES = [
    dict(gender="male", age="old", accent="us southern", page_size=10),
    dict(gender="male", age="middle_aged", accent="us southern",
         use_case="advertisement", page_size=10),
    dict(gender="male", age="old", search="announcer", page_size=10),
    dict(gender="male", search="radio host southern", page_size=10),
]

BASE = "https://api.elevenlabs.io/v1/shared-voices?"


def show(v: dict, seen: set) -> None:
    vid = v.get("voice_id")
    if vid in seen:
        return
    seen.add(vid)
    d = (v.get("description") or "").replace("\n", " ")
    print(f"  {v.get('name')!r}  {vid}")
    print(f"     {v.get('age')} / {v.get('gender')} / {v.get('accent')} / "
          f"{v.get('use_case')}")
    print(f"     {d[:170]}")


def main() -> int:
    k = key()
    q = next((a.split("=", 1)[1] for a in sys.argv[1:]
              if a.startswith("--q=")), None)
    probes = [dict(gender="male", search=q, page_size=12)] if q else PROBES

    seen: set = set()
    for p in probes:
        print(f"\n=== {p} ===")
        try:
            got = get(BASE + urllib.parse.urlencode(p), k).get("voices", [])
        except Exception as e:                                   # noqa: BLE001
            print(f"  query failed: {e}")
            continue
        if not got:
            print("  -- nothing")
        for v in got:
            show(v, seen)
    print(f"\n  {len(seen)} distinct voice(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
