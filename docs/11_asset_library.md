# 11 — The asset library: reusing a prop instead of re-rolling it

> **NOTHING IN THIS DOCUMENT IS BUILT.** Every other file in `docs/` describes
> machinery that exists and guards that fired. This one is a **design note**: an
> idea from outside this project, checked against what this pipeline already
> measured, and written down before any of it is written. Read it as a plan with
> its traps mapped, not as a description of the tree.
>
> The evidence sections cite real incidents. The design sections do not, because
> there is nothing yet to have an incident with. Where a decision is a guess,
> it says so.

The idea is **Promptwaffle's**, from a conversation about working the same
problem in Krea, and it is theirs rather than this project's: **a recurring
prop, location or character should be generated once, catalogued, and thereafter
*edited into* new plates — never re-rolled.**
Hero props and dressing props live in folders, an LLM tags them so they can be
found, and a new shot checks the library before it checks a seed. When the room
gets blown up in act three, you edit the room you already have rather than
asking a fresh render to remember it.

The claim underneath it is worth stating plainly, because it is the opposite of
how this pipeline works today: **seed-searching for a thing you have already
made is the expensive way round.**

---

## What this pipeline already does, and where it stops

This is not a foreign idea here. It is `PLATE_ALIAS` with the walls taken off.

- **Reusable text blocks.** `shot._KEEPER`, `shot._LIGHTHOUSE` — a character or
  a location that appears in more than one beat gets a named constant, because
  "retyping it is how two beats that are meant to be the same place stop being
  the same place" (`_session_template/shot.py`).
- **`PLATE_ALIAS`.** Two shots that must match get **one plate**, not two
  prompts. `gen_still.plate()` resolves the alias, so storyboard, motion,
  `make_video` and `assemble` inherit it without knowing it exists.
- **The look libraries.** `devices.py`, `cards.py`, `grades.py`, `framing.py`,
  `mixes.py` — a named thing, a plain default, and a `--sheet` you can look at.
  That is already the shape an asset library would take.

Where it stops, in three facts:

1. **The reusable blocks are words, not pictures.** `_LIGHTHOUSE` is a *string*
   describing a lighthouse. Two films handed the same string do not get the
   same lighthouse — `docs/05_prompting.md` says so outright: "two prompts will
   not converge on the same room."
2. **`PLATE_ALIAS` cannot cross a film.** It is a `dict[str, str]` of beat ids
   inside one `shot.py`. There is no vocabulary for "this is the same knife as
   the one in S2".
3. **There is no image→image step anywhere in the tree.** Every plate is
   text-to-image. The only `LoadImage` nodes in the repo are motion
   (`h3_shoot.py`) and lip sync (`italk.py`) reading a finished plate as a first
   frame. Nothing in this pipeline has ever edited a picture with a model.

That third one is the actual build. The rest is bookkeeping.

---

## The measured case for it

Three things this pipeline already paid for say the library is the right answer.

**A specific prop at thumbnail scale falls back to a generic.** A cardboard
disposable camera, described in the same words, rendered correctly in close-up
and came back as a metal rangefinder in a wide shot, **four rolls running**
(`docs/05_prompting.md`, `docs/10_fork_report.md`). The current advice is
"describe a distant shape and move the identifying detail into a beat that can
hold it" — which is a workaround for not being able to put the right object in
the frame. A library plus an edit step is the fix rather than the dodge.

**Asking two renders to agree on a composition does not work.** Beat 07 of a
real film was meant to be the same corner as beat 03: same seed, byte-identical
leading text, **three different corners**. That failure is what `PLATE_ALIAS`
exists for. It is the same failure, one scope up, every time a season needs the
same location in two films.

**The old assert passed while the device failed.** `shot.py` still carries the
comment: a check that beats 03, 07 and 12 shared their leading *text* went green
on three visibly different *pictures*. **A library that resolves by prompt text
inherits that bug exactly.** Whatever identifies an asset has to be the file,
not the sentence.

---

## What it needs

Seven pieces, roughly in order of how much work each is.

### 1. A root, in the one file allowed to hold a path

`season_paths.py` is the only file in the tree with a path in it, and every path
is an environment variable with a sane default. So:

```python
ASSETS = _env("SEASON_ASSETS", os.path.join(COMFY, "assets"))
```

**Outside any season, on purpose.** The whole value of the idea is that the
knife survives the season it was made for. A library that lives inside
`<season>/` is just `PLATE_ALIAS` with more typing.

```
<assets>/
  props/hero/<slug>/        the ones the audience is meant to read
  props/dress/<slug>/       the ones that only have to be present
  locations/<slug>/         the empty-room template
  characters/<slug>/        the turnaround
  pending/                  generated, not yet approved. Nothing may reference it
```

### 2. A sidecar. An asset is not a PNG

Identity is imported, never typed — the rule that `identity.py` exists for
applies here without modification. An asset is **a picture plus a record**:

| Field | Why |
|---|---|
| `slug` | what `shot.py` names |
| `class` | hero / dress / location / character |
| `block` | **the prompt sentences that describe it** — so `_LIGHTHOUSE` becomes an import instead of a retype |
| `light` | the lighting state it was made under. See the traps below; this is not optional |
| `model`, `seed`, `loras` | what made it. A re-roll of an asset is a new asset, not an overwrite |
| `sha256` | of the picture, so the record cannot drift from the file |
| `origin` | which project made it |
| `consent` | see §7 |
| `tags` | what the LLM wrote. Advisory, and marked advisory |

The `block` field is the quiet win, and it is worth having even if the edit step
is never built: **the words that describe the thing and the picture of the thing
stop being two facts that can disagree.**

### 3. The edit graph — this is the real work

A new `edit_plate.py`, taking a base plate plus one or more asset images plus an
instruction. It does not get to be a fresh script written from scratch, because
`gen_still.py` already paid for its own lessons and every one of them applies:

- **One render at a time, queue verified empty between.** Two Krea2 renders
  queued together walked a 24GB card to its ceiling and turned 2.5 s/step into
  170 s/step — a 22-minute image. Free VRAM cannot predict it. An edit graph
  carrying a second image is *more* memory, not less.
- **The gate is measured duration, not VRAM.** `SLOW_S = 300`, interrupt past
  it, and know that `/interrupt` does not give the memory back.
- **Idempotent per beat.** A composite already on disk is skipped.
- **Reject by renaming, never by deleting** — and `_rej_` must be skipped
  explicitly by the new selector too. `docs/02_traps.md` records what happens
  when one selector forgets: the reject becomes its own entity, survives frame
  prep, and gets billed as a second clip generated from the picture that was
  thrown out.

And one rule the edit step needs that generation did not:

**Key the composite on its recipe.** `docs/02_traps.md`: "key every derived
artifact on its RECIPE — a hash in the filename or a sidecar JSON. Duration
checks cannot detect a content swap." A composite plate is derived from a base
plate, N assets, an instruction and a seed. Any of those five changing and the
filename not changing is three paid lip-sync passes bought against the old
plate, again.

### 4. Search that is not allowed to decide

The LLM tags the folder **so a human can find things**. It does not get to pick
the prop.

`shot.py` names the slug explicitly, the way it names a device or a card today.
Search is a discovery tool that prints candidates and their sheet thumbnails,
and stops. This is not squeamishness about models — it is the single most
expensive failure class in this repo, stated in `docs/02_traps.md` and
`docs/06_verification.md` in four different forms: **a resolver that matches the
wrong thing and reports a pass.** A retrieval score is a grid search, and "a
search returns the least-bad point inside its grid, never *no idea*."

The honest version of automatic matching, if it is ever wanted: it may **refuse**
— "you named `hero/knife` and there are three, disambiguate" — but it may not
choose.

### 5. `props.py --sheet`

The library gets the same treatment every other library in this tree gets: one
command that renders all of it, at a size where you can compare. `contact.py`
exists because the comparison questions — "is that the same corner? is that the
right prop?" — cannot be answered one file at a time.

The sheet catches what the catalogue cannot: two slugs that are the same object,
one slug whose picture has drifted from its `block`, an asset that only reads at
the scale it was generated at.

**And it must refuse to count.** `docs/02_traps.md`: never count a subject off a
contact sheet — "three ospreys" was four, because two birds merged on a 980 px
thumbnail. The sheet is for *is this the thing*, not for *how many*.

### 6. `contract.py` and `residue.py` grow a case each

`contract.py` asserts the facts that live in more than one file, which is
exactly what an asset reference is:

- every slug named in any `shot.py` resolves to an asset that exists;
- every asset used by this season carries a consent record;
- no two slugs share a `sha256`;
- every sidecar's hash matches the file on disk.

`residue.py` is the harder one, and it is the trap that worries me most.
`docs/00_READ_ME_FIRST.md`, point 6: **a key that exists in every season is not
an identifier.** Every film numbers its beats `"01"`, `"02"`, so a table keyed
by beat id resolves perfectly in a tree it was never written for — nothing
raises, nothing counts wrong, and it is the wrong film.

`hero/knife` is that key with a shared filesystem behind it. A slug that resolves
in every project, pointing at a real file, from a project you are not making. It
will load. It will hash fine. It will be wrong, and it will look deliberate.

The precedent for the fix is already written: `season_identity.claim_clips()`
stamps a `.season` file into a clip folder it creates and refuses one stamped by
a different season — found by this template's own test clone. An asset borrowed
across projects should have to say so out loud, once, in `shot.py`.

### 7. Consent, and why it is structural here

`LICENSE`'s third condition — no synthesizing a real person's likeness or voice
without that person's freely given written consent — is the term that is not for
sale at any price. `docs/02_traps.md` closes on the code version of it: "a client
deliverable must not carry the user's own voice or face, **and the guard belongs
in code, not in a note**."

A `characters/` folder is precisely the mechanism by which a likeness stops being
a decision someone made for one film and becomes a file that four projects
import without anyone re-reading the terms. So the consent field is not
paperwork: **an asset without one is not resolvable**, the same way a blank
`identity.py` hard-fails on import.

---

## What it costs

Five, and the first two are the ones that will actually bite.

**An edit re-draws what it touches.** The composite is a *new picture*. It has
been through a model that was not handed `shot._MEDIUM` as its leading block,
and the leading block wins ties. The season's look is **not** preserved by
construction, so an edited plate needs the same full-size review as a generated
one and probably a measured one: the medium is the thing six films share, and
this is a machine for quietly breaking it in one of them.

**A prop carries its light.** An asset made under `_LIGHT_NIGHT` composited into
a `_LIGHT_DAWN` plate is `docs/05_prompting.md`'s contradictory-surface trap in
image form — two instructions about one surface produced "a white blank, not a
compromise", twice. Hence the `light` field, and hence: the edit instruction must
restate the destination's lighting as a **conserved property**, because that is
the only phrasing that has ever worked on this stack.

**Cross-season reuse flattens seasons.** The shared look is a feature *within* a
season. A library spanning four of them is a slow path to making them one thing,
and nothing will report it — the films will all render, and they will all be
fine, and they will all look like each other.

**A prohibition is still not a position.** Nothing about an edit model changes
`motion.py`'s load-bearing rule. "Put the knife on the table and change nothing
else" names everything else. What is conserved has to be said as what it is.

**The library is a cache, and caches serve you the bug you just fixed.** Three
separate failures in one film came from a cache keyed on a filename. An asset
that was re-rolled and re-approved, under a slug that did not change, is that
bug with a nicer folder structure.

---

## Before any of this ships

The rule that generates all the others: **a check that does not measure the
delivered artifact is not a check.** So the bar for calling the edit step
working is not "the composite looks right in review". It is at minimum:

1. **The prop is in the frame at the size the frame gives it.** The original
   incident was a hero prop degrading in a wide shot. If the composite is only
   verified in close-up, it has not been tested against the thing it was built
   for.
2. **A control.** `docs/06_verification.md`, rule 3: any threshold on
   photographic content needs a control run. Difference the composite against
   its own base plate; the region that changed should be the region named, and a
   change everywhere means the model re-drew the shot.
3. **The medium survived.** Measured on the delivered plate, not on the asset.
4. **One human, once, at native resolution**, before the slug is allowed out of
   `pending/`. Same shape as `preflight.py` refusing to render while
   `EXAMPLE_CONTENT` survives: the approval is a deletion, and only a person can
   do it.

And the honest note: a composite that fails any of those is not a failure of the
idea. It is the cost of the idea, and it should be written down here next to the
rest of them.

---

## Open questions

- **Which edit model.** This tree has never run one. Whatever it is has to be
  stated in `identity.py` like every other model choice, and it will be wrong on
  a different machine at a different time — the transferable part is the
  structure and the checks.
- **Whether an asset is one picture or a turnaround.** A character is plainly
  several views; a hero prop probably is too. That changes the sidecar from a
  record to a small manifest and it changes what the sheet shows.
- **Whether `PLATE_ALIAS` should be subsumed by this or left alone.** It works,
  it is cheap, and it needs no model. My guess is: leave it. Within one film,
  the same plate is *already* the right answer, and an edit step that gets used
  where an alias would do is a re-roll with extra steps.
