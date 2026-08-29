---
name: verify-work
description: Check finished work the way this repo means it - measure the delivered artifact. Use before declaring a film, part, or feature done; when asked to QC, verify, or review output; or when a check has just passed suspiciously smoothly.
---

# Verifying work

**The rule that generates all the others: a check that does not measure the
delivered artifact is not a check.** Measure the MP4 that ships, not the
wav, the plan, or the intermediate — `docs/06_verification.md`, rules 1–9.

Per film, after `assemble.py`:

```bash
python verify.py        # devices fire when the edit says; the mix measures right
python verify_cut.py    # the frame after every join IS that beat's clip -- with a control
python qc_drift.py      # ranks joins by luma/sat jump (advisory)
```

Season level:

```bash
python feature.py --check    # every part's codec/geometry/rate agree; mixes match picture
python show/audio_qc.py      # loudness per part -- the spread is what viewers feel
python show/sync_probe.py    # driver vs shipped lag; the only passing value is zero
```

## How to read results

- **Filmstrips decide; means lie.** A numeric verdict is a tripwire telling
  you where to LOOK, not a pass. Motion is judged on six spread frames
  (`check_clip.py`), never frame one.
- **A metric is a tripwire, not a verdict** — and the answer to a tolerance
  failure is never a looser tolerance.
- **Suspiciously smooth = suspect.** Checks that pass on empty sets,
  lexicographic "latest", cached frames — the catalogue of checks that lie
  is `docs/02_traps.md` and learnings.md. If a check found nothing, ask
  what it actually measured.
- **Ears are the filmstrip of the mix.** `feature.py` prints where the dead
  air is; listen there before publishing.
