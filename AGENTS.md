# For AI agents

This pipeline is designed to be **operated by agent sessions**. The
operating instructions live in one place:

1. **[`CLAUDE.md`](CLAUDE.md)** — the standing rules and the routing. Read
   it first regardless of which agent framework you are.
2. **[`docs/00_READ_ME_FIRST.md`](docs/00_READ_ME_FIRST.md)** then
   **[`docs/01_process.md`](docs/01_process.md)** — the manual.
3. `python parts.py --json` — the state of a season, machine-readable,
   runnable even on a season too blank to import.

If your framework loads skills from `.claude/skills/`, six thin routers
are provided (season-status, start-season, shoot-a-film, verify-work,
publish-and-deliver, fix-a-render). They point into the docs; they do not
replace them.

Do not duplicate rules from CLAUDE.md or the docs into this file — a rule
stated in two places is this repo's oldest fault class.
