# learnings — what forks find

**Audience: a Claude Code session working on the `showrunner` template.**

A running document. Each section is one season built on this template, what it
broke, and what was changed in response. Append; do not rewrite.

Four seasons so far and twenty faults between them. **Every single one
rendered clean, exited 0, and was wrong** -- that is not a coincidence, it is
selection: the faults that crash get found in the first hour by whoever wrote
them, and the ones that reach a document like this are the ones a green build
cannot see.

The first fork's report is [`docs/10_fork_report.md`](docs/10_fork_report.md).
It took the template to a 139.6s feature — a cold open, three films, a
three-segment wraparound with lip sync — and everything it says still holds.

This is a **second** fork, and it was deliberately the opposite shape: **one
film, no show layer, 55.2s, 2.39:1 scope, shot end to end in an afternoon.**
A small season exercises different machinery from a large one, and all three
faults below are things a six-film season would never have hit.

Everything here happened. Nothing is speculative, and every fix named was
applied to this repo and then run.

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
