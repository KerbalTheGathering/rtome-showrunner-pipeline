---
name: season-status
description: Re-enter a season and find out what state it is in. Use when resuming work on a season, when asked "where were we" / "what is left", or before deciding what to run next. Reads state off the disk instead of re-deriving it from prose.
---

# Where is this season?

One command answers it, machine-readably, on a season too blank to import:

```bash
python parts.py --json
```

It reports the season identity (and what is still blank), every session
folder with its clip/VO/bake counts, the running order, and which parts are
built. `python parts.py` is the human-readable version. Do NOT re-derive
"what exists" by reading docstrings or listing folders — that is the exact
context-burn `--json` was added to stop.

## Then pick the next move from the state

| State | Do this |
|---|---|
| identity fields blank | fill `season_identity.py` / the named `identity.py`, re-run `parts.py` |
| fresh clone, nothing run | `python smoke.py --template`, then `python residue.py` |
| content filled, nothing rendered | `python preflight.py` and `python contract.py` BEFORE anything that costs time or money |
| plates exist | `python contact.py` — every plate on one sheet, in running order |
| parts built, no feature | `python feature.py --check`, then `python feature.py` |
| something looks wrong | the `fix-a-render` skill, and `docs/02_traps.md` |

The four checks are different questions and not interchangeable —
`docs/00_READ_ME_FIRST.md` has the table. `season.py` builds everything in
order and runs `smoke` + `contract` first.

## Two facts to confirm before trusting anything

- `python season_paths.py --json` — does this machine resolve the right
  tools, and is the ComfyUI that answers the one that is configured?
  `problems` empty means yes to both. `SEASON_COMFYUI`/`SEASON_ENV` unset
  means defaults, and the defaults have pointed at a stale empty tree
  before.
- `curl $SEASON_COMFY_URL/system_stats` — is a ComfyUI already up? Prefer
  the instance that exists; if you start one, you own its teardown
  (CLAUDE.md, "The GPU is shared").
