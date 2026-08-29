"""Render the narration, one file per line, and report what each one costs.

ONE FILE PER LINE, NOT ONE LONG READ. It lets the edit place each line on an
exact frame and makes every silence a directorial choice rather than whatever
the model happened to leave between sentences.

`style` IS PASSED. Older make_vo.py in other source trees does not send it at
all, and two rounds of "still a bit monotone" were once spent moving stability
and the written direction while style sat unset the whole time. It is the
strongest lever for energy and it costs nothing in duration drift.

NEVER --force THE WHOLE SCRIPT TO RE-ROLL A FEW LINES. Every line's duration
sizes its beat downstream and the beat sizes the clip, so a blanket re-render
silently changes the edit. Candidates go to _vo_alt via --alt and get installed
deliberately.

THE RAW TAKES STAY UNTOUCHED, and what happens to their tails is MEASURED at
mix time rather than assumed here.

This note used to read "EVERY eleven_v3 take has a transient glued to its final
few milliseconds" and prescribe a flat ~25 ms trim. The observation was real --
12 of 20 takes on one film, tails at 0.06-0.10 amplitude with the last 10 ms
spiking to 0.29 -- but it is a thing SOME takes do, and stating it as a property
of the vendor turned it into a rule nobody re-checked. A later fork profiled all
34 of its takes at sample level against the actual signature (peak in the final
10 ms over peak in the preceding 100 ms) and found it in ZERO of them: the flat
trim would have discarded 850 ms of real speech across that film to solve a
problem it did not have.

So `assemble.vo_tail()` looks first and trims only where there is something to
cut. What is wrong on the other takes is milder and needs a different fix: a
file that ends while low-level energy is still present, butted against digital
silence, CLICKS -- and the fix for a discontinuity is a fade, which removes no
samples at all.

If you are reading this because a line sounds cut off, measure that take before
reaching for a bigger trim.
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

import identity
import script
from find_voice import key

HERE = os.path.dirname(os.path.abspath(__file__))
VO = os.path.join(HERE, "_vo")
ALT = os.path.join(HERE, "_vo_alt")
FF = season_paths.FFMPEG


# ElevenLabs categories that mean "this is somebody's actual voice".
_CLONE_CATEGORIES = {"cloned", "professional"}
_CATEGORY_OK: set[str] = set()


def ensure_category(voice_id: str, role: str, k: str) -> None:
    """The check identity.py PROMISES, made real.

    identity's VOICE note has said "make_vo.py asserts the category" since
    the table replaced the two slots, and nothing ever did -- a comment
    claiming a check that does not exist, this repo's own named class
    (fault 111). VOICE_IS_CLONE is a licensing statement: a deliverable
    declared clone-free must not carry a cloned voice, and the API knows
    which kind an id is. Checked once per id, only on runs that render --
    a disk-only rerun stays offline.
    """
    if voice_id in _CATEGORY_OK:
        return
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/voices/{voice_id}",
        headers={"xi-api-key": k})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            cat = json.load(r).get("category", "")
    except (urllib.error.URLError, OSError) as e:
        sys.exit(f"FAIL: could not read the category of voice {voice_id} "
                 f"({e}).\n  The clone assert cannot run, so nothing renders "
                 f"-- a check that cannot run\n  has never disagreed with "
                 f"anything.")
    if cat in _CLONE_CATEGORIES and not identity.VOICE_IS_CLONE:
        sys.exit(
            f"FAIL: role {role!r} is cast on a {cat} voice ({voice_id}) and "
            f"identity.VOICE_IS_CLONE is False.\n"
            f"  A film going to anyone who holds no licence to the voice uses "
            f"a PREMADE id.\n  Recast the role, or -- for personal work only "
            f"-- set VOICE_IS_CLONE = True.")
    _CATEGORY_OK.add(voice_id)


def render(voice_id: str, text: str, style: float, path: str, k: str) -> None:
    body = json.dumps({
        "text": text,
        "model_id": "eleven_v3",
        "voice_settings": {"stability": script.STABILITY,
                           "similarity_boost": 0.75,
                           "style": style,
                           "use_speaker_boost": True},
    }).encode()
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        data=body, headers={"xi-api-key": k, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"FAIL: {e.code} {e.read()[:400].decode(errors='replace')}")
    if not data:
        # A bare tag as the whole text returns 0 bytes rather than an error --
        # a silent empty file downstream is worse than a hard stop here.
        sys.exit(f"FAIL: empty response for {text[:50]!r}")
    open(path, "wb").write(data)


def dur(path: str) -> float:
    out = subprocess.run(
        [season_paths.ff("ffprobe"), "-v", "error", "-show_entries",
         "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def main() -> int:
    force = "--force" in sys.argv
    dest = ALT if "--alt" in sys.argv else VO
    # BARE LINE IDS COUNT, GHOSTS AND UNKNOWN FLAGS ARE REFUSED (fault 141).
    # This read only --force/--alt/--line=, so `make_vo.py 03` -- the
    # spelling every sibling tool teaches -- was silently ignored and the
    # WHOLE script rendered at API cost, and a ghost --line=999 rendered
    # everything a filtered run should have skipped... nothing, and exited 0.
    only = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--line=")]
    only += [a for a in sys.argv[1:] if a.isdigit()]
    known = ("--force", "--alt")
    bad = [a for a in sys.argv[1:]
           if not a.isdigit() and not a.startswith("--line=")
           and a not in known]
    if bad:
        sys.exit(f"FAIL: unrecognised argument(s) {bad} -- a line is a bare "
                 f"id or --line=NN; anything else here renders the whole "
                 f"script at API cost")
    ghost = [l for l in only if l not in script.BY_ID]
    if ghost:
        sys.exit(f"FAIL: {ghost} are not lines of this film. It has "
                 f"{[ln[0] for ln in script.LINES]}")
    k = key()
    os.makedirs(dest, exist_ok=True)

    total, rows, absent = 0.0, [], []
    for lid, sid, role, style, text in script.LINES:
        # THE ROLE IS THE LABEL AND THE LOOKUP IS THE ID. The old version
        # printed "narrator" or "guest" -- two names for a model that could
        # only ever hold two voices -- and the show's copy of this file printed
        # a TYPED name that belonged to the previous presenter.
        voice = script.voice_of(role)
        path = os.path.join(dest, f"{lid}.mp3")
        if only and lid not in only:
            if os.path.exists(path):
                total += dur(path)
            else:
                # SAID, NOT SKIPPED (fault 134): a --line= run used to fold
                # missing takes into the total silently, and "N lines,
                # Xs of speech" understated the film with no warning.
                absent.append(lid)
            continue
        if os.path.exists(path) and not force:
            d = dur(path)
            total += d
            rows.append((lid, sid, role, style, d, text, "on disk"))
            continue
        ensure_category(voice, role, k)
        render(voice, text, style, path, k)
        d = dur(path)
        total += d
        rows.append((lid, sid, role, style, d, text, "rendered"))

    wide = max([len(r) for r in script.VOICES] + [5])
    print(f"  {'line':>4} {'beat':>4}  {'role':<{wide}} {'sty':>4} {'secs':>6}")
    for lid, sid, role, style, d, text, state in rows:
        body = text[text.index("]") + 2:] if "]" in text else text
        print(f"  {lid:>4} {sid:>4}  {role:<{wide}} {style:>4.2f} {d:>6.2f}  "
              f"{body[:58]}{'...' if len(body) > 58 else ''}  [{state}]")

    # PER ROLE, BECAUSE A SCENE IS NOT A NARRATION. With one narrator this is
    # one line and says nothing; with two people in a beat it is the first
    # place an imbalance shows up, and it costs nothing to print.
    per_role: dict[str, float] = {}
    for _l, _s, role, _st, d, _t, _state in rows:
        per_role[role] = per_role.get(role, 0.0) + d
    if len(per_role) > 1:
        print()
        for role, d in sorted(per_role.items(), key=lambda kv: -kv[1]):
            n = sum(1 for r in rows if r[2] == role)
            print(f"  {role:<{wide}} {n:>3} line(s)  {d:>6.2f}s")

    if dest is ALT:
        # An alt folder holds only candidates, so a whole-script total computed
        # over it is meaningless -- printing one anyway is the "checker that
        # passes on zero items" class of lie.
        print(f"\n  {len(rows)} candidate(s) -> {dest}")
        print("  compare with: python measure_vo.py --alt, then install "
              "deliberately")
        return 0

    n = len(script.LINES)
    if absent:
        print(f"\n  !! {len(absent)} line(s) have no take on disk and are NOT "
              f"in the total: {', '.join(absent)}")
    print(f"\n  {n} lines, {total:.1f}s of speech ({total/n:.1f}s average)")
    # The film also carries a ~3s cold open, a silent standoff and the tail
    # under the card, so picture runs ~20% over speech.
    print(f"  -> picture will land near {total*1.20:.0f}s")
    if total > 105:
        print("  !! over budget for a ~110s film -- cut WORDS, not jokes; "
              "list items read faster than sentences")
    print(f"  -> {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
