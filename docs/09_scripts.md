# 09 — What every script is

An inventory, so you do not have to open twenty files to find out which one to
run. `python <script>.py` with no arguments usually prints its own usage; the
docstring at the top of each is the authoritative version and is generally an
incident report explaining why the file is shaped the way it is.

Most scripts take **beat ids as positional arguments** (`python gen_still.py 03
07`) and act on everything when given none.

---

## Season root

| Script | What it does |
|---|---|
| `season_identity.py` | **Who this season is.** Fill first. Hard-fails while blank. `python season_identity.py` prints what it thinks it is |
| `parts.py` | Discovers the running order from the folders on disk. `python parts.py` reports what is missing or inconsistent. Never imports a session's identity (a blank one would kill it) — it regex-reads instead |
| `season.py` | **Builds everything, in order, then joins.** `--films`, `--parts`, or name folders |
| `feature.py` | **The join.** Verifies every part's codec/geometry/rate/pix_fmt and every mix against its picture, then stream-copies the video and rebuilds the audio once from PCM. Every part boundary DIPS TO BLACK (`JOIN_DIP`, `JOIN_AFADE`; each part faded once at its own ends, cached by mtime -- fault 59 says why not on the joined stream). `--check` verifies and builds nothing. Lived in `show/` until a season with `SHOW = False` could not join itself |
| `upscale.py` | **Every H3 clip, once, through a real upscaler before the bake.** Cached beside the clips keyed on mtime, run in the ComfyUI venv over ffmpeg pipes. `season_identity.UPSCALE` names the model (x2 for 480p -> 1080p; None = the Lanczos stretch every earlier season shipped). A named model that is not on disk fails, it does not fall back |
| `credits.py` | **The end credit roll**, as a PART rather than a tail: a computed crawl (the block list decides the runtime), the season's display face, its own quiet cue, then 1920x1080 h264 + a sample-locked wav that `parts.py` appends and `feature.py` joins like any other part. Ships as EXAMPLE CONTENT and refuses to render until the names are the film's own — it is the one file in this repo that credits PEOPLE |
| `subs.py` / `subs_probe.py` | **A sidecar .srt/.vtt cut from the edit tables**, not from a transcript: the text is the line the voice was given, the time is the offset the mixer used. One worker subprocess per tree (three trees, three offset APIs). Labels every voice the audience cannot see, using `script.ON_SCREEN` to know who they can. Refuses if a line runs past the part it belongs to |
| `score.py` | **The local score**: ACE-Step 1.5 XL through ComfyUI, `render(name, secs, cue, out_dir)`; pinned bpm/key/time signature, `PAD` for the early fade, `usable_seconds()` to measure where the music stops, `{"silent": True}` for a span under nothing. `docs/03_audio.md` |
| `publish.py` | Feature + share cut → the delivery folder, with the lanczos downscale that keeps scanlines from moireing. Reads where the feature is from `feature.OUT` rather than rebuilding the path |
| `preflight.py` | Refuses to render while reference-season content survives in the files that decide what a film *is*. Parses string literals with `ast`, skipping docstrings |
| `new_season.py` | `--to <path> --sessions N` clones the template. `--session NAME` adds one film folder. Copies scripts and docs, never data |
| `smoke.py` | **Imports every module in every tree**, one subprocess per file. `--template` stubs identity so it runs on a fresh clone. Four seconds |
| `contract.py` | **Asserts the facts that span files** — beats agree, board type never exceeds spoken copy, every transition has a branch, every cue has a prompt. `season.py` runs it before it builds |
| `residue.py` | Finds the **previous season** in this one: beat ids and proper names that are not this season's. Advisory, exits 0 |
| `selftest.py` | **Regression tests for the shared pure logic**, each pinned to the fault it guards against (the solo lock, sum_to's padding, subs' de-overlap, the registries, next_take, the tag-habit assert, direction's own self-check). No GPU, no network, seconds. Run after editing any season-level module |
| `supervise.py` | Runs a **resumable** batch under a ComfyUI that sometimes hard-crashes: health-check, relaunch, **alternate the attention backend after a crash**, retry the command (finished items skip). `--stop` kills only what it launched, refuses on a busy queue, and prints `nvidia-smi` — the driver's number is the teardown evidence |
| `solo.py` | **One copy of a stage at a time**, refused at process entry. Every generator calls it in `main()`. `busy()` stops two renders overlapping; this stops two *processes* deadlocking on each other's queue guard. A stale lock from a dead PID is taken over, not obeyed. `--force` overrides |
| `surface.py` | Finds the largest flat surface in a plate and **draws the answer back on**. Given a colour hint and a search region, emits the rect type is drawn into. It finds the SURFACE, not the usable area |
| `devices.py` | **The transition library.** Ten of them, asked for by name in `edit.TRANSITIONS` with per-transition settings. `--sheet` renders every one so you can look rather than guess. A film with a device nobody else wants drops a `devices_extra.py` beside its own `edit.py` |
| `cards.py` | **The title and end card library.** `plain` is the default; the signature diagonal-break card is one option among five. A card declares its LAYOUT once and the drawing, the type fitting and the on-frame check all read it. `--sheet` draws them. `shot.MID_CARDS` reuses the same library for a card anchored to an arbitrary BEAT instead of the film's start or end -- text only, no picture treatment; see the note beside `MID_CARDS` in `_session_template/shot.py` |
| `grades.py` | **The look library.** `none` is the default; the season's carried flat grade is `flat`, tuned exactly as it was, beside mono, bleach, balance and day-for-night. Named in `identity.GRADE` (every beat) and `identity.GRADED_AS` (the beats `shot.GRADED` names, INSTEAD). They do not stack. `--sheet` draws all of them on a ramp, six swatches and a skin tone |
| `framing.py` | **How a plate of one shape enters a frame of another.** `crop` fills and loses the overflow, `pad` keeps the picture and adds bars, `stretch` distorts. The anchor is a name or a pair of fractions, per film in `identity.FIT_OPTS` and per beat in `shot.FIT_BEATS`. `--sheet` shows what each one keeps and loses, on two source shapes |
| `mixes.py` | **The audio bus library.** `ducked` sidechains the score to the voice (the carried arrangement), `flat` sums at fixed levels, `under` ducks by automation off the edit's own spans and so does not pump. Every bus owns the output LENGTH, which is the thing that has been wrong twice. `--graph` prints what each builds for a toy film |
| `direction.py` | **The negation rule, as a check.** Every `motion.py` calls `direction.check(MOTION)` at import and is refused if a prompt tells the model what NOT to do. Run it bare and it prints the banned list and then checks itself against seven phrasings it must catch and five it must not. It is one file, not three copies, because a rule enforced in one of three trees is not enforced |
| `contact.py` | **Every plate in the season on one sheet**, in running order, one subprocess per part. Drawable before any narration exists — `storyboard.py` is not. `--cols=N`, `--open` |
| `contact_probe.py` | The worker half of `contact.py`. Runs with the cwd set to one part and emits that part's resolved plates as JSON. Not usually run by hand |
| `check_clip.py` | **Six evenly-spaced frames from one clip** — the filmstrip motion is judged on. Season-level since finding 140 (it was byte-identical in three trees); each tree keeps a same-name shim, so run it from inside a film folder as always |
| `find_voice.py` | Voice lookup by name — your ElevenLabs library first, then the shared one — and the `key()` helper every VO tool imports. Season-level, shimmed per tree (finding 140) |
| `sheet.py` | Contact sheet of one tree's plates AS THE PIPELINE RESOLVES THEM (through `gen_still.plate()`, flips applied). Season-level, shimmed in `show/` and `cold_open/` (finding 140) |

### The four checks and what each can see

They are deliberately different questions, and no one of them substitutes for
another. The template shipped with only the first column filled in, and
[10_fork_report.md](10_fork_report.md) is what that cost.

| | asks | catches | when |
|---|---|---|---|
| `preflight.py` | is any of this still the example? | a film rendered from another film's words | before spending |
| `smoke.py` | does every module execute? | a `NameError` in a file nothing imports until it is needed | on a fresh clone, before anything is configured |
| `contract.py` | do the tables agree with each other? | a cue laid under a beat that does not exist; three lines of type against one line of copy | after `edit.py`, before generating |
| `residue.py` | whose beat id is this? | another season's numbers, keyed by an id that resolves in every season | once per clone |

---

## A film folder (`_session_template/`, copied per film)

### Fill these in — they are the film

| Script | What it does |
|---|---|
| `identity.py` | **The only file a clone must edit.** Name, number, title, slug, seed, LoRAs, `VOICES` (role → id), transition device |
| `script.py` | `LINES`: `(line_id, beat_sid, ROLE, style, text)`. The words and who says them. `SILENT` names the beats with no words; `LINE_CAP` declares how often a signature voice may speak |
| `shot.py` | One plate prompt per beat, plus the season's shared style block. Also `BEAT`, `GRADED`, framing rects |
| `edit.py` | The timeline. Beat durations derived from measured VO, `SILENT_SECS` for the beats with none, plus `TRANSITIONS` and `CUES` — where the score changes register is an edit, so it lives here and nowhere else |
| `motion.py` | One motion description per beat, plus the shared `_LOCK` block every beat inherits |

### Run these, roughly in this order

| Script | What it does |
|---|---|
| `make_vo.py` | Renders every line to `_vo/` via ElevenLabs. **Run before any video** |
| `measure_vo.py` | Prints measured take durations — the numbers everything else derives from |
| `find_voice.py` | A shim of the season-level file (finding 140): voice lookup, and the `key()` that make_vo imports |
| `audition.py` | Renders candidate voices on real lines for casting. **Do not rank on its pitch-spread column** — see `docs/06_verification.md` |
| `vo_candidates.py` | Renders several takes of one line so you can pick |
| `gen_still.py` | Generates the plates in ComfyUI |
| `storyboard.py` | One film's board: every plate in story order with its runtime and the line spoken over it. Needs `edit.table()`, so it **cannot be drawn before the VO exists** — that is what `../contact.py` is for. For approval, **not for counting things** |
| `h3_shoot.py` | Generates motion locally on MiniMax H3 -- the ref2va hybrid, the plate and a DRIVER of the real VO (silence where nobody on screen speaks) anchored at frame 0, identity references when he is alive in frame; NNx continuation beats open on the parent's tail. Free. The default. `docs/04_lipsync.md`, faults 51-54 |
| `make_video.py` | Generates motion on a paid partner node. Resolves the current clip for a beat — **use `make_video.clip(sid)` rather than globbing** |
| `qc_clips.py` | Inspect returned clips against the plates they came from — a filmstrip per clip, because one frame cannot see motion |
| `qc_drift.py` | Ranks the **joins** by luma/saturation jump — drift *between* shots, which no per-clip check sees. Advisory, exits 0; says where to look first |
| `verify_cut.py` | Proves the assembled film **is the cut**: the frame after every join against the clip that should be there *and against a wrong one*, so the test is shown able to fail |
| `track.py` | The fixed-recording mode: `analyze` measures a song (tempo **candidates**, sung spans off a Demucs stem), `beats --bpm` derives a shootable beat sheet and prints paste-ready `SILENT`/`SILENT_SECS`. Refuses to guess the tempo octave |
| `check_clip.py` | Six evenly-spaced frames from one clip. **`h3_shoot.py` runs it for you** — motion breaks in the middle, and a review step you have to remember gets skipped. A shim of the season-level file (finding 140) |
| `res_ladder.py` | Compare output at several resolutions |
| `lat_probe.py` | **UNTESTED.** Probes the Minimax H3 LATENT upscaler (`Comfyui_Minimax_h3_latent_Upscaler`) on one beat as a two-pass hires-fix -- base at half canvas, x2 in latent space, short refine at full -- against a same-seed control. Reads every node contract off the live server before submitting; lands in `<NAME>_latprobe/`, never in the clips. Its README's own caveat: "saves time, not VRAM" -- the token budget still governs |
| `mouth_scan.py` | Ranks takes by mouth aperture inside a beat window. Read `docs/04_lipsync.md` on its limits first |
| `italk.py` | WAN 2.1 InfiniteTalk lip sync -- **legacy, show tree only**; a session's sync is `h3_shoot.py`'s anchored driver. Opt-in per beat via `TALKING` |
| `make_music.py` | Score bed via the ElevenLabs music endpoint |
| `assemble.py` | **Bake, mix, mux.** `--keep-frames` re-mixes against frames on disk. `--jobs=N` caps the fan-out |
| `verify.py` / `qc.py` | Post-build checks on the finished film |
| `publish.py` | Copies plates, storyboard and film to the season's delivery folder. Refuses to choose between two files for one beat |

---

## The show folder (`show/`)

Everything above minus `make_video.py`, plus:

| Script | What it does |
|---|---|
| `crt.py` | The television chain: bandwidth-limited luma/chroma, lifted black, bloom, tube curvature, scanlines, aperture grille, rolling hum bar. `PRESETS` is the dial |
| `tvtest.py` | Renders preset comparisons on real frames at 1:1. **Use this before changing the preset** |
| `typetest.py` | Renders the on-screen type at bake resolution so spelling and fit can be checked |
| `board_rect.py` | THIS show's board: a two-setting configuration of `../surface.py` (which colour, which half of the frame). The detector itself is season-level |
| `sheet.py` | Detail sheet, cropped at 1:1 |
| `italk.py` | The lip sync. Writes `synced_XX.mp4` **and** `synced_XX.wav` in one call |
| `italk_multi.py` | **TWO speakers in one shot, on the InfiniteTalk Multi patch.** The node contract is no longer guessed: a port of this file ran the Multi patch on a later season and proved it by eye (its docstring has the findings). Still refuses to submit a graph it has not checked against the live `/object_info`, and still writes `synced_multi_XX.mp4` so it can never reach a bake by accident. `--check`, `--dry` |
| `mouth_open.py` | Aperture metric (insightface `buffalo_l`, `landmark_2d_106`, mouth 52–71) |
| `sync_probe.py` | **Lag between the driver and what actually shipped.** Passing value is zero |
| `which_source.py` | Did the bake use the synced render or the raw take? Read its docstring on its own limits |
| `audio_qc.py` | Loudness per part |
| `qc_feature.py` | Checks on the assembled feature |

**`feature.py` and `publish.py` moved to the season root** — see the root table
above. They were here, and a season with `SHOW = False` therefore could not
join itself. Neither read anything from the show tree.

### `show/_probes/`

Kept for provenance, **not part of the pipeline**. They are the investigations
that produced the rules in `docs/`: `lipsync.py` (the Kling path, superseded),
`w2l.py` / `wav2lip_test.py` / `lipsync_test.py` (the alternatives that were
measured and rejected), `it_sync.py` / `it_articulate.py` (InfiniteTalk
tuning), `audio_joins.py` / `audio_tone.py` / `vo_placement.py` (the audio
investigation), `cast.py`, `hosttest.py`, `glitch_scan.py`, `sync_qc.py`,
`_open_strip.py`.

Read one when you are about to re-litigate the decision it records.

---

### `show/h3_chain.py`

The show's H3 shooter for segments WITHOUT FACES: a segment longer than H3's
~15 s trained range is shot as a chain of pieces, each opening on the last
`H3_TAIL_FRAMES` of the piece before it, joined with the anchored frames
dropped. One canvas per chain (a join across canvases is a size mismatch),
every piece with a silent driver, baked `--raw`. `h3_shoot.py` stays the
faced lane.

## The cold open (`cold_open/`)

A cut-down film folder: `shot.py`, `edit.py`, `motion.py`, `gen_still.py`,
`h3_shoot.py`, `check_clip.py`, `make_music.py`, `assemble.py`, `sheet.py`. No
`script.py` — it has no words, and its beat lengths are therefore TYPED, in
`shot.SECS`. That is the one documented way to run a tree with no narration.

Its bake uses a **real worker pool** rather than the film trees' self-slicing,
because its loop body is pure — 22 s for 661 frames, and pixel-identical to the
serial version. See `docs/07_performance.md`.

---

## Patch scripts

The reference season's `patch_*.py` are not carried into the template — their
changes are already applied here. The pattern they establish is worth keeping:
**every substitution asserts its target exists and is unique**, and refuses
rather than guessing. If you write one, copy that shape. See `docs/02_traps.md`.
