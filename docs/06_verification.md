# 06 — How to check work, and how to check the check

In this domain you cannot see or hear the artifact, so every claim about it
reduces to a number. That makes the *metric* a piece of software with its own
bugs — and a broken metric is worse than none, because it produces a confident,
precisely-quantified falsehood.

Roughly half the wasted time in the reference season went to trusting a
measurement that was measuring something else.

---

## The four rules

### 1. A metric must measure what its label claims

An envelope check reported each beat's median RMS and its 10th percentile,
labelled the latter "noise floor", and warned when speech sat under 12 dB above
it. It fired: *"02 has only 9.4 dB between speech and room tone — the hiss will
be audible."*

**It was wrong and the number was real.** Those beats are near-continuous speech
— one talks for 5.84 s of 5.875 s — so the 10th-percentile window lands *inside
the dialogue*. It was measuring normal speech dynamics and libelling them as
noise.

Fixes that generalise:
- Read a floor only from windows **outside** the measured speech spans, and print
  `n/a (N non-speech windows)` when there are too few. An honest gap beats a
  confident wrong number.
- Keep **balance** (do the parts sit at the same loudness — always measurable)
  separate from **floor** (how loud is the hiss — needs actual silence).
- **When a check fires, verify the metric before reporting the finding.**

### 2. Validate a proxy where you USE it, not where it is convenient

A mouth-aperture metric correlated 0.47–0.59 against a known reference on clean
renders and **0.07–0.23** on the same content after the CRT pass. A reading of
"250–500 ms late" taken from the treated footage was noise.

Later, a *different* metric — per-frame motion energy — confidently identified
the wrong picture source for a delivered file. Its control (the two candidate
sources being uncorrelated with each other, r = 0.02) proved only that it could
discriminate **on clean footage**. Through the treatment it could not.

**Run the control on the treated artifact.** And when a proxy disagrees with a
build log, look at two frames before believing either.

### 3. Any threshold on photographic content needs a control run

A leak-checker rendered a rotated frame against a red fill and counted red
pixels: 1242 intrusions, confident FAIL. The same detector on the **flat** render
— no rotation at all — reported 1220, because the photograph has red knots in it.
It was measuring the picture.

**The version that needs no threshold: render the identical move twice with two
different fill colours and difference them.** Picture pixels are identical in
both; fill pixels differ by construction.

Same family: a near-black end card is a useless grain probe, because ±3 luma of
noise on black sits under the quantizer and reads 0.000 whether the filter is
there or not. Probe grain in a flat **mid-tone** region.

### 4. A search returns the least-bad point inside its grid, never "no idea"

A drift detector reported `1.000 solid` for a clip that visibly pushes from
chest-up to a tight head. Partly the range capped too low, partly a confidence
threshold that called 12 % relief solid — but fundamentally the move was a zoom
*plus a translation* and a centre-crop model cannot represent that at any range.

- **Peg detection**: a winner sitting at either end of the grid is the search
  running out of room, not a measurement.
- **A low-confidence row means "go and look", not "it's fine".**
- **If a checker's numbers are advisory, its summary line must say so.** A
  summary that overstates its evidence is the same silent-green failure as a
  checker that matches nothing.

---

## Known-bad metrics in this codebase

| Metric | Why it lies |
|---|---|
| F0 **pitch spread** in `audition.py` | Search band is 70–300 Hz, asymmetric about an older man's fundamental: octave-halving errors fall below 70 and get clipped, octave-doubling lands at 170–240 and survives. Artifacts only ever inflate. Diagnose with `p90/p50` in Hz — 2.00 is a clean octave error; it ran 1.17–1.80. **Rank casting on PACE instead**, which involves no estimation. |
| **Mouth aperture** under any treatment | See rule 2 |
| **Motion-energy source ID** on graded footage | See rule 2 |
| **"Step at the join" level check** | Never changes sign — it is measuring the fade at the end of every part, not a mismatch. A real mismatch scatters around zero |
| Any **automatic mouth locator** on short clips | Three methods failed: a fixed crop band (framings differ), "the region the model changed" (dominated by resampling noise — the boxes land on filing cabinets), and per-cell motion vs audio RMS (128 cells against ~50 samples hits r = 0.5 by chance). **Six frames straddling the boundary, looked at, is the gate that works.** |

---

## What to verify, and when

### Before spending money
- Every duration check reads the **measured JSON** and prints which source it
  used, so there is no way to spend while silently running off word-count
  guesses.
- The whole plan validates before the first submission — a missing table entry
  that crashes after the balance check has already cost you.
- Auth is **stable**, not merely working: probe it three times. A 401 during
  *polling* bills for a result that never arrives.

### After every bake
- Frame count against the edit. `assemble.py` asserts it.
- Mix sample count against the picture. `normalize()` asserts it.
- Loudness and true peak, printed.

### Before the join
- Codec, geometry, frame rate, pixel format identical across all parts
  (`feature.py`). A concat demuxer given a mismatch does not fail.
- Every PCM mix's duration against its own part's picture, 2 ms tolerance.

### On the delivered file, not the intermediate
This is the one people skip. Several bugs passed every intermediate check:
- The mix that was 16 samples short passed the picture-vs-cut check, because
  that check measured the silent intermediate.
- The AAC priming drift is invisible inside every part and only appears in the
  assembled feature.
- The wrong picture source is perfectly self-consistent.

**Grab frames and audio out of the delivered mp4.**

### Before publishing
```
python preflight.py     # is any of this still the template's content?
python parts.py         # does the season describe itself consistently?
```

---

## Writing a new check

- Make it **refuse**, not warn, when the invariant is structural.
- Make it **print what it measured**, not just its verdict. A count printed after
  a twenty-minute bake is a report; the same count printed before the loop is a
  guard.
- Give it a **self-test** where it can have one. The glyph detector refuses to
  vouch for a font unless a known-absent glyph looks absent to it.
- **Never `except: pass`.** If a check cannot run, that is a failure, not a pass.
- Say **how decisive** the result was. "The best lag was only 1.3× better than a
  random one" is a useful sentence; presenting that as a measurement is not.
