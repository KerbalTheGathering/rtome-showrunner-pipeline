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

- **A ported shooter carries the last film's safest assumption.** The H3
  shooter anchors an audio driver on every beat -- silence where nobody on
  screen speaks -- because absent audio invites an invented voice. Port it
  into a film whose sound *is* what H3 invents and every beat comes back with
  a valid, silent audio track; the bake, the loudness stage and the length
  check all pass (fault 64). `season_identity.H3_DRIVER = False` hands the
  channel to the model. The tell was a per-beat level measurement on the
  delivered file: −90 dB on ten beats against −50 on three.

## Caching and file resolution

**A cache keyed on a filename will serve you the bug you just fixed.** Three
separate failures in one film: a segment cache keyed on index skipped a file
already on disk at the wrong length; a beat re-pointed to a different plate at
the same duration produced the same frame count; and three paid lip-sync passes
were bought against the *old* plate because the output filenames existed. **Key
every derived artifact on its RECIPE** — source name + size + mtime + in-point +
frame count — as a hash in the filename or a sidecar JSON. Duration checks
cannot detect a content swap.

**Caching by existence alone is a trap the moment an earlier run was a
rehearsal.** An assembly chain was validated end-to-end *before* the real
sources existed, using a documented placeholder path. That left a full set of
cached placeholder segments on disk. Every later run would have reused them and
delivered the rehearsal — correct length, correct order, every check green.
**Invalidate a derived artifact whose source is newer than it** (compare mtimes,
or the recipe hash above). A `--rebuild` flag you have to remember is not a
safeguard; the whole failure mode is that you do not remember.

**`_rej_` must be skipped explicitly by every selector, in every script.**
Renaming a reject to `10_foo_rej_tall_00001.png` does not merely fail to be
skipped — under a `stem.rsplit("_00",1)[0]` key it becomes *its own entity*,
survives frame prep as a separate item, and gets billed as a second clip for the
same beat, generated from the picture that was thrown out.

**A mode with its own output directory must derive that path ONCE.** `--plain`
existed so an A/B probe could never be resolved as a film plate, and its
docstring said so. The directory the poller *watched* appended the suffix; the
prefix the render *wrote* did not, because that line had been extended for
`--obj` and never for `--plain`. The probe landed in the film's plate directory,
where `plate()` takes the last file for that sid — so the probe became the plate
the film would be shot from. **Two failures at once, and only the harmless one
is visible:** what the operator saw was `NO OUTPUT after 20s`, i.e. a message
saying the render had failed, from a render that had succeeded into the wrong
folder.

So: **"no output" from a renderer that plainly ran is a path fault, not a render
fault, and the file is somewhere.** Look for the file before you read the log.
And when two expressions have to agree about a path, make them one expression.

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

**A split shot rendered on two canvas buckets ships an aspect jump at the
seam.** Each canvas bucket carries its own small aspect error and the bake
corrects it per clip — but an `NNx` continuation is conditioned on its
parent's tail clip, so a pair on different buckets compounds two different
squashes that no per-clip correction can see. Every clip is individually
right; the cut is wrong; everything renders clean (fault 81). `h3_shoot`
picks one canvas per parent/continuation pair, sized by the longer member.

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

**`fade=t=in:st=X` blacks everything BEFORE X; `t=out` everything AFTER.** A
chain of both at every part boundary on an already-joined stream produced ten
minutes of black that encoded to 1.7 MB and exited 0 (fault 59). `afade` is the
same. Fade each PART at its own ends before the concat -- `feature.py` does,
cached per part -- and look at a frame from the middle of the delivered file.

**A grid-search checker returns the least-bad point inside its grid, never "no
idea".** A drift detector reported `1.000 solid` for a clip that visibly pushes,
because the move was a zoom *plus* a translation and a centre-crop model cannot
represent that at any range. **Peg detection**: a winner sitting at either end
of the grid is the search running out of room, not a measurement.

**A labelled filter output nothing consumes is an ffmpeg error, not a no-op.**
`assemble.mix()` places a clip-audio label per beat on every bus; only
`diegetic` sums them, and the first `ducked` mix after that change died at
the end of a bake with the whole graph as the traceback (fault 65).
`mixes.bus()` now sinks whatever the bus leaves unconsumed. The general rule:
a graph builder that places inputs for some consumers must terminate them
for the rest.

**libass `force_style` margins are in the subtitle's own 384x288 units.**
`MarginV=190` on a 1920-high frame is not 190 px from the bottom, it is
190/288 of the height — the top third. Burned captions for a vertical
delivery: `MarginV=45`, `FontSize=12`, and look at the frame.

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

## Long batches, guards and a shared GPU

**An attention node can be accepted and inert.** A model-patch node that
uses the SD/DiT `attn1` hook does nothing to H3, which routes through
`optimized_attention_override`; the graph runs, the log says "applied", the
render is bit-identical (fault 61). Prove a kernel with a warm clock AND a
PSNR against the same graph without it; shoot the base twice first so you
know what zero looks like.

**A resident model family thrashes the next one.** A Krea2 plate re-roll or an
ACE-Step cue leaves its weights loaded; the next H3 pass sits at sampler 0/6
with VRAM pinned near the card's ceiling and "0 models unloaded" in the log --
the queue says "running" and nothing errors (fault 60). **Restart ComfyUI
before an H3 pass whenever another family has been loaded since**, and verify
the drop with `nvidia-smi`, not `/free`. (Different from the canvas-budget
thrash of fault 41: that one is too many tokens, this one too many families.)

**A guard that prevents corruption but permits deadlock is half a guard.** Four
copies of a batch tool ran at once, each correctly refusing to submit while the
render queue was busy — and each waiting on the others. GPU at 0 %, one stuck
job at the head, no output, and **nothing in any log to say why**. The guard sat
at the point of damage ("is this action safe") when the missing one was at the
point of entry ("should this process exist"). Put a **PID lockfile at process
start** on anything owning a GPU, a queue or an output directory — and **treat a
lock whose PID is dead as stale and take it over**, or every `kill -9` leaves a
file that stops the next run and becomes the thing you route around at 4am.

**A guard that can block forever is worse than no guard.** A free-VRAM floor was
copied from a stage that loads a small model to one that deliberately runs the
card nearly full and swaps. The wait was `while free < floor: sleep`. It stalled
on the third item and would have waited until morning having produced two.
**Bound every wait**, then proceed with a warning. It fails silently and looks
exactly like slow progress.

**A resource limit is a property of a stage, not of the machine.** The same
number was sensible in one stage and *below normal operation* in the next.

**Order a fallible batch by importance, not by identifier.** Numeric order put
the two most important shots in a film last; the run lost its budget to crashes
and would have kept only the least important work. Reordering mid-run recovered
one of them.

**Degrade to the next-best real artifact, not to nothing.** A missing clip fell
straight back to a held still — right for a shot that never rendered, wrong for
one that rendered fine and was awaiting a re-shoot. Keep the ladder explicit:
new take → previous take → placeholder.

**An intermittent crash you cannot prevent is one you plan around.** A model
that hard-aborted the server roughly one run in four, on *both* attention
backends, with no pattern. The answer is a supervisor that owns the server, not
just the job: health-check before each item, relaunch when it dies, **alternate
the backend after a crash** (whichever just died is the one not to pick again),
and run **one item per subprocess** so an abort costs one item and not the
batch. Hand-driving the same work lost an hour to three aborts; supervised, it
finished with zero failures. **And do not conclude a backend is at fault from
one crash** — the same abort hit both.

**Do not orphan a process on a shared GPU, and verify teardown with the driver.**
Three traps, none guessable:
- **`nohup cmd &` under a tool harness reports success while the child keeps
  running.** The completion notification describes the wrapper, not the process.
- **The PID from `Start-Process -PassThru` is not necessarily the listener.**
  Cross-check `netstat -ano` for the port, then walk parents for the tree.
- **An "unload models / free memory" endpoint returns 200 without releasing
  VRAM** — the allocator keeps its arena reserved. Only killing the process
  returns it. **`nvidia-smi` is the evidence; the API response is not.**

Guard teardown on an empty queue so you never kill someone's render, and prefer
an instance that already exists over starting your own.

**Check whether a file is already installed before downloading it.** A model
listed as "5.21 GB" upstream and "4.85 GB" locally was the *same file* —
decimal GB against binary GiB. Compare **exact byte counts**, and after any
download verify the bytes match and the container parses (a truncated or
HTML-error download is a valid-looking file of the wrong size).

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
