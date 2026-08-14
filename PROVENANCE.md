# Provenance

A record of who holds the copyright in this codebase, and from when.

This project is dual-licensed. The commercial licence in
[COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md) can only be granted by a party
that holds sufficient rights over the whole work, so the chain of authorship is
part of what is being sold. This file is the baseline that chain starts from.

---

## Baseline

**At the first commit in this repository's history — 14 August 2026 — every
file in it was authored by Garrett Bloome (rtome / KerbalTheGathering), the
Licensor.** No third party had contributed to, or held any right in, any part
of it.

The work was developed entirely on the Licensor's own equipment and own time,
in a personal capacity, outside the scope of any employment and outside any
invention-assignment or employer intellectual-property provision. No employer
time, equipment, facilities, or confidential information was used in its
creation.

This includes the material written in the voice of "a fork" —
[`docs/10_fork_report.md`](docs/10_fork_report.md) and
[`learnings.md`](learnings.md). Those forks were the Licensor's own working
copies and the reports are the Licensor's own; the framing is narrative, not an
attribution to another person.

No third-party code, assets, or documentation are vendored into this
repository. The models the pipeline drives — Krea2, MiniMax H3, WAN 2.1
InfiniteTalk, ElevenLabs — are called as external services or local
installations and are not redistributed here. Their terms bind the user, not
this repository.

## After the baseline

Every contribution merged after the initial commit is covered by the
[Contributor Licence Agreement](CLA.md), which grants the Licensor the right to
relicense it commercially (§3) while the contributor keeps their copyright (§5).
Contributions made in the course of employment additionally require
[CLA-ENTITY.md](CLA-ENTITY.md).

The CLA does not operate retroactively on anything that predates it. It does not
need to: at the baseline there was nothing to cover.

## A note on AI-assisted authorship

Much of this repository was written with AI assistance, and the fork reports
were produced by Claude Code sessions run by the Licensor.

No third party acquires rights through that — a model vendor is not an author,
and no other person contributed. But it does raise a separate question from
ownership: under current US Copyright Office guidance and *Thaler v. Perlmutter*,
material generated without human creative control may not attract copyright
protection at all, while human selection, direction, arrangement, and
modification do.

### The human contribution

The Licensor directed the selection and arrangement of this work throughout.
That direction is not incidental to the project; it is the project. It is
visible in the repository itself:

- **The architecture.** The separation of season, show, cold open and session
  template; the boundary at `identity.py` where model choices are isolated so
  they can be replaced; the ordering of the pipeline set out in
  [`docs/01_process.md`](docs/01_process.md).
- **The refusals.** Which failures are guarded against, where each guard sits,
  and what each one measures. `smoke.py`, `residue.py`, `contract.py` and
  `preflight.py` exist because specific artifacts rendered cleanly, exited 0,
  and were wrong. Selecting those failure modes, and deciding what constitutes
  proof against them, is human judgement; no model supplied the list.
- **The governing rule.** *A check that does not measure the delivered artifact
  is not a check* — stated in the README and imposed consistently across every
  module, which is an editorial decision about the whole.
- **The incident reports.** The comments record observed failures. They are
  testimony about what happened on this machine, to this work.

Copyright in the work as a whole — as a compilation reflecting that selection
and arrangement, together with the human-authored expression throughout — is on
considerably firmer ground than copyright in any individual generated passage
considered alone.

### What remains open

Compilation copyright is generally described as **thin**: it reaches the
selection and arrangement rather than automatically extending to every generated
line within them. Independent reimplementation of an architecture is in any case
outside copyright's reach under 17 U.S.C. §102(b), which excludes methods and
systems of operation regardless of who authored them.

This is unsettled and moving law, noted here because both halves of the dual
licence — the AGPL's copyleft and the commercial grant — are built on copyright,
and anything uncopyrightable is something neither half can reach. It is
mitigated substantially by the fact that the commercial licence operates as a
**contract**: an executed agreement binds the licensee to its terms
independently of the scope of copyright in any particular file.

A question for counsel alongside the CLA review, not a defect to be fixed in a
file.

---

Copyright © 2026 Garrett Bloome (rtome / KerbalTheGathering).
