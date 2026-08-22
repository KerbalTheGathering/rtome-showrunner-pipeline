# 03 — Audio: loudness, sync, and the join

The single rule everything here follows:

> **Nothing in the delivery chain may have lookahead.**
>
> A filter with an `attack` time delays what it passes. On a film that is
> merely inconvenient. On a shot whose mouths were *generated from* the
> waveform, the picture is a function of the audio, so any offset at all is a
> sync error by construction rather than a tolerance.

---

## The chain, and why each stage is what it is

```
mix graph  ->  volume=<static dB>  ->  asoftclip hard  ->  aresample  ->  apad,atrim=end_sample
```

Measured delay, single-sample impulse at 48 kHz:

| filter | samples late |
|---|---|
| `alimiter=attack=5:release=50` | **239** — and the file does not lengthen, so the tail is lost |
| `asoftclip=type=hard:oversample=1` | **0** |
| `aresample` 96 k → 48 k | **0** |

`asoftclip=type=hard` is **bit-identical below its threshold** — verified against
a −20 dBFS tone, 0 differing samples out of 96 000 — so it is a ceiling, not a
grade. It does what a limiter does, minus the bug.

### Do not buy the ceiling by lowering the gain instead

Tried and rejected. One driver peaks at 0.0 dBFS, so fitting the raw sample peak
put that part at **−18.6 LUFS against −16.0** for the five around it. Clip the
handful of samples that poke through; warn if the clip is doing more than
shaving transients (`QUIET_WARN` in `assemble.py`).

---

## A local score: ACE-Step (`score.py`)

The ninth season scored itself on ACE-Step 1.5 XL, on the same GPU, for
nothing ($0.15/min on ElevenLabs Music). `score.render(name, secs, cue,
out_dir)` runs the bundled turbo graph (8 steps, cfg 1) and returns an mp3 with
at least `secs` of live music. What is not obvious:

- **`TextEncodeAceStepAudio1.5` pins bpm, key and time signature.** Cues are
  generated independently, so the KEY FAMILY is what makes them one score --
  pick one key for the film's world and its relative for the other side.
- **It fades out ~8 s before the requested end.** `PAD = 15` and
  `usable_seconds()` measures where the music actually stops; the template's
  rule that a file of the right length can still end in digital silence
  applies.
- **LRA varies by seed** (17.5 -> 9.3 on a re-roll of the same cue). Measure
  before the bus fights it.
- **A `{"silent": True}` cue writes `anullsrc` of the right length.** The mixer
  needs a file for every span; a span under nothing is an editorial choice,
  not a missing cue, and the tables should be able to say so.
- **Restart ComfyUI before the next H3 pass** -- the resident weights thrash
  it (`docs/02_traps.md`, fault 60).

## Getting the score out of the way: by signal, or by plan

`identity.MIX` names one of `mixes.py`'s buses, and the choice that matters is
whether the duck follows the **waveform** or the **edit**.

`ducked` sidechains the score to the voice bus. It is the carried arrangement
and the right default for anything narrated: the duck follows the actual signal,
so a loud line pushes the music further down than a quiet one.

**`under` draws the same duck from the edit instead, and for this pipeline that
is often the better answer.** The edit already states the exact second every
take begins and how long it runs — `assemble.mix()` hands those spans to the bus
— so there is nothing to infer from the signal. Measured on the toy film
`python mixes.py --graph` builds, lines at 4.0–6.0 s, 6.5–8.0 s and 20.0–23.0 s:

| t | gain | |
|---|---|---|
| 0.00 | 0.550 | before any line |
| 3.85 | 0.165 | **fully ducked 0.15 s before the word**, not after a compressor notices it |
| 6.25 | 0.165 | **still down between two lines 0.5 s apart** — spans closer than `2×(pad+ramp)` merge, so it cannot swell inside a sentence |
| 9.00 | 0.550 | back up |

Three things follow from having no sidechain:

- It **cannot be fooled by a breath or a hard consonant**, and the film's floor
  does not wander with the performance.
- It ducks around **silence a sidechain cannot see** — a beat where somebody is
  clearly about to speak stays down through the pause.
- It has **no sidechain input to be bounded by**. `sidechaincompress` is bounded
  by its key, which is how the ducked score once stopped when the last take did
  and `-shortest` took forty frames of picture with it. `under` cannot reach that
  fault; `ducked` pads its key to the full length to avoid it.

The cost is that it is the same dip every time, whatever the take is doing. That
is the point of it — pick by whether the film wants the score to react or to
behave.

---

## Loudness

Target: **−16.0 LUFS integrated, −1.5 dBTP true peak**, ceiling −2.0 dBFS.

**`loudnorm` in single-pass form is ADAPTIVE with no lookahead.** It starts from
a guess and converges over about five seconds, so every part opens ~2.1 dB quiet
and ramps up. Thirteen parts is thirteen fade-ups, one at every cut — and **no
static measurement of the finished file can see it**, because the integrated
number comes out correct either way.

**The test that finds it:** render the same mix graph twice, once with the
filter replaced by `anull`, and difference the two short-term
(`ebur128=framelog=verbose`) tracks. Keep the filter in a module-level constant
so it *can* be swapped; welded into an f-string it is untestable.

```
0-2s +1.84 dB   2-5s +2.88   5-10s +3.90   10-121s +3.9..+4.2
```

**`linear=true` does not fix it and fails silently.** Asked for a static move it
refuses and falls back to dynamic, reproducing the ramp exactly (−2.11 vs
−2.12). Its own JSON says why: −19.90 LUFS with a −3.69 dBTP peak means the
+3.90 dB needed would land at +0.21 dBTP. **If you ever use loudnorm, parse
`Normalization Type` out of pass two and shout if it says dynamic.**

What works: separate gain from ceiling. One static `volume=NdB` for the whole
file, then the hard clip. Result across the reference feature: opening deficit
−2.12 → −0.55 dB, integrated spread across parts 1.1 → 0.3 LU, LRA slightly *up*
(a static gain compresses nothing).

---

## Length: pin every mix to an exact sample count

`atrim=0:{secs:.3f}` truncates to three decimals. A 2918-frame film is
121.583333 s and the mix came out 121.583000 s — **sixteen samples short** — so
`-shortest` refused to emit a video frame it could not cover and the part shipped
with picture 41 ms shorter than sound.

```python
want = int(round(secs * RATE))
... "apad,atrim=end_sample={want}"
assert probed_duration_ts == want      # and it must be an assert
```

**`atrim=end_sample` counts in the FILTER GRAPH's rate, not the output's.** Two
parts built their bus at 96 kHz while the target was computed at 48 k, and the
cold open came out **13.77 s of a 27.54 s picture**. Resample *before* trimming
so the units mean one thing everywhere.

---

## The join: AAC priming accumulates

Every AAC stream carries an encoder priming delay (~2048 samples) a decoder is
meant to discard. Stream-copy thirteen parts together and the concat demuxer
stacks thirteen of them. Measured part-start offsets in a delivered feature:

```
+10, +20, +57, +72, +88, +105, +118, +138, +154 ms
```

A constant **per join**, not per second — invisible inside any one part, a sixth
of a second by the back half. At 48 kHz each priming is ~43 ms where 96 kHz made
it ~21 ms, so **consolidating onto one delivery rate is itself a sync change.**

Three layers were tried; only the last worked:

1. `-c copy` → concat **filter** for audio: +232 → +72 ms. Not enough — thirteen
   AAC *decodes* still inherit thirteen priming allowances.
2. Feed the filter the **PCM mixes** instead of the parts' AAC: worst offset
   **±10 ms, scattering around zero**. Noise, not drift.
3. Picture stays `-c:v copy`. Only the sound is re-encoded, once.

**Guard it:** assert each wav's length against its part's *video* duration
(`feature.py` does, at 2 ms tolerance), because a stale wav puts a whole part's
sound under the wrong film silently.

**A per-part check cannot find any of this.** Inside every film the VO measured
exactly where the edit put it. The only measurement that sees it correlates each
part's audio against the assembled feature at its cumulative offset.

---

## Measuring sync

`show/sync_probe.py` is the tool. It correlates the **energy envelope** (10 ms
frames, log RMS, mean-removed) rather than the waveform, because the delivered
mix is a different gain, a different rate, and has music the driver never had.
Exclude the music window or it drags the peak toward itself. Parabolic
interpolation around the peak gives sub-frame resolution.

Passing value for a lip-synced part is **zero**, not "small" — every stage
between the driver and delivery is a scalar or a copy, and a scalar cannot
produce a lag. Reference season after the fix, measured inside the assembled
14.4-minute feature: −0.0, +0.1, +0.3, +0.1, −0.0, +0.1 ms.

---

## EQ, if you touch it at all

**Measure the STEMS, not the mix.** A finished mix's average spectrum is mostly
whichever of voice or bed is louder, so "the voice is boxy" read off the
delivered file is a statement about the score.

**Normalise to energy per octave.** Summing raw FFT bins into bands makes a wide
band look loud for no reason but its width — 200–500 Hz and 2–5 kHz differ
tenfold. And sampling a coarse grid off a smooth curve invented an "18 dB notch
at 1 kHz" that was just the F1/F2 dip. Print the full third-octave curve before
believing any single band. Tools: `show/audio_qc.py`, `show/_probes/audio_tone.py`.

---

## Small measured constants

- **ElevenLabs music does not move `character_count`.** `/v1/user/subscription`
  showed the identical figure before and after six generated cues. That meter
  is TTS characters and nothing else, so it cannot be used to price a score —
  and do not read its stillness as "music is free" either. If cost matters,
  find out what actually meters it before generating a season's worth.
- **`/v1/music` resolves when it feels finished and pads the rest of the
  requested length with digital silence.** The mp3 is then exactly as long as
  you asked for, every duration check passes, and the end of the film plays
  under nothing. `make_music.usable_seconds()` measures where the music
  *stops*, which is the artifact-not-intent rule pointed at a file length.
- **Mono → stereo upmix costs ~3.4 dB** out of ffmpeg
  (`aformat=channel_layouts=stereo`). Compensate at the source, not with a
  second correction after the encode.
- **Source levels vary hugely between clips of one shoot** (−16.3 to −36.5 dB
  mean on one H3 batch), so per-beat gain solving is mandatory, not a
  refinement.
- **`rubberband` is only mostly length-preserving** — one beat came back
  sample-exact, another lost 78 ms of 5.888 s (1.3 %), which puts the voice
  78 ms ahead of the mouth by the end. Re-stretch with `atempo=d_out/d_in`; do
  not pad with silence, the speech inside is genuinely compressed.
- **Pitch matching must be closed-loop.** `ratio = target/measured` under-delivers
  (157 Hz asked down to 125 arrived at 139) because frames above the estimator's
  ceiling get excluded from the original and drop back into band once shifted.
  Widen the search band, then iterate — re-shifting the **original** each pass so
  artifacts do not compound.
- **A "step at the join" metric that never changes sign is measuring the fade.**
  Every part ends on a fade and begins at level, so all twelve differences were
  positive and the number was the fade length. A real mismatch scatters around
  zero.
