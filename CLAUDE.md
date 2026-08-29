# For the agent operating this repo

This pipeline is operated by sessions like yours. The docs are the manual;
this file only routes you into them and states the rules that cost real money
or real nights when broken. The skills in `.claude/skills/` (season-status,
start-season, develop-a-film, shoot-a-film, verify-work,
publish-and-deliver, fix-a-render) are thin routers into the same docs,
surfaced by task — use them, but the docs stay authoritative. Every one of them was learned the hard way — the
incident record is `learnings.md`, and the fastest way to re-litigate a
decision is to skip reading it.

## Before anything else

1. Read `docs/00_READ_ME_FIRST.md`, then `docs/01_process.md`.
2. `python season_paths.py` — does this machine have the tools, and is the
   ComfyUI that answers the one that is configured? Two different facts;
   `check_instance()` tests the second. `SEASON_COMFYUI` and `SEASON_ENV`
   unset means the defaults, and the defaults have pointed at a stale empty
   tree before. Set them.
3. Never hand-copy a season. `python new_season.py --to <path> --sessions N`
   exists because a hand copy drags gigabytes of the previous film with it.

## The standing rules

- **State identity once.** Every "which film is this" value lives in
  `identity.py` / `season_identity.py` and is imported. If you find yourself
  typing a title, a slug or a name anywhere else, stop — that exact move has
  shipped four silent faults.
- **The operator is the author, and development has gates.** Premise,
  script, look, cast and boards are approved in the season's `PLAN.md`
  before anything is bought or shot — `docs/12_development.md`. Draft and
  probe freely; commit nothing creative on your own verdict.
- **Checks before money.** `preflight.py` (is this still the example?),
  `smoke.py` (does every module execute?), `contract.py` (do the tables
  agree?), `residue.py` (whose beat ids are these?). They are not
  interchangeable; `docs/00_READ_ME_FIRST.md` has the table.
- **One render at a time, one batch per stage.** Every generator refuses a
  busy queue and takes a `solo.py` lock at entry. Do not background a second
  copy to "help" — two copies deadlock politely at 0 % GPU with nothing in
  any log.
- **A cut that must match is a paste, not a paraphrase**, negation summons
  what it names, and a prompt cannot out-argue an architectural prior — the
  prompting rules are `docs/05_prompting.md` and `direction.py` enforces the
  negation rule mechanically.
- **Lip sync is H3 with an anchored driver**, shot in the same pass as the
  motion (`h3_shoot.py`, `docs/04_lipsync.md`). InfiniteTalk is the show
  tree's legacy route; do not plan a new season around it.
- **A check that does not measure the delivered artifact is not a check**,
  and a metric is a tripwire, not a verdict. `docs/06_verification.md`,
  rules 1–9. Filmstrips decide; means lie.
- **Failure modes that render clean** — caching, thresholds, ffmpeg, guards
  that deadlock or block forever — are catalogued in `docs/02_traps.md`.
  When something "works" suspiciously smoothly, look there first.

## The GPU is shared

Check whether ComfyUI is already up (`curl <COMFY_URL>/system_stats`) before
launching one; prefer the instance that exists. If you start one, you own it:
guard teardown on an empty queue, kill the tree you launched and **verify
with `nvidia-smi` that the memory actually dropped** — the `/free` endpoint
returns 200 without returning VRAM, and `nohup`'s exit code describes the
wrapper, not the process. `supervise.py` wraps a crash-prone batch: it
relaunches the server, alternates the attention backend after a crash, and
retries the (resumable) command.

## When you learn something

Faults go to `learnings.md`, numbered, with what landed — plus a symptom
line in the lookup table at the top of that file, phrased the way an
operator would say it. Rules that generalise go to the `docs/` file a
future session will actually hit them in. All of it, not some — the log is
why, the docs are where, the table is how you find it again.
