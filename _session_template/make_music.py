"""The score cues, one per entry in edit.CUES, generated to the length the
picture is. This example writes two; a season with one cue writes one row in
that table and this file needs no other change.

THE SEASON VARIES ITS SCORE RATHER THAN REUSING ONE CUE. One film might take
smoky minor-key jazz --
walking bass, brushed kit, muted trumpet. #2 was western swing, dobro and
fiddle. #4 is a greasy swamp funk with the season's only backbeat. #5 is the
elegy: vibraphone over a bowed bass. #6 brings the bass and brushes back under a
warm tenor saxophone.

THIS ONE IS THE ONLY CUE IN THE SEASON THE FILM ITSELF NAMES. Beat 07 is "there
was a bolero coming out of a window somewhere, and it came around again every
time I passed", and beats 03, 07 and 12 are the same corner three times. So the
score is not scoring the film from outside it -- it is the thing coming out of
the window, and the repeat is the structure. A nylon-string guitar carries it
over the bolero's own rhythm, with a soft cajon and brushes, an upright bass and
a tres answering underneath.

IT IS ALSO WHY THIS SESSION GETS NO WALKING BASS. #1, #2 and #6 keep time with
one; a bolero does not, and using one here would have made the noir sound like
the first film with the lights off.

THE CUE CHANGE IS THE EDIT, WHICH IS WHY IT IS NOT WRITTEN DOWN HERE. MAIN runs
the night: the arrival, the shop, the corner, the chickens, the woman on the
step. LATE enters on the READING ROOM -- an empty room full of benches with
nobody in it, the beat where the film stops being a job and becomes about her --
and it does not get its percussion back until the end. WHICH beat that is comes
from edit.CUES, because it is a fact about the timeline, and because the two
copies this file and assemble.py used to keep disagreed.

BUT LATE HAS TO REACH FIRST LIGHT. It runs the name, the drawer, the walk back
and the refrain, and the film ends at dawn with the bird asking him to say it
again. So LATE is written with an arc rather than as a flat strip-back, and it
warms and resolves.

LENGTHS DERIVED from edit.py, never typed. NEVER NAME A LIVING COMPOSER: that is
a 400 `bad_prompt`, and the refusal helpfully carries a prompt_suggestion.

AND THE CUE MUST ACTUALLY REACH THE END OF THE PICTURE. /v1/music resolves early
and then PADS THE REST OF THE FILE WITH DIGITAL SILENCE, so the mp3 is exactly
the length that was asked for and the last stretch of film plays under nothing
while every duration check passes. usable_seconds() measures where it stops.
"""
from __future__ import annotations

# THE PROMPTS BELOW ARE THE TEMPLATE'S EXAMPLE, NOT YOUR SCORE.
# preflight.py refuses to render while this line is here. Delete it when you
# have replaced the cue prompts -- and only then.
#
# WHY THIS FILE CARRIES THE SENTINEL AT ALL. It did not, because preflight's
# CONTENT list was script/shot/motion/edit and a score prompt did not look like
# content. So a fork shipped a Cuban bolero, a 1978 brass sting and a
# Gulf-coast trumpet -- three cues written for another season's films, under
# its own -- and everything passed. A prompt that decides what the film SOUNDS
# like is content by any definition that matters.
EXAMPLE_CONTENT = True

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import json
import math
import os
import subprocess
import sys
import urllib.error
import urllib.request

import numpy as np

import edit
from assemble import FF
from find_voice import key

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_music")

# WHERE THE CUES COME IN IS edit.py'S FACT, NOT THIS FILE'S. `CROSSOVER_SID`
# was declared here AND in assemble.py, and the two disagreed -- so the cue was
# written to change register at one moment and laid under the picture at
# another. See edit.CUES.
PAD = 10.0

# Appended to both prompts. The model's default instinct on a slow sparse brief
# is to leave long gaps, and a gap reads as a dropout under picture.
_CONTINUOUS = (
    " The music plays continuously from the first second to the last with no "
    "silence, no long gaps and no fade-out before the end."
)

MAIN = (
    "A slow, wistful Cuban bolero for a wet brick street at three in the "
    "morning. About 76 beats per minute in a minor key, with the bolero's own "
    "gently insistent rhythm. A nylon-string Spanish guitar carries the melody, "
    "a tres answers it underneath, an upright double bass walks nowhere and "
    "just holds the low notes, and a soft cajon and light brushes keep the "
    "pulse. Romantic without being sentimental, unhurried, a little worn. It "
    "sounds like it is coming out of an open window from somewhere down the "
    "street. Instrumental, no vocals." + _CONTINUOUS
)

LATE = (
    "The same bolero, opened out and much barer, then quietly gathering itself "
    "again. It begins as the solo nylon-string guitar alone with no percussion "
    "at all and only the sparest low notes under it -- exposed, slow and held. "
    "About halfway through a soft cajon returns very quietly. In the last third "
    "the tres and the upright bass come back in, warm and low, and the piece "
    "settles and resolves gently at a walking pace rather than fading away "
    "unfinished. Never loud and never triumphant. Instrumental, no vocals."
    + _CONTINUOUS
)


# ONE PROMPT PER CUE, KEYED BY THE CUE'S NAME IN edit.CUES. A prompt with no
# cue is dead text and a cue with no prompt cannot be generated; both are
# checked below rather than discovered at the API call.
PROMPTS = {
    "main": MAIN,
    "late": LATE,
}


def usable_seconds(path: str, floor_db: float = -45.0) -> float:
    """Where the music actually STOPS, which is not where the file stops.

    /v1/music resolves when it feels finished and pads the remainder of the
    requested length with digital silence. The file is then exactly as long as
    was asked for, every duration check passes, and the end of the film plays
    under nothing. Measured in 0.5s RMS windows; returns the end of the last
    window above the floor.
    """
    raw = subprocess.run(
        [season_paths.ff("ffmpeg"), "-v", "error", "-i", path,
         "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
        capture_output=True, check=True).stdout
    x = np.frombuffer(raw, "<i2").astype(np.float32) / 32768.0
    win = 8000                                   # 0.5s at 16 kHz
    n = len(x) // win
    if not n:
        return 0.0
    rms = np.sqrt((x[:n * win].reshape(n, win) ** 2).mean(axis=1) + 1e-12)
    live = np.nonzero(20 * np.log10(rms) > floor_db)[0]
    return float((live[-1] + 1) * win / 16000.0) if len(live) else 0.0


def generate(prompt: str, ms: int, path: str, k: str) -> None:
    body = json.dumps({"prompt": prompt, "music_length_ms": ms}).encode()
    req = urllib.request.Request(
        "https://api.elevenlabs.io/v1/music", data=body,
        headers={"xi-api-key": k, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"FAIL: {e.code} {e.read()[:800].decode(errors='replace')}\n"
                 "(a ToS refusal carries a prompt_suggestion -- read it)")
    open(path, "wb").write(data)


def main() -> int:
    cues = edit.cue_spans()
    # AN UNSCORED FILM IS A REAL ANSWER and this is where it is said out loud.
    # edit.py used to refuse the empty list on this file's behalf; it does not
    # any more, because the mixer can now build a bus with no score in it.
    if not cues:
        print("  edit.CUES is empty -- this film is unscored. Nothing to make.")
        return 0
    missing = [c["name"] for c in cues if c["name"] not in PROMPTS]
    if missing:
        sys.exit(f"FAIL: no prompt for cue(s) {missing} -- edit.CUES asks for "
                 f"them and PROMPTS here has {sorted(PROMPTS)}")
    spare = sorted(set(PROMPTS) - {c["name"] for c in cues})
    if spare:
        print(f"  note: prompt(s) {spare} are not in edit.CUES and will not "
              f"be generated")

    total = sum(c["secs"] for c in cues)
    os.makedirs(OUT, exist_ok=True)
    k = key()
    print(f"  picture {total:.1f}s   " + "  ".join(
        f"[{c['name']}] beat {c['sid']} at {c['start']:.1f}s for "
        f"{c['secs']:.1f}s" for c in cues))

    short = []
    for c in cues:
        name, prompt, need = c["name"], PROMPTS[c["name"]], c["secs"]
        path = os.path.join(OUT, f"{name}.mp3")
        if os.path.exists(path) and "--force" not in sys.argv:
            print(f"  [{name}] on disk ({os.path.getsize(path)/1e6:.2f} MB)",
                  end="")
        else:
            ms = int(math.ceil(need + PAD) * 1000)
            print(f"  [{name}] generating {ms/1000:.0f}s ...", end="",
                  flush=True)
            generate(prompt, ms, path, k)
            print(f" {os.path.getsize(path)/1e6:.2f} MB", end="")
        live = usable_seconds(path)
        ok = live >= need
        print(f"   music stops at {live:.1f}s, needs {need:.1f}s  "
              f"{'ok' if ok else 'SHORT'}")
        if not ok:
            short.append((name, live, need))

    if short:
        print()
        for name, live, need in short:
            print(f"  FAIL: [{name}] the music stops at {live:.1f}s but the "
                  f"picture runs {need:.1f}s -- {need - live:.1f}s of film "
                  f"would play under digital silence")
        sys.exit("re-run with --force to regenerate the short cue(s)")

    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
