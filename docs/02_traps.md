# 02 — Failure modes that render clean

Every entry below produced a finished, playable file that was wrong. None of
them raised an exception. Read this before debugging anything, because the
symptom is almost never where the fault is.

---

## The class

**Nothing in generative video fails loudly.** A wrong picture source, a frozen
zoom, a stale cache, a 150 ms offset and a mouth moving under silence all encode
identically to correct work. So the pipeline is built out of *refusals*: guards
that stop the build when an invariant is violated, because there will be no
other signal.

Corollary: **a guard that fails open is worse than no guard**, because it
reports success. A bare `except: return []` in a missing-glyph checker turned an
AttributeError into "no missing glyphs" for every font, and a tofu box shipped in
a finished video where the user found it.

---

## Identity and cloning

**A correctness-critical source must never be an opt-in flag.** `assemble.py
--synced` read the lip-synced render; without it, `bake()` fell back to the raw
un-synced clip. Same plate, same length, same framing, same frame count. Six
interstitials shipped that way through three rebuilds, and the user's report was
*"the audio is out of sync"* — which sent two days into the audio chain while the
film contained the wrong picture. **The good output is the default; the fallback
must be asked for out loud** (`--raw`), and the delivered file gets checked
(`show/which_source.py`).

**Identity typed in five files produces four silent bugs.** Title cards naming
the wrong film; output written to another film's filename; a stale duration
table producing a confident "buy longer clips"; a transition name with no
implementation falling through to the previous season's device. Fixed
structurally: `identity.py`, imported everywhere, hard-failing when blank.

**An unimplemented branch must fail, not fall through.** `else: portal_in` is
how one season rendered another season's device. Enumerate and `sys.exit` on the
unknown.

**A missing table entry that crashes *after* the balance check costs money.**
Validate the whole plan before the first submission.

**A short NAME reused between seasons silently eats the older season's clips.**
Every generator writes to `<ComfyUI>/output/<NAME>_clips`, and NAME is a word
like `INTRO` or `GROVE` — exactly the kind of name a second season reuses. The
new build then reads the old clips, coherently, and makes the wrong film.
`season_identity.claim_clips()` stamps a `.season` file into a folder it creates
and refuses one stamped by a different season. **Found by this template's own
test clone** — and the first version of the guard *stamped* an already-populated
folder, writing this season's name into the reference season's data. A guard
with a side effect on data it does not own is not a guard: it now warns and
writes nothing.

---

## Caching and file resolution

**A cache keyed on a filename will serve you the bug you just fixed.** Three
separate failures in one film: a segment cache keyed on index skipped a file
already on disk at the wrong length; a beat re-pointed to a different plate at
the same duration produced the same frame count; and three paid lip-sync passes
were bought against the *old* plate because the output filenames existed. **Key
every derived artifact on its RECIPE** — source name + size + mtime + in-point +
frame count — as a hash in the filename or a sidecar JSON. Duration checks
cannot detect a content swap.

**`_rej_` must be skipped explicitly by every selector, in every script.**
Renaming a reject to `10_foo_rej_tall_00001.png` does not merely fail to be
skipped — under a `stem.rsplit("_00",1)[0]` key it becomes *its own entity*,
survives frame prep as a separate item, and gets billed as a second clip for the
same beat, generated from the picture that was thrown out.

**An unquoted glob after `ffmpeg -i` destroys the second match.** ffmpeg's
grammar is positional, so `ffmpeg -i "$B/s09_"*.mp4 ... out.png` takes the first
path as input and the second — an accepted take of a published film — as an
*output* and re-encodes over it. Exit code 0. `2>/dev/null` made it silent, and
it surfaced 20 minutes later as an edit error. **Never glob into an ffmpeg
argument list, and never discard stderr on a command that writes files.**

---

## Thresholds, selectors and grades

**A threshold meant to separate two populations must be measured between them.**
"Sharpen any beat arriving under 85 % of bake width" caught *both* stocks (752 px
and 1024 px against a 1440 px bake) and unsharped all 2814 frames. It rendered
clean. Two rules: measure the populations before choosing the line, and **decide
the per-item treatment before the loop, print the measured values and the
resulting set, and hard-fail if the set is everything.** A count printed after a
twenty-minute bake is a report, not a guard.

**A per-shot override that only one code path consults is a silent no-op.** A
framing window honoured on the zoom path but not the hold path rendered
plate-centred with no error anywhere.

**A guard that refuses in only one direction is the wrong shape.** A score
fitter that would speed a cue up but refused to slow one down treated "2 % short"
and "half as long" as the same fault.

**A colour constant tuned on a PNG export will not transfer to the video chain.**
Still export ends in full-range RGB; the video chain carries limited-range luma.
A levels stretch tuned on a test frame landed on the 16 floor and simply
multiplied the sky. Do tonal work in `lutrgb` (always 0–255) and **verify by
measuring the render, not the test still.**

**A vignette tuned on a wide frame is far stronger on a tall one**, and the
statistic that diagnoses it is measuring the **centre separately**: a darkening
that spares the centre and eats the edges is a vignette, not a level error.

---

## ffmpeg specifics

**`crop` cannot zoom.** `w`/`h` are evaluated once at filter configuration; only
`x`/`y` refresh per frame. Interpolating crop dimensions produces a frozen still
that renders clean, exits 0, and **encodes to almost exactly the size of a real
slow move**, so file size cannot tell you. Pans use `crop`; zooms use `zoompan`.

**`xfade` does not run its inputs in parallel.** It passes A through until
`offset`, then starts B from B's frame zero — so a camera move under a dissolve
blends two different zoom levels, and the output is `secs + offset` long. **The
test: crossfade the same image with itself.** In step it is exactly as sharp as
a plain render; out of step it is visibly soft (measured Laplacian variance
491.0 plain / 242.7 xfade / 491.1 blend). Use
`blend=all_expr='A*(1-k)+B*k'` with an explicit `k` ramp.

**`atrim` can only shorten, and `-shortest` will then amputate the picture.** A
narration-only mix ending 3.3 s short of the picture truncated the *video* and
silently removed the end card — while the picture-vs-cut check passed, because it
measured the silent intermediate. **`apad` before `atrim`, and check the
delivered file.**

**A grid-search checker returns the least-bad point inside its grid, never "no
idea".** A drift detector reported `1.000 solid` for a clip that visibly pushes,
because the move was a zoom *plus* a translation and a centre-crop model cannot
represent that at any range. **Peg detection**: a winner sitting at either end
of the grid is the search running out of room, not a measurement.

---

## Type and text

**Generated lettering comes back as garbage.** Anything that must be spelled
correctly is drawn with PIL at bake resolution, over a plate deliberately left
blank. Ask a model for *blank stock* and typeset it yourself.

**"Empty" cannot be requested by negation.** A prompt asking for an empty column
produced a plausible invented catalogue number in exactly that cell. Compose
around blanks, or clear the cell in post by pasting clean stock from the same
plate — and make that repair *find* its target and hard-fail if the plate does
not match, so it cannot erase the wrong row of a re-roll.

**A generated form will invent an identity.** A stamp card came back naming a
stranger as the applicant and contradicting its own stamp, in fields that were
not in the prompt. Enumerate every line of type you want and read back what the
model added.

**Fonts silently lack glyphs.** Candara, Constantia, Trebuchet and Georgia all
lack U+2192. **Draw an arrow; never typeset one.** And an invisible character in
source is lossy — one copy of a file survived a bare private-use character and a
second copy written minutes later turned it into an empty string, which would
have made the glyph detector vouch for every font. Use escapes.

---

## Patching and tooling

**A patch script that does not assert is the same bug as a guard that fails
open.** One patch used an asserting `swap()` for most substitutions and two bare
`str.replace()` calls for the rest; both matched nothing, reported nothing, and
the guard they were adding was never wired in. Everything printed PASS.
**Every substitution asserts its target exists and is unique** — `patch_*.py` in
this template all do, and they refuse ambiguous anchors rather than guessing.

**Prefer one choke point to per-site checks.** Validating every drawable string
in a `preflight()` cannot be forgotten at a new draw site; a `safe()` call at
each site is only as good as whoever added the last one.

---

## Claims about the world

**Never count a subject off a contact sheet.** "Three ospreys" was four — two
birds had merged into one on a 980 px review thumbnail. Verify at native
resolution, in the crop that ships.

**A spoken number is a claim about a picture that did not exist when the script
was written.** "Eleven people, if you count the egrets" played over a plate with
six in chairs and three egrets. Nothing in a pipeline that derives durations
from audio ever compares a spoken number to a frame. **After the plate lands,
re-read every line that asserts a number, a colour or a position.**

**A client deliverable must not carry the user's own voice or face**, and the
guard belongs in code, not in a note.
