---
name: fix-a-render
description: Diagnose wrong, ugly, or silently-broken output - a plate that ignores the prompt, motion that dissolves, sync that drifts, a bake that hangs, a check that passed but the film is wrong. Use before re-rolling blindly or adding prompt words.
---

# When the output is wrong

Almost nothing in this domain crashes — wrong output renders clean and
plays fine. Route by symptom, and read the trap catalogue first when the
failure "worked" suspiciously smoothly: `docs/02_traps.md`.

| Symptom | Where the answer is |
|---|---|
| plate ignores or distorts the prompt | `docs/05_prompting.md` — negation summons what it names; geometry beats wording; the most-described object becomes the subject; a word-trap table to add to |
| wrong shape at one seed only | re-roll the SEED, don't add sentences — one seed is a roll, two seeds failing the same way is a prompt fault |
| motion dissolves / invents content | H3 sustains the first frame; unallocated motion gets invented; a plate of pure texture cannot be moved, only lit (`docs/05`, learnings 90–96) |
| mouth moves under silence / invented voice | the driver rules — anchored silence is the signal, absent audio is an invitation (`docs/04_lipsync.md`, faults 51–54) |
| audio late / early / drifting | nothing in the audio chain may have lookahead; `docs/03_audio.md`, then `sync_probe.py` |
| loudness or true peak wrong | fault 97 in learnings.md: the source, the encoder and the assembler each add their own; a CEILING controls sample peak, never true peak |
| bake dies mid-run / ComfyUI crashes | `supervise.py` — relaunch, alternate attention backend, resume |
| 0% GPU, no output, no errors | two copies of a stage are deadlocked on each other's queue guard — find and stop the extra process; `solo.py`'s docstring |
| a check passed but the film is wrong | the check measured the wrong thing — `docs/06_verification.md` and the "checks that lie" entries in `docs/02_traps.md` |

When you find something new: the fault goes in `learnings.md`, numbered,
with what landed; the rule that generalises goes in the `docs/` file a
future session will hit it in. Both, not either.
