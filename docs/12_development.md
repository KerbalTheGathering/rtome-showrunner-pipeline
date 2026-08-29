# 12 — Development: everything before money

The phase where the film is decided — premise, register, words, look, cast
— costs nothing until the moment it doesn't, and every downstream number
derives from choices made here. This doc is the loop and the gates; the
season's `PLAN.md` is the workspace where the thinking lands.

**The operator is the author.** The agent drafts, probes, and lays options
side by side; the operator picks. Nothing in this phase is "done" because
the agent likes it — it is done when it is approved in `PLAN.md`'s log.

## The loop, in order

1. **Premise and register.** One paragraph of what it is, and — just as
   load-bearing — what it sounds like: the comedy/elegy dial sets lead
   lengths, cut speed, and how the score behaves (`docs/00`, "leads are the
   film's register"). Write both down before any words.
2. **Words.** The script IS the budget: every duration derives from the
   measured narration and picture lands near speech × 1.2 (`make_vo.py`
   prints both). Draft `LINES`, count seconds, and cut WORDS, not jokes —
   list items read faster than sentences. A film that must be ~110s gets
   ~90s of speech.
3. **Beats.** A film is a list of beats; each carries its lines and earns
   its length. Draft the beat sheet in `PLAN.md` prose first — it is
   cheaper to reorder a bullet list than an `edit.py`.
4. **The look, probed before it is married.** Candidate style LoRAs are
   tested on ONE beat with the probe discipline — `gen_still.py --beat=NN
   --filtered` renders into its own directory, same seed, same words, so
   candidates compare honestly. A film that cuts between two worlds
   declares `REGISTERS` in `identity.py` rather than fighting one look.
   The season's shared vocabulary is already drawn: `python ../devices.py
   --sheet`, likewise `cards`, `grades`, `framing`; `mixes.py --graph`.
5. **The cast.** `audition.py` renders candidates against the same three
   real lines and ranks what can be measured — duration and pitch spread —
   but the ear decides, and casting is on PACE as much as timbre. The
   licensing question is asked NOW, not at delivery: a film going to anyone
   without rights to a cloned voice uses a premade id
   (`identity.VOICE_IS_CLONE`; `make_vo.py` enforces it).
6. **Music: first or after?** A film cut to an existing recording is a
   different shape — `track.py` measures the song and derives the beat
   sheet FROM it. A scored film decides only where the score changes
   register (`edit.CUES`) and writes the music to picture later.
7. **Boards, then approval, then money.** Plates are cheap and local:
   generate, then `python ../contact.py` (the season on one sheet) and
   `python storyboard.py` (one film, with runtimes and lines) and put them
   in front of the operator. **Nothing is bought and no motion is shot
   past an unapproved board.**

## The gates

Recorded in `PLAN.md`'s approval log, in order — each one is a real
checkpoint the operator has said yes to:

    premise -> script (words + register) -> look (probe results) ->
    cast (auditions) -> boards -> [proof cut, if the format is new] -> shoot

**A new format gets a proof cut first.** Before committing a whole season
to an unfamiliar shape — a new genre, a new register, a new delivery
format — build the smallest thing that proves it: one promo, one movement,
one film. The cost of learning on a proof is one part; the cost of
learning on a season is the season.

## Scope decisions that look creative and are actually structural

- **The aspect is season-wide** (`season.W, H`). A vertical cut of one
  film is a SECOND season, not a setting — and its prompts want rewriting
  for the tall frame, not cropping (learnings, "a second delivery of the
  same film is a second season").
- **Anything that must be TRUE is drawn, not generated** — numbers, names,
  dates, on-screen type. Decide in development which surfaces carry type,
  because a generated signboard will letter itself (docs/05).
- **Faces are a choice with a cost.** A character LoRA holds identity; a
  film without one can design its faces out of frame entirely, which is a
  legitimate look and removes a whole class of fault. Decide per film,
  early — it shapes every plate prompt.
- **On-camera speech is opt-in.** Every mouth that moves must be driven
  (docs/04); a narrated film with closed mouths is the cheap, robust
  default. Count how many beats truly need lips before choosing a talking
  format.

The season this template came from is worked through in
`docs/08_case_study.md` — read it as one complete set of these decisions.
