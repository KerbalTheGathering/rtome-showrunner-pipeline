# showrunner

*The one who keeps a season of episodes pointing the same way.*

A working pipeline for making a **season of short generated films** — a cold
open, N films, an optional wraparound show — and joining them into one feature.
Local ComfyUI for pictures and motion, ElevenLabs for narration, ffmpeg and PIL
for everything else.

> **Unaffiliated with Fable Studio's *Showrunner*.** The name here is the
> ordinary television one — the person who keeps a season pointing the same
> way. This is an independently developed local pipeline, with no connection to
> that platform or that company.

It was extracted from a finished six-film season after that season shipped:
14.4 minutes, thirteen parts, about 16,000 frames of picture — and it has been
hardened by every season built on it since; `learnings.md` is the numbered
record. **Every guard, assert and refusal in this repo is here because
something rendered cleanly, exited 0, and was wrong.**

That is the thesis. In generative video almost nothing crashes. A film with the
wrong title card, the wrong picture source, a frozen zoom, a voice 150 ms late
or a mouth moving under silence all encode fine and play fine. So the pipeline
is built out of *refusals*, and the comments are mostly incident reports.

> **The rule that generates all the others: a check that does not measure the
> delivered artifact is not a check.**

## Where to start

| You are | Start at |
|---|---|
| A person, new here | this file, then [`docs/00_READ_ME_FIRST.md`](docs/00_READ_ME_FIRST.md) and [`docs/01_process.md`](docs/01_process.md) |
| An AI agent operating the pipeline | [`CLAUDE.md`](CLAUDE.md) (any framework — see [`AGENTS.md`](AGENTS.md)) |
| Resuming a half-built season | `python parts.py` — or `--json` for the machine-readable state |

## Quick start

```bash
git clone <this repo> my-season
cd my-season
python season_paths.py                       # does this machine have the tools?
python new_season.py --to ../MY_SEASON --sessions 6
cd ../MY_SEASON
# edit season_identity.py, then each S*/identity.py
python smoke.py --template                   # does every module execute?
python residue.py                            # whose beat ids are in here?
# ... write the scripts, generate the plates, record the narration ...
python preflight.py && python contract.py    # checks before money
python season.py                             # build everything, then join
```

`docs/00_READ_ME_FIRST.md` has the full first-run order, and every visual
library prints itself a contact sheet (`python devices.py --sheet`, likewise
`cards`, `grades`, `framing`; `mixes.py --graph`) so you look rather than
guess.

## Operating it with an AI agent

This repo is **designed to be driven by agent sessions** — that is how every
season on record was made. What an agent gets:

- **[`CLAUDE.md`](CLAUDE.md)** — the standing rules that cost real money or
  real nights when broken, and the routing into the docs.
- **[`AGENTS.md`](AGENTS.md)** — the same front door for non-Claude
  frameworks.
- **`.claude/skills/`** — six thin task routers (season-status,
  start-season, shoot-a-film, verify-work, publish-and-deliver,
  fix-a-render). They surface the right commands and doc at the right
  moment; the docs stay authoritative. `new_season.py` copies them into
  every season clone.
- **`python parts.py --json`** — season state as data, so a session resumes
  from the disk instead of from prose.
- **The refusals themselves** — identity files that hard-fail while blank,
  generators that refuse a busy queue, checks that run in seconds before
  anything spends. The pipeline assumes its operator will occasionally be
  wrong, human or not.

## What it does

- **A film is a list of beats.** Each beat is one generated still plus one
  motion clip made from it, carrying one or more lines of narration.
- **Every duration derives from the measured narration.** Nothing is typed
  twice; a beat owns its lines and computes its own length.
- **The picture is generated; the words are written.** Anything that must be
  *true* — a number, a name, a date, on-screen type — is drawn by hand at bake
  resolution, never generated.
- **Identity is imported, never typed.** One `identity.py` per part,
  hard-failing while blank, because the same values typed in five files
  produced four silent bugs on the season this came from.
- **Bakes use every core.** A 2814-frame film goes from ~11 min to under two;
  a six-film season from ~60 min to under nine. `docs/07_performance.md`.
- **The look is a library, not a ladder.** Transitions, title cards, the
  grade, the crop and the audio bus are named in `identity.py` out of
  `devices.py`, `cards.py`, `grades.py`, `framing.py` and `mixes.py` — a plain
  default for each and a sheet you can look at for all of them.
- **The checks look at the machinery, not only at the content.** `smoke.py`
  imports every module in every tree; `contract.py` asserts the facts that
  span two files; `residue.py` finds the previous season's beat ids in this
  one. `season.py` runs the first two before it builds.

## Requirements

| | |
|---|---|
| Python | 3.10+, with `numpy` and `Pillow`. `insightface` only for the mouth metrics |
| ffmpeg | ffmpeg + ffprobe on `PATH`, or set `$SEASON_FFMPEG` |
| ComfyUI | running; set `$SEASON_COMFYUI` and optionally `$SEASON_COMFY_URL` |
| Credentials | a `.env` holding `API_KEY=` (comfy.org) and `ELEVENLABS_API_KEY=`. Set `$SEASON_ENV` to point at it. **Never committed** |

Every path is an environment variable with a sane default — `python
season_paths.py` prints what your machine resolves to and what is missing.
Developed on Windows; the paths layer is POSIX-clean but the pipeline has not
been exercised on Linux or macOS.

## The example content

`_session_template/`, `show/` and `cold_open/` ship with a small **invented**
three-beat example (a lighthouse, a headland) so you can see the shape of a
filled-in `LINES`, `BEATS` and `MOTION`. It is not from anybody's film.

Each of those files declares `EXAMPLE_CONTENT = True`, and `preflight.py`
refuses to render while that line is present. Replace the content, delete the
line. **Keep the docstrings and the asserts** — they are the reasons the guards
exist and they cost nothing to carry.

## Layout

```
season_identity.py   who this season is; everything imports it
season_paths.py      where the tools live; the only file with a path in it
parts.py             discovers the running order from the folders on disk
season.py            bake every part in order, then join
feature.py           the join: verify every part matches, then concatenate
publish.py           the feature and a share cut, to the delivery folder
preflight.py         refuses to render while the content is still the example
new_season.py        clone the template / add a film folder
docs/                the process, the traps, and why every guard exists
.claude/skills/      the agent task routers; copied into every season
cold_open/           the wordless front door. Delete if not wanted
S1_.../ S2_.../      one folder per film
show/                optional wraparound: interstitials and lip sync
_session_template/   copied to make a film folder. Never rendered
```

The rest of the season root is the shared tool set — the checks, the look
libraries, the credit roll, subtitles, the local score, the upscaler, the
process locks. [`docs/09_scripts.md`](docs/09_scripts.md) inventories every
script and when to run it.

## Documentation

| | |
|---|---|
| [`docs/00_READ_ME_FIRST.md`](docs/00_READ_ME_FIRST.md) | Layout, vocabulary, what to run right now |
| [`docs/01_process.md`](docs/01_process.md) | **The order of operations, end to end** |
| [`docs/02_traps.md`](docs/02_traps.md) | Failure modes that render clean |
| [`docs/03_audio.md`](docs/03_audio.md) | Loudness, sync, the join |
| [`docs/04_lipsync.md`](docs/04_lipsync.md) | Mouths: H3's anchored driver, the silence test, and why models invent dialogue |
| [`docs/05_prompting.md`](docs/05_prompting.md) | Plates and motion |
| [`docs/06_verification.md`](docs/06_verification.md) | How to check work, and how to check the check |
| [`docs/07_performance.md`](docs/07_performance.md) | Why a bake takes 90 seconds |
| [`docs/08_case_study.md`](docs/08_case_study.md) | The season this came from, as a worked example |
| [`docs/09_scripts.md`](docs/09_scripts.md) | What every script is |
| [`docs/10_fork_report.md`](docs/10_fork_report.md) | What a fork found taking this from `git clone` to a finished feature |
| [`docs/11_asset_library.md`](docs/11_asset_library.md) | **A design note, not built.** A cross-project asset library and an edit step |
| [`learnings.md`](learnings.md) | The numbered incident log, across every season and fork this pipeline has run |

## A note on model choices

The scripts name specific models — Krea2 for plates, MiniMax H3 for motion and
lip sync, ACE-Step for the score, ElevenLabs for voice. Those were the right
answers on one machine at one time, and they are stated in `identity.py` and
`shot.py` so they are easy to change. **The transferable part is the structure
and the checks**, not the model list.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Two requirements: a signed
[CLA](CLA.md) before your first merge — the project is dual-licensed, so
relicensing rights have to sit in one place — and **evidence**. A patch that
changes behaviour shows the measurement on the delivered artifact, not a
description of it.

You keep your copyright, and the CLA binds the maintainer in return: your work
stays publicly available under a source-available licence, permanently.

## Licence

Dual-licensed.

**Free — GNU AGPL v3.0 with three Conditions**, for individuals, nonprofits,
and organizations under US $1M revenue. See [LICENSE](LICENSE). Use it, study
it, modify it, share it — copyleft, so the pipeline stays open. The films you
make with it are **yours**, including films you sell. Three things are
withheld: you may not sell the pipeline itself; an organization above the
threshold may not use it at all without a commercial licence; and nobody may
use it to synthesize a real person's likeness or voice without that person's
freely given written consent. That last term is not for sale at any price.

**Commercial — a separate licence from the copyright holder**, required for
any use by or for a larger organization, and for selling, hosting, or
closed-source shipping of the Software. See
[COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md).

Copyright © 2026 Garrett Bloome (rtome / KerbalTheGathering).
