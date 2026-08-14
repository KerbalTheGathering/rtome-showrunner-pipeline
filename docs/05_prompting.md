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

### The other motion rules

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
