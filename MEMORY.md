# showrunner — read this first

You are looking at a **working film pipeline**, not a skeleton. It renders a
multi-film season — a cold open, N films, an optional wraparound show — as one
feature, on a local ComfyUI stack plus a small number of paid partner nodes.

It was extracted from a finished six-film season after that season shipped. Every
guard, assert and refusal in these files is there because something **rendered
cleanly, exited 0, and was wrong**. That is the failure mode of this whole
domain: almost nothing crashes. A film with the wrong title card, the wrong
picture source, a frozen zoom, a voice 150 ms late or a mouth moving under
silence all encode fine and play fine.

**So the rule that generates all the others: a check that does not measure the
delivered artifact is not a check.**

---

## What to do right now

| Situation | Do this |
|---|---|
| Starting a new season | `python new_season.py --to <path> --sessions <N>` then read `docs/00_READ_ME_FIRST.md` |
| Inside a season, adding a film | `python new_season.py --session S7_NAME` |
| Don't know what state this season is in | `python parts.py` |
| Fresh clone, before writing anything | `python smoke.py --template`, then `python residue.py` |
| Plates exist and you want to look at them | `python contact.py` — every plate in the season, in running order |
| About to render for the first time | `python preflight.py` and `python contract.py` |
| Building everything | `python season.py` |
| Something is out of sync | `docs/03_audio.md`, then `docs/04_lipsync.md` |

The scripts **refuse to run** until the identity files are filled in. That is
deliberate — see `season_identity.py`.

---

## The documents

Read `00` and `01` before touching anything. Read the rest when you reach the
part of the build they describe; each one is a list of things that already went
wrong, with the numbers.

| File | What it is |
|---|---|
| `docs/00_READ_ME_FIRST.md` | The layout, the vocabulary, and what this pipeline is for |
| `docs/01_process.md` | **The order of operations, end to end.** The single most important document |
| `docs/02_traps.md` | Failure modes that render clean. Read before debugging anything |
| `docs/03_audio.md` | Loudness, sync, the join. Nothing in the audio chain may have lookahead |
| `docs/04_lipsync.md` | Mouths. InfiniteTalk, the silence test, and why H3 invents dialogue |
| `docs/05_prompting.md` | Plates and motion. What a prompt can and cannot fix |
| `docs/06_verification.md` | How to check work, and how to check the check |
| `docs/07_performance.md` | Why a bake takes 90 seconds and not an hour |
| `docs/08_case_study.md` | The season this came from: shape, stack and decisions |
| `docs/09_scripts.md` | What every script in the tree is, and which to run when |
| `docs/10_fork_report.md` | What a fork found taking this from `git clone` to a finished feature: seventeen faults, every one of them in machinery |
| `docs/11_asset_library.md` | **Design note — none of it is built.** A cross-project prop/location/character library and an image→image edit step: what it needs, what it breaks, what would have to be measured first |

---

## The shape of a season

```
<season>/
  season_identity.py     WHO THIS SEASON IS. Edit first. Everything imports it
  parts.py               discovers the running order from the folders on disk
  season.py              bake every part, then join
  preflight.py           refuses to render while the content is still borrowed
  smoke.py               imports every module in every tree. Four seconds
  contract.py            asserts the facts that live in more than one file
  residue.py             finds the previous season's beat ids in this one
  contact.py             every plate in the season on one sheet, pre-VO
  contact_probe.py       its worker: one part per subprocess
  surface.py             finds the flat surface type is drawn onto, and
                         draws its answer back for a human to approve
  devices.py             the transition library. `--sheet` renders every one
  cards.py               the title/end card library. `plain` is the default
  grades.py              the look library. `none` default, `flat` carried
  framing.py             crop/pad/stretch with a named or measured anchor
  mixes.py               the audio bus library. `ducked` default
  new_season.py          clone this template / add a session folder
  docs/
  cold_open/             the front door. Its own tree. Delete if not wanted
  S1_.../ S2_.../ ...    one folder per film. Copies of _session_template
  show/                  optional wraparound: interstitials, lip sync, the join
  _session_template/     copied to make a new film folder. Never rendered
```

Every folder that makes picture has the same shape:

```
identity.py    who this part is           <- the only file a clone must edit
script.py      the words, and who says them
edit.py        the timeline: beats, durations, transitions
shot.py        the plates: prompts, seeds, LoRAs
motion.py      what moves in each beat
gen_still.py   make the plates
make_vo.py     make the narration
h3_shoot.py    make the motion locally (free)
make_video.py  make the motion on a partner node (paid)
assemble.py    bake picture, build sound, mux
publish.py     copy the finished part where it is watched
```

---

## Five things that are true of this pipeline and surprise people

1. **VO before video, always.** Every duration in the film is derived from the
   measured length of the narration. A clip bought before the VO exists is a
   clip bought against a guess.
2. **The seed is the re-roll lever, not more words.** A shape that is wrong in
   the plate is usually a seed problem. Adding sentences to fix it is the
   expensive way round.
3. **A prohibition is not a position.** "No boats" does not remove boats.
   Say what IS there and what stays there. This applies to audio too — telling
   a model to be silent buys mumbling; describing room tone buys silence.
4. **Local generation is free and should be the default.** The reference season
   shot every film on local H3 with a 6-step turbo LoRA for $0.00 after
   measuring it against the paid alternative and finding it better.
5. **Nothing in the audio chain may have lookahead.** A limiter delays what it
   passes. Under a lip-synced mouth that is a sync error by construction.
6. **A key that exists in every season is not an identifier.** Every film
   numbers its beats `"01"`, `"02"`, `"03"`, so a table keyed by beat id
   resolves perfectly in a tree it was never written for. `MOTION[sid]`,
   `START_FRAME[sid]`, `BOARD_TYPE[sid]` — nothing raises, nothing counts
   wrong, and it is the wrong film. `residue.py` looks for exactly this.
7. **Content checks cannot see machinery.** `preflight.py` asks whether the
   words are still the example and every `check()` asks whether the season is
   configured. Neither has ever asked whether a module *executes*. `smoke.py`
   and `contract.py` are the answer, and `docs/10_fork_report.md` is why.

---

## Where the money is

Local (free): plates (Krea2), motion (MiniMax H3), lip sync (WAN 2.1
InfiniteTalk), all assembly. Paid: ElevenLabs narration (~1% of a Pro month per
film), partner video nodes (Seedance ~$0.30/clip, Ray, Kling ~$0.14/call) if
used at all. **Read `price_badge` from the node registry rather than spending to
measure a price.** A failed submission costs nothing — it bounces before
reaching the vendor — but a 401 *during polling* bills for a result you never
receive.
