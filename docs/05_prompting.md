# 05 — Prompting: plates and motion

Two different jobs with two different rulebooks. A **plate** prompt describes a
frame. A **motion** prompt describes what happens to a frame that already
exists — and the model can already see it, so describing the contents is wasted
weight at best and an instruction to re-draw them at worst.

---

## Plates

### Structure

```
medium / style block  →  subject  →  environment  →  light  →  framing
```

**The leading block wins ties.** Whatever must survive goes first. If the style
is the thing that must hold across a season, the medium block leads every
prompt in the season and is byte-identical in all of them (`shot._MEDIUM`).

### The seed is the re-roll lever

Most shape failures — a hand, a count, a pose, an object in the wrong place —
are **seed** failures. They cannot be argued away with more words, and adding
sentences to fight one is how a prompt turns into a list of denials that starts
costing you the things you *did* want.

Escalation, in order:
1. Change the seed.
2. If the same fault returns at a second seed, it is the prompt.
3. Before rewriting, ask whether it is a **capacity** problem. Four characters
   in one frame is not a wording failure — it is too much asked of one frame.
   **Widen the frame** before rewriting the sentence.
4. If a shape comes back wrong, check you did not describe the wrong shape.

### Two shots that must match need one plate, not two prompts

Two prompts will not converge on the same room. Generate one plate and derive
both framings from it, or alias one beat to another's plate through
`shot.PLATE_ALIAS` — every `gen_still.py` resolves it, so nothing downstream
needs to know the alias exists.

### Words the stack mis-hears

These are not wording preferences. Each one produced a wrong picture more than
once, at more than one seed, and the fix in every case was a different word
rather than a longer sentence.

| Word / phrase | What arrives | Say instead |
|---|---|---|
| **"furled"** | reads as *fur*. Three takes put a dead animal on the seat beside the umbrella | "rolled and strapped shut", "closed and tied" |
| naming a **blank surface type** | summons the surface. `"every sign board and destination panel is a blank rectangle"` does not request lettering — it requests **boards**, and produced a blank cream billboard in all three cold-open shots, one of them across the sky reserved for the title | describe only surfaces that were going to be in frame anyway; say nothing about the ones that were not |
| **two contradictory instructions about one surface** | a **white blank**, not a compromise. A dark window *and* daylight behind it did it twice | pick one and state it as a conserved property |

Add to this table as you find them. A word that costs a roll is worth one line.

### A specific prop at thumbnail scale falls back to a generic

`docs/02_traps.md` records this for faces: the model cannot render what it knows
at a size the frame does not give it, so it moves the camera or substitutes.

**It is not only faces.** A cardboard disposable camera, described in the same
words, rendered correctly in close-up and came back as a metal rangefinder in a
wide shot, four rolls running. If a prop has to be *that* prop, it has to be
close enough to show why — and if it must be distant, describe a distant shape
and move the identifying detail into a beat that can hold it.

That is a workaround for not being able to put the right object in the frame.
`docs/11_asset_library.md` is a design note on the fix — generate a hero prop
once and edit it in — and on what that would cost. **None of it is built.**

### LoRAs

- A style LoRA **may have no trigger word.** Check the tensors: a unet-only LoRA
  has nothing to trigger with, and typing a trigger anyway spends prompt weight
  on a token the model does not know.
- A character LoRA will fight a style LoRA for the same region of the frame.
  Solved compositions can *reopen* when you change either weight.
- **A character LoRA in a shot that is meant to be empty will populate it.** The
  cold open and the show host both set `CHAR_LORA = ""` deliberately.

### Blanks

Anything that must read as empty — a board, a column, a doorway — cannot be
requested by negation. Compose around it, or generate it filled and clear it in
post from clean stock taken from the same plate. See `docs/02_traps.md`.

---

## Motion

### Write the direction against the PLATE, not against the treatment

A motion prompt is handed a still and told what happens to it. **A noun in that
prompt which is absent from the still is the one instruction the model can only
satisfy by drawing it.**

Two beats of a music video named "the last of the crowd" because the treatment
described a crowd walking off toward the horizon. Both plates were an empty
plain with one chair. The model invented a crowd in each -- and on the beat
whose entire job was that everything stops, it invented one and then walked it
around, so the stillest beat in the film came back as the busiest thing on the
clip sheet. Both clips were coherent and beautifully lit and nothing failed.

The treatment is what the film is about. The plate is what the model can see.
Read the plate, then write the block -- and diff `qc_clips.py`'s sheet against
`contact.py`'s, because content that is in one and not the other is instant to
spot and invisible to any per-clip number.

### Give the prior what it insists on in frame zero

The rule above is about nouns in the DIRECTION. This one is about nouns the
GENRE demands: if the plate withholds something the scene-type strongly
implies, the model will fetch it during the clip, and no occupancy clause
stops the fetching -- it only changes what arrives.

Measured on one interview sketch, three rounds: an empty deposition room
across the table from a server rack grew **a clerk's arm arranging a
folder** (an unoccupied room fills itself, exactly as an unoccupied face
fills itself). A positive occupancy clause -- "the rack is the only occupant,
in the first frame, in every frame between, and in the last" -- banned the
humans, and the model then **materialised the props instead**: a folder, a
water glass and a wire tray fading in mid-clip, persisting to the last
frame. The deposition prior insists on a dressed table, and it will send
either a person or a poltergeist to dress it.

The root fix was in the PLATE, not the direction: re-roll the still WITH the
folder and glass on the table, so frame zero already has everything the
prior wants, and let the conservation clause pin it ("everything resting on
the table keeps the exact position the first frame gives it"). Same family
as negation and allocation: the model fills undirected space, undirected
audio, unallocated motion -- and unmet genre expectations.

Two smaller instances from the same season, both prompt faults confirmed at
two seeds: "seen from behind over his shoulder" summoned a SECOND figure
(an over-the-shoulder framing implies somebody to look at -- say "alone,
with his back to the camera" instead), and "one rack in a dark aisle" came
back a wall of lit racks (an aisle is a prior that fills itself with rows;
the orphan needed "a single free-standing rack alone in a wide bare hall").
Geometry beats adjectives, and framings carry implications the same way
negations carry nouns.

### A prohibition is not a position

This is the single most load-bearing rule in `motion.py`.

Naming a thing you do not want **puts it in the frame's vocabulary**. It does not
always summon it, but it never reliably removes it, and it wastes the tokens
that could have specified what *is* true.

The fix is to occupy the channel: say what is CONSERVED, and say it is still
true in the last frame.

| Instead of | Write |
|---|---|
| "no second person walks out of the door" | "the count of people is one, from the first frame to the last... he is still the only figure in the picture in the last frame" |
| "the doorways stay empty" | "every doorway keeps exactly what it has in the first frame: the lit ones stay lit, the dark ones stay dark, and every one of them is as empty at the end as at the start" |
| "his hands do not deform" | "his two hands stay clasped together exactly as they are in the first frame, one holding the other, resting in the same place, and they are still clasped in that same place in the last frame" |
| "no dialogue, no whispering" | (see `docs/04_lipsync.md` — describe the room tone) |

The pattern is always the same three parts: **what it is now, that it stays, and
that it is still that way in the last frame.**

**And it is a check now, not advice.** `direction.py` holds the banned list and
every `motion.py` calls `direction.check(MOTION)` at import, because this rule
is broken by accident in the most natural phrasing English offers — a fork
writing "constant pace" reached for *"moving **no** faster at the end than at
the beginning"*, into the very file that forbids it, minutes after reading the
paragraph above. Sixteen of the eighteen direction blocks this repo shipped
would have been refused by it.

### When the prompt cannot win: an architectural prior

Conservation and negation rules assume the model is *free* to do the thing you
are steering it away from. Some behaviour is not a free choice — it is what the
model was trained to produce, and no phrasing reaches it.

A video model whose weights carry an **audio head** generates a vocal
performance and lip-syncs any legible face to it. In a film whose only sound is
a record nobody on screen is singing, that reads as broken sync. Two fixes were
tried:

1. **Conserve by name** — the rule that reliably holds props and practical
   lights. `"his mouth stays closed and still, lips together"`. Mouth kept
   moving.
2. **3× the sampling budget** — full 20-step sampling instead of a 6-step turbo
   LoRA, on the theory that adherence was a step-count problem. Mouth kept
   moving, and a close-up's eyes still lit up.

> **A prior that survives a direct instruction AND a much larger sampling budget
> is not being under-served, it is being obeyed.** Stop rewriting the prompt.

The fix is to change model, and **to split the work by shot type rather than
switching wholesale**: send only the shots that trip the prior to the model that
lacks it, and keep the faster model everywhere else. Here that was faces to a
video-only model and landscape, machinery and distant figures staying put — a
figure too small for a mouth to read needs neither the clause nor the slower
model.

Two side benefits worth planning for: a video-only model usually exposes a
**real negative prompt**, so the fault can be named on the side where naming
removes instead of summons; and models disagree about legal frame counts
(17n+5 against 4n+1 here), so **a mixed-model cut will not all be re-processable
by one of them afterwards.**

### The other motion rules

- **A thing that must match across shots is a paste, not a paraphrase.** Shared
  blocks exist for characters; the same discipline applies to any recurring
  object. One shot *described* the film's vehicle in its own words instead of
  inserting the canonical block, and got a visibly different vehicle — in the
  climax, four shots after the audience last saw the real one. If it must match,
  it is a constant.
- **A simile becomes the subject.** "a seam running through the wall **like a
  river** of white metal" rendered a literal river; "green-bright glittering
  copper ore" rendered gemstone. The model does not distinguish what a thing IS
  from what it is COMPARED TO. Describe geometry and material, not resemblance.
- **An instantaneous pose is invented badly.** "caught at the top of the swing,
  body twisted" is a frozen instant the model must construct a whole body from,
  and it constructs it wrong — a distorted arm. Ask for the *continuous action*
  ("swinging, both hands on the haft, shoulders square") and let it pick the
  instant.
- **A rigid object made of visible parts must be conserved as ONE BODY.** Motion
  models track the action and let the object follow — the same failure as a
  character asked to walk carrying a sword arriving empty-handed. A vehicle's
  cab detached from its bed and drove on separately. "its bonnet, cab and bed
  joined together as one rigid body that keeps its shape" fixed it, alongside a
  quieter verb: **verb energy is the throttle and structure is what it spends.**
- **Camera movement must respect the frame, not just the object.** A slow
  sideways track through a *symmetrical* two-object composition put one object
  alone in centre frame halfway through and threw the pairing away. Match the
  move to what the frame was composed for; a push holds symmetry, a track
  destroys it.

- **Naming what a character LOOKS AT rotates them toward it.** Useful when you
  want it; a trap when you name scenery for atmosphere.
- **Head turns drag the body.** If you want only the head, say the shoulders
  stay square.
- **Never name the camera in a travelling shot.** Mentioning it at all is a
  strong pull toward moving it. If the camera must be still, say the *frame* is
  locked, not that the camera does not move.
- **A constant block repeated across every beat will bake in whatever it
  implies.** One shared block put a green band across the horizon of every shot
  in a session.
- **It voices talking animals** without being asked, if the shot contains one.
- **Pitch comes from the performance direction, not the seed.**

### Local vs paid, and where a plate can sit

Shoot locally first. The reference season measured local H3 with a 6-step turbo
LoRA against the paid alternative and found it better *and* free.

When you do buy, **choose the vendor by WHERE the plate sits in the clip**:

| Need | Vendor |
|---|---|
| plate is the FIRST frame | Seedance (first-frame only) |
| plate must be the LAST frame, or mid-clip | Ray 3.2 |
| same image at fraction 0.0 **and** 1.0 | Ray 3.2 — this makes a real loop |

Luma moderates input images and every moderation failure is free. Its web app
cannot take local images at all.

**Measure what you bought before designing a move on top of it.** Four clips
arrived carrying 1.06–1.28× of their own push; compounding a post move on top of
that is how a shot ends up somewhere nobody chose.

---

## Checking a prompt's output

The order that saves the most money:

1. **Night test / probe render** — one beat, cheapest settings, before
   committing a seed to fifteen.
2. **Free local probe before buying.** Render the riskiest beat on local H3
   first: one model family succeeding proves the plate is not fighting you.
   Measure the landmark the beat is *about*, not the whole frame.
3. **Full-size review of every plate**, with any spoken claim re-read against it.
4. **Reject by renaming**, never by deleting.
