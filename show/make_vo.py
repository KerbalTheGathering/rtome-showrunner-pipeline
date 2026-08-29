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
34 of its takes against the actual signature (peak in the final 10 ms over peak
in the preceding 100 ms) and found it in ZERO of them.

`assemble.tail_spike()` asks the question per take now, and `vo_tail()` trims
only where the answer is yes. A take with no transient gets a 10 ms fade and
keeps every sample -- which is the right fix for what is actually wrong with
those takes, a file ending on non-zero energy against digital silence, i.e. a
discontinuity rather than a spike.
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
        # THE ROLE IS THE LABEL AND THE LOOKUP IS THE ID. This read
        # `who = "DALE"` -- the PREVIOUS presenter's name, typed, printed
        # against every take of a reel he is not in, in the one column whose
        # whole job is to say which voice you are listening to. A label that
        # cannot be wrong is worth more than a pretty one.
        voice = script.voice_of(role)
        who = role
        path = os.path.join(dest, f"{lid}.mp3")
        if only and lid not in only:
            if os.path.exists(path):
                total += dur(path)
            continue
        if os.path.exists(path) and not force:
            d = dur(path)
            total += d
            rows.append((lid, sid, who, style, d, text, "on disk"))
            continue
        render(voice, text, style, path, k)
        d = dur(path)
        total += d
        rows.append((lid, sid, who, style, d, text, "rendered"))

    print(f"  {'line':>4} {'beat':>4}  {'voice':<7} {'sty':>4} {'secs':>6}")
    for lid, sid, who, style, d, text, state in rows:
        body = text[text.index("]") + 2:] if "]" in text else text
        print(f"  {lid:>4} {sid:>4}  {who:<7} {style:>4.2f} {d:>6.2f}  "
              f"{body[:58]}{'...' if len(body) > 58 else ''}  [{state}]")

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

    # PER SEGMENT, BECAUSE A FORMAT IS A THING THAT DOES NOT CHANGE SHAPE. The
    # copied version printed one whole-film total against a fixed budget, which
    # is the wrong question here: what matters is that the format segments come
    # out the SAME length, and that the break is allowed to be short in words
    # while running long on screen.
    per: dict[str, float] = {}
    for lid, sid, *_ in script.LINES:
        p = os.path.join(dest, f"{lid}.mp3")
        if os.path.exists(p):
            per[sid] = per.get(sid, 0.0) + dur(p)
    print()
    for sid in script.SIDS:
        s = per.get(sid, 0.0)
        # Each segment also carries a lead into the first line, gaps between
        # lines and a tail under the handoff -- call it ~2.5s of air on top.
        mark = " " if sid in script.FORMAT_SIDS else "*"
        print(f" {mark}segment {sid}: {s:5.2f}s speech  -> ~{s + 2.5:5.2f}s "
              f"on screen")
    # NAMED, NOT SLICED. `script.SIDS[:5]` compared the first five segments of
    # whatever the reel happened to be, which on any reel that is not this one
    # silently averages the break in with the format it is supposed to differ
    # from -- and on a reel of four, compares four things to nothing.
    body = [per.get(s, 0.0) for s in script.FORMAT_SIDS]
    if body:
        spread = max(body) - min(body)
        print(f"\n  the format ({len(body)} segment(s)) spans "
              f"{min(body):.2f}-{max(body):.2f}s ({spread:.2f}s apart)")
        if spread > 2.5:
            print(f"  !! that is a visible difference in a thing that repeats "
                  f"{len(body)} times -- even them up by cutting WORDS from "
                  f"the longest")
    print(f"  reel total ~{sum(per.values()) + 2.5 * len(script.SIDS):.0f}s "
          f"across {len(script.SIDS)} slot(s)   (* = the break)")
    print(f"  -> {dest}")
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
