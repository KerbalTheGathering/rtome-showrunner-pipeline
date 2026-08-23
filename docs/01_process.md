# 01 — The process, end to end

The order below is not a suggestion. Several steps are cheap before a later step
and expensive after it, and two of them cost real money in the wrong order.

---

## Phase 0 — Decide what the season is (no code)

Write down, in one place, before anything:

- **How many films, and what each one is about.** One sentence each.
- **What runs through all of them.** A refrain, a recurring composition, a
  structure the audience learns. The reference season closed every film on the
  same two-figure composition and opened each with a numbered interstitial.
- **What the last one does differently.** A season that ends the way it began
  has not gone anywhere.
- **Anything that must be true.** Real places, real dates, real people. See
  "Claims" below — this is the part that will embarrass you, not the rendering.

**Write scripts and generate plates for ALL films before spending on motion for
any of them.** Motion is the expensive, slow, hard-to-revise step; a plate is
cheap and a script is free. The reference season learned this by re-cutting a
film after its clips were bought.

## Phase 0.5 — Prove the clone runs (`smoke.py`), before writing anything

```
python parts.py                 # exits 0 once every identity.py is filled
python smoke.py --template      # every module in every tree, four seconds
```

**On a fresh clone, before the content is replaced.** `smoke.py` imports every
`.py` in every tree in its own subprocess and answers the one question no other
check in this repo asks: *does this code execute?* `preflight.py` reads content,
`parts.py` reads identity, every `check()` reads configuration — a season can
pass all three while being unable to shoot a frame. It has happened, to 27
modules at once; see [10_fork_report.md](10_fork_report.md).

It costs four seconds and it needs no knowledge of what any file does, which is
why it keeps working.

## Phase 1 — The words (`script.py`)

`script.py` holds `LINES`: `(line_id, beat_sid, ROLE, style, text)`.

- **A line names a ROLE, not a voice id.** `identity.VOICES` is the table of
  role → ElevenLabs id and it is the only place an id appears. A line that says
  `"keeper"` is readable, survives recasting, and cannot be an id from another
  film that happens to still resolve at the API.
- One narrator unless there is a reason. Every extra voice is a casting problem.
- **Two people in one beat is two lines with the same `sid` and different
  roles.** `edit.py` lays them out in order with `extra` between them,
  `make_vo.py` renders each in its own voice and reports per-role totals, and
  `script.speakers(sid)` says who is in a beat. What this repo cannot do yet is
  drive **two mouths in one shot** — `docs/04_lipsync.md` is exact about where
  that stands and what it would take.
- **If a voice is a signature, declare the cap.** `LINE_CAP = {"keeper": 1}`
  asserts it. That rule used to be welded into the template as "the second
  voice speaks at most once", which made one film's editorial decision a fact
  about every film.
- **A line that asserts a number, a colour or a position is a claim about a
  picture that does not exist yet.** Write it, then re-check it after the plate
  lands (Phase 3). Changing words is free; re-rolling a plate to match a number
  is not.
- Keep the script in the character's register. If the narrator is scrupulous,
  "four, that I can see" is better than a bare number — and it survives a plate
  that disagrees.

### The two length modes, and how a beat declares which it is in

Everything downstream derives from **measured** narration, and that is the best
decision in this repo. It is not a law of the universe: a film that is picture
and score, or one with a wordless passage in it, has nothing to measure.

| the beat | its length comes from | declared in |
|---|---|---|
| has copy | `lead + Σ(measured takes) + gap×(n−1) + tail` | `edit.BEATS` lists its line ids |
| has none | `lead + SILENT_SECS[sid] + tail` | `script.SILENT` names it, `edit.SILENT_SECS` times it |

**Two files, one fact each, checked against each other on import.** `script.py`
owns *which* beats are silent, because that is a decision about the writing;
`edit.py` owns *how long* each one runs, because that is a decision about the
timeline. Naming a beat in one and forgetting the other is a build failure, and
a beat with neither is refused outright — a beat that turns out to be lead plus
tail long is an accident, not an edit.

The cold open is the whole-tree version of the same thing: no `script.py` at
all, lengths typed in `shot.SECS`.

## Phase 2 — The voice (`make_vo.py`, `measure_vo.py`) — **BEFORE ANY VIDEO**

> **Do Phase 3's plates first, and look at them.** Nothing about a plate depends
> on the narration — only clip *lengths* do — and plates cost GPU time rather
> than money. They are also the first thing that can be wrong in a way no assert
> catches, so looking at them should not wait behind an API bill. Generate every
> plate in the season, run `python contact.py`, and read the sheet. Then come
> back here.
>
> This is the one place the numbered order is wrong, and a fork that took the
> template to a finished feature reordered it. "VO before video" is a rule about
> **motion**, not about stills.

```
python make_vo.py          # renders every line to _vo/
python measure_vo.py       # prints measured durations
```

**This is the hard ordering constraint in the whole pipeline.** Every beat
length, every transition, every lip-sync window and every clip purchase is
derived from these measured durations. A clip bought first is a clip bought
against a word-count guess, and it cannot be extended — only re-bought.

Casting, if you need it: `audition.py` renders candidate voices on real lines.
**Do not rank them on pitch spread** — that column is an octave-error artifact
(see `docs/06_verification.md`). Rank on **pace**: words per second on a line
the character is selling versus a line where there is nothing to sell. It
answers the question the casting actually turns on.

**Client work:** use a **premade** ElevenLabs voice and no character LoRA. A
cloned voice and a likeness LoRA are the point of personal work and exactly
wrong for anything handed to someone who holds no licence to either.
`identity.VOICE_IS_CLONE` records the decision.

## Phase 3 — The plates (`shot.py`, `gen_still.py`)

`shot.py` holds one prompt per beat plus the season's shared style block.

Structure a prompt as: **medium/style block → subject → environment → light →
framing.** The leading block wins ties, so whatever must survive goes first.

```
python gen_still.py 03            # one beat
python gen_still.py               # all of them
cd .. && python contact.py        # EVERY plate in the season, on one sheet
```

Then **look at every plate at full size**, and re-read Phase 1's claims against
them. Counting subjects off a contact sheet is how a script ends up asserting
three of something there are four of.

**And look at all of them together.** `contact.py` draws every plate in the
season in running order, one part per subprocess, resolved through
`gen_still.plate()` so aliases and flips are shown as the shoot will use them.
It is the only document that shows the season rather than a film, and it is
drawable **before any narration exists** — `storyboard.py` cannot be, because
its runtimes come from `edit.table()` and those come from measured VO.

The faults it catches are not the ones an assert catches, and none of them are
visible in one plate:

- the same location rendered as two locations
- a specific prop that fell back to a generic because the frame was too wide
- a figure in a landscape that was meant to be empty
- a shot whose light does not match the two either side of it

On the fork this came from, one look caught **six bad plates, three of them
prompt faults rather than seed faults** — and that is the distinction that
decides whether you re-roll or rewrite. It is only visible in comparison.

`sheet.py` inside a part is where you go to look at one plate at 1:1;
`contact.py` is where you go to notice that one of them is wrong.

If a plate is wrong: **change the seed first.** Most shape failures are seed
failures and cannot be argued away with more words. If the same fault comes back
at two different seeds, then it is the prompt — and usually it is a *capacity*
problem (too much asked of one frame) rather than a wording problem. Widen the
frame before rewriting.

See `docs/05_prompting.md`.

## Phase 4 — The timeline (`edit.py`)

`edit.py` turns measured VO into beats:

```
dur = lead + Σ(measured line durations) + gap × (n − 1) + tail
```

- **Never type a duration that must equal another number.** Two hand-typed
  tracks drifted 26 s apart in an early film, and since a lip-sync window is
  "the beat containing this line", every synced line past the drift landed in
  the wrong shot.
- **Quantise on the running total, not per beat.** Rounding each beat costs half
  a frame each and they sum: 20 beats drifted +0.31 s. Take each beat's frame
  count as the difference between the quantised running *end* of this beat and
  the last. Measured drift after the fix: −0.000 s over 147 s.
- `TRANSITIONS` names a device per join, out of the library in `devices.py`,
  with that transition's own settings as an optional fifth element:

  ```
  ("03", "04", "wipe", 0.7, {"angle": 20.0, "seam": 3})
  ```

  `python devices.py` lists them and `--sheet` renders every one at five points
  across its travel — which answers the only question a description cannot.
  **Nothing falls through to a default**: an unknown name, or a setting the
  device does not have, is refused by `contract.py` before anything renders.
  A device only your film wants goes in a `devices_extra.py` beside `edit.py`,
  which nothing shared ever has to know about.

### The look, the crop and the bus

Three more of the same shape, all named in `identity.py` and all refusing a name
they do not have:

- **`GRADE` / `GRADED_AS`** out of `grades.py`. `GRADE` is the look every beat
  gets; `GRADED_AS` is what the beats in `shot.GRADED` get **instead**. One
  grade per frame, ever — they do not stack, because `bleach` under `flat` gives
  you neither and the film where that happened would be very hard to read back
  to a cause. Defaults are `none` and `flat`, which is exactly what the template
  did when the grade was a function called `flatten()` in the assembler.
- **`FIT` / `FIT_OPTS`** out of `framing.py`, overridden per beat in
  `shot.FIT_BEATS`. A crop is normally wrong on **one** beat, not on a film —
  the shot where the subject sits low and the centre crop takes the head off.
  Fix it there. The anchor is a name or a pair of fractions of the leftover
  space, so `{"anchor": (0.5, 0.3)}` keeps a little above centre.
- **`MIX` / `MIX_OPTS`** out of `mixes.py`. `ducked` sidechains the score to the
  voice and is right for anything narrated. `under` drops it by automation off
  the edit's own speech spans instead: the same dip every time, whatever the
  take is doing, and it stays down through a pause a sidechain cannot see.
  `flat` sums at fixed levels.

  Every bus copes with a film that has **no cues** and with one that has **no
  takes**. The hand-built graph these replaced produced `amix=inputs=0` for
  either — an ffmpeg error a hundred lines into a filter chain at the end of a
  bake, which is the worst possible place to learn it. `edit.py` used to assert
  `CUES` was non-empty to stop that happening; an unscored film is an ordinary
  thing to want and it no longer does.

`python grades.py --sheet`, `python framing.py --sheet` and
`python mixes.py --graph` show you what each one does rather than describing it.
- `CUES` names where the score changes register: `[("main", "01"), ("late",
  "11")]`, one row per cue, the sid it comes in on. **This is the only place
  that fact is written down.** It used to be a `CROSSOVER_SID` in `assemble.py`
  *and* another in `make_music.py`; they disagreed, and the cue was generated to
  turn over at one moment and laid under the picture at another.
- **A season is not six films long.** Nothing in a film tree should decide
  anything with `sid == "06"`, `rows[5]` or `SIDS[:5]`. If a beat or a segment
  is special, name *which* in the file that knows why — `script.FORMAT_SIDS`
  does this for the show — and read it everywhere else.

**The card is picked by name in `identity.TITLE_CARD`, and `plain` is the
default** — the type fades up over the opening shot, holds, fades out. The
signature card the template used to hard-code (a diagonal break that resolves as
the type lands) is `break_diagonal`, one option among five. `python cards.py`
lists them with their timings; `--sheet` draws them.

**A card is on screen for `fix + hold + out` seconds regardless of the lead** —
5.6 s for `break_diagonal`, 3.5 s for `plain`. It does **not** shrink to fit a
short opening beat. Choose leads as editorial register, never as room for the
card; if the card does not fit, shorten the *card*.

```
python contract.py                # the tables agree, before anything is bought
python residue.py                 # whose beat ids are these?
```

`contract.py` is the first check that can catch a cue written for a beat that
does not exist, or three lines of drawn type against one line of copy. It costs
a second. Run it here, after `edit.py` and before anything is generated —
`season.py` runs it for you at build time, which is later than you want it.

## Phase 5 — Motion (`motion.py`, then `h3_shoot.py`)

`motion.py` holds one motion description per beat. `docs/05_prompting.md` is the
rulebook; the short version:

- **State what is CONSERVED, not what is forbidden.** "No second person" invites
  a second person; "exactly one person, and he is the only figure in the last
  frame" does not.
- **Naming what a character looks at rotates them toward it.**
- **Never name the camera in a travelling shot** unless you want it to move.
- **Occupy the audio channel.** H3 is omni-modal — picture and sound decode from
  one latent — so undirected audio gets *invented*, and an invented voice moves
  the mouth. Describe room tone.

```
python h3_shoot.py 03             # local, free
python h3_shoot.py 03 --seed=...  # re-roll a plate-level fault
```

**Shoot locally first, always.** The reference season measured local H3 with a
6-step turbo LoRA against the paid alternative and found it better as well as
free. Buy a partner clip only when the local model cannot do the specific thing
— see `docs/08_case_study.md` for which vendor places a plate where.

Reject a take by renaming it `*__rej_<reason>.mp4`. **Never delete.** Every
selector skips `_rej_` explicitly, in both the frame prep and the generator,
because "highest number wins" has carried a worse re-roll into a film.

**Every clip gets a filmstrip as it lands, and you do not have to ask.**
`h3_shoot.py` calls `check_clip.py` on each clip it shoots — six frames evenly
spaced, which is the review unit, because motion breaks in the *middle* and the
first frame is the plate. `--no-strip` turns it off.

**Do not choose a canvas by hand.** `pick_canvas()` sizes each clip from the
latent-token budget in `season_paths.BUDGET_M`, measured at 2.80 M on a 24 GB
card. Going over does not fail, it *thrashes*: one clip at 2.99 M took 12.7
minutes against 3.0 and 1.8 either side, with nothing failing and nothing
warning, because at 99 % utilisation a thrash looks exactly like work. If your
card is bigger, set `SEASON_LATENT_BUDGET_M` rather than editing a file.

## Phase 6 — Assemble (`assemble.py`)

```
python assemble.py                # bake, mix, mux
python assemble.py --keep-frames  # re-mix against frames already on disk
```

This does, in order: explode clips to PNG → bake (upscale, type, cards,
transitions, grade) → build the mix → mux → assert. It uses every core; see
`docs/07_performance.md`.

Read the loudness output. `-16.0 LUFS` and a true peak under `-1.5 dBTP` is the
target; a warning about the ceiling means a transient in the VO is costing the
part its level, and the fix is at the source.

## Phase 7 — The show, if there is one (`show/`)

The wraparound is built like a film with two differences: it makes N+1 short
pieces instead of one long one, and **its host speaks on camera** for whole
segments at a time.

**Lip sync in a session is not a phase: it is Phase 5.** `h3_shoot.py`
anchors the on-screen lines as a driver and H3 moves the mouth in the same
pass that makes the motion (`docs/04_lipsync.md`, the standing rule). The
`italk.py` path below is the show tree's legacy route, kept because a talking
desk needs holds longer than one H3 clip; nothing outside `show/` uses it.

```
cd show
python assemble.py --clean        # ungraded, untyped picture -> feeds the sync
python italk.py                   # WAN 2.1 InfiniteTalk, local, free
python assemble.py                # bake the synced render with type and tube
python which_source.py            # PROVE the bake used the synced render
python sync_probe.py              # PROVE the voice matches the driver
```

`docs/04_lipsync.md` is mandatory reading before touching any of it. The two
checks above exist because six interstitials shipped three times from the wrong
picture source and nothing else could see it.

## Phase 8 — Join and publish

```
cd ..
python season.py            # every part, in order, then the join
python publish.py           # feature + share cut -> where it is watched
python S1_.../publish.py    # per-film folders
```

`feature.py` verifies every part's codec, geometry, rate and pixel format before
joining, and verifies every PCM mix against its own part's picture duration.
**Neither check is optional** — a concat demuxer handed a mismatch does not
fail, it produces a file that plays wrong somewhere in the middle.

`feature.py` also prints what fraction of the running time is connective tissue,
and it is worth reading. **The cold open and the wraparound do not shrink when
the season does.** On a three-film season, 26.1 s of cold open plus 29.0 s of
show was **39.5 % of a 139.6 s feature** — proportions designed for six films,
carried unchanged into half that. A short season probably wants a shorter cold
open and two-line interstitials; decide that in Phase 0, not after the join.

## Claims: the part that is not a rendering problem

Before publishing anything that touches the real world:

- **A real person is not a character.** If a premise comes from someone real,
  the film must invent the name, the face and every quote, and assert that in
  code rather than in a note.
- **Do not name a real subject in a piece that implies fault.** The reference
  season's fifth film is about an animal that died in an accident and never
  names it — the script asserts the absence.
- **You are unreliable about what currently exists.** Any claim of the form "X
  is still there" must be verified or supplied by the user before it goes into a
  prompt or a line. Historical detail is safer than present tense.
