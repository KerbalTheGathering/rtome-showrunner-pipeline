# 10 — What a fork found

> **A later fork's findings are in [`../learnings.md`](../learnings.md).** This
> report is the first fork's and is left as it was written; nothing in it has
> been revised in the light of the second. Where the two overlap, they agree.

**Audience: a Claude Code session working on the `showrunner` template.**
This is a report from a fork that took the template from `git clone` to a
finished 139.6s feature — a cold open, three films, a three-segment wraparound
with lip sync, and the join. Everything below happened; nothing here is
speculative.

---

## Status: what has been acted on

**Part 2 is built.** `smoke.py`, `residue.py` and `contract.py` exist at the
season root and `season.py` runs the first and the third before it builds
anything. Every fault in Part 1's table is fixed, and `smoke.py` found twenty
more of the same shape that the fork had not reached — including all thirteen
files in `show/_probes/`, which carried `show/*.py`'s two-dirname path preamble
one level too deep and could not be imported at all.

**Most of Part 3 is done.** `script.FORMAT_SIDS` replaced `sid == "06"` in four
files. `edit.CUES` replaced the two `CROSSOVER_SID` declarations and `mix()`
builds one branch per cue instead of counting to two. `season_paths.BUDGET_M`
and `pick_canvas()` own the latent ceiling for all three `h3_shoot.py` copies,
and the canvas ladder derives from the season's delivery aspect. The transition
**registry** (Part 3's `DEVICES` suggestion) is declared rather than
dispatch-only, and `contract.py` reads the `kind == "..."` branches back out of
the source so the declaration cannot drift from the code.

**Part 3 is now done, and further than it asked.** Part 3 named "six-ness" —
the ways one season's shape was welded into the machinery. The same argument
turned out to apply to everything the assembler decided on a film's behalf, so
after the transition and title-card libraries came three more:

- `grades.py` — the look. `flatten()` was a function in `assemble.py` and so was
  one season's only possible grade. It is `flat` in the library now, tuned to
  the same six numbers and byte-identical on a random image, beside five others.
  `shot.GRADED` says WHICH beats; `identity.GRADED_AS` says WHAT, and
  `identity.GRADE` is the look every other beat gets.
- `framing.py` — the crop. `fit_aspect()` centre-cropped, with the 2 inside the
  expression. It is a named fit with a named anchor now, overridable per beat in
  `shot.FIT_BEATS`, and it can pad as well as crop — which a vertical delivery
  cut from horizontal plates needs and the template could not do at all.
- `mixes.py` — the bus. `mix()` built one arrangement and, worse, built
  `amix=inputs=0` for a film with no cues or no takes. Both now render. The bus
  also owns the output LENGTH, which is the invariant that has silently
  truncated a film once and turned up wrong again in `italk_multi.py`.

**Part 5 is done.** `contact.py` and `contact_probe.py` are at the season root:
every plate in the season, in running order, one subprocess per part, resolved
through `gen_still.plate()` so aliases and flips show as the shoot will use
them, and drawable before any narration exists. `docs/01_process.md` now says in
Phase 2 to do Phase 3's plates first and look at the sheet — the one place the
numbered order was wrong. `check_clip.py` exists in all three trees, no longer
imports the paid `make_video.py` to resolve a clip, and is called by
`h3_shoot.py` after every clip it lands (`--no-strip` opts out).

**Part 7 is done except for one half of one item, and that half is named.**

- **7.1 multi-speaker — the script side is done, the render side is not, and
  the two are separated on purpose.** `identity.VOICES` is a role → id table
  and `script.LINES` names a role, so any number of speakers is expressible;
  two people in one beat is two lines with the same sid, `make_vo` renders each
  in its own voice, `script.speakers(sid)` says who is in a beat, and
  `contract.py`'s `cast` check catches a role with no voice or a voice with no
  lines. The one-guest-one-line cap is now `LINE_CAP`, declared by the season
  that wants it rather than welded into the template. **Two mouths moving in
  one shot has not been made to work** — `docs/04_lipsync.md` names both
  routes and says which to try first and why.

  **The Multi graph is written and has never been run.** `show/italk_multi.py`
  carries UNPROVEN at the top of it and three safeguards that are the whole
  reason it is safe to have: it cannot submit a graph whose node contract it
  has not checked against the live `/object_info` (and on a mismatch prints
  what it assumed, what the node has, and why it thought so); it writes
  `synced_multi_XX.mp4`, a filename `assemble.py` does not read, so an
  experiment cannot reach a bake by accident; and `--dry` builds and
  structurally audits the graph without submitting.

  Everything in it that could be verified without a GPU was. That mattered:
  the per-speaker driver builder produced a 7.29 s track for a three-line role
  and a 2.65 s track for a one-line role **in the same segment** — the obvious
  `apad,atrim` spelling, right for one input count and wrong for the other.
  Both files existed, both played, one was a driver two-thirds too short, and
  only measuring where the energy actually was could have found it.
- **7.2 `surface.py` exists** at the season root and does exactly what this
  report describes, including refusing to pretend it can see the usable area.
  `board_rect.py` is now two settings and a subprocess call.
- **7.3 non-narrated is a documented mode.** A beat named in `script.SILENT`
  takes its length from `edit.SILENT_SECS`; the two files own one fact each and
  are asserted against each other on import, and a beat with neither is
  refused. `contract.py` checks it across files too.
- **7.4 not-4:3**: the bake floor, the lip-sync render size and the QC
  comparison cell all derive from `season_identity.W/H` now, alongside the
  canvas ladder from Part 3.

Part 6's practical notes are folded into `01_process.md`, `03_audio.md`,
`04_lipsync.md` and `05_prompting.md`.

Read the rest as the argument for why those tools exist. It is a better
explanation than their docstrings can be, because it is the account of the
failure rather than the design.

---

## The one-line version

**The template's thesis is right and its checks do not implement it.**

> *A check that does not measure the delivered artifact is not a check.*

Twelve real faults were found in this fork. **Every single one was in
machinery, and `preflight.py` only inspects content.** So the season passed
`parts.py`, `preflight.py`, every identity `check()`, every edit-table assert
and every content assert written for it — while being unable to shoot a single
frame, unable to run its own verifier, and (later) drawing one line of type
where three were reported.

The fix is not more asserts inside content files. It is **three new checks that
look at the machinery**, described in "What to build" below.

---

## Part 1 — What actually broke

Ordered by how much of the pipeline they blocked. The `blind to` column is what
*should* have caught it and did not.

| # | File | Fault | Blind to |
|---|---|---|---|
| 1 | `h3_shoot.py` (**all six copies**) | Uses `season_paths.COMFY_URL/INPUT/OUTPUT` at module level and never imports `season_paths`. `import edit` puts it in `sys.modules`, which is not the same thing. `NameError` on the first frame anybody shoots. | preflight (machinery) |
| 2 | `verify.py` | Imports `edit` but not `shot`, then uses `shot.SLUG` — on the very line whose comment explains that the filename is *derived rather than typed*. | preflight |
| 3 | `_session_template/motion.py` | Example references `_LOCK`, which is never defined. `NameError` on import. | preflight *passes the file* — the sentinel is present, so it is "still the example", which is reported as a state rather than a failure |
| 4 | `_session_template/shot.py` | Example has 3 beats and asserts `len(BEATS) == 15`, plus `PLATE_ALIAS.get("07") == "03"`. | as above |
| 5 | `cold_open/shot.py` | Example asserts `set(SECS) == set(CUT)` and never defines `SECS` (which `cold_open/edit.py` imports). Its example prompts also violate its own "no left/right" assert. | as above |
| 6 | `show/shot.py` | Example references `BOARD_RECT` and `TYPE_INSET*`, never defined. | as above |
| 7 | `show/motion.py` | Asserts `"unbroken sheet of plain dark turquoise felt" in _p` — a phrase that lives in `_BOARD`, which is never concatenated into `MOTION`. | as above |
| 8 | `assemble.py` + `make_music.py` | **`CROSSOVER_SID` declared separately in both.** They disagreed (03 vs the reference season's 11): the cue was generated to change register at 19.4s and the mix was told to lay it under a beat that does not exist. | nothing — it only crashed because "11" was absent. In a tree that *has* a beat 11 the cue is written for one moment and laid under another, silently |
| 9 | `show/edit.py` | `AIR_EMPTY if sid == "06" else AIR` — the break segment identified by a literal. Also `rows[:5]` and `rows[5]` in `main()`: `IndexError` on any reel that is not six long. | nothing |
| 10 | `show/make_vo.py` | `script.SIDS[:5]` for the format comparison; prose says "across six slots"; `who = "DALE"` — the previous presenter's name, typed, printed against every take. | nothing |
| 11 | `show/gen_still.py` | No `PLATE_ALIAS` support, though `_session_template/gen_still.py` has always had it. "One plate, N segments" was a hope, not a mechanism. | nothing |
| 12 | `cold_open/h3_shoot.py`, `show/h3_shoot.py` | No `pick_canvas()`/`BUDGET_M` — they predate it and still choose canvas by hand with `--small`. **Cost 12.7 minutes on one clip** (243f at 1024x768 = 2.99M tokens, over the 2.80M thrash line) against 3.0 and 1.8 minutes either side. Nothing failed and nothing warned. | nothing — at 99% utilisation a thrash looks exactly like work |
| 13 | `show/italk.py` | `START_FRAME = {"01": 27, "02": 25, "04": 14, "05": 5}` and `SHIFT = {"04": 3}` — **per-take measurements from another season, keyed by segment id**, so this reel's 01 and 02 silently inherit an anchor measured on a different actor in a different room. | nothing |
| 14 | `show/mouth_open.py` | Defaults to `["01", "04", "05"]` with no arguments — in another tree that is two segments that do not exist and one that does, so it measures a third of the reel and reports success. | nothing |
| 15 | `show/qc_feature.py` | Iterates `feature.SEASON` and `feature.KREA`, which `feature.py` **no longer has** (it reads `parts.running_order()`). `AttributeError` the first time anyone QCs a finished feature. | nothing — a checker that cannot run has never disagreed with anything |
| 16 | `show/assemble.py` ↔ `show/script.py` | `marks = [...offsets...][:len(BOARD_TYPE[sid])]` takes **one board mark per spoken line**. Three lines of type against one line of copy ⇒ only the first is ever drawn, while the log prints `3 line(s) of type`. | nothing. Found by grabbing a frame off the delivered mp4 and looking at the felt |
| 17 | `_session_template/audition.py`, `show/audition.py` | `PICKS = {"intro": "01", "peak": "03", "empty": "17"}` — sid 17. `VOICES` ships effectively empty. | nothing |

Plus reference-season **content** in every `make_music.py` (a Cuban bolero, a
1978 brass sting, a Gulf-coast trumpet) which `preflight` does not check,
because `make_music.py` is not in `CONTENT`.

### The pattern

Three distinct failure shapes, and they want three different fixes:

1. **Modules that cannot import** (1–7). Nothing runs them until late.
2. **The previous season's data, keyed by an id that exists in every season**
   (9, 10, 13, 14, 17, and the `make_music` cues). `MOTION[sid]`,
   `START_FRAME[sid]`, `BOARD_TYPE[sid]` — *a key that exists in every session
   is not an identifier*. The template says this, in `motion.py`, about
   `SESSION`. It is true of six more files.
3. **The same fact typed in two files** (8, 16 in spirit). The identity layer
   solved this for names and killed a whole bug class. It was never applied to
   editorial facts.

---

## Part 2 — What to build

Three files. Between them they would have caught 15 of the 17.

### 2.1 `smoke.py` — import every module in every tree

```
python smoke.py          # every .py in every part folder, in its own process
```

Catches faults 1–7 in about four seconds, on a fresh clone, before anything is
configured. Each module is imported in a **subprocess with cwd set to its own
folder**, because every tree owns an `identity.py`, a `script.py` and a
`shot.py` and one interpreter can only hold one of each.

Two modes, because a fresh clone and a configured season fail differently:

- `--template`: content files still carry `EXAMPLE_CONTENT`. **The example must
  import.** Faults 3–7 are all example content that cannot be executed, which
  means the shipped template has never been run end to end since those files
  were last edited.
- default: a configured season. Everything must import *and* every module that
  declares a `main()` must be runnable with `--help`-ish arguments, or at least
  be import-clean.

This is the single highest-value addition. It is also the one that keeps
working forever, because it needs no knowledge of what any file does.

### 2.2 `residue.py` — find the previous season in this one

```
python residue.py        # scan every tree for ids and names that are not ours
```

The scan is mechanical:

- Collect this season's vocabulary: `shot.CUT` / `script.SIDS` per tree,
  `identity.NAME`, `SLUG`, `TITLE`, `season.SEASON`, `SHOW_NAME`.
- Walk every `.py` in that tree for **two-digit string literals** used as dict
  keys or compared with `==`, and for **quoted names in ALL CAPS**.
- Report anything that is not in the vocabulary.

On this fork that reports, immediately: `"06"` in `show/edit.py`, `"04"`/`"05"`
in `italk.py` and `mouth_open.py`, `"17"` in `audition.py`, `"11"` in
`assemble.py`, `"DALE"` in `make_vo.py`, `"07"`/`"03"` in the `shot.py`
example. Every one of those is a real finding.

False positives are fine here in a way they are not in `preflight`: this is a
tool you run once per clone and then argue with, not a gate.

### 2.3 `contract.py` — assert the cross-file facts

The identity layer proved that *state it once, derive it everywhere, hard-fail
when blank* kills a bug class. Extend it from **names** to **shape**:

```python
# imported by every tree's assemble.py, or run standalone
check_beats(shot, script, edit)   # same sids in all three, same order
check_marks(shot, script)         # len(BOARD_TYPE[sid]) <= spoken lines
check_devices(edit, assemble)     # every TRANSITIONS kind has a branch
check_cues(edit, make_music)      # one CROSSOVER_SID, one owner
```

Fault 16 is the interesting one. `assemble.py` **counted what it was handed and
reported that**, which is the same class as a resolver matching zero files and
printing a pass. Two rules fall out:

- **A count in a log line must be a count of what was DONE**, not of what was
  requested. `3 line(s) of type` should have read `1 of 3 line(s) drawn`.
- **Where a table's length must match another table's length, assert it in
  whichever file can see both.** Here that was `shot.py` (it already imports
  `script`); `script.py` cannot import `shot.py` without a cycle.

---

## Part 3 — Where the six-ness is welded in

`N_SESSIONS` is a variable. The *shape* of a six-film season is not. Being
three films is what surfaced faults 9, 10, 11, 14 and 15. A future season that
is two films, or eight, or one, will hit the same wall.

Places that assume the reference shape, beyond the faults already listed:

- **`show/`'s "the last one is different"** is encoded as `sid == "06"`. This
  fork replaced it with `script.FORMAT_SIDS` — *which segments are the format*
  is a fact about the writing, so it lives in `script.py`, and `edit.py`,
  `make_vo.py` and `motion.py` all read it. Recommend upstreaming that exact
  shape; it is a one-line change in each consumer and it removes a whole class.
- **`assemble.py`'s transition dispatch** is a hard-coded `if kind == ...`
  chain over four names. It hard-fails on an unknown name, which is right — but
  it means adding a device is editing the assembler. A registry
  (`DEVICES: dict[str, Callable]`, one module per device) would let a season add
  one without touching shared machinery, and would let `contract.py` check the
  edit's names against the registry instead of against a chain.
- **Two cues and one crossover** is baked into `mix()`. A season with one cue,
  or four, has to edit the mixer. A cue *table* in `edit.py` —
  `CUES = [("main", "01"), ("late", "11")]` — generalises it and puts the
  editorial fact where the other editorial facts already are.
- **4:3 at 1440x1080** appears in `season_identity`, in `pick_canvas`'s
  `CANVASES`, in `dims()`, and in the tile geometry of every contact sheet.
  Three of those four derive; `CANVASES` does not.

---

## Part 4 — What genuinely worked, and should be extended

This is not a bad codebase. These are the parts that paid for themselves in one
fork, and the generalisations they suggest.

**The identity layer.** Zero identity bugs in nine parts. Extend it to shape
(Part 2.3).

**Durations derived from measured VO.** The single best decision in the repo.
It caught two beats that could not be shot before a frame was rendered, and it
is why re-recording one line safely re-flowed an entire reel.

**The derived in-point (`SS_MAX` shrinking to fit).** S3 beat 01 did not fit at
a full in-point; `table()` cut it to 0.25s rather than overrun. This is the best
pattern in the repo: **make the overrun impossible by construction rather than
detectable by an assert.** More things should work like this.

**`PLATE_ALIAS`.** "Two shots that must match need one plate, not two prompts"
is correct and cheap. It should exist in *every* `gen_still.py` (fault 11).

**`usable_seconds()`.** Measuring where music *stops* rather than where the
file ends is exactly the artifact-not-intent rule, correctly applied.

**`which_source.py`.** Proving by motion-energy correlation that the shipped
segment came from the lip-synced render, not the raw take, is the best check in
the repo. It measures the delivered file and it answers a question no frame grab
can. **Generalise the idea:** any time two indistinguishable sources can be
shipped, there should be a `which_source` for it.

**The incident-report comment style.** Genuinely useful to a fresh session. Keep
it. The one improvement: when a comment describes a value measured on *this*
season's takes, say so in the comment, because the next clone cannot tell the
difference between a measured number and a copied one. That ambiguity is
fault 13.

---

## Part 5 — Two tools this fork added that are worth upstreaming

**`contact.py` + `contact_probe.py`** (season-level plate sheet, pre-VO).
`storyboard.py` needs `edit.table()`, so it cannot be drawn until narration
exists — but plates are the first thing that can be wrong in a way no assert
catches, and looking at them should not wait behind an API bill. The probe runs
**one part per subprocess** for the `sys.modules` reason above. On this fork the
sheet caught six bad plates in one look, three of which were prompt faults
rather than seed faults.

**Filmstrips as the default review unit.** `check_clip.py` exists and is right
(six frames, evenly spaced). It should be run automatically after `h3_shoot.py`
rather than being a separate thing to remember, and `cold_open/` and `show/`
should have a copy — they do not.

---

## Part 6 — Practical notes for whoever runs this next

- **`insightface` is not installed on a normal box** and `mouth_open.py` is the
  only thing that needs it. Its own docstring says the metric is not believed
  until it agrees with the eyes; the eye half — crop frames 0–26 to the face,
  tile them, pick the most closed square-on frame — takes two minutes and is
  what the metric is validated *against*. Consider shipping the by-eye
  procedure as the documented path and the metric as the optional confirmation.
- **ElevenLabs music does not move `character_count`.** `/v1/user/subscription`
  showed the identical figure before and after six cues. If cost matters, that
  meter is not the place to read it, and the docs should say so rather than
  leaving someone to infer music is free.
- **The canvas thrash line on a 24GB card is between 2.77M and 2.95M latent
  tokens** and `pick_canvas()` is correct at `BUDGET_M = 2.80`. The measured
  cost of not having it is 4× wall clock with no error.
- **The title card runs 5.6s over the opening beat regardless of the lead**
  (`TITLE_FIX + TITLE_HOLD + TITLE_OUT`). Leads should therefore be chosen as
  editorial register, never as room for the card. Worth one line in
  `docs/01_process.md`; it is not obvious and it changes every opening beat.
- **Prompt traps found on this stack, beyond the ones already documented:**
  - Naming a *blank surface type* summons the surface. `"every sign board and
    destination panel is a blank rectangle"` does not request lettering — it
    requests **boards**, and produced a blank cream billboard in all three cold
    open shots, one of them across the sky reserved for the title. Describe
    only surfaces that were going to be in frame anyway.
  - **"furled"** reads as *fur*. Three takes put a dead animal on the seat
    beside the umbrella. `docs/05_prompting.md` should carry a short list of
    words the stack mis-hears; this is the first entry.
  - Two contradictory instructions about one surface produce a **white blank**,
    not a compromise. Asking for a dark window *and* daylight behind it did it
    twice.
  - A prop described at close range renders correctly and the **same words at
    thumbnail scale fall back to a generic**. A cardboard disposable camera
    became a metal rangefinder in a wide shot four rolls running, while the
    identical block rendered correctly in close-up. Same capacity failure
    `docs/05_prompting.md` already describes for faces — worth generalising the
    entry from "faces" to "any specific prop".

---

## Part 7 — Accommodating other genres

The template is currently shaped for one thing: **narrated object-films with a
talking-head wraparound**. It does that well. Four things stand between it and
a wider range, in order of how much they cost to fix.

**1. Multi-speaker scenes (cheap-ish).** The model is one narrator plus an
optional single-line guest, and exactly one on-camera speaker in `show/`.
Dialogue needs: per-beat speaker lists (already possible — `LINES` carries a
voice), and lip sync driven per speaker per region. `italk.py` generates the
whole frame from one driver, so two people talking needs either two passes with
a composite or the InfiniteTalk *Multi* patch — which is already on disk
(`Wan2_1-InfiniteTalk-Multi_fp16.safetensors`) and unused.

**2. Drawn type on any surface (cheap).** `board_rect.py` is genuinely good, and
it is welded to *one green felt board in the right half of the frame*. The
useful generalisation is a small `surface.py`: given a plate and a colour hint,
find the largest flat region, draw the answer back onto the picture for a human
to approve, and emit a rect. Then a season can put type on a whiteboard, a
newspaper, a departures screen, or a shop window — which is most of what other
genres need. **One thing the detector cannot do and must not pretend to:** it
finds the *surface*, not the *usable area*. On this fork the lower third of a
correctly-detected board had a counter, a ledger and a mug in front of it. That
is what `TYPE_INSET_B` is for and it can only be set by eye.

**3. Non-narrated forms (moderate).** Everything downstream derives from
measured VO. A season with no narration — pure picture and score, or dialogue
only — currently has one worked example (`cold_open/`, which types its lengths
because there is no voice). That pattern is the right one; it just needs to be
a *documented mode* rather than a special case in one folder. Concretely:
`edit.py` should accept either `lids` or an explicit `secs`, per beat, and
`docs/01_process.md` should say which trees are in which mode.

**4. Anything not 4:3 (moderate).** See Part 3.

---

## Part 8 — If you are doing this again, the order that worked

1. `season_paths.py`, then fill every `identity.py`. **`parts.py` exits 0 before
   anything else happens.**
2. **`smoke.py`** (once it exists). On a fresh clone, before writing content.
3. Words — every `script.py`. Nothing downstream can be honest before this.
4. **Plates, out of the documented order.** They cost only GPU, they are the
   first thing that can be wrong invisibly, and nothing about them depends on
   the words. Build the contact sheet and *look at it* before spending on VO.
5. VO, then `measure_vo.py`.
6. `edit.py`. This is where the season becomes real: it is the first file that
   can refuse.
7. `motion.py` — needs both the plates and the beat lengths.
8. Shoot, **filmstrip every clip**, then assemble.
9. The show last, and budget for it: on a three-segment reel it was board
   measurement, anchor picking, two InfiniteTalk passes and a re-shoot, and it
   took longer than all three films together.

**One structural note for small seasons.** On this fork, 26.1s of cold open plus
29.0s of wraparound is **39.5% of a 139.6s feature**. `feature.py` prints that
figure and it is worth reading: the connective tissue was designed for six films
and it does not shrink when the season does. A three-film season probably wants
a shorter cold open and two-line interstitials, and the template should say so.
