"""Cut a film to a FIXED recording: measure it, then derive the silent beats.

THE TEMPLATE'S CORE ASSUMPTION RUNS THE OTHER WAY. Everywhere else, duration
derives from narration the pipeline generates; a music video inverts that —
the audio is a finished master that cannot move, and the picture must tile it
exactly. identity.py documents the mode (`script.SILENT` + `edit.SILENT_SECS`
covering every beat) and, until this file, the numbers those tables need had
to come from a stopwatch. A film that is 0.4s short of its song does not fail
anywhere; it just ends on the wrong chord.

    python track.py analyze <song.wav>     # measure: tempo, bars, sung spans
    python track.py beats --bpm <chosen>   # derive: a beat sheet that tiles it

Both write into `_track/`; `beats` prints paste-ready `script.SILENT` and
`edit.SILENT_SECS` blocks and the numbers stay traceable to a measurement.

THREE RULES THIS FILE EXISTS TO ENFORCE, each paid for once:

* **THE TEMPO ESTIMATOR IS OFF BY AN OCTAVE AND CANNOT KNOW IT.** librosa
  locks to the eighth-note pulse on a steady drummer — 172 reported against a
  true 86 — and autocorrelation is near-tied between the two, so measurement
  cannot settle it. The tell is structural: at the wrong octave a four-minute
  rock song is 185 bars. `analyze` therefore reports BOTH candidates with
  their bar counts and `beats` REFUSES to run without an explicit `--bpm`,
  because an octave error in the bar grid is invisible until the edit is
  wrong. Record why you chose, next to the number, in the season's log.

* **GATE THE STEM, NOT THE MIX.** "Is anyone singing here" asked of a full
  mix means guessing from a band a guitar also occupies. With torchaudio
  present the record is split (HDEMUCS, overlap-faded chunks) and the vocal
  stem is gated with hysteresis; without it, the mix is gated and the JSON
  says so — treat those spans as approximate and check them by ear.

* **A TILER MUST ASSERT ITS OUTPUT IS SHOOTABLE, NOT ONLY EXACT.** The first
  one of these asserted coverage, order, gaps and sum — four greens — around
  a 32-second final beat, because the cut search ran dry and the fallback
  swallowed the whole last chorus. Cuts here come from a two-tier candidate
  list (sung-span starts first, the bar grid where the spans run thin) and
  every beat is range-asserted between MIN_BEAT and MAX_BEAT. Both tiers are
  musical; no cut lands a third of the way through a phrase.

Sung spans also mark where a LYRIC lands, which is where a cut wants to be —
but this file does not transcribe or align words. If the film must cut on
specific lines, align the writer's lyric sheet by forced alignment and
validate it against an independent transcription (median word-start delta,
not the aligner's own confidence — it scores the match to what it was TOLD).
That machinery is heavier than a template earns; the method is recorded in
learnings.md under the second music video.
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TRACK = os.path.join(HERE, "_track")
STRUCT = os.path.join(TRACK, "structure.json")
BEATS = os.path.join(TRACK, "beats.json")

# Hysteresis for "is anyone singing": enter above ON_DB (relative to the
# stem's own peak), leave below OFF_DB, ignore blips, join breaths.
ON_DB, OFF_DB = -34.0, -40.0
MIN_SUNG, JOIN_GAP = 0.45, 0.6

# What a cut can hold. MAX matters most: past ~9s a local i2v clip drifts and
# a beat that long is a beat that needs several takes.
MIN_BEAT, TARGET, MAX_BEAT = 3.4, 5.7, 9.0


def _load_audio(path: str):
    import numpy as np
    try:
        import librosa
    except ImportError:
        sys.exit("FAIL: `analyze` needs librosa (pip install librosa) -- it "
                 "is how tempo and energy are measured.")
    y, sr = librosa.load(path, sr=22050, mono=True)
    return np, librosa, y, sr


def _vocal_stem(path: str):
    """The vocal alone, via torchaudio's Demucs -- or None, honestly."""
    try:
        import torch
        import torchaudio
        from torchaudio.pipelines import HDEMUCS_HIGH_MUSDB_PLUS
        from torchaudio.transforms import Fade, Resample
    except ImportError:
        return None
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    wav, sr = torchaudio.load(path)
    if wav.shape[0] == 1:
        wav = wav.repeat(2, 1)
    wav = wav.to(dev)
    bundle = HDEMUCS_HIGH_MUSDB_PLUS
    model = bundle.get_model().to(dev).eval()
    if sr != bundle.sample_rate:
        wav = Resample(sr, bundle.sample_rate).to(dev)(wav)
    ref = wav.mean(0)
    wav = (wav - ref.mean()) / ref.std()
    seg, ov = 10.0, 0.1
    chunk = int(bundle.sample_rate * seg * (1 + ov))
    ovf = int(ov * bundle.sample_rate)
    fade = Fade(fade_in_len=0, fade_out_len=ovf, fade_shape="linear")
    mix = wav[None]
    out = torch.zeros(1, len(model.sources), *mix.shape[1:], device=dev)
    start, end = 0, chunk
    while start < mix.shape[-1] - ovf:
        with torch.no_grad():
            o = fade(model.forward(mix[:, :, start:end]))
        out[:, :, :, start:end] += o
        if start == 0:
            fade.fade_in_len = ovf
            start += chunk - ovf
        else:
            start += chunk
        end += chunk
        if end >= mix.shape[-1]:
            fade.fade_out_len = 0
    v = dict(zip(model.sources, (out * ref.std() + ref.mean())[0]))["vocals"]
    os.makedirs(TRACK, exist_ok=True)
    p = os.path.join(TRACK, "vocals.wav")
    torchaudio.save(p, v.cpu(), bundle.sample_rate)
    del model, out
    if dev.type == "cuda":
        torch.cuda.empty_cache()
    return p


def analyze(song: str) -> int:
    np, librosa, y, sr = _load_audio(song)
    dur = len(y) / sr
    t = float(np.atleast_1d(
        librosa.beat.beat_track(y=y, sr=sr, units="time")[0])[0])
    # BOTH octaves, with the structural tell beside each. Choosing is the
    # operator's job and beats() refuses until it has been done.
    cands = sorted({round(t, 2), round(t / 2, 2) if t > 120 else round(t, 2),
                    round(t * 2, 2) if t < 70 else round(t, 2)})
    stem = _vocal_stem(song)
    gated_on = "vocal stem" if stem else "MIX (torchaudio absent -- approximate)"
    ys, srs = librosa.load(stem or song, sr=22050, mono=True)
    rms = librosa.feature.rms(y=ys, frame_length=2048, hop_length=512)[0]
    db = librosa.amplitude_to_db(rms, ref=np.max(rms))
    tt = librosa.frames_to_time(np.arange(len(db)), sr=srs, hop_length=512)
    on, spans, s0 = False, [], 0.0
    for i, v in enumerate(db):
        if not on and v >= ON_DB:
            on, s0 = True, tt[i]
        elif on and v < OFF_DB:
            on = False
            if tt[i] - s0 >= MIN_SUNG:
                spans.append([round(s0, 2), round(float(tt[i]), 2)])
    if on:
        spans.append([round(s0, 2), round(dur, 2)])
    joined: list[list[float]] = []
    for a, b in spans:
        if joined and a - joined[-1][1] < JOIN_GAP:
            joined[-1][1] = b
        else:
            joined.append([a, b])
    os.makedirs(TRACK, exist_ok=True)
    json.dump({"song": os.path.abspath(song), "duration": round(dur, 3),
               "tempo_reported": round(t, 3), "tempo_candidates": cands,
               "gated_on": gated_on, "sung": joined},
              open(STRUCT, "w", encoding="utf-8"), indent=1)
    print(f"  {dur:.2f}s   sung spans: {len(joined)}   gated on {gated_on}")
    print(f"  tempo candidates -- CHOOSE ONE and pass it to `beats --bpm`:")
    for c in cands:
        bars = dur / (4 * 60.0 / c)
        print(f"    {c:7.2f} BPM  ->  {bars:6.1f} bars"
              f"  {'<- plausible for a song this long' if 40 <= bars <= 130 else ''}")
    print(f"  wrote {STRUCT}")
    return 0


def beats(bpm: float) -> int:
    st = json.load(open(STRUCT, encoding="utf-8"))
    dur, bar = st["duration"], 4 * 60.0 / bpm
    if not any(abs(bpm - c) < 1.0 or abs(bpm - 2 * c) < 1.0
               or abs(2 * bpm - c) < 1.0 for c in st["tempo_candidates"]):
        print(f"  !! {bpm} is not near any measured candidate "
              f"{st['tempo_candidates']} -- proceeding, but re-check the pin")
    starts = sorted(a for a, _b in st["sung"])
    preferred = sorted({0.0, round(dur, 3), *starts})
    grid = [round(x * bar, 3) for x in range(1, int(dur / bar) + 1)]
    cuts, cur = [], 0.0
    while cur < dur - 1e-6:
        if dur - cur <= MAX_BEAT:
            cuts.append((cur, dur))
            break
        legal = [c for c in preferred if MIN_BEAT <= c - cur <= MAX_BEAT] \
            or [c for c in grid if MIN_BEAT <= c - cur <= MAX_BEAT]
        if not legal:
            nxt = min((c for c in preferred + grid if c - cur >= MIN_BEAT),
                      default=dur)
            legal = [nxt]
        nxt = min(legal, key=lambda c: abs(c - (cur + TARGET)))
        if dur - nxt < MIN_BEAT:
            nxt = dur
        cuts.append((cur, nxt))
        cur = nxt
    # EXACT **AND** SHOOTABLE. The second half is the one the first version
    # of this pattern shipped without, around a 32-second beat.
    assert abs(cuts[-1][1] - dur) < 1e-6 and abs(cuts[0][0]) < 1e-6
    for (a, b), (c, _) in zip(cuts, cuts[1:]):
        assert abs(b - c) < 1e-6, f"gap at {b}"
    for i, (a, b) in enumerate(cuts):
        lim = MAX_BEAT + (bar if i == len(cuts) - 1 else 0.0)
        assert MIN_BEAT - 1e-6 <= b - a <= lim + 1e-6, (
            f"beat {i+1} runs {b-a:.2f}s ({a:.2f}->{b:.2f}) -- outside "
            f"[{MIN_BEAT}, {lim:.1f}]; the tiler ran out of cut points")
    out = [{"sid": f"{i+1:02d}", "start": round(a, 3),
            "secs": round(b - a, 3)} for i, (a, b) in enumerate(cuts)]
    json.dump({"bpm": bpm, "bar_seconds": round(bar, 4), "beats": out},
              open(BEATS, "w", encoding="utf-8"), indent=1)
    sids = ", ".join(f'"{b["sid"]}"' for b in out)
    print(f"  {len(out)} beats, {min(b['secs'] for b in out):.2f}-"
          f"{max(b['secs'] for b in out):.2f}s, tiling {dur:.2f}s exactly\n")
    print(f"  # script.py -- every beat is silent; the song is the voice")
    print(f"  SILENT = {{{sids}}}\n")
    print(f"  # edit.py -- lengths measured off the record, never typed")
    print(f"  SILENT_SECS = {{")
    for b in out:
        print(f'      "{b["sid"]}": {b["secs"]},')
    print(f"  }}\n  wrote {BEATS}")
    return 0


def main() -> int:
    a = sys.argv[1:]
    if a[:1] == ["analyze"] and len(a) == 2:
        return analyze(a[1])
    if a[:1] == ["beats"]:
        if "--bpm" not in a:
            sys.exit("FAIL: beats needs an explicit --bpm. `analyze` printed "
                     "the candidates and the\n  bar counts; the octave is a "
                     "decision, not a measurement -- see the docstring.")
        return beats(float(a[a.index("--bpm") + 1]))
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
