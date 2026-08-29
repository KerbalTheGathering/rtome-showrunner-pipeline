---
name: publish-and-deliver
description: Join the season into the feature and land it in the delivery folder - credits, feature join, subtitles, share cut, final QC. Use when a season's parts are built and it is time to assemble, publish, deliver, or export the finished film.
---

# Publishing the season

Every part built (`python parts.py` shows no `*`)? Then, in order:

```bash
python credits.py            # optional: the roll is a PART; skip if the season has none
python feature.py --check    # every part's codec/geometry/rate agree; mixes match picture
python feature.py            # the join: picture stream-copied, audio rebuilt once from PCM
python show/qc_feature.py    # sample the FINISHED file at every seam (if there is a show)
python show/audio_qc.py      # loudness per part -- the spread is what viewers feel
python show/sync_probe.py    # driver vs shipped lag; the only passing value is zero
python subs.py               # sidecar .srt/.vtt cut from the edit, not a transcript
python publish.py --check    # say what would land where, touch nothing
python publish.py            # feature + lanczos share cut -> the delivery folder
```

## The rules of this phase

- **A join failure is a fact about ONE part.** `feature.py` names the odd
  one out — fix that part; never re-encode the season to paper over a
  mismatch.
- **Measure the DELIVERED file.** True peak on the mix wav is not true peak
  on the mp4 (fault 97); `qc_feature.py` and `audio_qc.py` read what ships.
  Above −1.0 dBTP a lossy transcode can clip on playback.
- **Listen where feature.py says.** Its dead-air notes are tripwires: a
  pause over 2 s is legal, but somebody's ears go there before publishing.
  Ears are the filmstrip of the mix.
- **Never copy to the delivery folder by hand.** `publish.py` exists so
  every rebuild lands in the same places with the same names — a hand copy
  is how the delivery folder accumulates two versions of one film. All
  names derive from `season_identity.py` (`$SEASON_DELIVER` overrides the
  destination).
- **The share cut is lanczos on purpose** — a naive downscale folds the
  scanline back as crawling moire. Don't "simplify" it.

The verification rules behind all of this are `docs/06_verification.md`;
the audio chain and the join are `docs/03_audio.md`.
