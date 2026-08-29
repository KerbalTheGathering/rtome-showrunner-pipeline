"""The show's sting -- one cue, used identically all six times.

ONE PIECE OF MUSIC FOR THE WHOLE REEL, and that is a decision rather than
economy. The sting is the format's signature: it is the sound that says the
programme has started, and a programme whose theme changes week to week is not a
programme. It plays over segment six exactly as it plays over segment one, with
nothing to announce underneath it -- degrading the music there would be doing
the joke twice, and the joke is that the format is completely intact and empty.

/v1/music RESOLVES EARLY AND PADS THE REST WITH DIGITAL SILENCE, and a four
second cue is the worst possible case for that: there is almost nothing to
resolve. A previous film asked for 38s, got a 38.0s file that stopped playing at
31s, and nothing in the pipeline could see it -- right length, ffprobe happy,
duration assert passed. So this asks for FIFTEEN seconds to use about five, the
prompt states outright that it must play from the first second to the last, and
usable_seconds() walks the file and hard-exits if the music stops early.

NO COMPOSER NAMES. Naming a living composer as a style reference returns a 400
`bad_prompt` ToS rejection; the refusal helpfully includes a prompt_suggestion.
Instrumentation, tempo and register only.

    python make_music.py            # render if absent, always measure
    python make_music.py --force    # re-roll
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
import struct
import subprocess
import sys
import urllib.error
import urllib.request
import wave

from find_voice import key

HERE = os.path.dirname(os.path.abspath(__file__))
MUSIC = os.path.join(HERE, "_music")
FF = season_paths.FFMPEG

WANT_S = 5.0                 # what the reel actually uses
ORDER_MS = 15000             # what is bought, because length bought != delivered

PROMPT = (
    "A short, brassy, cheerful television theme for a low-budget local cable "
    "programme from about 1978. Small brass section playing a bright confident "
    "fanfare over a walking electric bass, a chirpy electric organ, and a dry "
    "close-miked drum kit with rimshots. Bright major key, brisk two-beat feel, "
    "slightly too loud and slightly too pleased with itself, the sound of a "
    "programme that is certain you are glad it is on. Recorded in a small dry "
    "room on modest equipment. "
    # The paragraph that stops it resolving early -- see the header.
    "It plays continuously and at full energy from the very first second to the "
    "very last second of the audio. Do not fade out, do not stop early, do not "
    "ritardando, and leave no silence at the beginning or the end. The very "
    "last second is as loud and as busy as the first."
)


def usable_seconds(path: str) -> float:
    """Last 0.5s window above -45 dBFS. What is actually AUDIBLE, not the length."""
    wav = path[:-4] + ".wav"
    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                    "-i", path, "-ac", "1", "-ar", "22050", wav], check=True)
    with wave.open(wav) as w:
        sr, n = w.getframerate(), w.getnframes()
        pcm = struct.unpack(f"<{n}h", w.readframes(n))
    win = int(sr * 0.5)
    last = 0.0
    for i in range(0, n - win, win):
        rms = math.sqrt(sum(v * v for v in pcm[i:i + win]) / win) / 32768.0
        if 20 * math.log10(rms + 1e-12) > -45.0:
            last = (i + win) / sr
    return last


def render(path: str, k: str) -> None:
    body = json.dumps({"prompt": PROMPT, "music_length_ms": ORDER_MS}).encode()
    req = urllib.request.Request(
        "https://api.elevenlabs.io/v1/music", data=body,
        headers={"xi-api-key": k, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        raw = e.read()[:800].decode(errors="replace")
        sys.exit(f"FAIL: {e.code} {raw}\n"
                 "  (a 400 bad_prompt is usually a named artist -- the response "
                 "carries a prompt_suggestion)")
    if not data:
        sys.exit("FAIL: empty response from /v1/music")
    open(path, "wb").write(data)


def main() -> int:
    # Unknown arguments are refused, not ignored (fault 141): a typo like
    # --forc silently meant "reuse everything on disk", which reads as a
    # successful re-render.
    _bad = [a for a in sys.argv[1:] if a != "--force"]
    if _bad:
        sys.exit(f"FAIL: unrecognised argument(s) {_bad} -- this tool takes "
                 f"only --force (re-render existing cues)")
    os.makedirs(MUSIC, exist_ok=True)
    path = os.path.join(MUSIC, "sting.mp3")
    if "--force" in sys.argv or not os.path.exists(path):
        render(path, key())
        print(f"  rendered {os.path.getsize(path)/1e6:.2f} MB")

    dur = float(subprocess.run(
        [season_paths.ff("ffprobe"), "-v", "error", "-show_entries",
         "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True).stdout.strip())
    live = usable_seconds(path)
    print(f"  file {dur:.2f}s, audible to {live:.2f}s, reel uses {WANT_S:.2f}s")

    if live < WANT_S:
        sys.exit(f"FAIL: the sting stops at {live:.2f}s but the reel plays "
                 f"{WANT_S:.2f}s of it. The file is the right LENGTH and the "
                 "music is not there -- re-roll with --force.")
    print(f"  -> {path}")
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
