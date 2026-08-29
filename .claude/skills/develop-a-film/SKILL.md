---
name: develop-a-film
description: Ideate and develop a film or season before anything renders - premise, register, script, beat sheet, look probes, voice casting, boards. Use when brainstorming concepts, writing or revising the words, choosing a style or LoRA, casting voices, or planning what a season IS.
---

# Developing a film

This is the phase before money, and the operator is the author: you draft,
probe, and lay options side by side; they pick. The process and its gates
are `docs/12_development.md`; the season's `PLAN.md` is where the thinking
and the approvals land. Work THERE — prose in PLAN.md is the cheap place
to cut, merge and reorder before anything touches `script.py` or
`edit.py`.

The loop: premise + register → words → beat sheet → look → cast → boards
→ (proof cut if the format is new) → shoot. In that order, because:

- **The script is the budget.** Every duration derives from measured
  narration; picture lands near speech × 1.2. Over budget: cut WORDS, not
  jokes.
- **Probe a look before marrying it**: `python gen_still.py --beat=NN
  --filtered` renders a candidate into its own directory — same seed, same
  words, honest comparison. Two-world films use `REGISTERS`, not a
  compromise style. The shared vocabulary is already drawn:
  `../devices.py --sheet`, likewise `cards`, `grades`, `framing`.
- **Cast on the ear, and on pace**: `python audition.py` puts candidates
  against the same three real lines. Ask the licensing question NOW
  (`identity.VOICE_IS_CLONE`) — not at delivery.
- **Boards before shooting**: `python ../contact.py` (the season on one
  sheet), `python storyboard.py` (one film with runtimes and lines), in
  front of the operator. **Nothing is bought and no motion is shot past an
  unapproved board** — record the verdicts in PLAN.md's approval log.

Structural choices that masquerade as creative ones (aspect is
season-wide; true things are drawn, not generated; faces and on-camera
speech are opt-in costs) are in `docs/12_development.md` — read it before
proposing a format.
