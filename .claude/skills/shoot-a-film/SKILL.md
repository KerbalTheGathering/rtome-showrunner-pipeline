---
name: shoot-a-film
description: Generate one film's assets in the right order - narration, plates, motion, assembly. Use when rendering, shooting, re-rolling a beat, or running gen_still / h3_shoot / make_vo / assemble in a film folder. Carries the GPU-sharing and money rules.
---

# The shoot loop (inside one film folder)

The order is load-bearing; `docs/01_process.md` is the full manual.

```bash
python make_vo.py            # 1. narration FIRST -- every duration derives from it
python measure_vo.py         # 2. the numbers everything else uses
python ../contract.py        # 3. do the tables agree? BEFORE generating
python gen_still.py          # 4. plates (ComfyUI, local, free)
python ../contact.py         # 5. look at every plate in the season together
python h3_shoot.py           # 6. motion, locally on H3 -- free, the default
python assemble.py           # 7. bake + mix + mux
python verify.py && python verify_cut.py   # 8. check the DELIVERED film
```

## The rules that are expensive to relearn

- **One render at a time, one batch per stage.** Every generator refuses a
  busy queue and takes a `solo.py` lock. Do NOT background a second copy to
  "help" — two copies deadlock politely at 0% GPU with nothing in any log.
- **The seed is the re-roll lever, not more words.** A wrong shape in a
  plate is usually a seed problem; `--seed=N` re-rolls, and the per-beat
  seed is written down in `shot.PLATE_SEED`.
- **A prompt cannot out-argue an architectural prior**, and negation
  summons what it names — `direction.py` enforces the negation rule
  mechanically; the rest is `docs/05_prompting.md`.
- **Re-roll surgically.** Name the beat (`gen_still.py 03`, `h3_shoot.py 05
  --rej=blurry`). A blanket `--force` on `make_vo.py` silently resizes the
  whole edit.
- **Local is the default; paid is opt-in.** `h3_shoot.py` is $0.00;
  `make_video.py` is the paid partner path. Read `price_badge` from the
  node registry rather than spending to learn a price.
- **Judge motion on filmstrips**, never one frame — `check_clip.py` runs
  automatically after each shoot; look at the strips.
- **Lip sync is H3 with an anchored driver**, shot in the same pass as the
  motion (`docs/04_lipsync.md`). InfiniteTalk is the show tree's legacy
  route.

## The GPU is shared

Check `curl $SEASON_COMFY_URL/system_stats` before launching a ComfyUI;
prefer the instance that exists. If you start one you own it: tear down on
an empty queue only, and verify with `nvidia-smi` that the memory actually
dropped — `/free` returns 200 without returning VRAM. `supervise.py` wraps
a crash-prone batch (relaunch, alternate attention backend, resume).
