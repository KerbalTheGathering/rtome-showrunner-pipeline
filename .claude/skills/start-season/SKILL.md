---
name: start-season
description: Scaffold a new season or add a film to one. Use when starting a new film/season/project on this pipeline, cloning the template, or adding a session folder. Covers the scaffold, identity fill, and the checks that must pass before any content is written.
---

# Starting a season

**Never hand-copy a season.** A hand copy drags the previous film's
gigabytes and beat ids with it. The tool exists:

```bash
python new_season.py --to ../MY_SEASON --sessions 6   # a new season
python new_season.py --session S7_NAME                # one more film, inside a season
```

Then, in order:

1. Edit `season_identity.py` — who this season is. Everything imports it;
   every script refuses while it is blank. If you find yourself typing the
   season's title/slug/name anywhere else, stop: that move has shipped four
   silent faults (`docs/00_READ_ME_FIRST.md`, "Identity").
2. Rename `S1_UNNAMED...` and fill each film's `identity.py`. `python
   parts.py` says what is still blank; run it until it stops complaining.
3. `python smoke.py --template` — does every module in every tree execute?
4. `python residue.py` — whose beat ids and names are in here?
5. Write the films: per film, `script.py` (words) → `shot.py` (plates) →
   `edit.py` (timeline) → `motion.py`. `preflight.py` refuses to render
   while any of them still carries `EXAMPLE_CONTENT = True`.

The full order of operations end to end is `docs/01_process.md` — read it
before generating anything. The environment (`SEASON_COMFYUI`,
`SEASON_ENV`, `SEASON_COMFY_URL`, `SEASON_FFMPEG`) is verified by
`python season_paths.py`; set the variables rather than trusting defaults.

Two rules that cost money when skipped:

- **VO before video, always.** Every duration derives from the measured
  narration; a clip bought before the VO exists is bought against a guess.
- **Checks before money**: `preflight.py`, `smoke.py`, `contract.py`,
  `residue.py` — four seconds against a bake measured in hours.
