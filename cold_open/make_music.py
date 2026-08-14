"""One sparse cue under the whole cold open, ~32 seconds.

IT IS NOT THE BOUNTY SHOW'S STING AND IT MUST NOT SOUND LIKE IT. That cue is
brassy, cheap and pleased with itself because it is television. This is the
film, at first light, with nobody talking -- and it plays straight into the
sting four seconds after the title card, so the contrast is doing structural
work. Bright brass here would flatten the cut it exists to set up.

/v1/music RESOLVES EARLY AND PADS WITH SILENCE, and a piece asked to be "sparse"
and "spacious" is the exact wording that has caused that before. So the prompt
says outright it must play to the last second, forty seconds are bought to use
thirty-two, and usable_seconds() hard-exits if the music stops early.

NO COMPOSER NAMES -- a named living artist returns a 400 bad_prompt ToS refusal.
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

import edit
import shot
from find_voice import key

HERE = os.path.dirname(os.path.abspath(__file__))
MUSIC = os.path.join(HERE, "_music")
FF = season_paths.FFMPEG

WANT_S = sum(edit.SECS.values())
ORDER_MS = 40000

PROMPT = (
    "A slow, spare, unhurried piece for a film opening at first light on a "
    "shallow Gulf coast. A single muted trumpet playing a simple unhurried "
    "melody with a lot of air around it, over a quietly brushed upright bass "
    "and the softest possible brushed snare, with an occasional low warm "
    "electric piano chord underneath. Minor key, very slow, patient and a "
    "little melancholy but not sad -- the sound of somebody going to work early "
    "on water, who has done this many times before. Recorded warm and close in "
    "a small room, with tape noise. "
    "It plays continuously from the very first second to the very last second "
    "of the audio at a steady level. Do not fade out, do not stop early, do not "
    "ritardando, and leave no silence at the beginning or the end. The last "
    "second is as present as the first."
)


def usable_seconds(path: str) -> float:
    """Last 0.5s window above -45 dBFS. What is AUDIBLE, not the file length."""
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
        sys.exit(f"FAIL: {e.code} {e.read()[:800].decode(errors='replace')}")
    if not data:
        sys.exit("FAIL: empty response from /v1/music")
    open(path, "wb").write(data)


def main() -> int:
    os.makedirs(MUSIC, exist_ok=True)
    path = os.path.join(MUSIC, "open.mp3")
    if "--force" in sys.argv or not os.path.exists(path):
        render(path, key())
        print(f"  rendered {os.path.getsize(path)/1e6:.2f} MB")

    dur = float(subprocess.run(
        [season_paths.ff("ffprobe"), "-v", "error", "-show_entries",
         "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True).stdout.strip())
    live = usable_seconds(path)
    print(f"  file {dur:.2f}s, audible to {live:.2f}s, "
          f"cold open needs {WANT_S:.2f}s")
    if live < WANT_S:
        sys.exit(f"FAIL: the cue stops at {live:.2f}s against a {WANT_S:.2f}s "
                 "cold open. Right length, no music -- re-roll with --force.")
    print(f"  -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
