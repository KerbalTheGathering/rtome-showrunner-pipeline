"""Look a voice up by name, in my own library first and then the shared one.

The key is read from .env at runtime and sent as a header -- it never goes on a
command line and never lands in shell history.
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import json
import sys
import urllib.parse
import urllib.request

ENV = season_paths.ENV_FILE


def key() -> str:
    for ln in open(ENV, encoding="utf-8"):
        if ln.strip().startswith("ELEVENLABS_API_KEY"):
            return ln.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("FAIL: ELEVENLABS_API_KEY not in .env")


def get(url: str, k: str):
    req = urllib.request.Request(url, headers={"xi-api-key": k})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main() -> int:
    q = " ".join(sys.argv[1:]) or "Elder Strig"
    k = key()
    terms = [t.lower() for t in q.split()]

    mine = get("https://api.elevenlabs.io/v1/voices", k)["voices"]
    hits = [v for v in mine if any(t in v["name"].lower() for t in terms)]
    print(f"MY LIBRARY ({len(mine)} voices):")
    for v in hits:
        print(f"  {v['name']!r}  {v['voice_id']}  {v.get('category')}")
    if not hits:
        print("  -- no name match")

    url = "https://api.elevenlabs.io/v1/shared-voices?" + urllib.parse.urlencode(
        {"search": q, "page_size": 12})
    for v in get(url, k).get("voices", []):
        print(f"\nSHARED  {v.get('name')!r}  {v.get('voice_id')}")
        print(f"  {v.get('category')} / {v.get('age')} / {v.get('gender')} / "
              f"{v.get('accent')} / {v.get('use_case')}")
        d = (v.get("description") or "").replace("\n", " ")
        print(f"  {d[:200]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
