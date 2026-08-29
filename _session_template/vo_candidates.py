"""Render VO candidates for ONE line into _vo_alt, measure them, install nothing.

WHY THIS EXISTS. make_vo.py's own rule is that a take's duration sizes its beat
and the beat sizes the clip, so re-rendering straight over `_vo/` silently
changes the edit. Candidates belong in `_vo_alt` until one has been chosen.

WHAT IT MEASURES, AND WHY IT IS NOT JUST LENGTH. The film's last line -- the
bird's "Say it again" -- came back 0.640s with speech running to the FINAL
SAMPLE and no trailing pad at all. assemble.py destroys the tail of every take
to kill eleven_v3's trailing transient, so a take with no pad loses real speech.
The fix at mix time is now measured rather than fixed, but the better fix is a
take that HAS a pad. So what matters here is:

    speech seconds   -- is the delivery actually slower, or just padded?
    trailing silence -- is there room for the fade to land on?

A candidate that is longer only because it has 300ms of silence bolted on is
still the right answer for this problem; one that is longer because the words
are slower is a better one. Both are reported so the choice is made on the
numbers rather than on the total.

    python vo_candidates.py           # render and measure
    python vo_candidates.py --install b   # copy candidate b over _vo/15.mp3
"""

import os
import shutil
import subprocess
import sys

import numpy as np

# THE SEASON ROOT, THEN THIS TREE. `import edit` puts season_paths in
# sys.modules and that is NOT the same thing as putting it in this module's
# namespace: every use of season_paths below was a NameError, in three copies
# of this file, on the first frame anybody tried to shoot. smoke.py exists
# because nothing else in the repo could see it.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import season_paths  # noqa: E402
import identity  # noqa: E402
import make_vo   # noqa: E402
import script    # noqa: E402
from find_voice import key  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
VO = os.path.join(HERE, "_vo")
ALT = os.path.join(HERE, "_vo_alt")
FF = season_paths.FFMPEG

# WHICH LINE IS BEING RE-ROLLED. `LID = "15"` was line fifteen of the film
# this file was copied from -- a line id resolves in a film that has fifteen of
# them and does not resolve at all in one that does not, and neither answer is
# the line you meant. It defaults to the LAST line, which is what a tail-shaping
# re-roll is nearly always for, and takes an id on the command line.
#
#     python vo_candidates.py            # the last line of the film
#     python vo_candidates.py 07         # that one
def pick_lid() -> str:
    want = [a for a in sys.argv[1:] if not a.startswith("-")
            and a not in ("a", "b", "c", "d")]
    if not script.LINES:
        sys.exit("FAIL: this film has no lines to re-roll.")
    if not want:
        return script.LINES[-1][0]
    if want[0] not in script.BY_ID:
        sys.exit(f"FAIL: {want[0]!r} is not a line of this film. It has "
                 f"{[ln[0] for ln in script.LINES]}")
    return want[0]


# RESOLVED IN main(), NOT AT IMPORT. `LID = pick_lid()` at module level reads
# sys.argv, which makes the module's contents depend on how the PROCESS was
# invoked -- so `import vo_candidates` from any other tool picks up that
# tool's arguments and refuses. smoke.py caught it immediately.

# THE WORDS DO NOT CHANGE -- they are THIS FILM'S line, verbatim. What varies
# is the DELIVERY DIRECTION and the punctuation that shapes the tail -- an
# ellipsis makes eleven_v3 trail off rather than stop dead, which is exactly
# the trailing room the mix needs.
#
# EXAMPLE CONTENT, AND THE ONLY CONTENT FILE THAT SPENDS MONEY ON ITS OWN.
# These candidates are the source film's closing line ("Say it again", the
# bird's). Every other content-bearing template file carries the sentinel so
# preflight can refuse; this one did not (fault 130) -- so a clone rendered
# ANOTHER film's words as candidates for its own last line, at ElevenLabs
# prices, and `--install b` would overwrite the clone's real closing take
# with them. Write this film's line here, then delete the sentinel.
EXAMPLE_CONTENT = True
CANDIDATES = {
    "a": ("[dry] Say it again.", 0.40),               # the current take, for reference
    "b": ("[dry] Say it again...", 0.40),             # trail off
    "c": ("[slowly, quietly] Say it again...", 0.30),  # slower delivery + trail
    "d": ("[dry, unhurried] Say it again.", 0.25),    # flatter, lower style
}


def measure(path: str) -> tuple[float, float, float]:
    """(file seconds, speech seconds, trailing silence seconds)."""
    raw = subprocess.run(
        [season_paths.ff("ffmpeg"), "-v", "error", "-i", path,
         "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
        capture_output=True, check=True).stdout
    x = np.frombuffer(raw, "<i2").astype(np.float32) / 32768.0
    n = len(x) / 16000.0
    win = 160
    k = len(x) // win
    if not k:
        return n, 0.0, n
    rms = np.sqrt((x[:k * win].reshape(k, win) ** 2).mean(axis=1) + 1e-12)
    live = np.nonzero(20 * np.log10(rms) > -45.0)[0]
    if not len(live):
        return n, 0.0, n
    start, end = live[0] * 0.01, (live[-1] + 1) * 0.01
    return n, end - start, n - end


def main() -> int:
    # REFUSED HERE AS WELL AS IN preflight: this tool spends money the
    # moment it runs, so it cannot wait for a render gate to notice.
    if EXAMPLE_CONTENT:
        sys.exit("FAIL: CANDIDATES is still the template's example -- another "
                 "film's closing line.\n  Rendering it costs real ElevenLabs "
                 "credit and --install would overwrite THIS\n  film's take "
                 "with it. Write this film's line into CANDIDATES and delete "
                 "the\n  `EXAMPLE_CONTENT = True` line above it.")
    LID = pick_lid()
    # THE VOICE COMES FROM THE LINE, not from a film-wide constant. A film with
    # two people in it has two voices, and re-rolling one character's line in
    # the other's voice is the kind of mistake that renders cleanly.
    VOICE = script.voice_of(script.BY_ID[LID][2])

    if "--install" in sys.argv:
        which = sys.argv[sys.argv.index("--install") + 1]
        src = os.path.join(ALT, f"{LID}_{which}.mp3")
        if not os.path.exists(src):
            sys.exit(f"FAIL: no candidate {which!r} at {src}")
        dst = os.path.join(VO, f"{LID}.mp3")
        shutil.copyfile(dst, os.path.join(ALT, f"{LID}_previous.mp3"))
        shutil.copyfile(src, dst)
        f, sp, sil = measure(dst)
        print(f"  installed {which} -> _vo/{LID}.mp3   "
              f"{f:.3f}s file, {sp:.3f}s speech, {sil:.3f}s trailing")
        print(f"  the take it replaced is kept at _vo_alt/{LID}_previous.mp3")
        return 0

    os.makedirs(ALT, exist_ok=True)
    k = key()
    cur = os.path.join(VO, f"{LID}.mp3")
    f, sp, sil = measure(cur)
    print(f"  CURRENT  _vo/{LID}.mp3   {f:.3f}s file  {sp:.3f}s speech  "
          f"{sil:.3f}s trailing")
    print(f"  {'':8s} {'file':>7s} {'speech':>7s} {'trailing':>9s}   text")
    for name, (text, style) in CANDIDATES.items():
        path = os.path.join(ALT, f"{LID}_{name}.mp3")
        if not os.path.exists(path) or "--force" in sys.argv:
            make_vo.render(VOICE, text, style, path, k)
        f, sp, sil = measure(path)
        flag = "  <-- has a pad" if sil >= 0.075 else ""
        print(f"  [{name}] {f:>7.3f} {sp:>7.3f} {sil:>9.3f}   "
              f"style {style}  {text!r}{flag}")
    print(f"\n  -> {ALT}\n  install with:  python vo_candidates.py --install <a|b|c|d>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
