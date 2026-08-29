# 00 — Read me first

## What this makes

A **season**: several short films that share a world, a look and a voice, joined
into one feature with connective tissue between them. The reference season was
six films of about two minutes each plus a cold open and six interstitials —
14.4 minutes total, 861 seconds, thirteen parts.

It is not a general video tool. It is opinionated about a specific shape:

- **A film is a list of BEATS.** Each beat is one still plate plus one motion
  clip generated from it, carrying one or more lines of narration.
- **Every duration derives from the measured narration.** Nothing is typed
  twice. A beat owns its lines; its length is `lead + Σ(measured line durations)
  + gap×(n−1) + tail`.
- **The picture is generated; the words are written.** Anything that must be
  *true* — a number, a name, a date, a piece of on-screen type — is placed by
  hand at bake resolution, never generated.

If your project does not have that shape, take the parts you want. `crt.py`,
`italk.py`, the audio chain in `assemble.py` and `feature.py` are independently
useful.

## What to do right now

| Situation | Do this |
|---|---|
| Starting a new season | `python new_season.py --to <path> --sessions <N>`, then read on |
| Inside a season, adding a film | `python new_season.py --session S7_NAME` |
| Don't know what state this season is in | `python parts.py` (`--json` for the machine-readable version) |
| Fresh clone, before writing anything | `python smoke.py --template`, then `python residue.py` |
| Plates exist and you want to look at them | `python contact.py` — every plate in the season, in running order |
| About to render for the first time | `python preflight.py` and `python contract.py` |
| Building everything | `python season.py` |
| Something is out of sync | `docs/03_audio.md`, then `docs/04_lipsync.md` |
| Output is wrong but nothing crashed | `docs/02_traps.md` first |

The scripts **refuse to run** until the identity files are filled in. That
is deliberate — see `season_identity.py`.

## The vocabulary

| Word | Means |
|---|---|
| **season** | The whole thing. One folder. One feature at the end |
| **session** / **film** | One short film. One sub-folder. Has a SESSION_NO |
| **show** | The optional wraparound — a host, interstitials between films |
| **cold open** | The wordless front door before anything else |
| **beat** | One unit of a film: a plate, a clip, some narration. Has a `sid` |
| **sid** | A beat's two-digit id, `"01"`..`"15"`. Strings, not ints, everywhere |
| **plate** | The generated still a beat's motion is made from |
| **take** | One generated attempt. Rejected ones are renamed, never deleted |
| **bake** | Turning clips + type + grade into numbered PNGs |
| **part** | Any one of the thirteen mp4s the feature is made of |

## The layout, and why it is this way

Each part is a **self-contained folder that builds one mp4**. It has its own
`assemble.py`, its own `_work/`, its own `out/`. Nothing reaches into another
part's folder except `parts.py` (which only reads paths) and `feature.py` (which
reads finished mp4s and their mixes).

That isolation is the point. In the reference season the parts lived as eight
sibling `*_src` trees with no season-level anything, and the two bugs that cost
the most both came from that: the running order was typed in two files that
could disagree, and rebuilding "the season" meant remembering an order and a
set of flags. Both are now `season.py`'s problem.

**`_session_template/` is never rendered.** It is the thing `new_season.py`
copies. If you improve a session script, improve it there too, or the next film
inherits the old one.

## Identity: the one rule that generates the file layout

Every value that says *which* film this is lives in exactly one place:
`identity.py` in that folder, which imports `season_identity.py` at the root.

This exists because the reference season did the opposite. Its eight trees were
copies of each other with identity typed into five files apiece, and it produced
four separate silent bugs — a title card naming the wrong film, an output
written to another film's filename, a stale duration table that produced a
confident "go and buy longer clips", and a transition name with no
implementation that fell through to the *previous* season's device. None of them
failed. All of them rendered.

So: **if you find yourself typing a film's name, stop.** Import it.

The identity files call `check()` at import time and `sys.exit` if they are
blank. A half-configured clone cannot get as far as spending money.

## What you need installed

- **ComfyUI**, running. `$SEASON_COMFYUI` is its root and `$SEASON_COMFY_URL`
  its address (default `http://127.0.0.1:8188`). It needs the models named in
  `shot.py`, `h3_shoot.py` and `italk.py` — `docs/08_case_study.md`
  lists the set the reference season used.
- **ffmpeg and ffprobe** — found on `PATH`, or point `$SEASON_FFMPEG` at the
  directory holding them.
- **Python** with `numpy` and `Pillow`. `insightface` only if you use the mouth
  metrics in `show/mouth_open.py`.
- **A credentials file** — `$SEASON_ENV`, by default `.env` at the ComfyUI
  root — holding `API_KEY=` (comfy.org) and
  `ELEVENLABS_API_KEY=`. **Read them at runtime; never put a key on a command
  line.** ComfyUI does not read `.env` itself — the key goes in the POST body as
  `extra_data.api_key_comfy_org`, and **only that field**: setting
  `auth_token_comfy_org` as well takes a Bearer branch this API rejects, and the
  401 reads exactly like a bad key.

## First run, in order

```
python season_paths.py          # does this machine have the tools?
python new_season.py --to ../MY_SEASON --sessions 6
cd ../MY_SEASON
# edit season_identity.py
python parts.py                 # tells you what is still blank
# rename S1_UNNAMED.. and fill each identity.py
python parts.py                 # until it stops complaining
python smoke.py --template      # does every module in every tree execute?
python residue.py               # whose beat ids and names are in here?
```

Then `docs/01_process.md`, which is the real instruction manual.

## The four checks, and the one question each one asks

They look similar and they are not interchangeable. The template shipped with
only the first of them, and `docs/10_fork_report.md` is the account of what a
fork found in the gap: seventeen faults, **every one of them in machinery, and
`preflight.py` only inspects content.**

> A check that does not measure the delivered artifact is not a check.

| | asks | run it |
|---|---|---|
| `preflight.py` | is any of this still the template's example? | before spending |
| `smoke.py` | does every module actually execute? | on a fresh clone, before writing anything |
| `contract.py` | do the tables in different files agree? | after `edit.py`, before generating |
| `residue.py` | whose beat id is this? | once per clone, then argue with it |

`season.py` runs `smoke.py` and `contract.py` before it builds anything —
four seconds against a bake measured in hours.

A fifth machinery check guards the TEMPLATE rather than a season:
`selftest.py` pins the behaviour of the shared pure logic (the lock, the
bus padding, the subtitle de-overlap, the registries) to the faults that
were once fixed in them. Run it after editing any season-level module; a
failure names the learnings entry to reread.

The fifth thing to run is not a check, because what it catches cannot be
asserted: **`contact.py` draws every plate in the season on one sheet**, in
running order, before any narration exists. The same location rendered as two
locations is obvious in comparison and invisible in isolation, and no amount of
code will ever see it.

## A note on the code you are about to read

The scripts are heavily commented, and the comments are mostly **incident
reports** — what went wrong, what the measurement was, and why the code is the
shape it is. They are long on purpose. When you modify one of these files, the
comment is usually the reason you should not.

If you delete a guard, delete its comment too, so the next reader does not
believe a protection is present that is not.

## Where the money is

Local (free): plates (Krea2), motion (MiniMax H3), lip sync (H3's anchored
driver), the score (ACE-Step), all assembly. Paid: ElevenLabs narration
(~1% of a Pro month per film), partner video nodes (Seedance ~$0.30/clip,
Ray, Kling ~$0.14/call) if used at all. **Read `price_badge` from the node
registry rather than spending to measure a price.** A failed submission
costs nothing — it bounces before reaching the vendor — but a 401 *during
polling* bills for a result you never receive.
