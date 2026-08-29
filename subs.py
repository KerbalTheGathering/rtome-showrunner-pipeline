"""THE SUBTITLES: a sidecar .srt for the whole feature, built from the edit.

NOT A TRANSCRIPTION. Every line's text is the line the voice was given and
every line's position is the offset the assembler placed it at, so the file
cannot drift from the film the way a machine transcript does -- and the radio
lane, which auto-captioning mangles, comes out exactly right.

NOT BURNED IN. This writes a sidecar YouTube (or any player) can switch off;
the picture is untouched.

    python subs.py                 # out/<slug>.srt  and  out/<slug>.vtt
    python subs.py --sdh           # add [MUSIC] / [RADIO STATIC] style cues
    python subs.py --check         # report timing, overlaps and long lines only

WHO IS SPEAKING. A voice the audience cannot see gets a label; a character
on screen does not. Who is on screen is `script.ON_SCREEN` -- the same table
h3_shoot.py drives the lip-sync driver from, so the two cannot disagree about
who the audience can see. A tree without that table labels nobody.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parts                                                       # noqa: E402
import season_identity as season                                   # noqa: E402
import season_paths                                                # noqa: E402

OUT = os.path.join(HERE, "out")

# HOW A ROLE READS ON SCREEN, where the role id is not what an audience should
# be shown ("capcom" is a job, "FLIGHT CONTROL" is a voice). A role absent from
# here is upper-cased as it stands. A role in `script.ON_SCREEN` gets no label
# at all, whatever this says -- we can see them.
#
# A voice that belongs to a character but is NOT the room talking (a narrator,
# a voice in his head, a recording of himself) still wants a label, and it
# belongs here: the audience cannot tell those apart by ear alone.
LABELS: dict[str, str] = {
    # "capcom": "FLIGHT CONTROL",
}

WRAP = 42          # characters per line: the width players lay out comfortably
MAX_LINES = 2
MIN_SECS = 1.0     # nobody can read a flash
PAD = 0.10         # a beat of hang time, never into the next line


def clean(text: str) -> str:
    """The spoken words only.

    The scripts carry ElevenLabs delivery tags ("[cheerful]", "[whispers]")
    that steer the read and are NOT words anybody says. A subtitle that prints
    them is a bug the audience can see.
    """
    t = re.sub(r"\[[^\]]*\]", " ", text)
    t = t.replace("--", "—").replace("...", "…")
    return re.sub(r"\s+", " ", t).strip()


def wrap(text: str) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > WRAP:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    # A cue is at most MAX_LINES; anything longer is split into more cues by
    # the caller, which is why this returns every line rather than truncating.
    return lines


def stamp(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def probe(path: str) -> float:
    out = subprocess.run(
        [season_paths.ff("ffprobe"), "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True).stdout.strip().rstrip(",")
    return float(out)


def tree_rows(folder: str, sid: str | None) -> list[dict]:
    cmd = [sys.executable, os.path.join(HERE, "subs_probe.py")]
    if sid:
        cmd += ["--sid", sid]
    r = subprocess.run(cmd, cwd=folder, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"FAIL: subs_probe in {folder} exited {r.returncode}\n"
                 f"{r.stderr[-1200:]}")
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        sys.exit(f"FAIL: subs_probe in {folder} printed no JSON\n"
                 f"{r.stdout[-600:]}\n{r.stderr[-600:]}")


def collect() -> list[dict]:
    """Every spoken line in the feature, in order, with feature-absolute times."""
    cues, t = [], 0.0
    for label, mp4, _wav in parts.running_order():
        if not os.path.exists(mp4):
            sys.exit(f"FAIL: {label} is not built ({mp4}) -- subtitles are cut "
                     "against the delivered parts, so build first.")
        secs = probe(mp4)
        folder, sid = None, None
        if label == "COLD OPEN":
            folder = parts.cold_open_dir()
        elif label.startswith("interstitial"):
            folder, sid = parts.show_dir(), label.split()[-1]
        elif label == "CREDITS":
            folder = None                       # a roll says nothing
        else:
            folder = next((r["path"] for r in parts.audit()[0]
                           if (r["title"] or r["dir"]) == label), None)
            if folder is None:
                sys.exit(f"FAIL: no tree for part {label!r}")
        if folder:
            for row in tree_rows(folder, sid):
                txt = clean(row["text"])
                if not txt:
                    continue
                # A LINE MUST FIT INSIDE ITS OWN PART. If a tree's offsets run
                # past the picture it produced, the edit and the delivered part
                # disagree -- and every later part's subtitles would be wrong
                # too, silently, because the offsets are cumulative.
                if row["start"] + row["dur"] > secs + 0.25:
                    sys.exit(
                        f"FAIL: {label}: line {row['lid']} ends at "
                        f"{row['start'] + row['dur']:.2f}s but the part is only "
                        f"{secs:.2f}s\n  The edit and the built part disagree; "
                        "rebuild that part before cutting subtitles.")
                cues.append({"start": t + row["start"],
                             "end": t + row["start"] + row["dur"],
                             "role": row["role"], "text": txt,
                             "on_screen": row.get("on_screen", []),
                             "part": label, "lid": row["lid"]})
        t += secs
    cues.sort(key=lambda c: c["start"])
    return cues


def shape(cues: list[dict]) -> list[dict]:
    """Label, split and de-overlap. The last stop before the file."""
    out = []
    for c in cues:
        lab = "" if c["role"] in c.get("on_screen", ()) else             LABELS.get(c["role"], c["role"].upper())
        # THE LABEL IS WRAPPED WITH THE WORDS, NOT GLUED ON AFTERWARDS. Added
        # after the wrap, it pushed the first line of every radio cue past the
        # width, and a player then broke that line wherever it liked.
        lines = wrap(f"[{lab}] {c['text']}" if lab else c["text"])
        # one cue per MAX_LINES lines, sharing the take's time by line count
        chunks = [lines[i:i + MAX_LINES] for i in range(0, len(lines), MAX_LINES)]
        span = (c["end"] - c["start"]) / max(1, len(chunks))
        for k, ch in enumerate(chunks):
            out.append({"start": c["start"] + k * span,
                        "end": c["start"] + (k + 1) * span,
                        "text": "\n".join(ch), "part": c["part"], "lid": c["lid"]})
    # FLOORS FIRST, THE DE-OVERLAP LAST -- the order is the fix (fault 114).
    # This used to clamp to the next cue's start and THEN apply a 0.4s
    # readability floor, so whenever two cues began within ~0.42s -- which
    # chunk-splitting a wordy take guarantees -- the floor pushed the end
    # straight back over the start it had just been pulled off, and the
    # overlapping cues were written to the file. The docstring's contract is
    # "the last stop before the file"; the last operation must be the one
    # the file cannot ship without.
    for i, c in enumerate(out):
        c["end"] = max(c["end"], c["start"] + MIN_SECS) + PAD
        if i + 1 < len(out):
            c["end"] = min(c["end"], out[i + 1]["start"] - 0.02)
            # A cue squeezed to nothing means the chunk arithmetic gave two
            # cues one instant -- keep it visible, never past its successor.
            c["end"] = max(c["end"], c["start"] + 0.05)
    return out


def write(cues: list[dict]) -> tuple[str, str]:
    os.makedirs(OUT, exist_ok=True)
    srt = os.path.join(OUT, f"{season.SEASON_SLUG}.srt")
    with open(srt, "w", encoding="utf-8") as fh:
        for i, c in enumerate(cues, start=1):
            fh.write(f"{i}\n{stamp(c['start'])} --> {stamp(c['end'])}\n"
                     f"{c['text']}\n\n")
    vtt = os.path.join(OUT, f"{season.SEASON_SLUG}.vtt")
    with open(vtt, "w", encoding="utf-8") as fh:
        fh.write("WEBVTT\n\n")
        for c in cues:
            fh.write(f"{stamp(c['start']).replace(',', '.')} --> "
                     f"{stamp(c['end']).replace(',', '.')}\n{c['text']}\n\n")
    return srt, vtt


def main() -> int:
    cues = shape(collect())
    if not cues:
        sys.exit("FAIL: no spoken lines found -- has anything been built?")
    # THE DEFECT IS A LINE WIDER THAN THE WRAP, not a full two-line cue: a cue
    # that uses both of its lines is doing its job.
    long_ones = [c for c in cues
                 if max(len(ln) for ln in c["text"].split("\n")) > WRAP]
    overlaps = [(a, b) for a, b in zip(cues, cues[1:]) if b["start"] < a["end"]]
    last = cues[-1]
    print(f"  {len(cues)} cues, {cues[0]['start']:.1f}s .. {last['end']:.1f}s")
    print(f"  {len(long_ones)} line(s) wider than {WRAP}, {len(overlaps)} overlaps")
    for c in long_ones[:5]:
        print(f"    wide  {c['lid']}: {c['text'][:70]}...")
    voices = sorted({c["text"][1:c["text"].index("]")] for c in cues
                     if c["text"].startswith("[")})
    print(f"  labelled voices: {', '.join(voices)}")
    if "--check" in sys.argv:
        return 0
    srt, vtt = write(cues)
    print(f"\n  -> {srt}\n  -> {vtt}")
    print("  Upload the .srt in Studio > Subtitles; the picture is untouched.")
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
