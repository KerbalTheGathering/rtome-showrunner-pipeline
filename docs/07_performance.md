# 07 — Why a bake takes 90 seconds and not an hour

Measured on a Ryzen 9 5950X (16 cores / 32 threads), RTX 4090, NVMe.

| | before | after |
|---|---|---|
| one 2814-frame film | ~11 min | **1 min 44 s** |
| six films | ~60 min | **8.8 min** |
| six CRT interstitials (2257 frames) | ~25 min | **3 min 42 s** |
| the cold open (661 frames) | ~2 min | **22 s** |
| the join (stream copy + one audio encode) | — | ~40 s |

The serial bake ran at **292 frames/min on one core** — 5 % CPU on a 32-thread
box. The whole of the gain is parallelism; nothing was made cheaper.

---

## Two different parallelisms, for two different loop bodies

### A real worker pool, where the body is pure (`show/assemble.py`, `cold_open/assemble.py`)

The interstitial bake is a pure function of `(frame, index)` — the tube's hum
bar takes its phase from the index and nothing carries between frames. So it
uses `concurrent.futures.ProcessPoolExecutor` with the loop body lifted into a
module-level `_bake_one(i)` and the context delivered once per worker through an
`initializer`.

Two things that bite on Windows, which **spawns rather than forks**:

- **A closure cannot make the trip.** The worker must be module-level, and every
  argument must pickle. PIL `FreeTypeFont` objects do not.
- **A module global set from `argv` is not inherited.** `--tv=` rebinds a global
  in `main()`; a spawned child re-imports the file from scratch and would have
  quietly baked the *default* preset while the parent reported the requested
  one. Pass it explicitly through the initializer.

Also worth ~30 %: `im.save(path, compress_level=1)` on intermediates that exist
for the length of one ffmpeg call and are then deleted.

### The one restructure a pool needs

`cold_open/assemble.py` originally exploded one shot, baked it, and deleted the
directory before moving to the next. Workers cannot race each other extracting
and deleting shared directories — that is precisely the bug the film trees hit,
where a child succeeds alone and dies in company. So **every clip is exploded
before the pool starts** and the directories are removed once, afterwards. It
costs a few hundred MB of PNGs for the length of one bake.

**The parallel result is pixel-identical to the serial one**, verified rather
than assumed: PSNR between the two renders is infinite, MSE 0.00 on all three
planes across all 661 frames. Any reordering-sensitive bug in a parallel bake
would show up there.

### Slicing the script, where the body is not (`*/assemble.py` for films)

The film bake body reads **neighbouring frames** off disk for the register slip,
draws with font objects, and closes over a dozen locals. Lifting it into a
worker would mean rewriting the part of six diverged files that actually makes
the picture — to make them faster.

So the loop body is not touched at all. The parent builds the plan, wipes the
output directory, and runs **itself** once per core:

```
python assemble.py --bake-slice=k/N
```

Each child rebuilds the identical plan, writes only the frames where
`i % N == k`, and `sys.exit(0)` before the mix. The parent counts the PNGs
afterwards.

**Three requirements, all of which were violated on the first attempt:**

1. **The plan must be deterministic.** No `random`, no `time.time()`, no
   `datetime` anywhere in the module. `patch_parbake.py` refuses to patch a file
   that reaches for any of them, because slicing a non-deterministic plan
   silently produces frames from different edits and the film cuts wrong
   somewhere in the middle.
2. **Children must not re-run the plan's side effects.** `plan()` opened with
   `shutil.rmtree(WORK)` and re-exploded every clip, so sixteen children deleted
   each other's source frames mid-read — and their parent's. A child succeeds
   when run alone and dies in company, which is the worst possible signature.
   Extraction stays in the parent; children list what is on disk.
3. **Count the output afterwards, and require exact equality.** Not `>=` — a
   stale PNG left over from a longer edit passes that, and the encode makes a
   film of the wrong length without complaining. This count is the only reason
   the first failure was noticed rather than shipped.

```
JOBS = max(1, min(16, (os.cpu_count() or 4) - 2))
```

Two threads left for ffmpeg and the machine. Above sixteen the PNG writes start
contending for the disk rather than the CPU. `--jobs=1` restores serial
behaviour, which is what you want when a bake is misbehaving and you need to
read its output.

---

## What is still serial, and what it would take

- **The clip explode** (ffmpeg PNG extraction) fans out in `extract_all()`
  since finding 139 — each beat writes its own directory, the exact property
  the slice children already rely on, so the race that forces serialisation
  elsewhere does not apply. Batched at JOBS; ~30 s serial became ~5 s. The
  **upscale pass inside it stays serial**: it is the GPU.
- **Generation** is GPU-bound and inherently serial on one card. A six-chunk
  InfiniteTalk segment is 5–15 minutes; a film's worth of H3 beats is longer.
  This is where the wall clock actually goes on a fresh season — the bake being
  fast matters because you re-bake constantly and you generate once.

  **An UNTESTED candidate for exactly this**: a latent-space upscaler for
  H3 (`Comfyui_Minimax_h3_latent_Upscaler`, weights on the author's
  HuggingFace) promises the base pass at a quarter of the tokens, with a
  short refinement at full resolution — a two-pass hires-fix inside the
  latent. `_session_template/lat_probe.py` is wired to test it on one
  beat against a same-seed control; nothing in this repo uses it until a
  filmstrip from that probe says so. Two facts to hold onto from its own
  README before hoping too hard: **"saves time, not VRAM"** (the refine
  runs at target resolution, so `BUDGET_M` and the canvas ladder still
  govern), and the audio latent is split off and rejoined untouched —
  whether sync survives the refine pass is the first thing the probe's
  verdict must say.

---

## Practical notes

- **Do not run two trees at once.** Each already uses every core; `season.py`
  runs them one after another deliberately.
- **`--keep-frames`** re-mixes and re-muxes against frames already on disk and
  checks the count first. It is the right flag when only the audio changed, and
  the wrong one after any edit change.
- **Background a long build and poll a condition**, do not sleep in a loop. A
  full season rebuild is ~15 minutes including the join.
