"""The worker half of subs.py: one part's spoken lines, as JSON, on stdout.

RUN WITH THE CWD SET TO A TREE, one subprocess per part -- the same shape as
contact_probe.py, and for the same reason: every tree has its own `identity`,
`script` and `edit`, and importing two of them into one interpreter gets you
whichever landed on sys.path first.

    python ../subs_probe.py            # an act, or the cold open
    python ../subs_probe.py --sid 02   # one segment of the show

THE OFFSETS COME FROM THE FILES THAT PLACED THE AUDIO, never from a second
derivation and never from a transcription: `assemble.vo_offsets(edit.table())`
for an act, `vo.takes()` for the cold open, `edit.offsets(sid)` for a show
segment. If a line moves in the edit, the subtitle moves with it.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def rows() -> list[dict]:
    sid = None
    if "--sid" in sys.argv:
        sid = sys.argv[sys.argv.index("--sid") + 1]

    # --- the cold open: vo.py placed the takes and knows their lengths -------
    if os.path.exists("vo.py") and not os.path.exists("script.py"):
        import vo
        text = {ln[0]: ln[-1] for ln in vo.LINES}
        role = {ln[0]: "narrator" for ln in vo.LINES}
        return [{"lid": lid, "start": start, "dur": d,
                 "role": role.get(lid, ""), "text": text.get(lid, "")}
                for lid, _path, start, d in vo.takes()]

    import script
    text = {ln[0]: ln[4] for ln in script.LINES}
    role = {ln[0]: ln[2] for ln in script.LINES}
    # WHO THE AUDIENCE CAN SEE, from the table the lip-sync driver reads, so
    # the subtitles and the mouths agree about it. Absent = label nobody.
    seen = sorted(getattr(script, "ON_SCREEN", []) or [])
    import edit

    # --- a show segment ------------------------------------------------------
    if sid is not None:
        return [{"lid": lid, "start": start, "dur": edit.speech(lid),
                 "role": role.get(lid, ""), "text": text.get(lid, ""),
                 "on_screen": seen}
                for lid, start in edit.offsets(sid)]

    # --- an act --------------------------------------------------------------
    import assemble
    return [{"lid": lid, "start": start, "dur": edit.vo_dur(lid),
             "role": role.get(lid, ""), "text": text.get(lid, ""),
             "on_screen": seen}
            for lid, start in assemble.vo_offsets(edit.table())]


if __name__ == "__main__":
    print(json.dumps(rows()))
