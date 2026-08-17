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

import script
from find_voice import key

HERE = os.path.dirname(os.path.abspath(__file__))
VO = os.path.join(HERE, "_vo")
ALT = os.path.join(HERE, "_vo_alt")
FF = season_paths.FFMPEG


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
    only = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--line=")]
    k = key()
    os.makedirs(dest, exist_ok=True)

    total, rows = 0.0, []
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
            continue
        if os.path.exists(path) and not force:
            d = dur(path)
            total += d
            rows.append((lid, sid, role, style, d, text, "on disk"))
            continue
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
