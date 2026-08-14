# Contributing

Contributions are welcome. Two things are non-negotiable: the CLA, and evidence.

---

## 1. The CLA

**Before your first pull request can be merged, you must sign the Contributor
Licence Agreement.** Open the PR first — signing happens in a comment on it.

Leave a comment containing exactly:

```
I have read the CLA Document and I hereby sign the CLA
```

A bot records the signature and re-runs the check. You sign once, ever.

- Individual, personal capacity → [CLA.md](CLA.md)
- Contributing as part of your job → your **employer** must also execute
  [CLA-ENTITY.md](CLA-ENTITY.md)

### Why there is a CLA at all

This project is dual-licensed: AGPL + the Licensor's Conditions for
individuals and small organizations, and a paid
commercial licence for those who need to sell it. The commercial half only
functions if one party holds relicensing rights over the whole codebase. One
merged patch under bare AGPL, with no CLA behind it, would permanently
contaminate that — the commercial licence could no longer be granted over the
file it touched.

You keep your copyright. You can reuse your own work anywhere. And [CLA.md
§6](CLA.md) binds the maintainer in return: your contribution stays publicly
available under a source-available licence, permanently. It cannot be taken
closed-only.

If that trade is not acceptable to you, fork instead — the AGPL gives you that
right and no one can withdraw it.

---

## 2. Evidence

> **The rule that generates all the others: a check that does not measure the
> delivered artifact is not a check.**

This repo exists because generative video fails silently. Almost nothing
crashes. A film with the wrong title card, a frozen zoom, or a voice 150 ms late
encodes cleanly, exits 0, and is wrong. Every guard and refusal here was paid
for by one of those.

So a PR that changes behaviour needs to show its work:

- **What you ran.** The actual command, the actual season or fixture.
- **What you measured.** Not "it looks right" — the measurement, on the
  delivered artifact. Frame counts, durations, loudness, offsets, hashes.
- **What it did before.** The failure, reproduced, with output.

A patch that removes or weakens a check needs to explain what incident the
check was written for and why that incident can no longer happen. Look for the
comment above it; the comments are mostly incident reports.

### Good PR shapes

| Kind | What it needs |
|---|---|
| New refusal / guard | The artifact that passed and was wrong |
| Bug fix | Reproduction before, measurement after |
| New model or backend | Comparison on the same shot, both stated in `identity.py` |
| Docs | Nothing but accuracy — these are read under pressure |
| Refactor | Proof of no behavioural change |

---

## 3. Practical

- **Discuss large changes first** in an issue. A rejected 2,000-line PR wastes
  your evening more than mine.
- **Keep the diff to one concern.** Separate concerns, separate PRs.
- **Match the surrounding code.** Comment density, naming, and idiom included.
  The comments carry the incidents; keep writing them that way.
- **Do not commit output.** `_work/`, `_baked/`, `_vo/`, media files and
  `out/` are ignored for a reason — a season runs to tens of gigabytes.
- **Do not commit credentials.** `season_paths.ENV_FILE` points outside the
  repo by default precisely so this is hard to do by accident.
- **Third-party code** must be declared in the PR, with its licence, per
  [CLA.md §8](CLA.md). AGPL-incompatible code cannot be accepted at all.

---

## 4. What happens to your PR

1. CI checks the CLA signature.
2. I read the evidence before I read the diff.
3. Expect questions about failure modes rather than style.
4. Merged contributions appear in the Git history under your name, and become
   part of both the public and the commercially licensed builds, per the CLA.

There is no service-level agreement on review time. This is one person's
project.

---

Questions: **licensing@rtome.net** · Licensing: [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md)
