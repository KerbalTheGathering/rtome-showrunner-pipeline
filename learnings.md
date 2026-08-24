# learnings — what forks find

**Audience: a Claude Code session working on the `showrunner` template.**

A running document. Each section is one season built on this template, what it
broke, and what was changed in response. Append; do not rewrite.

Six seasons so far and twenty-seven faults between them. **Every single one
rendered clean, exited 0, and was wrong** -- that is not a coincidence, it is
selection: the faults that crash get found in the first hour by whoever wrote
them, and the ones that reach a document like this are the ones a green build
cannot see. Fault 27 is the purest example in here: a render that succeeded, a
file that was written, a check that printed "all present", and a pipeline that
could not find any of it.

The first fork's report is [`docs/10_fork_report.md`](docs/10_fork_report.md).
It took the template to a 139.6s feature — a cold open, three films, a
three-segment wraparound with lip sync — and everything it says still holds.

This is a **second** fork, and it was deliberately the opposite shape: **one
film, no show layer, 55.2s, 2.39:1 scope, shot end to end in an afternoon.**
A small season exercises different machinery from a large one, and all three
faults below are things a six-film season would never have hit.

Everything here happened. Nothing is speculative.

**Every fix named was applied to this repo and then run.** Faults 21–26 came
out of a sixth season built in a copy that has since diverged completely, so
they arrived here as a work order rather than a changelog; that work was done
on **2026-08-17** and each entry now says what landed. Fault 27 was found while
doing it.

---

## The season this came from

| | |
|---|---|
| Shape | cold open (2 shots, wordless) + one film (10 beats) |
| `SHOW` | `False` — no wraparound, no interstitials, no lip sync |
| Delivery | 1482×602, 24fps, 2.39:1 scope — **not** 4:3 |
| Plates | Krea2, 11 renders, local |
| Motion | local H3, 6-step turbo, 12 clips, $0.00 |
| Voice | ElevenLabs, 10 takes, 27.0s of speech |
| Result | 1324 frames, 55.19s, joined and verified |

The content was found text: a language model's posted chain-of-thought before
it answered "Hi there! Tell me about yourself", read straight, over monumental
architecture. Which is irrelevant to this document except for one thing — **the
film's whole construction depended on one frame being empty**, and that is how
fault 3 was found.

---

## The three faults

Every one of them rendered clean, exited 0, and was wrong. That is the house
style and it is not a coincidence: the ones that crash get found in the first
hour by whoever wrote them.

### 1. `shot.PLATE_SEED` had no effect on any plate you would ever put in a film

**`gen_still.py`, all three trees.** The dispatch line read:

```python
rc = render(sid, shot.obj_prompt(sid) if OBJ else b["prompt"],
            b["what"], shot.plate_seed(sid) if OBJ else seed)
```

`shot.plate_seed(sid)` — the function whose entire job is to resolve a per-beat
seed — was consulted **only on the `--obj` branch**. Every normal plate got the
film-wide `seed` instead.

So `shot.PLATE_SEED`, whose own comment reads *"Any beat re-rolled with
`--seed=` must be written down here… after which it is a lie for those beats
and nothing complains"*, was itself the lie. Writing the re-roll down was the
documented, disciplined, obedient thing to do, it looked like it worked, and
the next render of that beat quietly used the default.

**How it was found.** Three plates were re-rolled after a contact sheet, all
three were recorded in `PLATE_SEED` as instructed, and the log kept printing
the old seed. Nothing else would have shown it — the plates that came back
were *different* plates (a re-roll of a cached-free graph varies anyway), just
not the seeds that had been asked for and written down.

**Fixed.** `--seed=` on the command line still overrides everything; without
it, the per-beat table wins. One flag, three files.

> **The shape of this fault is worth more than the fix.** A record that has no
> effect is worse than no record, because the next person reads it and believes
> it. If a table exists to be honoured, something must read it — and the thing
> that reads it is the only proof it is honoured.

### 2. A season with `SHOW = False` could bake everything and then refuse to finish

`season_identity.py` offers `SHOW = False` for "a season that is just a cold
open and N films", and `season.py` honours it right up to the last step:

```
FAIL: the join lives in show/feature.py and this season has no show layer.
Add one, or join the films by hand.
```

Both parts baked. Both were correct. The one artefact the entire run exists to
produce could not be made, and the remedy offered was to add a wraparound you
had explicitly declared you did not want.

**The coupling was nothing at all.** `feature.py` imported the show's
`identity` and `shot` and **used neither**. Two dead imports were the only
reason the joiner lived inside the optional folder. Everything it actually
reads — `parts.running_order()`, `season_identity` — is season-level and
always was.

**Fixed.** `feature.py` and `publish.py` moved to the season root, the dead
imports are gone, `season.py` joins without asking whether a show exists, and
`publish.py` and `show/qc_feature.py` now read `feature.OUT` rather than
rebuilding the path from their own location. Verified by joining a real
no-show season end to end.

> A dead import is not free. It decides where a module is allowed to live, and
> nothing in the repo can see that it is dead.

### 3. The cold open's light guard could only ever say "nothing changes"

`cold_open/motion.py` ended with:

```python
assert "The sun stays where it is" in _p, f"beat {_sid} does not pin the light"
```

That is a sentence out of one season's outdoor cold open, made the guard for
every cold open the template will ever produce. This fork's cold open was an
interior — a stone hall, no sun in it anywhere — which left two options:

- carry a sentence pinning a light source that is not in the frame, which pins
  nothing at all while still passing the check; or
- **delete the guard**, which the docs tell you never to do.

It also could not express a cold open where the light is *meant* to change.

**Fixed.** The guard now checks that the beat **declared** something about its
light, either way, and leaves the answer to the film.

---

## And the rule the template teaches, which the template then broke

`_session_template/motion.py`'s docstring states it in capitals:

> **A PROHIBITION IS NOT A POSITION.** Naming a thing you do not want puts it
> in the frame's vocabulary; it does not reliably remove it.

`cold_open/motion.py`'s example `_HOLD` block read *"It does not rise,
brighten, change colour or move."* Four prohibitions, in the tree that is
copied verbatim into every new season, immediately below the file that
forbids them.

This fork copied that shape into an interior cold open and got exactly what
the rule predicts: **H3 lit the bulb, and then lit every arch in the hall like
strip lighting, over five seconds, in a shot whose one job was to be dark.**
Nothing failed. The clip was beautiful. It was the wrong clip.

Rewriting the same instruction as a conserved positive — *"the stone is unlit
dark grey in the first frame, in every frame in between, and in the last"* —
fixed it at the same seed, first try. The example block has been rewritten so
the template stops demonstrating against its own rule.

**The reusable form is three parts, and it is already in the docs:** what it is
now, that it stays, and that it is *still* that way in the last frame.

---

## Two things about content, not machinery

Not faults in the repo. They cost this fork time and they will cost the next
one the same.

**A shared style block is an instruction every frame must obey.** `shot.py`
asks for a `_THESIS` that rides in every prompt so the season argues one thing
in every frame. This fork's read *"An enormous apparatus is deciding something
trivial"* — and the one shot in the film that had to be a completely empty
room came back with a beautifully rendered enormous apparatus standing in the
middle of it. The block was right fourteen times and was still an instruction
the fifteenth frame had to follow. **A frame that must lack the season's
subject needs the medium block without the thesis**, which is one more named
constant, not an exception in the assembler.

**Nothing but the contact sheet would have caught it.** `contact.py`'s
docstring says to look at it. Do. Of eleven plates, four were wrong — the
apparatus in the void, a face that was supposed to be withheld and came back
lit, a warm doorway that came back as cold as the cold one, and a bulb that
was supposed to be off. Every one rendered clean. Every one was obvious the
moment they were side by side, and invisible one at a time.

---

## What was confirmed working, without qualification

Worth saying, because a document that is only faults misrepresents the thing.

- **`smoke.py`, `contract.py`, `residue.py`, `preflight.py` all earned their
  four seconds.** `preflight.py` in particular caught `make_music.py` in two
  trees still carrying the reference season's bolero, which is exactly the
  fault its own comment says it was added for.
- **Scope worked with no special-casing.** `season_paths.canvases()` derives
  the ladder from the delivery aspect, so `W, H = 1440, 602` produced a
  1024×416 ladder and everything downstream simply followed.
- **`PLATE_ALIAS` is the right construction and it is under-sold.** Beat 09 of
  this film is beat 01's plate, so the last thought lands on the *same* frame
  the first one did. Two clips off one plate, and the difference lives in
  `motion.py` where it costs nothing.
- **The look libraries paid for themselves before a single frame was baked.**
  `grades.py --sheet` is what argued this film out of `night` — it would have
  tinted the only warm element in the picture blue, to say something the
  plates already said. That decision took one look and no renders.
- **Local H3 shot 12 clips for $0.00** at roughly 0.35 s/frame, and
  `check_clip.py`'s filmstrips are what caught fault 3. The strips are not a
  nicety; they are the only place a five-second lighting drift is visible
  without watching every clip.

---

# The music video — a third season, and the mode that could not be entered

A third season, built a day later and deliberately shaped to break different
machinery: **`UNEXPECTED_ITEM`, 77.6s, one film, no show, no cold open, no
spoken word, and not one paid API call.** Krea2 for plates, local H3 for
motion, **ACE-Step v1.5 for the song**, which the machine writes and sings.

It is a torch ballad performed by a supermarket self-checkout about a customer
who did not come back. What matters here is the shape: **the picture is cut to
the song.** That inverts the spine of this entire repo, and the inversion is
what found the faults.

| | |
|---|---|
| Delivery | 1440×1080, 24fps, 4:3 |
| Beats | 11, every one exactly two bars |
| Voices cast | **none** |
| Score | ACE-Step v1.5 turbo, 8 steps, 1.7 min, local |
| Result | 1862 frames, 77.60s, $0.00 |

---

## 4. The non-narrated mode was documented, supported, and unreachable

`_session_template/identity.py` refused an empty `VOICES`:

```
FAIL: identity.py declares no VOICES. A film with nobody in it needs
  script.SILENT covering every beat and edit.SILENT_SECS giving each one a
  length -- see docs/01_process.md on the non-narrated mode.
```

Every word of that is correct, and **it exits anyway**. `identity.py` cannot
check either condition: it does not import `script.py` or `edit.py`, and it
must not, because they import *it*. So the guard could only ever state the
requirement and refuse to proceed.

Which means the mode `edit.SILENT_SECS` was built for, that `mixes.py` has a
dedicated bus for, that `docs/01_process.md` documents — **could not be
entered.** The only way past was to cast a narrator who never speaks. On a
season with no ElevenLabs in it anywhere, that means writing an ElevenLabs
voice id into `identity.py` for a film that never calls the API: recording
something untrue in order to satisfy a check.

`script.py` had a second, quieter version of the same problem —
`NARRATOR = next(iter(VOICES))` raised `StopIteration` at import on an empty
table, taking the module and everything downstream of it with it.

**Fixed.** The refusal moved to `contract.py`'s `check_cast`, which already
loads both files and can see the answer: a film may have no voices, but if it
has none then every beat in `shot.CUT` must be in `script.SILENT` with a length
in `edit.SILENT_SECS`, and `script.LINES` must be empty. `NARRATOR` is now
`next(iter(VOICES), None)`.

> **A guard that states a requirement it cannot verify is not a guard, it is a
> wall.** This one was written by somebody who knew exactly what the right
> answer was and put it in the one file that could not check it.

---

## 5. Asking a model for 68 BPM does not give you 68 BPM

No fix in the template, because it is not a bug in the template. It is the
sharpest example this repo has yet produced of its own thesis, and the next
season that cuts to anything generated will hit it.

Every cut in this film is arithmetic. Eleven beats, two bars each, at the
tempo the song was asked for. So `song.py` asks ACE-Step for 68 BPM in 4/4 and
77.65 seconds — and `TextEncodeAceStepAudio1.5` takes bpm, duration and time
signature as **real inputs**, not as adjectives in a style tag, which is the
only reason cutting to a grid is possible at all.

What came back was **77.64 seconds**. Dead on. A duration check passes it
without a murmur.

It is also **68.91 BPM** — 1.3% fast. The model honoured the length exactly and
simply put more beats inside it.

Cut that song on a 68 grid and the first edit is right, the fourth is a frame
or two late, and the last one misses its bar by about a quarter of a bar. It
renders. It plays. Every shot is the right shot. The cuts are just wrong, by
more at the end than at the start, which is the hardest kind of wrong to see
and the easiest to feel.

**What the film does instead:** measures the tempo off the delivered audio —
onset envelope, half-wave-rectified first difference, autocorrelation over
0.30–2.20s — and derives the bar from **that**. 3.483s, not 3.529s. The last
beat absorbs the ~1.0s remainder so the picture totals exactly the song.

```
asked for 68 BPM  ->  delivered 68.91 BPM (+1.3%)  ->  bar = 3.483s [measured]
```

`song.verify()` refuses on two counts now, not one: length outside a tenth of a
bar, **or** tempo more than 6% off. The second is the one that earns its keep.
The first take passed the first check.

> The repo already says it: **a check that does not measure the delivered
> artifact is not a check.** A duration is not a tempo, and length agreeing is
> not the grid agreeing.

---

## 6. `contract.py` assumes a score generator is prompt-per-cue

Minor, and arguably correct as it stands. `check_cues` looks for
`make_music.PROMPTS` keyed by cue name. A local ACE-Step generator does not
have one string per cue — it has **tags** (what the record sounds like) and
**lyrics** (what is sung) as separate inputs.

The season satisfies it by exposing `PROMPTS = {CUE: TAGS + "\n" + LYRICS}`,
which is honest rather than a shim: between them those two fields are the
entire brief, and if either were empty the cue could not be made. What
`contract.py` is really asking — *can every cue in the timeline actually be
generated* — is answered truthfully. Worth knowing before writing a second
non-ElevenLabs generator.

---

## What the previous fork's fixes did in production

Both backports were exercised by accident rather than on purpose, which is the
only test worth much:

- **`shot.PLATE_SEED` earned itself on the first re-roll.** Two plates were
  re-rolled after the contact sheet and recorded as `2478`; the log printed
  `seed 2478`. Before the fix it would have silently printed `2477` and
  rendered at the film-wide default.
- **The relocated `feature.py` joined a season with one part, no show and no
  cold open** without being asked to think about it. Under the old layout this
  season could not have been joined at all — it has no `show/` for the joiner
  to live in.

---

## What was confirmed, again

- **The contact sheet caught 2 of 11 plates.** Beat 08 had a face in a shot
  whose motion direction says only a hand and forearm are in frame — H3 would
  have animated a person who was not supposed to exist. Beat 11 came back as
  brightly lit as the intro, when the whole content of the shot is the room
  going down. Both rendered perfectly.
- **Stating geometry beats forbidding content, twice more.** "The arm
  continuing out of the top of the frame" left the rest of the body
  unaccounted for and the model found room for it; "the frame is cropped at
  the elbow and holds only the hand, the forearm, the bag and the shelf" fixed
  it. "Half the ceiling lights out" is a fraction, not a picture; naming
  *which* tubes are lit and *where* the darkness is fixed that.
- **Local H3 shot 11 clips at 1024×768 for nothing**, and dropped beat 11 to
  896×672 on its own when the latent budget said so — `pick_canvas()` working
  silently and correctly.

---

# The tiny desk — a fourth season, and lip sync outside the show layer

**`POLO_TEES`, 2:28.6, 16:9, one film, seventeen beats, no spoken word, and no
paid API call.** An NPR-Tiny-Desk parody: a character in a clear space helmet
and an Edwardian suit performing an acoustic cut-down of a song about gangsta
manatees, played entirely straight by a room full of session musicians.

It is the first film in this repo to lip-sync a SINGER, the first to run
InfiniteTalk from a film tree rather than the show tree, and the first to carry
two LoRAs. Every one of those firsts found something.

| | |
|---|---|
| Delivery | 1920×1080, 24fps, 16:9 |
| Beats | 17 — eight lip-synced spine, nine H3 cutaways |
| Spine | WAN 2.1 InfiniteTalk, 32 chunks, ~55s each warm |
| Score | ACE-Step v1.5, 52 bars at 84 BPM |
| Driver | the vocal stem, separated locally from that same song |
| Result | 3566 frames, 148.60s, $0.00 |

---

## 7. `publish.py` made an optional folder mandatory

`season_identity.EXTRA` is documented as *"a second folder every render is
copied to, or `''`"*. `publish.py` read:

```python
os.makedirs(SEASON_DIR, exist_ok=True)
os.makedirs(MEMES, exist_ok=True)          # MEMES = "" when EXTRA is blank
```

`os.makedirs("")` raises `WinError 3`. So a season that left `EXTRA` blank --
the default, and what the comment invites -- crashed the publisher **after**
encoding the share cut: full work done, both sizes printed, then a traceback
on the last step of the last script in the pipeline, over a value the season
was explicitly allowed to leave empty.

Found by the first season to take the default. `--check` had been hinting at
it for a while, printing a blank line as a destination.

**Fixed.** The second copy is skipped when there is no `EXTRA`, and `--check`
no longer advertises an empty path.

## 8. `draw_text()` understood two anchors out of three — and the right version was already in the repo

```python
x = cx - (x1 - x0) // 2 - x0 if anchor[0] == "m" else cx - (x1 - x0) - x0
```

Centre, or else RIGHT. **There is no left branch.** `cards._lower_third`
returns anchor `"lm"`, so a left-anchored title was drawn right-aligned on its
own `cx`: the block ENDED 8% into the frame and ran off the left edge. On a
1440px delivery that put all but the last glyph of the title outside the
picture.

What makes it the house fault rather than a typo: `cards.limit()` and
`cards.span()` receive the same anchor and read it **correctly**, three
branches, left included. So the fitter sized the type to the space a
left-anchored block would have, and the bake printed

```
TITLE_1  0.080..0.395  (margins 0.080 / 0.605)
```

— a report of comfortably on-frame type, over a bake where the words were off
the screen. The check measured the INTENT and the renderer did something else.

It survived because only left-anchored cards are affected: the reference
season used `plain` (`mm`) and `corner` (`rm`), and `"r"` happened to fall into
the else branch that was already right-aligned.

> **AND THE CORRECT CODE WAS ALREADY IN THE REPO.** `cold_open/assemble.py`
> has had the proper three-branch version all along. The fix landed in one copy
> of `draw_text` and never reached `_session_template`, which is the copy that
> gets cloned into every film. A bug fixed in one of three copies is not fixed.

## 9. "SESSION #n" was one season's vocabulary, welded into the assembler

`_session_template/assemble.py` built its title card as:

```python
TITLE_1, TITLE_2 = f"SESSION #{shot.SESSION_NO}", shot.TITLE
```

"Session" is what the reference season happened to call its films. Every season
made from this template inherited it, so an episode was a session, a chapter
was a session, and a one-off music video with no numbered parts was
"SESSION #1". Same shape as the transition that lived in an `if` and the grade
that lived in a function.

**Fixed.** `season_identity.PART_LABEL` is a template (`"EPISODE {n}"`,
`"CHAPTER {n}"`, a constant, or `""`), `identity.LABEL` overrides it per film,
and `season.part_label(n)` does the formatting in ONE place so a malformed
template fails once with a sentence instead of printing `SESSION #{n}` across
every card in the season.

**The load-bearing part is what `""` does.** An empty label drops the line
rather than drawing a blank one: the line count feeds `cards.layout()`, so a
one-line card is laid out AS a one-line card, and the type is sized per line
COUNT rather than per index -- otherwise a single title silently renders at the
eyebrow's smaller size. The bake report going from two `TITLE_` rows to one is
how you can see it took that path.

> **TWO COPIES OF THE STUB, AND BOTH HAD TO BE TAUGHT.** `assemble.py` calls
> `identity.label()` at module level, so the fake identity that `smoke.py` and
> `contract.py` install for `--template` mode needed `label()` and
> `part_label()` or every tree reported as broken. `contract.py` keeps its
> **own** copy of that stub-boot code, separate from `smoke.py`'s `BOOT`, doing
> the same job with the same lambdas. Two copies free to diverge, in the two
> tools whose entire purpose is catching things that are free to diverge.
> Consolidating them has not been done.

## 10. The tempo check refused a song that was correct

Fault 5 says a duration check is not a tempo check. This is its other half:
**the tempo check I wrote then asked the wrong question, and refused a good
take.**

`song.verify()` fired with *"the song measures 34.00 BPM against 84 asked
for"*. The obvious response is to re-generate. The song was fine:

```
2.8212s  (21.3 BPM)   ac 0.436   <- the BAR
1.7647s  (34.0 BPM)   ac 0.393
1.0565s  (56.8 BPM)   ac 0.369
0.7082s  (84.7 BPM)   ac 0.250   <- the actual beat
```

Every one of those is a multiple of the beat. The detector took the single
strongest autocorrelation lag in a wide band (0.30–2.20s), and on an acoustic
band arrangement with a firm bar that lag is the BAR. The song was asked for 84
and delivered 84.7 — 0.9% out, entirely fine.

> **A CHECK THAT REFUSES CORRECT WORK COSTS AS MUCH AS ONE THAT PASSES WRONG
> WORK**, because the obvious response to it is to widen the tolerance until it
> stops complaining — and then it is not a check any more.

**Fixed** by narrowing the question. "What is the tempo of this audio" is a
research problem; "did the generator honour the tempo it was given" is
answerable. The band is now ±35% around the REQUEST, and a flat correlation
there — no pulse near the requested tempo at all — is the real failure and is
reported as one. Verified it did not break the case that already worked: the
previous season still measures 68.91 BPM, unchanged.

## 11. A character LoRA with no style LoRA could not be rendered at all

`gen_still.py` built the character loader as:

```python
if shot.CHAR_LORA:
    g["59"] = {... "model": ["52", 0], "clip": ["52", 1]}
```

Node 52 is the STYLE LoRA, and it is only added `if shot.STYLE_LORA`. So the
combination *character LoRA, no style LoRA* produced a link to a node that was
never in the graph: HTTP 400 from `/prompt`, every time, for that one
combination.

`_tail()` immediately below handles all three combinations with great care, and
its docstring even warns about "pointing the sampler at a node that is not in
the graph". The line above it had exactly that fault.

Nothing caught it because no film had tried it — the reference season ran
style-only or neither. **Fixed** in all ten copies of `gen_still.py`, including
the templates.

## 12. The bake deleted twenty-eight minutes of lip sync

`assemble.plan()` opens with:

```python
shutil.rmtree(WORK, ignore_errors=True)
```

`italk.py` writes `synced_XX.mp4` into `_work/`, and `stem.py` writes the
per-beat drivers there too. That is the SHOW tree's convention, where it is
safe. In a film tree `_work` is the assembler's scratch and is cleared at the
top of every run.

So starting the bake — the next command in the documented order of operations —
destroyed every lip-sync render. **And it did not fail honestly.** The bake ran,
took beat 01 from its H3 clip, and stopped at beat 02 with

```
FAIL: no clip for beat 02 in ...\TINYDESK_clips -- run make_video.py
```

which points at the wrong tool entirely.

> **TWO TOOLS SHARING A DIRECTORY WITH DIFFERENT LIFETIMES.** `_work` is
> scratch by design: extracted frames, mixes, things rebuilt every run and
> meant to be disposable. A lip-sync render is the opposite — it costs half an
> hour and nothing else reproduces it. They cannot share a directory.

**Fixed:** `_sync/` holds `vo_<sid>.wav`, `it_raw_<sid>.mp4` and
`synced_<sid>.mp4`, and `assemble.source()` looks there.

**Recovered without re-rendering**, because ComfyUI keeps its own copy of every
render: the raws came back out of `<ComfyUI>/output/it/` and `italk.py
--shift-only` re-derived the 24fps segments. Worth knowing that `output/it/` is
shared across seasons and its numbering simply continues — the same hazard the
repo already solved for clip folders with the `.season` stamp
(`season_identity.claim_clips`). The lip-sync output folder has no equivalent
guard.

## 13. A film tree could not say how long a beat is, in frames

`italk.py` renders at 25fps and converts down, so it must know exactly how many
delivery frames the finished segment has to be — ask for one too few and the
mouth runs out before the bar does. It reads `edit.FRAMES[sid]`.

`show/edit.py` has carried `FRAMES` since the reference season.
`_session_template/edit.py` never had it, so a film tree could not answer the
question at all. One more way lip sync was welded to the show layer.

**Fixed.** `FRAMES` is a derived lazy attribute alongside `SECS`, and the two
are deliberately different numbers: `SECS` is how much CLIP TO BUY (beat plus
margin, snapped up to a whole second, because the assembler enters each clip a
little way in), `FRAMES` is what actually reaches the cut.

## 14. `SOFT_UNDER` was being used as a global grade

The default `SOFT_UNDER = 0.60` flagged all seventeen beats and `assemble.py`
refused, correctly:

```
FAIL: every beat reads as soft. SOFT_UNDER is a line BETWEEN the stocks in
the film, not a global grade.
```

Every source in this film is smaller than its 1920px delivery, so a line at
0.60 catches everything and sharpens everything, which is not a comparison.
This film has exactly two stocks, and they are two different MODELS:

```
 880px   the InfiniteTalk spine   (880/1920  = 0.458)
1024px   the H3 cutaways          (1024/1920 = 0.533)
```

0.50 is the line between them: the sync renders get the unsharp pass and the
cutaways do not. **A good refusal** — it named exactly what the number is for
and why the default could not be right here.

---

## What lip sync outside the show layer actually needs

Nothing in `docs/04_lipsync.md` is wrong. All of it is about SPEECH, and three
of its assumptions do not survive contact with a singer.

**The driver must be the isolated vocal, not the mix.** InfiniteTalk drives a
mouth from an audio track, and every previous film handed it a dry VO take.
This film's audio is a band. Hand that to a lip-sync model and the mouth chases
the loudest transient — it lands on the cajon and the guitar attack instead of
on the words. It renders. It is confident. It is somebody chewing in time with
a snare.

`MelBandRoFormer` splits it locally in fifteen seconds, and the two are
sample-aligned because one came out of the other, which is the only reason the
mouth and the music agree. Verify the split by measuring rather than by ear:

```
song.mp3    rms -11.55 dBFS   silent blocks   0.9%
vocal.wav   rms -22.12 dBFS   silent blocks  52.8%
```

That 52.8% is the signature of an isolated voice. The instrumental would have
been near-continuous like the mix — and taking output index 1 instead of 0 is a
silent failure that renders a closed mouth moving to the guitar.

**Singing wants LESS lip amplitude than speech.** The show tree ships
`audio_scale = 1.5`, arrived at by sweep for "a man selling something at
volume". On one 81-frame chunk of a sung beat:

```
scale 1.00   mouth energy 0.849   corr(mouth, voice) +0.481
scale 1.75   mouth energy 1.033   corr(mouth, voice) +0.377
```

More amplitude bought MORE motion and LESS agreement with the voice. Sung
vowels are sustained and the gaps between phrases are long — about half of each
11.3s spine beat has no voice in it at all — so the extra amplitude spends
itself on movement the envelope never asked for.

**The plate's mouth must be CLOSED.** This one was got wrong first and
corrected by the person watching it. The instinct is that a singing plate makes
a singing shot, so the plates were rolled with the mouth open mid-word. That is
backwards: the plate is the FIRST FRAME and the model generates every
subsequent frame from it, so it is the REST POSITION the mouth returns to
between syllables. Anchor it open and the whole clip is biased open, and the
long gaps never close. Closed-mouth plates measured *better* over a full beat:

```
open-mouth plate   ( 81f)   mouth 0.849   corr +0.481
closed-mouth plate (272f)   mouth 1.577   corr +0.465
```

Nearly double the articulation with the correlation held, because from a closed
rest position the mouth has further to travel to open.

**A glass helmet over the face was not a problem.** It was the main worry going
in and it simply did not materialise.

**Measure it with something, even if the repo's metric will not run.**
`show/mouth_open.py` wants insightface's 106-point landmark mesh, which was not
installed and would in any case be asked to find a human face mesh on a
hand-painted character inside a dome. Mouth-ROI motion energy against the
driver's envelope, with a CONTROL ROI elsewhere in the frame, answers the same
question without needing to locate a face: the control staying near zero is
what proves the signal is the mouth rather than the whole shot drifting.

---

## Three prompting failures, one rule

`shot.py` states it in capitals — **THE LEADING BLOCK WINS TIES** — and this
film broke it three times, in three different directions. All three rendered
clean.

**A style LoRA does not outrank the sentence it is handed.** `_MEDIUM` opened
all seventeen prompts with "Photographic still on 35mm colour negative" while
a hand-painted animation LoRA was loaded at 0.85. A probe settled it: that LoRA
ALONE, against a prompt saying "photographic portrait", returned a completely
photographic portrait. The LoRA was loading; the words were beating it.

**A character trigger buried mid-prompt is a diluted trigger.** The trigger sat
fourth, after ~60 words of medium block and set dressing, and the face came
back different in every framing — plausible and wrong. The same LoRA alone,
against a six-word prompt, produces one specific repeatable person.

**And then the correction overshot.** Describing the character exhaustively
from a reference — beard, dome, brass ring, rivets, lining, three-piece,
piping, buttons, collar, cravat, pocket square, about ninety words — got the
character exactly right and **no guitar at all**. He sat with his hands on his
knees in all three cameras. The instrument was last in the sentence and lost
the tie.

> A character LoRA supplies the likeness. The prompt's job is the few
> identifiers it needs, plus the things the LoRA cannot know. In a music video
> the guitar is not set dressing, it is the action — so it goes in capitals and
> gets its own clause.

**The general form, which is already in `docs/05_prompting.md` for shapes and
turns out to hold for everything:** state GEOMETRY, not absence. "The arm
continuing out of the top of the frame" left the rest of the body unaccounted
for and the model found room for a face; "the frame is cropped at the elbow and
holds only the hand, the forearm, the bag and the shelf" fixed it. "Half the
ceiling lights out" is a fraction, not a picture; naming *which* tubes are lit
and *where* the darkness is fixed that. "A wall of shelves" left the foreground
unclaimed and got two strangers in it; "one shelf filling the entire frame"
fixed that.

---

## What was confirmed, a third time

- **The contact sheet is the cheapest tool in the repo.** It caught the
  photographic-instead-of-painted look, the wrong character, the missing
  guitar, a face in a hand-only shot, and a band that had vanished from the one
  wide that exists to show there is a band. Every one of those rendered
  perfectly.
- **`PLATE_ALIAS` earned itself again.** Eight lip-synced beats off three
  plates — three cameras returning, which is what the format being parodied
  actually is. Each aliased beat still gets its own sync render from different
  bars, so nothing repeats.
- **The relocated `feature.py` joined a one-part, no-show, no-cold-open season**
  without being asked to think about it.
- **`assemble.py`'s in-point needs care with a synced clip.** An H3 take is
  bought longer than its beat and entered `ss` seconds in to skip vendor
  settling. A synced render is generated to exactly `FRAMES[sid]` — it IS the
  beat. Entering it 0.35s in would drop the first third of a second of the
  performance and slide every mouth late against the band, which is precisely
  the failure the lip sync exists to prevent.
- **Local H3 and local InfiniteTalk on one 4090**: 32 sync chunks at ~55s each
  warm (102s cold), nine H3 cutaways, eleven Krea2 plates, a 2:29 song and a
  stem separation. Whole film, $0.00.

---

# Pete's Vet Tips — a fifth season, a real dog, and a card that never got drawn

**`PETES_VET_TIPS`, 2:11, 16:9, one film, thirteen beats, a talk show hosted
by a real dog.** SaintFame throughout, no character LoRA -- there is no
trained likeness for the dog, so the character is a description held constant
across every plate, checked against a real photo. Six of the thirteen beats
are lip-synced (a desk-bound "host" camera, aliased across the beats that
talk); the rest are H3 cutaways carrying narration.

| | |
|---|---|
| Delivery | 1920×1080, 24fps, 16:9 |
| Beats | 13 -- 6 lip-synced, 5 H3 cutaways, 2 cards |
| Voice | ElevenLabs, cast by measured pitch spread, not by ear |
| Character | described from breed traits, corrected against a real photo, six passes |
| Result | 3141 frames, 130.9s, published, then corrected twice more after review |

---

## 15. `CLIP_MAX = 12` was a paid vendor's ceiling, applied to a free local one

`edit.py` refused: *"beat 02 needs 14.7s but the vendor caps at 12s."* Half
this film's lines were long enough to trip it. `CLIP_MAX` is the template's
default for a paid-per-second vendor (Seedance and similar bill by the second
and cap what they will sell in one call) -- and this film buys every clip
from LOCAL H3, which chains chunks with no such ceiling. `h3_shoot.py` had
already chained an 11.4s beat without trouble on the previous season; the real
constraint is VRAM/canvas size, and `season_paths.pick_canvas()` already
handles that by shrinking the frame rather than refusing.

**Fixed per season, not in the template.** `CLIP_MAX` is an editorial fact
about what a FILM is buying from, not a fact about the pipeline -- a season
still using a paid vendor needs the real ceiling. Raised to 24 in this film's
own `edit.py`, with the reasoning written beside it, rather than butchering
good lines to fit an assumption that never applied here.

> The number was never wrong. It was answering a question -- "what will a
> paid vendor sell me" -- that a local-only film never asked.

## 16. Nothing checks that a declared cue's audio exists before the bake spends its time

The mix step failed with an opaque `CalledProcessError`, exit code
4294967294, no readable ffmpeg output in the captured trace. The video half
of the bake had already finished -- 3206 frames, several minutes of CPU/GPU
work -- before the failure surfaced on the very last step.

Root cause, found by re-running the exact `ffmpeg` command by hand rather
than trusting the wrapper's error handling: `_music/main.mp3` did not exist.
The jingle's prompt had been written into `make_music.py`, but the script
that actually calls `/v1/music` and writes the file had never been run.
`preflight.py`, `smoke.py` and `contract.py` all passed -- none of them check
that a cue `edit.CUES` names has a rendered file backing it, only that the
declarations agree with each other. A season can be internally consistent
and still be missing the one file the bake needs.

> **When a subprocess fails with an opaque code and no visible stderr, rerun
> the literal command by hand before debugging anything else.** The wrapper's
> error handling is not guaranteed to surface the real cause, and it did not
> here -- the actual `ffmpeg` error ("No such file or directory") appeared
> immediately once run directly.

Not fixed in the template: this is a real gap (a check that verified
`_music/<cue>.mp3` exists for every `edit.CUES` entry before `assemble.py`
starts baking would have failed in four seconds instead of after the video
bake), and it has not been built. Noted below, under Still open.

## 17. `publish.py`'s share cut was 4:3, unconditionally, for two seasons running

Both `POLO_TEES` and this film delivered 16:9 features with a **4:3** share
cut -- `SHARE_W, SHARE_H = 720, 540` was a literal, and 720/540 is exactly
4:3. The comment even explained why: *"matched to what shipped, probed off
the published file rather than guessed"* -- true, and the whole problem: it
was probed off the reference season, which delivered 4:3, then carried as a
literal into every season cloned afterward. `ffmpeg`'s `scale` filter does
not refuse a mismatched aspect; it squashes the picture, silently, and
nothing downstream ever compared the share cut against its own source to
notice.

**Found by the user watching the actual file**, not by any check in this
repo -- worth sitting with. Fixed by deriving `SHARE_H` from the season's own
aspect:

```python
SHARE_W = 720
SHARE_H = round(SHARE_W * season.H / season.W / 2) * 2   # even, for yuv420p
```

Backported to `publish.py` at the season root and to every season's own copy.
`HELLO_GLIMMER_FILM` and `UNEXPECTED_ITEM` were both 4:3 already, so the bug
was latent there rather than visible -- the fix is correct for them too, it
just happened to be a no-op.

## 18. A style block's wording summoned a literal object into every unrelated scene

`shot.py`'s `_THESIS` -- the block that rides in *every* prompt in the film,
the same mechanism `_MEDIUM` uses -- opened with: *"A small, slightly worn
local-access television set, warm and a little old-fashioned..."* Meant as
the show's register (a TV *production*). Read by the model as an object,
because the sentence is grammatically identical to how every real object in
this repo's prompts gets introduced -- "A small round plush dog bed...", "A
leash hanging on a hook..." -- and there was nothing in the words to tell it
otherwise.

It leaked a vintage television into: a hallway with a vacuum cleaner, a
garden path with a mail carrier (rendered as a TV standing in the flower bed,
*and*, on the first attempt at fixing the SEPARATE window-vs-screen fault in
the same beat, an actual television screen filling the frame with a hand
reaching toward it -- two different manifestations of the same root cause in
one beat), a porch with a product shot, and a doorway with a leash. Every
scene that was not the desk it was actually describing.

**Fixed** by rewriting it to describe a *programme* rather than an object --
*"In the warm, a little old-fashioned register of a small local-access cable
program..."* -- so there is nothing noun-shaped left for the model to place.
Re-rolled the four affected plates and re-shot their H3 clips (the old clips
were generated from the contaminated plates and would not have updated on
their own).

> The negation trap ("nobody in the frame" summons a person) is well
> documented in this project by now. This is the same failure from a
> different angle: **a metaphorical noun phrase is read literally**, not
> because it names an absence, but because nothing marks it as figurative.
> Any block that rides in every prompt is a block every unrelated scene has
> to survive.

## 19. A card's on-screen duration and its beat's length are two numbers, and they drifted

The opening title faded out, then sat on the plain, undimmed, empty room for
two and a half seconds before the cut to the host -- reported by the user as
"fades to black, then pops back to the same scene," which is exactly what it
was doing. `identity.TITLE_CARD`'s own settings (`over_colour`: fix 0.6 +
hold 3.0 + out 0.8) add up to 4.4s. The beat was typed as 7.0s. The gap
between them was silent, undimmed screen time with nothing happening in it.

**Fixed** by deriving the beat's length from the card instead of typing a
round number next to it -- and the fix immediately became the shape of a
second, matching bug: beat 07's own mid-film card (see the next entry) was
about to make the identical mistake, `SILENT_SECS["07"] = 4.0` against
whatever the card actually needed. Derived that one too, at the point of
writing it rather than after a second report:

```python
_mid_style, _ = shot.MID_CARDS["07"]
SILENT_SECS["07"] = cards.seconds(_mid_style)   # exactly, not a typed guess
```

> **Any duration that has to equal another duration is a bug waiting for the
> day they disagree.** `edit.py` already says this about VO ("a beat's length
> is computed from the MEASURED narration... so the sound and the picture
> cannot disagree"). It is equally true of a card's hold against the beat it
> sits on, and it had not been applied there until a viewer caught the gap.

## 20. There was no machinery for a card anchored to a beat other than the first or last

Beat 07's `"what"` comment read *"AND NOW, A WORD FROM OUR SPONSOR"* and
nothing ever drew it. `TITLE_CARD` and `END_CARD_STYLE` are the only two
cards `assemble.py` knows how to place, and both are anchored to the film's
START and END respectively -- there was no way to say "draw this card over
THIS beat," wherever it happens to fall in the running order.

**Built, not just fixed** -- this is new machinery, not a patch:

```python
# shot.py
MID_CARDS: dict[str, tuple[str, list[str]]] = {
    "07": ("plain", ["AND NOW, A WORD FROM OUR SPONSOR"]),
}
```

`assemble.py`'s `plan()` computes each mid-card's alpha window **clamped to
its own beat's frame range** -- the same clamping discipline the title card's
picture-treatment window already uses against its own beat, generalised to
an arbitrary beat instead of assuming beat one. The alpha shape matches the
title card's (a short fixed fade-in, a hold, a fade-out sized by the card's
own `out` setting), so a card announced mid-film reads as the same
vocabulary as the one at the start rather than a new one. `bake()` fits and
caps its fonts the same way `END_CARD` does, and its text goes through the
same on-frame overflow check every other card gets -- a mid-card that ran
off the edge would refuse the bake, not ship. `contract.py` validates the
card name and the beat both exist, the same shape of check as everywhere
else in this repo.

**Deliberately scoped down.** It draws text only -- it does not run a card's
PICTURE treatment (the effect `break_diagonal` uses over the opening beat).
That needs neighbour-frame lookback that does not generalise to an arbitrary
later beat without real additional machinery, and no card in active use
needs one; `break_diagonal` is a season signature, not something a quick
mid-film aside would reach for. The gap is documented in `shot.py` at the
point a season would need it, rather than built speculatively now.

Backported whole: `_session_template/shot.py` (empty `MID_CARDS = {}` by
default, same pattern as `PLATE_ALIAS`), `_session_template/assemble.py`
(all five patch points), `contract.py` at the season root, and a line in
`docs/09_scripts.md`.

---

## Six passes to draw a real dog

Every previous character on this pipeline was either invented (G-Man) or
matched against a photo from the first attempt (also G-Man, corrected once).
This was the first attempt to draw an ACTUAL PET from a description alone,
before a photo arrived, and then correct the description against the photo
once it did. Six rolls, and each one taught something specific.

**"Hound" alone reached for the most common hound.** A "Ridgeback and hound
mix" came back as a Beagle -- compact, a white blaze, a patched tricolour
coat. "Hound" was doing real work as an attractor toward the most common
hound, and it took dropping the word entirely (stating Ridgeback proportions
and a Pit Bull build directly) to stop it.

**Then a real photo arrived, and it corrected TWO earlier guesses that were
both wrong in different directions.** The invented "solid orange-brown coat"
was not his coat -- he has a brindle mask over a warm reddish-tan base. The
invented burgundy bow tie was not his -- he wears his own teal collar and a
bandana. A photo doesn't just fix accuracy, it replaces invention with fact,
and the fork had no way to know which of its inventions were wrong until it
had one to check against.

**Even with a photo, "a mask" and "stocky" both overshot.** Asking for "a
darker brindle mask... fading to lighter tan on the ears" came back as a
near-solid grey-blue face AND ears -- a Cane Corso, not the warm tan dog in
the photo. "Stocky, muscular, broad blocky head" pushed the muzzle short and
mashed-in. Both fixed the same way as everywhere else on this pipeline:
**state the geometry precisely rather than handing the model an adjective it
is free to run with** -- "his ears are the SAME reddish-tan colour as the rest
of him, not a different colour" fixed the mask; "a LEAN, athletic build...
slender rather than stocky" fixed the muzzle. Capitals in the actual prompt
text, not just in this document -- geometric facts stated as facts read
differently from geometric facts stated as suggestions.

**And the negation trap found two new shapes to wear.** "A plush pet bed
shaped like a small ornate throne" read as a full-size armchair -- "throne"
pulled toward furniture-with-a-back-and-arms, and stating the shape as
absence of furniture ("low to the ground, no legs, no armrests, no
backrest") fixed it. Then the SAME bed came back with an uninvited puppy
curled up in it, because "small enough for a dog to curl up in" is an
invitation with the same shape as "nobody in the frame" -- stating the
cushion as "flat, smooth and completely bare" fixed that one.

> None of these six passes were wasted, and that is worth saying plainly:
> the fifth pass's overshoot (too grey, too stocky) was corrected by the
> sixth in about the time it took to read the render. A character built from
> a photo costs iteration; it does not cost redesign.

## The lip-sync gate, on a face that has never been tried before

The probe methodology from the singing season generalised cleanly to a dog.
One 81-frame chunk, driven by real VO, measured the same way:

```
mouth-ROI energy   1.353   control  0.131    (mouth carries ~10x the motion)
corr(mouth, voice)  +0.394
corr(control, voice) -0.163   <- not as clean a null as the human probes
```

The correlation sits in the same range the proven singing case measured
(+0.377 to +0.481), and the mouth region carries roughly ten times the raw
motion of anywhere else in frame -- almost all the movement in the clip is
at the muzzle. The control was not as clean a zero as prior probes (-0.163
rather than near-0), and at only 81 frames the noise floor on a correlation
estimate is roughly ±0.11 -- within range of sampling noise, not
necessarily a real secondary effect, but worth naming rather than rounding
off. **The gate does not replace a human watching the clip.** The numbers
said go; the actual judgement of whether a dog's mouth moving this way reads
as charming or uncanny was handed to the user, because that is a taste call
no correlation coefficient answers.

`_session_template/italk.py` turned out to already have a properly-built,
general, per-beat-opt-in lip-sync tool -- `TALKING: set[str]`, a `--probe`
mode built in for exactly this gate, GW/GH already derived from the season's
own aspect via `season_paths.at_aspect()`. This fork used it directly rather
than re-porting `show/italk.py` by hand the way the previous fork did.
**Two different, non-interoperable lip-sync integrations now exist in this
repo's history** -- see Still open.

## Verifying a long render is healthy, not stalled

Asked directly to confirm a ~40-minute background render was not stuck in
the documented offload-thrashing failure mode (`gen_still.py`'s own comment:
2.5s/step becoming 170s/step under VRAM pressure). Three checks, in order of
how much they prove:

1. **ComfyUI's `/queue` endpoint** -- one prompt actively `running`, not
   pending or dead. Necessary, not sufficient: a hung process can still hold
   a queue slot.
2. **`nvidia-smi`, sampled three times a few seconds apart** -- 99-100%
   GPU utilization, power draw near the card's TDP, VRAM comfortably under
   budget. Thrashing looks the opposite: LOW compute utilization despite
   apparent "activity", because the bottleneck becomes PCIe transfer to
   system RAM rather than the GPU cores.
3. **A log file is not evidence unless its own mtime says so.** The first
   instinct was to check ComfyUI's startup log; its last line matched
   something already seen hours earlier. `ls -la` on the log itself showed
   it was 13 hours stale -- checked BEFORE trusting its content, which is
   the only reason it was caught rather than reported as confirmation.

Separately, Python fully buffers stdout when redirected to a file rather
than a terminal -- 21 minutes of silence from a background task was not a
stall, it was output sitting in a buffer that had not filled yet. A `sys.exit()`
flushes on the way out, which is why the earlier FAILED run had looked more
"responsive" than the healthy long one; that is an artifact of how failure
exits, not a sign of health.

---

## What was confirmed, a fourth time

- **The contact sheet caught the negation traps again** -- a person at an
  "empty" desk, a chair-shaped bed, a puppy in a bed that was supposed to be
  bare. Every one of them rendered perfectly and none of them were what was
  asked for.
- **`h3_shoot.py`'s frame-grid chunking handled the longest beat in any film
  so far without complaint** once `CLIP_MAX` stopped refusing to let it try
  -- 532 frames (22.17s) at 768×448, chained cleanly, same mechanism as
  every shorter beat.
- **`audition.py`'s pitch-spread measure was worth trusting.** Frederick
  measured far more "performed" than the other two candidates (19.4/15.5/17.4
  semitones against Marshal's 6.6-7.9, close to the tool's own "drone"
  band) and the user confirmed the pick on listening.
- **Byte-hash verification plus a forced timestamp refresh is the right
  pattern for a OneDrive publish**, not just a copy. `Copy-Item` preserves
  the SOURCE file's original modified time, so a "fresh" republish can carry
  the exact timestamp the sync client already cached and never trigger a
  re-sync. Verified `Get-FileHash` match, then explicitly stamped
  `LastWriteTime`/`CreationTime` to `Get-Date`, on every publish this
  season.

---

## Still open

- **The audio rebuild in `feature.py` is untested against a no-show season with
  more than two parts.** It worked here, on two, and the priming-delay
  arithmetic it exists for only bites further down a running order.
- **`show/qc_feature.py` still has not been run.** The first fork's report
  lists it as fault 15 and says it was fixed. None of the four seasons in this
  document had a show layer, so none of them could exercise it. Five seasons
  in, nobody has QC'd a finished feature.
- **Lip sync now works from a film tree in TWO seasons, via TWO DIFFERENT,
  non-interoperable designs.** `POLO_TEES` used a hand-ported `italk.py`
  (plate from `gen_still` rather than a clean bake, a new `stem.py`,
  `assemble.source()` preferring the synced render at a zero in-point,
  `edit.FRAMES`, the `_sync/` convention) built because the fork building it
  did not know a template copy existed. `PETES_VET_TIPS` found that
  `_session_template/italk.py` had, the whole time, its own properly-general
  version -- `TALKING: set[str]` opt-in per beat, canvas derived from the
  season's own aspect via `season_paths.at_aspect()`, a built-in `--probe`
  gate, and writing its result straight into the H3 clip sequence via
  `next_take()` rather than needing a `_sync/` folder at all -- and used that
  instead. Both work. They do not agree on where a synced clip lives, how
  `assemble.py` finds it, or what a probe looks like. Only `edit.FRAMES` was
  ever backported from the POLO_TEES side. **Nobody has decided which of the
  two is the template's answer**, and a third season picking lip sync now has
  to choose rather than being told.
- **`contract.py` and `smoke.py` keep SEPARATE COPIES of the identity-stub
  boot code**, doing the same job with the same lambdas. Both had to be taught
  `part_label()` and `label()` in the same change. Two copies free to diverge,
  in the two tools whose whole purpose is catching things that are free to
  diverge. Consolidating them is an afternoon and has not been done.
- **`<ComfyUI>/output/it/` has no season stamp.** Clip folders are protected by
  `season_identity.claim_clips` writing a `.season` file, precisely so one
  season cannot consume another's renders. The lip-sync output folder is shared
  across seasons with numbering that simply continues, and has no equivalent
  guard. It was benign here only because recovery read by MTIME rather than by
  the highest number.
- **The local ACE-Step generator lives in a season, not in the template.**
  `UNEXPECTED_ITEM/S1_CHECKOUT/make_music.py` generates a full sung score on
  the machine for nothing, in the same shape as `h3_shoot.py`, and
  `song.py` beside it holds the bar grid and the tempo measurement. Neither is
  in `_session_template/`, because the template's `make_music.py` is
  ElevenLabs and swapping it would change what every existing season sounds
  like. A second, named generator alongside it is the obvious move and has
  not been made.
- **`_session_template/motion.py` still carries `{secs}` in its example head and
  absolute `0-4s` cue times in its beats.** Both are typed numbers describing a
  timeline `edit.py` owns and derives from measured narration. This fork
  removed them from its own copy and directed the shape of the change instead
  ("by the last frame", "for the whole clip"), which is true at any length. The
  template has not been changed — the numbers are useful direction on a
  long, busy beat and actively wrong on a near-static one, and which of those
  a season is made of is not the template's business to assume.
- **No check verifies a declared cue's audio file exists before `assemble.py`
  starts baking.** `PETES_VET_TIPS` lost most of a bake's worth of time to a
  cue named in `edit.CUES` with nothing rendered at `_music/<cue>.mp3`
  (see fault 16) -- `preflight.py`, `smoke.py` and `contract.py` all passed,
  because all three check that the TABLES agree with each other, not that
  the files a table points at exist on disk. The fix here was operator
  discipline (run `make_music.py`); the check that would have caught it in
  four seconds instead of after a full video bake has not been written.

---

# A Suitable Candidate — a sixth season, a scope aspect that did not snap, and a model that needs a run-up

**Read this one differently from the five above it.** Every previous section
could end "and the fix was applied to this repo and then run." This one cannot.
This season was built in a **copy** of the template at
`E:\Claude\Projects\EMPLOYMENT OPPORTUNITIES`, which is not a git repo and no
longer shares a line of code with this one. Every fix named below was written
and run **there**.

So this section arrived as a work order rather than a changelog. Faults 21–24
were findings about *this* repo, verified against the files in it at
**`cbf8378`** (2026-08-16, `docs: add 11_asset_library.md`). 25 and 26 were
carried from that fork's own documentation.

> **All of it has now been applied here**, on 2026-08-17, one commit per fault.
> Each entry below carries a **What landed** note. Fault 25's A/B was run
> against the local instance rather than taken on trust, and doing so turned up
> a twenty-seventh fault, which is written up at the end.

Fault 21 was reproducible in four lines and was the one to start with:

```
python -c "import season_paths as sp; cw,ch=sp.canvases(2688,1120)[0]; \
print(f'{cw}x{ch} = {cw/ch:.4f} against a delivery 2.4000')"
```

---

## The season this came from

| | |
|---|---|
| Shape | one narrated short film, six movements, no show layer |
| Delivery | **2592×1080, 2.40:1** — 1080 on the SHORT side |
| Runtime | 349.0s of cut + a 6.5s end card = **355.5s** |
| Plates | Krea2 + 3 style LoRAs + 1 character LoRA, 72 locked plates |
| Motion | local H3, 6-step turbo, ~90 takes, $0.00 |
| Voice | ElevenLabs, 34 takes, 131.0s of speech |
| Score | ElevenLabs `music_v2`, one 340s composition plan, 10 cues, ~$0.85 |

---

## 21. `season_paths.canvases()` does not return the delivery aspect, and five seasons never noticed

Its docstring is the claim:

> ```
> Render canvases at the DELIVERY aspect, largest first.
> ```

It snaps **both edges independently** to a multiple of 32 (`_snap32`), which
cannot preserve an arbitrary ratio. Measured against this repo:

| delivery | canvas returned | aspect error |
|---|---|---|
| 4:3, 1440×1080 | 1024×768 | **0.00%** |
| 16:9, 1920×1080 | 1024×576 | **0.00%** |
| 2.39 scope, 1482×602 | 1024×416 | **−0.01%** |
| **2.40 scope, 2688×1120** | **1024×416** | **+2.56%** |

**That is why five seasons ran clean.** 4:3 and 16:9 snap exactly. And the
second fork's 2.39 delivery — 1482×602 — *is itself* 2.4618:1, which is the
canvas aspect, so its plates were already the shape the canvas wanted. The
function has only ever been asked for aspects that happened to agree with it.

Ask it for a true 2.40:1 and the canvas is 2.4615:1, and every plate handed to
the video model is squeezed 2.56% before the model sees it.

**The model squashes; it does not crop.** Measured rather than assumed — clip
frame zero against the source plate resized three ways (squashed to fit,
cropped horizontally, cropped vertically), on eight shots spanning all four
style LoRAs. Squash fit 2–3× better than either crop, **unanimously, 8 of 8**.

So the picture comes back squeezed and **nothing in the bake un-squeezes it**.
`assemble.fit_aspect()` → `framing.apply(FIT, …)` fits by cropping, which
preserves the distortion and trims the edges as well.

**The repo already knows this failure mode by name.** Directly beneath
`canvases()` sits `at_aspect()`, whose docstring reads:

> ```
> that pair was typed, so a season that is not 4:3 would have synced at 4:3
> and been squashed on the way back out.
> ```

The lip-sync path was fixed for exactly this. The plate path was not.

**What landed** (`95c03df`). Both halves, plus a third nobody had noticed.

`_fit_grid()` searches the long edge two 32-steps down and tries **both**
short-edge neighbours at each, scoring on ratio error with ties to the larger
canvas; the ladder is derived from the pair that won rather than from the
pre-search one. `framing.unsqueeze()` then finishes the job at the bake, called
from `fit_aspect()` before any fit, keyed on the **exact** canvas size so it
fires on a frame off the video model and on nothing else.

Measured end to end on a drawn circle through the 2.40 path, width/height:

```
old canvas 1024x416   crop only 1.0300     unsqueeze+crop 1.0000
new canvas  992x416   crop only 0.9901     unsqueeze+crop 1.0000
```

**The third thing:** only rung 0 had ever been measured. The lower rungs were
worse than the table above and `pick_canvas()` reaches them on a long beat, so
they were in use — 16:9's bottom rung was **−3.57%**, and is now −0.48%. No
rung 0 moved on a shape a season has shipped, so existing clips keep their
canvas.

The tolerance idea was **dropped deliberately**: ~0.2% refuses 16:9's lower
rungs, which are the best the 32-grid has and are corrected at the bake anyway.
`aspect_error()` prints instead and says it is advisory —
`docs/06_verification.md` is explicit that a check refusing correct work costs
as much as one passing wrong work.

---

## 22. `h3_shoot.py` gives the video model no run-up, and the first half second of every clip is slower than the rest

`h3_shoot.py:173` — `length = grid(secs)`. The clip is exactly as long as the
beat, so its first frame is the cut's first frame.

That first frame is a **still plate**, and the model spends roughly its opening
half second climbing from it to the motion that was asked for. Measured on one
shot across **four different seeds**: the opening eighth of each clip ran at
**0.30, 0.32, 0.33 and 0.34 of that same clip's own peak** frame-to-frame
change. The consistency across independent draws is the finding — it is a
property of conditioning on a still, not a bad draw.

Neither words nor seeds move it:

- *"The movement is constant"* was **already in the shipped prompt** and did
  nothing. It describes a property, not the first frame.
- Rewriting it to *"already at full speed in the very first frame"* moved the
  ramp only **2.36× → 2.01×**.
- The best of four seeds still opened at 0.33 of its own peak.

**On most beats this is invisible or correct** — a man starts walking, a candle
starts guttering, a banner starts to lift. It is a fault only where the beat
must be **already at speed on the frame it cuts in on**: a melee, a chase,
anything cut into mid-action.

**The fix is structural.** Shoot the clip longer by a per-beat amount and throw
the run-up away in post. In the fork: `motion.RUNUP[47] = 1.0`, read by the
shooter to extend the length *and* by the trimmer to remove exactly that much —
one number, so the two cannot drift apart — and the trimmer **asserts that
enough frames survive to fill the beat** rather than shipping a short clip. That
assert fired correctly on the first attempt, against a clip shot before `RUNUP`
existed.

| | first eighth | peak | first/peak | ramp |
|---|---|---|---|---|
| as shipped | 1.39 | 8.05 | **0.17** | 2.70× |
| after dropping the run-up | 7.54 | 8.84 | **0.85** | 0.87× |

**What landed** (`011b86c`). `edit.RUNUP[sid]`, not `motion.RUNUP` — it is a
claim on the clip **length**, which is the same argument that put `TRANSITIONS`
in `edit.py` rather than in the assembler. `table()` adds it to the clip length
(so `h3_shoot` buys it, via `edit.SECS`) and to the in-point (so `assemble`
skips it, via `r["ss"]`), off one lookup. `motion.py`'s docstring points at it,
since the beat that needs one is found while writing direction.

```
no run-up        02  beat 5.40  buy 7s  ss 0.35   (unchanged)
runup 1.0 on 02  02  beat 5.40  buy 8s  ss 1.35
runup 1.0 on 01  FAIL: beat 01 needs 11.2s plus a 1.0s run-up but the vendor
                 caps at 12s -- shorten the line, split the beat, drop the run-up
```

`assemble.plan()` gets an **exact** frame check when a run-up is in play. The
trap is specific: `h3_shoot` skips a beat that already has a clip, so adding a
run-up to an already-shot beat moves the in-point into a clip nobody
lengthened, and the existing 0.9 slack is loose enough to ship most of a second
short in silence. The message says to re-shoot it.

`cold_open` gets a note rather than the machinery — it has no in-point at all,
and its shots are the ones that *start* something, where the ramp is the shot.

---

## 23. `motion.py` teaches the negation rule in prose and does not enforce it

`_session_template/motion.py` opens with the rule, correctly and at length:

> ```
> Naming a thing you do not want puts it in the frame's vocabulary; it does
> not reliably remove it…
> ```

It is a comment. Nothing checks the prompts.

The fork added an assert — a `_BANNED` tuple (`" no "`, `" not "`, `"n't"`,
`"never"`, `"nothing"`, `"without"`, `"empty of"`, `"free of"`, `"absent"`,
`"neither"`, `"none of"`) refused at import, naming the offending beat.

**It caught a violation in the same session it was consulted.** Rewriting a beat
to fix the speed ramp in fault 22, the natural English for "constant pace" came
out as *"moving **no** faster at the end than at the beginning"* — written into
the very file that states the rule, by someone who had just read it. The guard
refused the import; the phrase became *"holding one even pace from the first
frame to the last."*

A rule this easy to break by accident, in the most natural phrasing available,
belongs in an assert and not a docstring.

**What landed** (`6695107`). `direction.py` at the season root — one file, not
three copies, because fault 8 is a correct `draw_text` that sat in
`cold_open/assemble.py` the whole time while the copy every season clones had
the broken one. Every `motion.py` calls `direction.check(MOTION)` at import.

**It refused the repo's own shipped example, in every tree.** Run against the
direction text as it stood at HEAD:

```
_session_template   8 of 9 blocks refused, 42 phrases
cold_open           6 of 7 blocks refused, 28 phrases
show                2 of 2 blocks refused, 11 phrases
```

The style header's *"NOT photoreal, NOT 3D, NOT CGI, NOT anime"*. The frame
lock's four "does not"s in one sentence. `cold_open`'s `_HOLD`, opening with
six, and its `_EMPTY` — which is `docs/05_prompting.md`'s own worked example of
the trap (*"'No boats' does not remove boats"*) written out as direction, in the
folder copied verbatim into every new season. `show/motion.py`'s docstring
makes the argument for the positive form better than most and then spends eight
clauses on what the camera does not do.

Fault 3 above fixed `cold_open`'s **light guard** and left its prompts alone.
This is the other half of that finding. Every block is rewritten to the
three-part form; the audio blocks lose their "No voice, no dialogue" lists
outright, since `docs/05_prompting.md` sends that exact phrasing back to
"describe the room tone" and the description was already doing the work.

`python direction.py` self-tests against seven phrasings it must catch and five
it must not — including "cannot", "another" and "note", which contain banned
substrings and are ordinary direction. A negation checker that silently matched
nothing would vouch for every prompt in the repo.

---

## 24. `mixes.py` ducks the score by listening to the voice, when the edit already knows where every line is

`mixes.py:157` registers `ducked` — `sidechaincompress`, the score keyed off the
voice bus. It works, and it carries its own scar in the module docstring: it
*"once ate forty frames off the end of a finished film"*, because the compressor
is bounded by its sidechain input.

But a sidechain **guesses where speech is** from the signal. This pipeline does
not have to guess: the edit states the exact second every take begins and how
long it runs.

The fork drew the duck envelope from the plan instead — attack applied *before*
the line starts rather than after a compressor notices, and overlapping windows
taking the minimum so it cannot pump back up between two lines 0.5s apart. It is
sample-exact, it cannot be fooled by a breath or a hard consonant, and it has no
sidechain input to be bounded by, so the `-shortest` fault is not reachable.

Worth having as a second registered mix beside `ducked`, for seasons whose edit
knows its own line times.

**What landed** (`31dad05`) — **nothing, because it was already there.**
`mixes.under` has done exactly this since the library was extracted.

Verified rather than assumed: the ffmpeg volume expression evaluated directly,
on the toy film `mixes.py --graph` builds, lines at 4.0–6.0 s, 6.5–8.0 s and
20.0–23.0 s:

```
t 0.00   gain 0.550   before any line
t 3.85   gain 0.165   fully ducked 0.15s BEFORE the word
t 6.25   gain 0.165   still down between two lines 0.5s apart
t 9.00   gain 0.550   back up
```

Every property named above: attack ahead of the line, spans closer than
`2×(pad+ramp)` merged so it cannot swell inside a sentence, the deepest duck
taken where windows overlap, and no sidechain input to be bounded by.

So this is fault 8's shape again — *"AND THE CORRECT CODE WAS ALREADY IN THE
REPO"* — and `POLO_TEES` hand-porting `italk.py` for the same reason. What was
actually missing is that **nothing a person reads while deciding how to duck a
score mentioned it**: `identity.py` names it in a passing comment, and
`docs/03_audio.md`, the document about the audio chain, had not a word about
choosing a bus. Fixed where the looking happens, plus a pointer out of
`_ducked`'s own docstring. No second bus, because a duplicate of `under` is the
duplication this repo keeps paying for.

---

## 25. `gen_still.py` still carries two nodes a fork removed for degrading Krea2

Present in **all three trees** — `_session_template/gen_still.py:96,104`,
`show/gen_still.py`, `cold_open/gen_still.py`:

- node `28`, `ConditioningKrea2Rebalance`
- the `krea2filterbypass3.safetensors` LoRA

The fork's render harness omits both deliberately and says so in its own
docstring and README.

**⚠ Carried from that fork's documentation.** That session confirmed the nodes
are still present here, and did **not** run the A/B. Worth one controlled
comparison before either removing them or writing down why they stay.

**What landed** (`e66f2b2`). **The comparison was run**, against the local
instance, through the shipped `graph()` itself. Two seeds, one prompt, no
LoRAs, everything else byte-identical: a painted night interior with brass,
glass, a named optical part and a figure.

| | A (as ships) | B (`--plain`) |
|---|---|---|
| near-black | 15.3% / 21.5% | **0.21% / 0.77%** of the frame |
| detail (lapvar) | 0.0074 / 0.0076 | **0.0095 / 0.0121** |
| saturation | 0.236 / 0.297 | 0.188 / 0.217 |
| the fresnel lens | **generic lantern**, both seeds | **rendered as asked**, both seeds |

**The lens is the finding.** The prompt names "the great fresnel lens"; A
returned an ordinary storm lantern at both seeds and B drew the concentric
prism rings at both. That is `docs/05_prompting.md`'s *"a specific prop falls
back to a generic"* — the failure that costs re-rolls — tracking the **graph**
rather than the words or the seed. B also holds 30–60% more high-frequency
detail and does not crush a fifth of the frame to black.

Against B: A honoured *"the only light is the lamp itself"* better, and B
renders "on textured paper" as a literal sheet with margins, which a full-bleed
plate does not want. A's extra contrast and saturation is a **look**, and
`grades.py` makes it on purpose from a picture that still has its shadows.

**The default did not move**, and that is deliberate twice over. Six seasons
shipped through this graph and removing the nodes changes what all of them look
like — an editorial decision about a body of work, not a bug fix. And the
measurement has a hole in it: **no LoRA was loaded**, while every season that
shipped ran a style LoRA, which is exactly what a bypass at strength 100 would
interact with. `--plain` is the flag that made this one command instead of an
edit, and it stays for whoever runs it on a real film's prompt.

Two structural fixes fell out of adding the flag: the chain root is a **pair**
now rather than the literal `"51"` (node 52 and node 59 both hard-coded a node
id, and node 59's own comment records the last time that shipped an HTTP 400),
and `graph()` asserts every link points at a node that is in the graph — two
LoRAs times `--plain` is eight graphs and no film exercises more than one.

---

## 26. `make_vo.py`'s trailing-transient trim did not reproduce on 34 takes

`_session_template/make_vo.py:17` and `show/make_vo.py:17` state it as
universal — *"Every eleven_v3 take has a transient glued to its final
milliseconds"* — and prescribe a trim at mix time.

The fork profiled **all 34 of its takes at sample level** (peak amplitude in the
final 10ms against peak in the preceding 100ms, which is the actual signature of
a trailing transient) and found it in **zero of them**. Trimming 25ms from every
take would have discarded 850ms of real speech across the film to solve a
problem it did not have.

What *was* wrong is milder and needs a different fix: several takes end while
low-level energy is still present, and a file ending at 0.09 butted against
digital silence **clicks**. That is a discontinuity, and the fix for a
discontinuity is a **fade**, which removes no samples at all.

**⚠ Also carried from that fork's documentation rather than re-measured here.**
Either way the prescription should be conditional on a measurement rather than
stated as a property of the vendor.

**What landed** (`39e5f33`). Conditional, in both trees:

```
transient, ends in silence   trim 25ms, fade 50ms    (the old behaviour)
transient, ends on a word    trim 12ms, fade 20ms
no transient                 trim  0,   fade 10ms
```

The detector reads **peaks, not RMS** — a 10 ms spike barely moves the RMS of
the window holding it, which is why the existing trailing-silence measurement
could not have seen one even if it had been looking, and it was not looking.
Threshold 2.0, below the 3–5× the real ones measured and above anything
ordinary word-final energy does. Checked against synthetic takes:

```
documented transient (0.06 tail -> 0.29 spike)   4.83  TRIM
ends in clean silence                            0.00  fade only
ends on a word, decaying                         1.06  fade only
ends abruptly at ~0.09 (clicks, no spike)        1.38  fade only
word-final plosive, 1.6x                         0.82  fade only
```

The **fade** is the fix for the milder fault, and it removes no samples. The
trailing-silence half is kept: it is what stops a warranted trim landing on
speech, which shipped once on Session #3's last line.

`mix()` prints what the measurement decided (`vo tails: 9 no transient, 1
transient (25 ms trimmed in total)`). The count it leaves alone is the whole
point, and a run that suddenly trims everything — or nothing — is the first
sign the threshold has stopped discriminating. `show/` had no way to ask the
question at all; `tail_spike()` is new there.

---

## 27. `season_paths.check()` never asked whether the configured ComfyUI is the running one

**Found while running fault 25's A/B, by doing exactly this.**
`SEASON_COMFYUI` was unset, so `COMFY` fell back to `C:\ComfyUI\ComfyUI` —
which **exists**, and holds output folders from a fortnight earlier. The server
was running out of `I:\ComfyUI\ComfyUI`.

`python season_paths.py` printed the ComfyUI line as fine, because `check()`
asks whether `COMFY` is a directory and it is. The render submitted, ran, and
succeeded. The file landed in the other tree. The probe script's own
disk-listing scan found nothing and reported `NO OUTPUT` on a render that had
completed perfectly — which is how it was noticed at all.

In a season that would read: every plate resolver saying *"FAIL: no plate for
beat 07 — run gen_still.py"* about a beat that had just been rendered twice,
and an operator rendering it a third time into the same invisible folder.

> **The path exists and the path is the right one are two facts, and only the
> first was ever tested.** This is the repo's own thesis pointed at its own
> configuration layer: the check passed, nothing crashed, and it was wrong.

**What landed** (`e0fccb5`). `check_instance()`, read-only: ComfyUI advertises
its own input directory in `LoadImage`'s file combo, so if that listing and
`COMFY_INPUT` have no file in common and both are non-empty, they are not the
same folder. It also catches the cruder case this machine had, where the
configured tree has no `input` directory at all.

It says **nothing rather than guessing** when it cannot tell — server not
running (not an error; most of this pipeline runs without it), or either
listing empty, since an empty input folder is a fresh install. It lives outside
`check()`, which every `identity.py` calls on import and which must stay
offline; `season_paths.py`'s own `main()` runs both.

---

## What this fork built that the template has no equivalent of

Not faults — machinery that did not exist to be broken. Named because the next
scope-aspect, long-form season will want all of it.

- **A cut defined once and read by everything.** One module owns where every
  shot and every line lands; the storyboard, the animatic, the assembler and the
  audio mixer all read it, so they cannot disagree about which shot a line plays
  over. The template's equivalents each work out their own offsets.
- **A verifier that proves the assembled film IS the cut.** Length is the check
  that cannot fail interestingly — a film with two shots transposed is exactly
  the right length. So: for every shot, compare the frame the finished film has
  at that shot's timecode against frame zero of the clip it should open on —
  **and against the wrong clip**, so the test is shown able to fail. Honest
  matches scored 1.2–4.9; wrong clips 20.9–80.8.
- **A verifier that proves a post step reached the plate.** Hash every locked
  plate against every image that could have been its source; anything with a
  match is provably untouched since the sampler. A plate it *cannot* trace to a
  raw render is indistinguishable from one somebody quietly painted on — so when
  a relock renders into a new output directory, the right response is to tell
  the tool where the renders went, **never to relax the check**. It fired
  correctly three times this season on exactly that.
- **Per-cue fader targets for a generated score.** As generated, a 10-cue score
  spanned **28.6 dB** (loudest cue −14.0 dBFS, quietest −42.6 with a 0.035
  peak). Normalising the file as a whole put the quiet end near **−46 dBFS —
  below audibility**, which silently converts "the score fades away" into "there
  is no score". State a target dBFS per cue, measure each cue, apply the
  difference, and ride the gain across the joins. 28.6 dB → 11 dB kept the decay
  *and* kept the quiet end in the room.

---

## Three findings about derivation, which the template does not do at all

The fork derives shots from locked environment plates by img2img. All three cost
renders.

1. **A description that contradicts the init image fights the derivation instead
   of steering it — and at denoise 0.65 the description wins.** A block calling
   a stone "a rounded boulder" when the plate held a low warm-brown slab
   returned four plates carrying a tall round boulder: perfectly consistent with
   each other and nothing like the plate they derived *from*. **Transcribe the
   init image into the prompt before deriving.**
2. **That failure did not fail to fix the continuity — it MOVED it.** Four shots
   became consistent with each other and inconsistent with the fifth, which was
   the payoff shot. *A fix that relocates a problem onto a more expensive shot
   reads exactly like a fix until you check the neighbour.*
3. **Denoise is set by what has to be ADDED, not by the shot.** A figure that
   must appear where the init has clean, confident, empty ground costs far more
   denoise than one appearing against busy edges. At 0.55 one shot came back
   beautiful, matching, and **with no character in it**; a two-figure shot in the
   same sequence was fine at 0.55 because both stood against soft treeline.

Related, for removing something from a plate: **clone-patching only works when
the SOURCE region is featureless.** Cloning stock from a horizontal offset to
remove a sword imported a faint tree trunk and stood it up in the middle of a
light column. Where the background is a smooth gradient, interpolate across the
gap instead — it looks slightly smeared and imports **no structure**, which is
the only property an img2img init actually needs. Better still, where the clean
background for a region exists in an **ancestor plate**, composite it from
there: real pixels rather than a guess.

---

## And one about reviewing a sequence

**Check the shots a prop is a CLOSE-UP of, not just the shots its location is
in.** Re-deriving a seven-shot sequence for one stone's continuity, the extreme
close-up of the sword hilt had **no stone in frame at all** — so a location
continuity pass could never flag it — yet it was the only frame in the film
where the hardware is examined at full size, and it disagreed with every other
plate in the sequence.

From the same pass: **a length-changing post pass breaks any frame-for-frame
diff report.** It does not merely mislead; the arrays do not broadcast. Report
what was removed instead.

---

## Still open, from this fork

- ~~**Nothing above has been applied to this repo.**~~ **Applied 2026-08-17**,
  faults 21–27, one commit each. `smoke.py --template` green after every one.
  What is *not* done is the thing no check can do: **none of this has been
  through a finished film.** The un-squeeze, the run-up and the rewritten
  direction blocks are all verified against measurements and synthetic cases,
  and the first real season to use them is the one that will find what those
  missed.
- **Fault 25's measurement has a hole in it and the default was left alone.**
  Two seeds, one prompt, **no LoRA loaded** — and every season that shipped ran
  a style LoRA, which is exactly what a filter bypass at strength 100 would
  interact with. Re-run `gen_still.py --plain` against a real film's prompt
  with its own LoRAs before moving the default.
- **The template's example direction is now positive throughout, and nothing
  has shot from it.** Sixteen of eighteen blocks were rewritten to satisfy
  `direction.check()`. They read correctly and they are *untested as prompts* —
  the previous wording, for all that it broke the rule, had a season behind it.
- **The fork's copy has diverged completely.** It has its own render harness,
  shooter, assembler, verifiers, scorer and mixer, none of which import from
  here. Backporting is a deliberate project, not a merge.
- **No effects track and no cross-shot grade** exist in the fork either. Its
  clip-level tool corrects colour drift *within* a clip and has nothing to say
  about drift *between* two shots rendered weeks apart.

---

# Like a Stone — a music video, a rejected first cut, and a fault class the checks could not see

A 4:17 music video cut to a pre-existing recording: 45 shots, two generation
models, no narration. The first cut was **rejected by the user on sight** for
three faults — a character mouthing the lyrics, a vehicle splitting in two, and
"other graphical glitches". All three were real, all three were in the delivered
file, and **every check that fork had written rated all of them clean.**

That is the season's finding. The faults below are numbered from 28; the rules
they generalise to are in `docs/02_traps.md`, `docs/05_prompting.md` and
`docs/06_verification.md`.

## The shape this pipeline was not built for

A film driven by an **existing recording** inverts the template's core
assumption. The template derives every duration from narration it generates;
here the audio is fixed and immovable and the picture must be cut to it. What
that needed, and the template has no equivalent of:

- **A measured song, not a described one.** Tempo, bar grid, and the exact spans
  where anyone is singing, gated off an isolated vocal stem rather than the mix.
- **A forced alignment of the writer's lyric sheet against the record**, so the
  words are authoritative and the times are measured, and neither is typed.
- **A beat sheet derived from that alignment** — every shot length a consequence
  of where a line falls, tiling the record exactly.

## 28. A clip checker measured whole-frame means, and could not see any fault that shipped

**Found by the user, not by the checks.** The pass measured mean frame-to-frame
motion, whole-frame drift and end-to-end saturation across 45 clips and reported
44 clean. Meanwhile: a character was lip-syncing a song nobody on screen sings,
an old man's eyes lit up orange in a close-up, and a vehicle's cab detached from
its bed and drove on as a second vehicle.

A mouth is about **1 %** of the frame. Averaged over half a million pixels, all
three faults are noise. The metric answered its question correctly.

> **Faults are local; means are global.** A checker that reduces each frame to
> one number can only find faults that move the whole frame.

**What landed.** A structural pass measuring peak-block over median-block
motion, largest jump over median jump, and edge-energy growth — and, more
importantly, **a filmstrip sheet for every clip**, because all three faults were
obvious in five frames and invisible in every number. See rules 5 and 7 in
`docs/06_verification.md`.

## 29. A tiler asserted its output was exact and never that it was sane

Beats tiled the record exactly, in order, gapless, summing to the duration —
four asserts, all green, on a tiling whose **final beat was 32 seconds**,
because the cut search ran out of legal points and the fallback took everything
to the end. Nothing asked whether a beat was a length a camera could be asked
for.

> **An exhaustive check of the wrong property is not a check.** Structural
> asserts are cheap and all of them pass on nonsense.

**What landed.** A per-unit range assert, and a two-tier cut-candidate list
(prefer a lyric line, fall back to the bar grid) so the search cannot run dry.

## 30. A concurrency guard sat at the point of damage, not the point of entry

A backgrounded batch outlived its shell invisibly, so a second copy was started;
four ended up alive. Each **correctly** refused to submit while the render queue
was busy — and all four waited on each other behind one stuck job. GPU at 0 %,
no output, nothing in any log.

> **A guard that prevents corruption but permits deadlock is half a guard.**
> Correctness guards answer "is this action safe"; they cannot answer "should
> this process exist".

**What landed.** A PID lockfile at process entry, with **stale locks taken over
rather than obeyed** — a safety device survives `kill -9` only if it can tell a
dead owner from a live one.

## 31. A VRAM floor was copied between two stages with opposite profiles, and its wait was unbounded

3000 MB free is a sensible floor for a small resident model and is **below
normal operation** for one that fills the card and swaps its text encoder. The
batch stalled on its third item. The wait was `while free < floor: sleep`, so it
would have waited until morning having produced two clips.

> **A resource limit is a property of a stage, not of the machine — and a guard
> that can block forever fails silently and looks like slow progress.**

**What landed.** Per-stage floors, and every wait bounded, then proceeding with
a warning.

## 32. A rehearsal was cached and would have shipped as the film

The assembly chain was deliberately validated end-to-end *before* any clip
existed, using the documented placeholder path. That left a full set of cached
placeholder segments. Every later run would have reused them and delivered the
animatic: right length, right cuts, every check green.

> **Caching by existence alone is a trap the moment an earlier run was a
> rehearsal.** Invalidate against source mtime. A flag you must remember is not
> a safeguard — not remembering is the entire failure mode.

## 33. A fallible batch ran in index order, so running out of time cost the most important shots

Numeric order put the film's reveal and its two-hander last. Crashes ate the
budget. Stopped and restarted in importance order mid-run, which recovered the
reveal; the next one was lost to the following crash.

> **Order a fallible batch by importance, not by identifier.** When the clock
> runs out you keep what matters instead of what sorts first.

## 34. A degradation path skipped the good fallback for the poor one

A beat with no clip fell straight back to a held still. Correct for a shot that
never rendered; wrong for one that had rendered fine and was awaiting a
re-shoot, where the archived take was right there.

> **Degrade to the next-best real artifact, not to nothing.** A moving take with
> a known fault beats a frozen frame. Keep the ladder explicit.

---

## 35. A probe's isolation was documented, half-implemented, and reported as a failed render

`gen_still.py --plain` exists to settle an A/B without contaminating the film,
and its docstring is explicit: the probe renders "into its own `<NAME>_plain`
directory -- the discipline `--obj` already uses -- so a probe can never be
resolved as a film plate."

`OUT` appended the suffix. **The write prefix did not** -- that line honoured
`--obj` and had never been extended -- so the probe landed in the film's plate
directory while the poller watched an empty `<NAME>_plain` folder and printed
`NO OUTPUT after 20s -- check _comfy_startup.log`.

Two failures at once, and only the harmless one is visible. `plate()` resolves a
beat as `have[-1]`, the last file for that sid, so the probe silently becomes
the plate the film is shot from -- and the thing that tells you about it is a
message saying the render **failed**.

Found on the first `--plain` render anyone ever ran, in all three copies of the
file.

> **A guard that is described in a docstring and implemented in one of the two
> places it needs to be is not a guard.** When a mode gets its own output
> directory, everything that writes AND everything that reads must derive the
> path from one expression -- not two that agree today.

> **And an isolation bug can present as a failed render.** "No output" from a
> renderer that plainly ran is not a render fault; it is a path fault, and the
> output is somewhere. Look for the file before you look at the log.

---

## 36. A direction block named something the plate did not have, so the model drew it

Two beats of a music video were written from the film's TREATMENT, which
describes a crowd walking off toward the horizon. Neither of their plates has a
crowd in it -- both are an empty plain with one chair.

Handed an empty plain and told what "the last of the crowd" does, the model
invented a crowd. On the beat whose entire job was that **everything stops**, it
invented one and then walked it around: the stillest beat in the film came back
as the busiest thing on the clip sheet.

Nothing failed. Both clips were coherent, well exposed and beautifully lit, and
the whole-frame numbers were unremarkable -- an invented crowd at that scale is
a few percent of the picture.

> **A noun in a direction block that is absent from the plate is a request to
> draw it.** An i2v model is conditioned on a still and told what happens next;
> a thing named in the direction and missing from the frame is the one
> instruction it can only satisfy by drawing. Motion prompts are written against
> the PLATE, not against the treatment. The treatment is what the film is
> about; the plate is what the model can see.

> **And this is what `qc_clips.py` is for.** It cannot pass or fail anything and
> deliberately does not try -- it puts every clip's frames on one sheet beside
> the plate contact sheet, and what the eye is doing is diffing two sheets. A
> crowd that is in one and absent from the other is instant; the same fault is
> invisible in any per-clip metric.

---

## 37. The file whose job is to say the film is wrong was another film's

`verify.py` looks at the finished film where each device is supposed to fire and
measures the mix. A clone's copy still held the beat ids and device names of the
film the template was extracted from, and it went through the whole pipeline
untouched: `preflight.py` did not list it (`CONTENT` was script / shot / motion /
edit / make_music -- a verifier did not look like content), `smoke.py` imported
it clean because the stale table is read inside `main()` rather than at import,
`residue.py` saw beat ids that all exist in this film, and `contract.py` has no
opinion about it.

It surfaced by crashing on the first run after the first bake, on a transition
table this film deliberately leaves empty. **That is the lucky case.** In a tree
where every name happens to resolve -- which is the normal case, since every
film numbers its beats from "01" -- it would have measured the wrong moments
against the wrong expectations and reported a pass.

> **A verifier is content.** It names beats, devices and the moments they are
> expected to fire, and all of those belong to one particular film. The file
> whose whole job is to tell you the film is wrong is the last file that should
> be another film's.

Fixed by putting `EXAMPLE_CONTENT = True` in `_session_template/verify.py` and
adding it to `preflight.CONTENT`. Same fix, same reasoning and same paragraph as
`make_music.py`, which was added to that list for the same reason after a fork
shipped three cues written for another season.

---

## 38. The delivery spec was declared in season_identity and ignored by the file that delivers

`season_identity.py` states the season's loudness targets, its ceiling and its
sample rate, with a paragraph about why they live in one place. `assemble.py`
then opened with

    I_TARGET, TP_TARGET, LRA_TARGET = -16.0, -1.5, 11.0
    CEIL_DBFS = -2.0
    RATE = 48000

-- the same four numbers, typed again, three inches from a comment explaining
that `24` had been typed in eleven files beside a `season_identity.FPS` that
already said so.

Found by moving one: a music video wanted -14 LUFS instead of -16, the value was
changed in `season_identity.py`, the film was re-baked, and it came out at -16
with the build log printing the number it had ignored. Nothing failed. The only
reason it was caught is that the operator happened to read the line.

> **A value that is declared in one file and obeyed in another is not
> declared.** Deriving it is one line; the duplicate is silent for as long as
> nobody moves it, and the day somebody moves it is the day it lies.

The comments around those literals were about the METHOD -- two-pass loudnorm,
static gain, an explicit ceiling -- and they were all true and worth keeping.
That is what made the duplication easy to miss: the paragraph justified the
mechanism, not the number, so it read as a considered decision rather than as a
copy.

---

## The fault no prompt could fix, and how to tell

The lip-sync was not a prompting failure. The video model carries an **audio
head** — it generates a vocal performance and syncs any legible face to it.

Two fixes were tried, and **trying both is what produced the diagnosis**:

1. **Conserve by name**, the rule that reliably holds props and practical
   lights. The mouth kept moving.
2. **3x the sampling budget** — 20 steps instead of a 6-step turbo LoRA, on the
   theory that adherence was a step-count problem. Mouth kept moving, eyes still
   lit.

> **A prior that survives a direct instruction AND a much larger sampling budget
> is not being under-served, it is being obeyed.** Stop rewriting the prompt and
> change model.

**Split by shot type rather than switching wholesale.** Faces went to a
video-only model; landscape, machinery, distant figures and silhouettes stayed
on the faster one. A figure too small for a mouth to read needs neither the
clause nor the slower model. Two consequences to plan for: the video-only model
exposes a **real negative prompt**, so the fault can be named where naming
removes rather than summons; and the two disagree about legal frame counts
(17n+5 against 4n+1), so **a mixed-model cut is not uniformly re-processable by
either afterwards.**

## Four prompting findings, from re-rendering the shots that were wrong

- **A thing that must match across shots is a paste, not a paraphrase.** One
  shot described the film's vehicle in its own words instead of inserting the
  shared block, and got a visibly different vehicle — in the climax, four shots
  after the audience last saw the real one.
- **A simile becomes the subject.** "like a river of white metal" rendered a
  river; "green-bright glittering copper ore" rendered gemstone. The model does
  not distinguish what a thing IS from what it is COMPARED TO.
- **An instantaneous pose is invented badly.** "caught at the top of the swing"
  gave a distorted arm; the continuous action did not.
- **Camera movement must respect the frame, not just the object.** A sideways
  track through a symmetrical two-object composition put one alone in centre
  frame and threw the pairing away.

## Two findings about measurement that generalise past this film

- **Non-convergence tells you the alarm is measuring content, not defect.** An
  iterative saturation correction converged in one pass on three clips and
  **oscillated** on two — because those two were push-ins that genuinely brought
  more warm content into frame. Correcting them would have flattened a correct
  shot. Iterate even when one pass would do, and read non-convergence as a
  diagnosis.
- **Validate an alignment externally, never by its own confidence.** A forced
  aligner scores how well audio matched the text it was *told* to match, so its
  weakest lines were simply the most heavily produced part of the record. The
  real check was an independent transcriber that never saw the lyric sheet:
  where both named the same word they agreed to a **median 0.18 s**.

## Identity across 45 shots with no character LoRA

Two characters — the same man young and old — held by **three age-invariant
marks pasted verbatim into every prompt** (a bead on a named side of the beard,
a scar through a named eyebrow, a distinctive nose). Everything else was free to
age. Derivation was deliberately **not** used despite being available: a derived
plate inherits its parent's camera, and 45 shots inheriting one camera is one
shot 45 times. **Identity by text; framing free.**

## Confirmed again, a fifth time

- **An estimator's octave error is invisible until the edit is wrong.** Tempo
  detection returned the eighth-note pulse (172 BPM against a true 86). The tell
  was structural: at the wrong reading the song is 185 bars, which no
  four-minute rock song is. Pin it, and record the measurement that settles it.
- **Match the generation canvas to the delivery aspect** and nothing is squashed
  anywhere in the chain — fault 21, avoided by choosing 16:9 up front.
- **A latent budget can be a hang, not an error.** Past the ceiling the sampler
  stops progressing rather than failing, and takes the night with it.

## Still open

- ~~**None of faults 28–34 has been applied to this repo's own tooling.**~~
  **Applied.** 28 (`qc_clips.py` now samples a filmstrip across each clip
  instead of one late frame), 29 (`edit.BEAT_MIN`, a floor on the derived beat
  itself — `CLIP_MIN` is what a vendor sells, not what a cut can hold), 30
  (`solo.py`, wired into all nine generator entry points), 32
  (`--keep-frames` now refuses when any source clip is newer than the baked
  frames, because a count is not a recipe).
- **31, 33 and 34 were checked and have no instance here, and that is the
  finding.** All four wait loops were already bounded (`SLOW_S`, 1200, 3600,
  5400). Every output resolver either honours `subfolder` or never joins on
  `filename`. There is no "importance" concept for a batch to order by, and a
  missing clip *should* fail loudly in the template rather than substitute
  something. **Not inventing a fix for a fault a repo does not have** is the
  same discipline as not inventing a metric.
- **The two new guards are unexercised against a real season.** `BEAT_MIN`
  cannot fire without measured VO on disk, and the `--keep-frames` staleness
  check needs a baked film — `smoke.py` imports modules, it does not run bakes.
  Same caveat as faults 21–27 carried, and for the same reason.
- **The structural QC metric published a known failure.** Its localisation score
  ranks by *shot type* as much as by fault — it rated three confirmed faults
  below two confirmed-good clips, because in a close-up the whole frame is
  textured. It ships with that stated and with edge-growth doing the real work.
  A metric that separates local motion from local texture would replace it.
- **Nine of twenty face shots were re-shot only on the second attempt**, after
  an intermittent server abort ate the first budget. The supervisor pattern that
  fixed it is written into `docs/02_traps.md` and exists in no tool in this repo.
- **No cross-shot grade, still.** Two models now contribute shots to one film and
  nothing measures drift *between* them.

# The Late Bulletin — a seventh season, a talking format, and the prior that dresses its own set

## The season this came from

An SNL-style news-satire episode, 2026-08-19: a G-Man cold-open monologue
(the cold open's first VO lane), an InfiniteTalk anchor at 16:9, and three
sketches cut from that week's verified news. 350.5s delivered, all picture
local, one day from scaffold to publish. Seven faults surfaced; three were
machinery and are fixed in this repo, four were content lessons recorded
below and in `docs/05_prompting.md`.

## 39. The tube dial was declared in identity and obeyed nowhere

`show/identity.py` declares `TV` and its comment says `""` disables the tube
pass entirely. `show/assemble.py` carried its own `TV = "heavy"` literal and
never read the identity. A season that set `TV = ""` (a clean modern
broadcast, not a television) shipped all three desk segments through the
heavy tube, at the tube's cabinet geometry, and the only tell was a log line
saying `tube=heavy` on a season whose identity said otherwise.

Same class as fault 38, found six days later in the next file over: a spec
declared in one place and obeyed in another is not a spec. `assemble.py` now
reads `identity.TV`, and an empty dial skips the crt pass at the call site
— `crt.PRESETS` has no `""` entry and must not grow one, because a preset
named "nothing" that renders something is this fault wearing a disguise.

## 40. The show bake's cover scale never cropped, and 4:3 hid it for five seasons

`dims()` scales a source UP until it covers both delivery floors and hands
the result straight to the encoder. On every 4:3 season the numbers happen
to land exact (768x576 -> 1440x1080). On a 16:9 season, InfiniteTalk's
near-16:9 canvas came back **1920x1082**, and `feature.py` — correctly —
refuses a part two rows taller than the films it joins.

`_bake_one` now centre-crops the overshoot to the season's exact geometry,
and `bake()` reports what was written rather than what was scaled: a log
that says 1082 about a directory full of 1080s is a count of what was asked
for, which is fault 12's lesson wearing new clothes.

## 41. The base clip was welded to the segment, and a talkative desk cannot shoot itself

The show's H3 base clip was sized to the full segment. A desk that talks
22-27s a segment needs a 600-670 frame hold — over the 2.80M latent budget
at every canvas the aspect offers, and past the budget H3 thrashes rather
than fails. The reference reel's segments were half that length, so the
weld never showed.

What broke the weld was reading what the sync actually consumes: `italk.py`
takes FRAME ZERO of the clean bake as its anchor and regenerates the entire
segment from the voice at `edit.FRAMES` length; every base frame after zero
is discarded. The base clip's job is to exist and to make the driver audio
the right length. So `edit.BASE_CAP_F` caps the base shoot at 294f (the
longest clip proven on the measured card), `h3_shoot.py` shoots the cap,
and the clean pass pads to segment length by repeating the last frame. On a
reel whose segments fit, `BASE_FRAMES == FRAMES` and nothing changes.

## The prior dresses its own set — three findings, one rule

All three are in `docs/05_prompting.md` now; the incidents:

- **"Seen from behind over his shoulder" summoned a second G-Man, twice.**
  An over-the-shoulder framing implies somebody to look at, and the LoRA
  populated the implication — at two seeds, which is the prompt-fault
  signal. "He stands alone with his back to the camera... the only figure
  anywhere in the studio" fixed it at the same seed.
- **"One rack in a dark aisle" was a wall of lit racks, twice.** A
  datacenter aisle is a genre prior that fills itself with rows. The orphan
  needed geometry, not adjectives: "a single free-standing rack alone in a
  wide bare concrete hall."
- **An empty deposition room staffed itself.** The interview sketch's rack
  beats first grew a clerk's arm arranging a folder (fixed by a positive
  occupancy clause — the same rule as an unoccupied face), and then, with
  the humans banned, H3 *materialised the props instead*: folder, glass and
  a wire tray fading in mid-clip, because the plate's table was bare and
  the deposition prior insists on a dressed one. The root fix was in the
  PLATE: give the first frame the props the prior demands, and the motion
  clause pins them. **Give the prior what it insists on in frame zero, or
  it will fetch it during the clip** — the conservation family's fourth
  member, beside negation, allocation and identity-scale.

## What was confirmed, a fifth time

- The clip-folder stamp (`claim_clips`) refused a reused NAME on day one —
  `OPEN_clips` belonged to another season — which is the guard doing
  exactly what its docstring promises.
- The InfiniteTalk chain end to end on a NEW host at a NEW aspect:
  `which_source` proved all three segments baked from the synced render,
  `sync_probe` worst lag +0.9ms. The two proofs exist because six
  interstitials once shipped from the wrong picture; they took seconds.
- `BEAT_MIN` and the vendor-cap exit both fired during editing (a 12.8s
  take against `CLIP_MAX = 12`) and were answered with words, not machinery.
- The `--plain` A/B's own measurement was adopted as production: this
  season shot the plain graph into the film plate directories (`--filtered`
  is the probe now, in this season's copies), and the props the prompts
  named arrived as asked.

## Still open

- ~~**The season's gen_still probe inversion is not in the template.**~~
  **Applied, 2026-08-20, on the user's go-ahead.** All three gen_still
  copies now ship the plain graph as production and `--filtered` as the
  probe (its own `<NAME>_filtered` directory, same isolation discipline).
  The docstring's own condition was met before the move: two production
  seasons ran plain on their own prompts, one with a character LoRA loaded.
- ~~**`show/tvtest.py` names segment 05.**~~ **Applied, 2026-08-20.** The
  default sample is now first/middle/last of `shot.CUT`, derived — a reel
  of any length gets a spread of what it actually has.
- **The anchor segment 02 mix works its clipper for 1.6 dB on one
  transient.** In spec (-16.0 / -1.9 dBTP) and shipped; the fix, if the ear
  wants one, is at the take — content in the delivered season, not
  machinery, so it stays here rather than in a tool.


# Vertical Hold -- an eighth season, and the tube becomes the season

`E:\Claude\Projects\VERTICAL HOLD` -- 7:37, nine parts, 16:9. A television
very late at night, counting down past zero: a wordless cold open surfs
channels 9-4, a lip-synced infomercial host sells sleep, dreams and
memories between four films that ARE channels (80s fantasy, vaporwave
exercise, a 1953 parlor drama, the viewer's own living room), and the
finale finishes the countdown through derived below-zero rooms to the
white dot. First season to put the crt pass on EVERY part, first with a
per-part dial, first with a drawn OSD lane, first silent cold open, first
to use the derive registry pattern in anger (two rungs: h3ref prop-swap,
qwen door-removal), and the largest (N=4, escalating 76/70/86/130s).

## Faults 42-44

**42. `show/board_rect.py` assumes the reference reel's surface.** It
hunts dark teal felt; this season's board is a glossy white card on black
void, and the detector returned nothing for two segments and the HOST'S
SHIRT for one -- a rect that passes every shape assert and would have put
the price on the man. What landed: a season-local density measurement
(only pixels whose 31x31 neighborhood is >90% bright count -- glints are
thin, a card is a slab), rects drawn back onto the plates and looked at.
Still open for the template: the detector wants the season to DECLARE its
surface (a colour band, a brightness class) instead of inheriting the
felt.

**43. `show/audition.py` derives its "peak" line as `max(style)` and a
uniform script hands it the first line.** Every line at 0.50 made
intro==peak and the audition's own duplicate-line assert refused the
import -- the guard did its job, before money, but the derivation invites
the tie. What landed: the season gave its true crescendo line the top
style, which is what the field means anyway. A tie-break that prefers any
line over lines[0] would remove the trap.

**44. `h3_shoot.py <sid> --seed=N` silently SKIPs a beat whose take is on
disk.** The flag reads as "re-roll with this seed"; the tool prints SKIP
and does nothing, and the re-roll only happens after a manual
`*__rej_<reason>` rename. Correct behavior by the never-delete rule -- but
the message should say "rename the take to _rej_ first", not just SKIP,
because a seed that was asked for and not used is how a re-roll gets
reported that never ran.

## Rules that generalise (instances of standing rules, confirmed hard)

- **A light with a verb rises.** "The striped sun... glowing with a very
  slow, even pulse" -- written as a HOLD -- raised the sun in all three
  shots that contained it, identically. docs/05's rule ("a light is never
  the subject of a verb") covers even gerunds attached to a pinned object.
  Shipped anyway, deliberately: identical wrongness in every shot reads as
  the program's own rule, which is this season's premise. That defense is
  not transferable to a season about a place that behaves.
- **When the clip contradicts a line and the prior caused it, move the
  words.** The parlor teapot poured -- no seed un-pours a pot already
  tilted over a cup in frame zero -- and the line became "There is always
  more tea. That is one of the terms", which is better than the joke it
  replaced. Changing words is free; arguing with a physics prior is not.
- **Frame zero is the law, and sometimes it is the better director.** The
  finale's plates seated the salesman in the viewer's own couch depression
  against the motion's "he stands"; the staging ships because occupying
  the collected seat IS the thesis. Judge the plate's disobedience on what
  it means, not on whether it obeyed.
- **The glass is identity; only the wear escalates.** A tube season that
  drops the cabinet for one part reads as leaving the television. "signed"
  (no bezel, no curve) was right for a season where the tube was one
  show's dressing and wrong here; the season added a "worn" preset (tube's
  glass, lightest wear, the roll kept) to both crt.py copies. If per-part
  dials become template machinery, the cabinet belongs to the season and
  the wear to the part.

## What worked without argument

- The season-root channel layer (crt.py copy + new osd.py) went into five
  assemblers with three byte-identical anchored patches; the OSD drawn
  BEFORE the tube rides the same glass as the picture, and the tube's
  roll doubles as the channel detent (per-film at frame 0, per-beat in
  the cold open).
- The bleed as a second music cue: channel 3's own VO take, band-passed,
  under channel 2's held beat -- the ducked bus released it into her
  silence with no new machinery at all.
- The derive pattern carried from BALLAST held: ref key spelled
  `ref_images.ref_image_0`, frame 0 of the R2V sample kept via settle(),
  h3ref under-removes (right for the prop swap), qwen over-removes (it
  took the door AND the night; kept -- the over-removal escalated the
  ladder in the right direction).
- InfiniteTalk through a clear space helmet: all four segments SYNCED per
  which_source, worst sync_probe lag +0.8ms. The helmet was never a
  variable; the mouth is visible and that is all the sync needs.

## Still open

- **The channel layer is season-local.** If a second season wants a tube
  on its films, the layer (identity.TV defaulting to "", the osd lane,
  the three assemble patches) belongs in `_session_template` -- an empty
  TV is exactly every prior season, so the default costs nothing.
- **`board_rect.py` wants a surface declaration** (fault 42).
- **The audition peak tie-break** (fault 43).

# The eighth season's polish pass (2026-08-20, faults 45-46)

The user's notes after delivery: recast the host's face younger against a
reference, drain THE HOLD from technicolor to mono over its runtime, give
the parlor two-person lip sync, and remove a tube the helmet had grown.
Everything below was learned applying them.

## Fault 45 -- a V3 dynamic combo's option inputs are dotted paths

`WanInfiniteTalkToVideo.mode` is a `COMFY_DYNAMICCOMBO_V3`: the
"two_speakers" option carries `audio_encoder_output_2`, `mask_1` and
`mask_2` as ITS OWN inputs, and in an API prompt they must be spelled
`mode.audio_encoder_output_2`, `mode.mask_1`, `mode.mask_2`
(comfy_api/latest/_io.py `parse_class_inputs` finalizes option inputs as
`<combo_id>.<input_id>`). Spelled flat, the graph is ACCEPTED and the
three inputs are silently dropped -- the first two-speaker render steered
both faces from channel 1 alone, and the beat whose channel 1 was a
silence track moved nobody. Nothing errored anywhere.

Two rules out of it:

- **Acceptance is not consumption.** `--check` proves the names exist on
  the node; only a judged take proves they were wired. Judge channel 2's
  mouth specifically, at frames inside ITS OWN line window.
- **The dotted path is a contract family, not a one-off** -- it is the
  same shape as the derive graphs' `ref_images.ref_image_0`. When a
  node's input lives under a parent in `/object_info`, its prompt key
  lives under the parent too.

What landed: `show/italk_multi.py` rewritten against the read-off-the-node
contract (guessed ASSUME table deleted); proven by eye on VERTICAL HOLD
S3 -- both mouths track their own lines, a silent-presence speaker holds
closed on a full-length silence track. The word UNPROVEN came off the
port's header the way its own instructions demanded.

## Fault 46 -- an idempotent skip outlives its inputs

`show/italk.py` skipped every segment with a `synced_XX.mp4` on disk.
After the recast replaced every plate and every take upstream, it said
"have it, skipping" four times, and the stale v1 faces would have shipped
if a face-check had not caught them. Same class as fault 44 (h3_shoot's
--seed skip): a requested re-render silently not running -- one layer up.

What landed: the skip now compares mtimes against `clean_XX.mp4` (the
anchor source) and re-renders when the picture changed under it. The
general rule: **an idempotency skip must name the input it is idempotent
OVER, and check its freshness** -- "the output exists" is not that check.

## Priors that would not roll away (instances of the restage rule)

- **A brass-collared bubble helmet seen in profile grows a diving hose.**
  Three seeds, three hoses, plate clause and motion clause both present.
  What worked was denying the angle: restage so the character never turns
  his back or profile to the camera. A prompt cannot out-argue the prior;
  blocking can.
- **Tilted glass under a light source grows a hard glint that
  crystallizes** (a translucent patch on the forehead, an opaque square
  on an eye -- three seeds). What worked: a dedicated plate that removes
  the head-tilt action entirely (the remote already in hand; the beat is
  only the aim). When two takes fail the same way, change the SHOT, not
  the seed -- confirmed twice more.
- **The LoRA's second-copy failure arrives through H3 too**: a duplicate
  of the character coalesced under the desk mid-clip in an anchor-donor
  take. Harmless when InfiniteTalk regenerates the picture (it consumes
  only frame zero), but it means an anchor frame must be chosen EARLY,
  before the dark space populates.

## What worked without argument

- **A grade that needs to know where it is, is a device**: THE HOLD's
  technicolor-to-mono drain is a film-local `graded_at(im, i, total)` in
  its own assemble (smoothstep to full mono at 75%), taking the
  one-grade-per-frame slot; grades.py stays stateless, exactly as its
  header demands. A/B the saturated end on a real plate -- 1.45 read as
  rich gothic, 2.1 rouged the faces, 1.8 shipped.
- **The face is stated once or it drifts**: the LoRA trigger alone did
  not hold the host's face across photoreal plates (gaunt bureaucrat in
  one tree, a different fifty-ish man in another -- the "one long night"
  read had papered it over). A season-level GMAN_FACE block appended
  after the trigger in every prompt that stages him pinned the identity
  in six plates, six clips and four sync chains on the first try.

## Addendum: the infomercial rebuild (same day, faults 47-48 + one pattern)

- **Fault 47 -- ReActor''s bundled face-restore loader is broken on this
  install**: `face_restore_model="GPEN-BFR-512.pth"` dies inside
  r_chainner''s `load_state_dict` (unbound `model`). The working chain is
  ReActorFaceSwap with restore `"none"` piped into the separate
  "GPENO Face Restoration" node (512 preset -- the 1024 model is not on
  disk and the node FileNotFounds rather than falling back).
- **Fault 48 -- an estimator is not a progress bar**: a sync render sat at
  "~1 second remaining" for the better part of an hour with VRAM pinned
  at 23.6/24.5 GB -- paging, not progress (43C; heat was never the
  story). The kill-bounce-requeue cost 8 minutes against the crawl''s 60+.
  When VRAM is pinned and chunk times triple, restart the server; verify
  the drop with nvidia-smi, never /free.
- **The pattern that paid twice: a face swap on frame zero survives
  whole-shot regeneration.** InsightFace-swapping the PLATE is enough --
  H3 sustains the swapped face, and InfiniteTalk holds it through
  11-chunk, 30-second chains (checked at 27s on four segments). Swap
  once at the source; never chase faces downstream. Corollary: the
  prompt must carry what the swap cannot -- hairline and build are the
  render''s job, the oval is the swap''s.

## Addendum: the pre-swap face leak (same day, fault 49)

- **Fault 49 -- a clip outlives the plate it was shot from**: the face
  swap re-made the plates and retired the old ones with reasons, but the
  ACCEPTED CLIPS shot from the old plates stayed the highest non-reject
  takes, and three beats of a delivered feature carried the pre-swap
  face. The operator caught it in a screenshot; the mtimes had recorded
  it all along (clips 8:59-9:53 AM, plates swapped 12:01 PM). The italk
  freshness check (fault 46) could not see it -- it compares synced
  against clean, one stage downstream of where this one broke. Fix:
  h3_shoot's SKIP now flags a take older than its plate ("STALE: its
  plate is NEWER than this take") in all three repo copies. It warns
  rather than re-rolling because a clip is a reviewed lottery take, not
  a deterministic derivation -- retiring one needs a reason string,
  which needs a human or an agent, not a skip path. The general rule:
  every re-made artifact staleness-dates EVERYTHING downstream of it,
  and each generator's skip must check one link -- its own input --
  or the chain has a blind stage.

# The ninth season: LOSS OF SIGNAL (2026-08-21)

A 10:11 solo space film on a "sanity dial" (two style LoRAs as one
continuum, driven by signal delay), the first season scored LOCALLY
(ACE-Step), the first shot end to end on the ref2va hybrid with the real VO
anchored, and ten viewing rounds of operator notes in one day. What follows
is what those rounds cost. The season-level modules that came out of it --
`upscale.py`, `score.py`, the rewritten `_session_template/h3_shoot.py`,
`show/h3_chain.py`, the dip in `feature.py`, the continuation pattern in
`edit.py` -- are in this commit; the film's own devices (a delay-counter
OSD, shared motion blocks, a radio lane, a composite "crawl" register) stay
with the film and are cited here by path.

## Fault 50 -- the LoRA scheduler honours only its start value

SCG's `LoRAScheduler` was meant to drive the style LoRA from 0 to 1.3
across the sampler, a "crawl" between the two ends of the dial. Measured
across a ladder of start/end pairs: the output tracked the START value and
nothing else, on this sampler (er_sde / beta57). The end value was
decoration.

What landed: the CRAWL register became a COMPOSITE -- the SANE plate and
its GONE twin (same seed, same latent) through a mask, in the film's
`crawl.py`. Same seed + same latent holds composition across a style swap
(confirmed on 60+ renders), which is what makes a composite of the two
honest. Rule: **a scheduler is a claim; measure the output at two settings
that should differ before building on it.**

## Fault 51 -- a voice reference alongside an anchored driver kills the sampler

ref2va takes `<Audio 1>` as a voice reference. Wired TOGETHER with a driver
track anchored through `MiniMaxH3AddGuide`, the sampler died on an
audio-row mismatch (1160 vs 2254, `model.py:605`). Either alone is fine.

What landed: no voice reference is ever wired -- the driver IS his voice
wherever he speaks. `season_identity.H3_VOICE_REF` is recorded and unused,
with the fault number on it, so the next session does not "fix" the
omission.

## Fault 52 -- no driver is not silence; it is an invitation

A beat where only the RADIO speaks (S1 04) was shot with no audio
anchored. H3 invented a voice and mouthed the radio's line back at it.
The beat whose driver was digital silence until his one word (S1 06) kept
his mouth shut to the second. Confirms `docs/04_lipsync.md` "H3 invents
dialogue" from the other side: the fix is not "no audio", it is ANCHORED
SILENCE.

What landed: `h3_shoot.driver()` always writes a driver -- the on-screen
roles' lines at their edit offsets, `anullsrc` everywhere else, for every
beat including the ones where nobody on screen speaks. `ON_SCREEN` names
the roles that belong in it (`script.ON_SCREEN`, else every role).

## Fault 53 -- identity references on a plate where he is a picture

With the two identity plates wired, a beat where he appears only as a
PRINTED POSTER (S3 06, a parade) animated the poster's face and then cut
to the hero reference as a new scene -- "shot two". The references say
"this man, alive"; a painted board wants neither.

What landed: a `norefs` flag on the beat (beside `nochar`), honoured by
the shooter. Rule: **references are for the character alive in frame;
when the plate is itself a depiction of him, wire none.**

## Fault 54 -- the continuation anchored the frames past the cut

An NNx continuation beat opens on the parent's last `H3_TAIL_FRAMES`
frames so the handoff carries velocity. The first version took the
parent CLIP's last frames -- which are ~2 s past the edit's cut -- and the
continuation replayed them after it: a visible repeat at every seam. A
second, smaller fault in the same table: `("01x")` is a string, not a
tuple, and the membership test passed silently until an assert on the
in-point caught it.

What landed: `tail_clip()` takes the frames ENDING AT THE CUT (`ss + beat
+ trans`); `edit.RUNUP = H3_TAIL_FRAMES/FPS - SS_MAX` for every NNx beat
so the in-point lands on the first NEW frame, and `table()` asserts
`ss == _TAIL` for those beats. One link, never a chain, in a faced film;
`show/h3_chain.py` chains freely because its room has no faces.

## Fault 55 -- "imperceptible" renders as a still

Direction written as "the clouds turn imperceptibly", "a degree at most",
"barely visible" produced clips with no motion at all -- four visions in a
row rendered as stills (the operator: "V1 doesn't move or animate at
all"). The model took the hedge literally. The fix was QUANTITIES: "by the
width of the largest crater", "an eighth of a full turn", "a third of the
frame's width". Sibling findings from the same day: "extreme close-up"
PULLS THE FRAME IN over the clip (the plate's framing is lost); "rings"
summons Saturn; moving hands mutate (keep hands flat and still unless the
beat is about the hands); a surface the direction does not allocate (the
back of a photograph turned over) gets invented, transparent.

## Fault 56 -- the porthole prior, twice

Any Earth in a porthole GROWS under H3 -- a coin-sized Earth in the plate
was a full window by 5 s and two Earths by 10 s, the cabin drifting with
it (v9). Re-plated to stars and the motion block `STARS_GLASS` ("one
faintly blue star"): held. Then on a 12 s hold the blue star itself became
the Earth (S3 05) -- and the beat's motion block was `EARTH_GLASS`, which
NAMES the Earth. Two faults, one rule, the negation rule's positive twin:
**what the direction names, the model paints; what the prior wants, the
direction cannot hold back -- so name only what must be there, and for a
window that must stay empty, "stars, and only stars."** The film's
`move.STARS_ONLY` is that block.

## Fault 57 -- the thesis typeset its own nouns

A block of direction about the film's "PROCEDURE" rendered the word
PROCEDURE on the panel. Printable nouns in a prompt are candidates for
lettering, and the style LoRA's trigger leaked as literal text ~5/26
frames at the deep registers. Corner-check every plate at those
registers; keep the thesis out of the prompt and in the treatment.

## Fault 58 -- the Lanczos stretch was the whole upscale

H3 renders at 864x480; delivery is 1920x1080; every season stretched the
frames 2.2x with Lanczos at bake and that was the picture. A one-frame
A/B against RealESRGAN -> delivery was not close (edges, the helmet ring,
the dial type). Two measurements decided the model: x4plus is 0.67 s/frame
at 1024x576 because it paints 4096x2304 and we keep a quarter; x2plus is
0.13 s/frame for the same delivered pixels. ~40 min a film.

What landed: `upscale.py` -- each clip once into `<clips>/_up/` keyed on
mtime, x264 crf 10 4:4:4, in the ComfyUI venv over ffmpeg pipes; every
assembler's explode reads the twin; `season_identity.UPSCALE` names the
model (None = the stretch); a named model that is not on disk FAILS rather
than falling back. Rule: **pick an upscaler by delivered scale, not by the
biggest number on the shelf.**

## Fault 59 -- chained fades black the whole film

`fade=t=in:st=X` holds every frame BEFORE X black and `t=out` every frame
AFTER. A chain of both at every part boundary on the already-joined stream
produced ten minutes of black at 1.7 MB, and nothing errored (a frame
check caught it before delivery). `afade` has the same semantics.

What landed: `feature.py` dips per PART -- each part re-encoded once with
its own two fades (cached by mtime in `_work/dip_NN_*.mp4`), the concat
copies those, the audio fades ride each mix input inside the concat
filter. Durations untouched. Measured at the first join: luma 139 -> 0 ->
77, RMS -27 -> -75 -> -33. `JOIN_DIP = 0` restores the splice. In
`docs/02_traps.md` under ffmpeg.

## Fault 60 -- a resident model family thrashes the next H3 pass

Twice in one day: a Krea2 plate re-roll, then an ACE-Step cue, left their
weights resident; the next H3 pass sat at sampler 0/6 with VRAM pinned at
~23.7 GB and "0 models unloaded" in the log. Not a hang anyone can see
from the queue -- the job is "running". Different from the canvas-budget
thrash of fault 41 (that one is too many tokens; this one is too many
families).

What landed: the rule, by hand -- **restart ComfyUI before an H3 pass
whenever another model family has been loaded since**, and verify the drop
with nvidia-smi. Not yet automated in `season.py`; that is the open item.

## What else landed without a number

- **ACE-Step 1.5 XL as the score** (`score.py`): turbo graph, 8 steps,
  cfg 1; `TextEncodeAceStepAudio1.5` pins bpm / key / time signature, so
  independently generated cues are one score by KEY FAMILY. It fades ~8 s
  before the requested end -- `PAD = 15` and measure where the music
  stops. LRA varies by seed (17.5 -> 9.3 on a re-roll). A `{"silent":
  True}` cue writes `anullsrc` of the right length: the mixer needs a file
  for every span, and a span under nothing is a choice, not a gap.
- **The delay PLAYED, not stated** (the operator: "the signal delay is
  never felt, just stated"): the gap inside a two-voice beat is the round
  trip -- `extra` = 2x the counter -- and the motion for that gap is THE
  WAIT, written as a beat of its own.
- **Silent beats** (`script.SILENT` + `edit.SILENT_SECS`) and a silent
  cue: a wordless set piece needs no lines to exist in the tables.
- `contract.py` wanted `PROMPTS` where the tree had `CUES` -- the contract
  should name what it actually reads; aliased for now.
- The show's chained pieces: a concat of pieces at different canvases
  produced a size-mismatch join; one canvas per chain. A 0-byte join file
  counted as a take until a size check.
- The corner crop (2 %, for the style's painter's signature) was not
  applied under transitions or to a card's neighbour frames -- the
  signature came back for one second at every device. Crop at every site
  that loads a frame, which is the same choke-point argument as
  `fit_aspect`.

## Fault 61 -- an attention node accepted and inert on H3 (fault 45, again)

`comfyui_SLA-sage`'s `SLAAttention` node wires between the LoRA loader and
the guider, the graph is accepted, the log says "SLA Attention applied",
and the render is BIT-IDENTICAL to the same graph without it (PSNR inf,
same seed, 362 frames). It patches `set_model_attn1_patch` -- the SD/DiT
transformer-patch hook -- and H3 routes its attention through
`optimized_attention_override`, which the node never touches. Nothing
errored anywhere.

The probe that caught it (LOSS OF SIGNAL `_probes/attn_probe.py`) shot one
faced beat four ways on the same seed: the film's stack; lightx2v's 4-step
SLA turbo LoRA alone; the LoRA plus the node; `ComfyUI-sol-attn`'s H3
patch. Two controls made the numbers mean something: **the base shot twice
is PSNR inf** (the sampler is deterministic, so any difference is the
variant's), and **time per frame is read warm**, after the first run has
paid the model load. What the probe found on a 4090 (SM89):

- the SLA kernel node: inert (above);
- Sol-Attn: runs (PSNR 23.9 against base), 1.9 vs 2.0 min -- within noise
  on SM89, which its README says is unbenchmarked;
- the 4-step SLA LoRA as a plain turbo LoRA under Sage, on the ref2va
  hybrid: 0.25 vs 0.33 s/frame, the anchor, the face and the mouth held at
  filmstrip scale. A real saving from fewer steps, and a different
  distillation -- a next-season default candidate, not a mid-film switch.

Rules, both already in the book and both confirmed hard: **acceptance is
not consumption -- a speed claim is proved by a warm clock and a PSNR
against the graph without the node**; and **a probe needs a control that
shows zero** before its other numbers are read.

## Fault 62 -- two streams, two numbers, one lost frame

The first end-credit roll wrote its audio from a float (`secs`) and its
picture from `round(secs * fps)` frames. Those disagree by up to half a
frame; `-shortest` then trimmed the video to the shorter one, and
`feature.py`'s mix-vs-picture check refused the part: "mix is 42.3600s
against 42.3333s of picture". Nothing was damaged, because the check exists
-- but the shape is worth the number: **a part's picture and its mix must be
derived from ONE quantity, and that quantity is a whole number of frames.**
Everything that owns a length in this repo already does it that way; a new
part-maker is where it gets forgotten.

What landed: `credits.py` computes `n` frames first and takes `secs = n /
FPS` for the mix. `docs/06_verification.md` gained the rule, next to the
reminder that the answer to a tolerance failure is never a looser tolerance.

## Fault 63 -- a typed tempo H3 did not keep, and a direction with too much in it

The tenth season (MADE WITH, the H3 sync-sound contest entry: every sound
must come out of the same H3 pass as the picture) probed sync before
spending. Beat 05 asked for five rubber-stamp landings at exactly 1.2 s.
Two takes, two seeds: the picture stamped **twice** and handled paper in
between, and the onsets in the returned audio (0.35, 1.52, 3.04, 4.02,
5.89 s in take 1) were the sound of whatever the picture was doing -- the
two real landings carried a thud within ~80 ms, the rest were paper. So the
sync engine is real and the count is not: H3 keeps a pulse of its own and
honours a small number of big events. The tempo beats were rewritten to
three events spaced two seconds apart, and the film's sync proofs are the
single-event beats.

Two more things from the same probe. (1) The direction header typed 6.6 s
for a clip h3_shoot shot at 8.0 s -- it shoots edit's `buy` length, then
grid-rounds up -- so 1.4 s went unallocated at the tail of every beat.
`motion.SESSION_SECS` now derives from `edit.table()` through the same
grid, and every "holds to the last frame" line runs to it. (2) Beat 09
asked for a stamp to land on a television screen over a speaking mouth,
pull back, leave a seal, with the lips moving under it and the voice
muffled. Take 1: the hand waved the stamp across the screen and set it on
the desk -- synced to the frame, and the wrong action. Rewritten as one
action ("press at 2.0 s and stay there") it pressed and stayed. Also
measured, for the record: H3's native English from a plate of a man at a
lectern transcribes at Whisper no-speech 0.4-0.5 on the long policy line
and 0.08 on a short one -- usable for a bureaucrat, not for a line that
must be heard; and the generated room tone sat at -53 to -56 dB, near-mono
(L/R correlation 0.99), across three beats and five takes, which is the
first evidence that thirteen independently generated beds may cut
together. Rules in `docs/05_prompting.md`, "The other motion rules".

## Fault 64 -- the shooter anchored silence over the film's only sound

The tenth season's first assembly on the diegetic bus came out 76 s long,
-16.1 LUFS, thirteen clip tracks placed -- and ten of them were digital
silence (-90 dB). Only the three probe takes, shot before the season was
ported forward, carried sound. The ported shooter always writes a driver
and anchors it (fault 52: anchored silence is how a face keeps its mouth
shut; absent audio invites an invented voice), so every beat with no
on-screen line was shot against a silent driver, and H3 obliged: a clean
audio stream of nothing. Nothing failed. The bake, the loudness stage and
the length check all passed, because a silent track is a valid track.

Caught only because the verifier measured the delivered file -- onsets per
beat and bed level 300 ms either side of every cut -- and ten beats read
-90 dB against three at -50. `season_identity.H3_DRIVER` now says which
kind of film this is: True (the default, and every narrated season) anchors
a driver; False hands the audio channel to the model. Ten beats re-shot.

Two rules from it. **A port carries the last film's assumptions, and the
safest of them are the ones that never fail.** And **a measurement that
reports a level is worth ten that report a pass** -- `assemble.py` printed
"13 clip track(s)" and was telling the truth.

## The diegetic bus: the third thing H3 decodes, finally placed

`mixes.py` gained `diegetic` and `assemble.mix()` gained a third placed
source -- each beat's own clip audio, at the picture's in-point, length and
start -- carried as `ctx["clips"]` so the bus signature did not move and
the three existing buses did not change. Built for the tenth season (the
H3 sync-sound contest entry, where no other sound is allowed) and
documented in `docs/03_audio.md`. Two details that were nearly wrong:
the upscaled twin `explode()` reads from has no audio stream, so the audio
input is the original clip; and an `-i` with no audio makes `[n:a]` an
error a hundred lines into the graph, so `has_audio()` asks first.

## Credits name people, so they are example content with a lock

`credits.py` is the only file in this repo that names PEOPLE -- the author,
the cast, and whoever trained each LoRA the film's look IS. Every other
example ships a wrong cue or a wrong beat and costs a re-render. This one
credits a stranger for someone else's work, or silently drops the person
whose weights the film is made of.

So it ships with `EXAMPLE_CONTENT = True`, `preflight.py` now scans the
SEASON ROOT as well as the folders (`ROOT_CONTENT`), and main() refuses on
its own too -- twice. The second refusal reads the ROLL rather than the
marker: every replaceable string in the template says "EXAMPLE" out loud, and
`example_lines()` refuses while any of them survive. That is the lock that
holds against impatience -- deleting the marker to see the roll move is one
keystroke, and it leaves a half-filled list (author replaced, LoRA creators
still EXAMPLE) that only the roll itself can catch. **A placeholder that could
pass for a credit is worse than no placeholder**: "EXAMPLE CREATOR" is a
mistake anybody spots in a single frame; "<creator>" or a plausible name is
one nobody spots at all. And one fact that made the lock necessary: **a LoRA's
.safetensors carries no author field.** Checked across three of them -- the
`ss_*` and `modelspec.*` keys hold the base model, the trigger and the
training run, never a name. Attribution is research, from the page the file
was downloaded from; it is not something a session can recall or infer.

## Subtitles come from the edit, never from a transcript

`subs.py` builds a sidecar .srt from the same tables that placed the audio:
the text is the line the voice was GIVEN (with the delivery tags -- "[cheerful]"
-- stripped, since those are direction, not words), and the time is the
offset the mixer USED. A transcript drifts and mangles exactly the material
this pipeline is fondest of: band-limited radio, voices in a character's
head, anything under a bed. Two details that made it work across trees:

- One WORKER SUBPROCESS PER TREE (the `contact.py` shape) -- every tree has
  its own `identity`, `script` and `edit`, and two of them in one interpreter
  gets you whichever landed on `sys.path` first. Three trees turned out to
  have three different offset APIs.
- WHO GETS A LABEL is `script.ON_SCREEN`, the same table the lip-sync driver
  reads. A voice the audience cannot see is labelled; a character they can
  see is not. Deriving it from the driver's table means the subtitles and the
  mouths cannot disagree about who is visible.

# The reel: ADOPT A DATACENTER at 9:16 (2026-08-23, faults 65-67)

`E:\Claude\Projects\ADOPT A DATACENTER` -- THE LATE BULLETIN's S3 reshot as a
standalone 1080x1920 Reel. One film, no cold open, no show, no credits;
95.3s against the 16:9 film's 84.8s; two beats added (the orphan asking
itself questions; a share line, because on a Reel the ask is a share); the
hook moved from the aerial to one amber LED, because an aerial in portrait
is sky. Twelve H3 clips at 576x1024, $0.28 of music and two VO lines bought;
everything else local or reused.

## A second delivery of the same film is a second SEASON

The geometry (`season.W, H`) is season-wide, so a vertical cut of one film
cannot live inside the 16:9 season that made it. `new_season.py --sessions 1`,
delete `cold_open/` and `show/`, port the four content files. What ports
verbatim: the VO takes (same role, same voice, same text -- the mp3s were
copied with their LINE IDS kept, and `script.REUSED` asserts the ids exist,
because `make_vo.py` will not re-render an existing file and an edited line
over an old take is otherwise silent). What does not port: the prompts. Every
one was rewritten around the tall frame rather than cropped, and the subject
turned out to be a gift to it -- a rack is tall, an aisle is deep, a pylon is
tall. `NAME` had to change (`ADOPTREEL`): `claim_clips()` refuses the other
season's `ADOPT_clips`, which is exactly what it is for.

## Fault 65 -- every non-diegetic bus broke the day the diegetic one landed

`assemble.mix()` now places `[cN]` -- each beat's own clip audio -- on every
bus, and the comment said "every bus that predates it ignores it". The buses
did. **ffmpeg does not: a labelled filter output nothing consumes is an
error**, and the first `ducked` mix after the change died eight minutes into
a bake with the whole graph printed as the traceback. The diegetic work was
tested on the one film that uses the diegetic bus, so the other four never
ran. Fix in `mixes.bus()`, once: any clip label the bus left out of its graph
gets `anullsink`. Alongside it, the `--graph` demo's "clips only" case crashed
every non-diegetic bus in `sum_to([])`; a bus handed nothing but clip sound
is a silent film, and it is now refused by name with the fix in the sentence.

## Fault 66 -- a push-in on a still life dissolves the objects into each other

Beat 08 (the adoption kit on the hall table) was directed as a slow push,
as it was in the 16:9 film, where it held. At 9:16 the same direction
crossfaded the certificate card into translucency with a face from a frame
behind it coming through. **Camera travel is licence to redraw; on a still
life nothing may move but the light.** Locked frame, objects named as solid
and opaque and in the same place in the last frame, and it held at the next
seed. (`docs/05_prompting.md`.)

## Fault 67 -- a card and a caption in the same lane

A Reel is watched muted, so `captioned.py` burns `subs.py`'s sidecar into a
second file. The `lower_third` CALL NOW card and the caption lane then
occupied the same bottom third and overprinted each other -- and there was
no way to move the card, because `MID_CARDS` took no settings and the end
card had no `END_CARD_OPTS` either (the end card landed exactly on the one
lit LED the last frame is about). Both now take the card's own settings, the
same way `TITLE_CARD_OPTS` always did; the mid card sits at cy 0.50. And the
libass number that bit on the way: **`MarginV` in `force_style` is in the
subtitle's 384x288 units, not pixels** -- 190 put the line in the top third.

## Three plates from one contact sheet, all prompt faults

Of eleven plates, three were wrong and none by seed: the hook rendered an
aisle because the shared `_ORPHAN` block said "long dark aisle" and that
clause won the frame; the ward aisle grew real candles on the floor from
"like votive candles" (a simile summons the object as surely as a negation
does); and "soft unreadable glow" on a wall of monitors produced a wall of
readable text. Each rewritten, each right on the next roll. The `none` title
card, which BALLAST had added to its own clone and never sent back, is now
in the repo's `cards.py`: a Reel has no title at its head, and the end card
carries the name.

## Fault 68 -- the manual still crowned the tool the template had already replaced

`docs/04_lipsync.md` opened with "What works: InfiniteTalk" and Phase 7 of
the process sent every on-camera mouth through `italk.py` -- while the
session shooter had been syncing on H3's anchored driver since the ninth
season, in one pass, with no clean bake, no sync pass and no source-proof.
A reader following the docs would have built the slow path on a tree that
no longer needs it. The operator's ruling (2026-08-23): **H3 with an
anchored driver is the lip sync, everywhere a new season plans**. The doc
now says so at the top, `CLAUDE.md` carries it as a standing rule, and
InfiniteTalk is labelled what it is -- the show tree's legacy route, kept
until a talking desk's 600-frame holds are cut into continuation beats.
The pattern a single-voice film needs to go with it: two roles on one voice
id (`gman` in `ON_SCREEN`, `inner` not), so the same clone narrates over
the beats he is not in without the driver moving somebody else's mouth.


## Fault 69 -- two tools, two spellings of "one beat", and the wrong one renders everything

`h3_shoot.py` takes bare sids; `gen_still.py` took only `--beat=NN` -- and a
bare sid matched no flag and FELL THROUGH, so `gen_still.py --force 01 08`
re-rendered the whole film at full latent, silently, while looking exactly
like a two-beat re-roll. Found because a re-roll batch was still printing
beats it was never asked for. Same fault class as the resolver that matches
zero files and reports a pass: an argument that resolves to nothing must be
refused, not ignored. `gen_still.py` now accepts bare sids the way
`h3_shoot.py` does and refuses anything it does not recognise.

## Fault 70 -- an identity reference with a scene in it becomes a shot the model cuts to

The season's dream-register identity ref was a 60%-scene crop of a plate --
a legible SUNSET TOUR sign, a Hummer hood, a sky -- and H3 CUT TO IT
mid-clip in three beats of two other films: held the anchored plate for a
beat, smeared through a transition, and finished the clip inside the
reference's scene. The smear frames read exactly like an attention-kernel
artifact, and the operator reasonably suspected the attention backend; the
tell was the reference's own signage standing in a train station. Fault 53
is the same failure entered through a poster; this one came in through the
ref slot itself.

Rules: **a reference is a FACE, not a scene** -- tight head crop, minimal
background, nothing readable; **a face ref against a beat where the
character is TINY pulls a cut to close-up** -- the model reconciles the big
reference face with the small figure by cutting to the reference, so a
beat where he is a speck takes `norefs` (his likeness at that size is the
plate's job); and **before blaming the backend, look for the reference's
content in the failed frames** -- a kernel cannot paint a sign it was
never shown. The three takes were retired `_rej_refcut` and
re-shot on face-card refs; a last-frame sheet of every strip (frame 6 of
each filmstrip, one page) is what found the full blast radius in one look.

## Fault 71 -- the subtitle probe could not survive a tree with no words

`subs_probe.py` handled a narrated cold open (vo.py) and a scripted film
(script.py) and crashed on a cold open that has neither -- three
typed-length shots and a title -- which took `subs.py` down for the whole
feature. A wordless tree has an EMPTY subtitle lane, not an error; the
probe now says so in one early return. The subtitles machinery had only
ever run against a season whose every tree spoke.


## Fault 72 -- a deliberately silent cue can never pass a liveness check

`make_music.py` measures every cue with `usable_seconds()` -- where does the
music actually stop -- and a `{"silent": True}` room cue's music stops at
0.0s forever, so the first film to score itself with silences (HOW TO HAVE
A DAY, six sung stings inside six silences) reported every silence SHORT
and refused to proceed. The check was right for music and unanswerable for
silence: the only checkable fact about a silence is its DURATION. What
landed: silent cues are ffprobe'd for length instead of listened to for
liveness, in the session, the season template and the repo template.

## Fault 73 -- the season's ACE graph renders lyrics as noise; the sidecar sings them

Two probes, two lyric formats, two seeds: the bundled 8-step turbo graph
(`score.py`, cfg 1.0) given a `lyrics` field returned music whose "vocal"
Whisper heard as dots. The same lyrics through the OmniVoice ACE-Step
plugin's sidecar -- ACE-Step 1.5's own inference stack, planner LM
available -- sang intelligibly on the first try. The turbo graph's settings
are tuned for instrumental beds and there is no knob in it worth arguing
with. What landed: `score.py` takes an optional per-cue `lyrics` key (the
default stays instrumental), and the HOW TO HAVE A DAY `make_music.py`
routes lyric cues to `POST /api/plugins/ace-step/generate` (payload wrapped
in `{"fields": ...}`) and everything else through `score.render` as before.

## Fault 74 -- a mug raised toward a face goes through sealed glass to the lips

The helmet-clink gag: raise a mug, it taps the bubble helmet, it cannot
reach his mouth. Directed as "raises the mug toward his face... meets the
glass with a tap and stays there", H3 put the rim on his lips THROUGH the
dome -- twice, at two seeds, so it was the prompt. man-raises-mug is a
drinking motion in the prior, and "toward his face" is the drinking
phrasing. What landed: the barrier stated as the subject and the
destination changed -- the dome is "a single solid sealed surface" that is
sealed in the first, every, and last frame; the motion is "aimed at the
curved OUTSIDE of the glass"; the rim "stops dead... a full hand's width of
sealed glass and air between the rim and his lips"; and the face behind the
glass is given an expression that contains the closed mouth. Third take
tapped and stayed. Same family as the mouth rule: a prior is beaten by
occupying the geometry, never by narrating the collision.

## Fault 75 -- a one-second action in a twelve-second clip pays for the other eleven

"He sits bolt upright, then holds that position" across a 12s clip: H3 sat
him up in one second, held a while, then spent the unallocated tail
standing him up, DISSOLVING THE BED under him, and re-colouring his
trousers grey -- a whole invented scene change, coherent and unasked for.
Unallocated motion gets invented (the ninth season's lesson), and a hold
is not an allocation: it decays. What landed: the hold is allocated in
small directed events ("blinks once, slowly, at the halfway mark, and once
more near the end; between those blinks he is motionless"), the set is
conserved as ONE RIGID BODY by name ("the bed -- frame, mattress, sheet,
pillow and quilt together -- is one solid object"), and the palette and
wardrobe are conserved explicitly. Take three sat up and stayed. Residue:
H3 still warms a void's colour a little over long holds; qc_drift ranks
whether any join cares.


## Fault 76 -- the diegetic bus orphans the score it was told not to play

`diegetic` defaults `music=0.0` and only summed the score labels when the
level was above zero -- but `assemble.mix()` has already BUILT one placed,
trimmed, delayed chain per cue by then, and an output label nobody consumes
is an ffmpeg "unconnected output" refusal at the end of the bake. Fault 65
fixed exactly this shape for CLIP labels by sinking the unconsumed ones in
`bus()`; the music side was left uncovered because "every bus consumes vo
and mus" -- true of every bus until the first film to run a score through
`diegetic` (HOW TO HAVE A DAY: sung stings through the clips' own bus).
What landed: `_diegetic` consumes the score whenever it exists -- at
`volume=0` it is silent but connected -- in the season and the repo.


## Fault 77 -- a dark room lights itself, and conservation does not reach the lamp

Two beats shot from a near-black bedroom plate ("the frame reads as shapes
of black on black", darkness conserved first-to-last frame in the
direction): H3 lifted both into a fully lit pink bedroom -- one steadily
across an 11.5s clip, one up and back down inside 3.5s -- as if someone
walked in and hit the switch. The conservation clause was direct, the
instruction survived, the room lit anyway: a dark interior is a prior that
wants to be SEEN, the same family as the unoccupied face and the undressed
deposition table. Do not re-argue it. What landed: the two beats were
always written as "black screen" in the treatment, and black is a TRUTH,
not a picture -- so the clips are hand-made (`color=black` + anullsrc
audio, placed as the next take, old takes retired `_rej_lightleak`),
which cannot drift and costs nothing. A beat that must actually be a DARK
ROOM on screen -- shapes legible, staying dark -- should go to a
video-only model with a real negative prompt, per the split-by-shot-type
rule in docs/05_prompting.md.


## Fault 78 -- the mixer's crossfades are bed assumptions, and they erased the stings

`assemble.mix()` fades every cue in over 2s, out over 2s, and resolves the
last over 3s -- right for ambient beds handing off to each other, and it
took a 3.5s jazz sting to nothing: under a 2s rise and a fade-out that
starts at 1.5s the cue never reaches full level, and the film's final stab
died entirely inside the end-of-picture resolve. Nobody heard a sting in
the delivered mix and every check passed, because no check listens. What
landed: the fade is the CUE's fact -- make_music.CUES entries may declare
"fade_in"/"fade_out", assemble reads them with the old defaults, and a
sting declares 0.01 in / a declick out. The check that would have caught
it at the bake is an open question; the operator's ear caught it first.

## Fault 79 -- level-matching to a singer the source had already buried

Two failures stacked in sting_swap. HDEMUCS classified ACE-Step's crooner
as "other": the "vocal" stem was scraps, the conversion was babble, and
the accompaniment kept the original voice -- replaced by the OmniVoice
Manager's Mel-Band-RoFormer over HTTP (POST /api/process-clip,
isolate=true), with the accompaniment made by phase-subtraction in mono.
Then the remix matched the converted vocal to ACE's OWN vocal level --
measured 23 dB under the horns, because ACE buries its singer inside a
sting -- so even a clean conversion shipped inaudible. Fidelity to the
source balance was the wrong brief: the film's brief is a LEAD singer, so
the remix now targets the accompaniment's mean plus 2 dB. The general
rule: when replacing an element, mix to the FILM's intention for it, not
to the level the generator happened to give it.

## Fault 72 -- a stale mix shipped 31 seconds of dead air, and only ears caught it

The recast rebuilt VO, clips and parts across three chained sessions of
fixes, and one film's mix was assembled somewhere in the churn against a
stale intermediate: its last third was digital silence under moving
picture, at target LUFS, past every check, into the published feature. The
operator heard it at 4:05. A `--keep-frames` re-mix against the same
inputs came out clean, so the graph was never wrong -- the ORDER was, and
the artifact carried no trace of which build made it. Two things landed:
`feature.py` now sweeps every part with silencedetect before the join and
prints where any 2s+ stretch lives ("listen there"), a tripwire in the
spirit of rule 9 -- ears are the filmstrip of the mix. And the operating
lesson: after a multi-stage recast, re-assemble every affected part in one
pass, in order, rather than trusting the parts that "already built" in an
earlier round of the same churn.
