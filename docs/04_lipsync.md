# 04 — Mouths

Read all of this before changing anything in `show/`. Lip sync is the only place
in the pipeline where **the picture is a function of the audio**, which changes
what "close enough" means everywhere downstream.

---

## The arbiter: THE SILENCE TEST

> **Look at the mouth at frames of true silence.**

It needs no metric, no threshold and no tooling, and it is the only test that
has never been wrong. A mouth that moves under silence is the defect an audience
reads instantly — far more than a mouth that is slightly late under speech.

Everything below is in service of that.
---

## The standing rule: H3 with an anchored driver is the lip sync

**Every lip-synced plate is animated on local H3, with the on-screen lines
anchored as a driver at frame 0.** That is `_session_template/h3_shoot.py`
(the ref2va hybrid shooter, ninth season) and it is the only path a new
season should plan around. The operator's call, 2026-08-23: it is better and
faster than InfiniteTalk, and it does in one pass what InfiniteTalk needed a
base shoot, a clean bake, a sync pass and two proofs to do.

Why it works, in one sentence: H3 is omni-modal, picture and sound decode
from one latent, so **the mouth follows whatever audio is anchored** -- the
real VO where he speaks, and digital silence where he does not. Anchored
silence is the strongest "mouth closed" the model accepts; *absent* audio is
an invitation to invent a voice (fault 52). Details and the three faults that
shaped it are in "The ref2va shooter" below.

What a season declares:

- **`script.ON_SCREEN`** -- the set of roles whose lines go in the driver.
  Undeclared, every role is on screen (a single-character film). A narrator,
  a radio, a voice in his head are *not* in it: nobody in frame says them.
- **One voice, two registers = two roles on one id.** A character who talks
  on camera in some beats and narrates over others is `VOICES = {"gman": ID,
  "inner": ID}` with only `"gman"` in `ON_SCREEN`. `contract.py` accepts one
  id under two roles; what it refuses is a role with no lines.
- **A beat with nobody speaking still gets a driver** -- of silence. The
  shooter does this; do not turn `season.H3_DRIVER` off for a film that
  writes its words (fault 64 is the one film where it is off: its sound *is*
  the clips).

The silence test above is still the arbiter. `check_clip.py`'s filmstrip
lands with every clip; look at the mouth on the silent frames.

**InfiniteTalk (below) is the legacy path.** It is what the `show/` tree
still runs, because a talking desk needs 600-frame holds that H3 cannot fit
under the latent budget in one clip (`show/edit.BASE_CAP_F`). Porting the
show to H3 means cutting a long segment into continuation beats (`NNx`,
anchored on the parent's tail) -- designed, not done. A season that has no
show tree never touches it.

---

## The legacy path: WAN 2.1 InfiniteTalk (show tree only)

InfiniteTalk is **not a patch**. It generates the shot from the plate with the
audio as a driver, at the model's own resolution — so there is no mouth region
pasted over anything and nothing to feather.

It also fixes a second complaint for free: motion driven by speech lands where
the words do, and each segment moves differently because each says something
different. A locked-off shot generated from "a still and a sentence" has one
gesture vocabulary and reads as repetitive.

### The recipe (`show/italk.py`)

| | |
|---|---|
| UNET | `Wan2_1-I2V-14B-480p_fp8_e4m3fn_scaled_KJ` |
| patch | `Wan2_1-InfiniTetalk-Single_fp16` via `ModelPatchLoader` |
| LoRA | `lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16` |
| CLIP | `umt5_xxl_fp8_e4m3fn_scaled`, type `wan` |
| VAE | `Wan2_1_VAE_bf16` |
| audio encoder | `wav2vec2-chinese-base_fp16` |
| sampler | euler / normal / **4 steps** / **cfg 1.0** (the distill LoRA's numbers) |
| size | 768×576 |
| chunk | 81 frames at **25 fps**, `motion_frame_count` = **9** |
| `audio_scale` | **1.5** |

**Chunk arithmetic — get this wrong and the film is silently short.** Only the
first chunk yields 81 frames; every chained one re-decodes the motion frames it
was handed and contributes `81 − 9 = 72`.

```python
def chunks_for(n25):
    return 1 if n25 <= 81 else 1 + -(-(n25 - 81) // (81 - 9))
```

Dividing the target by 81 undercounts, and it undercounts *silently* — two
segments came back eight frames short, which is a tenth of a second of on-screen
type sitting on the wrong word. **Assert the frame count after every render.**

### Rules that are not obvious

- **Build the whole chain in ONE graph.** `previous_frames` is the *whole
  accumulated batch*, not the last few frames, because that is how the node knows
  where it is in the audio. Splitting across submissions means writing it to a
  video and reading it back, so every chunk re-encodes all its predecessors and
  the picture degrades down the segment. In one graph it stays a tensor.
- **`start_image` is the ORIGINAL plate on every chunk**, not the previous tail.
  That is what stops a six-link chain drifting off the character.
- **A fresh seed per chunk** (`seed + k*7919`). Reusing one correlates the noise
  between passes and lands the same micro-gesture every 3.24 s.
- **The fifth output is where a chained chunk's new frames begin.** Append from
  there (`ImageFromBatch` with `batch_index` from the node) or the join stutters
  every 3.24 s.
- **Choose the anchor frame deliberately.** The anchor's mouth becomes the
  segment's opening mouth, so a plate caught mid-vowel opens on an open mouth
  over silence — the exact defect this pass exists to remove, reintroduced by the
  anchor. Find a closed frame in the first ~60. Take it **early**: H3 pushes in
  ~6 % across a clip, so a late anchor starts the segment tighter and walks any
  drawn type off its target.
- **`audio_scale` is lip amplitude.** At 1.0 the silence test passes but the
  openings are small for someone selling something at volume. 1.5 shipped.
  **Put the decided value in the file, not in shell history** — re-rendering one
  segment without the flag rebuilds it with lips that move less than the five
  around it, and no assert catches that.
- **A glitched take is usually a SEED problem; a take that glitches the same way
  twice is not.** Hands fused at 13.2 s on one seed and webbed into a flipper at
  14.5 s on another. Two takes failing the same way means re-rolling is a
  lottery — give the failing thing a **conserved position and a job**, phrased as
  what stays rather than what must not happen, and name it as still true in the
  last frame.

---

## The driver is the contract

The wav handed to the model **is** the timeline the mouths were generated from.
Everything downstream must preserve it sample-for-sample.

- `italk.py` cuts the picture and the voice **in the same ffmpeg call**, from the
  same frame count, and writes `synced_XX.wav` beside `synced_XX.mp4`.
- `assemble.py` reads that wav, refuses if it is missing, and refuses if it is
  **older than the picture** (the render was re-rolled and the voice was not).
- A **sidecar wav, not a muxed AAC track** — an AAC track inside the intermediate
  puts an encoder priming delay between the render and the bake, which is exactly
  the class of shift this design exists to eliminate.
- 25 → 24 fps **does not retime anything**. `fps` drops frames to hit a rate; the
  wall clock is untouched, so the voice needs no compensation for the
  conversion, only the same end cut.

Shifting the picture against the voice by a whole number of frames is legitimate
and is done with `tpad=start=k:start_mode=clone` on the picture only — the tail
frames lost are frames of someone sitting still. Confirm the direction by
injecting a known shift into a segment that measures zero and checking the tool
recovers it (+3 f read as +125 ms, −3 f as −125 ms).

---

## What does not work, and why it is worth knowing

**Kling lip sync** does not track this voice at all: eight of ten frames at true
silence had the mouth open, half the peak-speech frames were shut, and it
repaints 42.6 % of the frame to do it. It also **picks one face per clip and does
not tell you which** — given a two-shot it animated the wrong man. That is not a
reason to avoid two-shots (a second pass drove the correct face, and the two-shot
was the better shot); it is a reason to treat its choice as unverified output.
Other Kling facts, if you use it anyway: video must be 2–10 s and 720–1920 px on
both axes; it returns a slightly different geometry and frame rate than it was
given (1440×1072 @30 fps for a 1440×1080 @24 input) and comes back ~0.03 s short,
so force geometry, rate **and frame count** back, using `tpad` to lengthen before
`-frames:v` cuts. It closes the mouth through leading silence even when the
source was talking, so head-padding works.

**Wav2Lip** does track the voice and rebuilds the mouth from a 96×96 crop. The
verdict on it was "it's not clean".

---

## H3 invents dialogue, and an invented voice moves the mouth

MiniMax H3 is **omni-modal**: picture and sound decode from one latent through
two VAEs. Undirected audio does not come back silent, it comes back *invented* —
and a character with an invented voice has a moving mouth.

Verified by transcribing the AAC track with Whisper.

**A prohibition does not fix it.** "No voice, no dialogue, no whispering" bought
mumbling. What fixes it is occupying the channel:

> AUDIO — The soundtrack of this clip is one continuous quiet room tone and
> nothing else, at the same steady level from the first frame to the last: fine
> rain, the small sounds of the building, and still air. That flat ambience is
> the entire soundtrack and it never stops, never changes and is never
> interrupted.

Also check the **still** prompt. Four motion takes were faithfully conserving an
open mouth because the plate prompt said "speaking directly out toward the
camera". Fix it upstream, at the plate.

### The ref2va shooter: anchor a driver, always, and never a voice reference

`_session_template/h3_shoot.py` (ninth season) shoots every beat on the ref2va
hybrid with the plate AND a driver track anchored at frame 0 through
`MiniMaxH3AddGuide`. Three rules, each a fault:

- **A beat where nobody on screen speaks still gets a driver -- of silence.**
  Shot with no audio anchored, a radio-only beat invented a voice and mouthed
  the radio's line; the beat whose driver was `anullsrc` until his one word
  kept his mouth shut to the second (fault 52). Anchored silence is the
  signal; absent audio is an invitation. `ON_SCREEN` (from `script.ON_SCREEN`)
  says whose lines go in; a narrator, a radio, a voice in his head do not.
- **No voice reference alongside the driver.** `<Audio 1>` wired together with
  an anchored driver crashes the sampler on an audio-row mismatch (fault 51).
  The driver is his voice wherever he speaks; `season_identity.H3_VOICE_REF`
  is recorded, not wired.
- **Identity references are for the character ALIVE in frame.** On a plate
  where he is a poster, the references animated the poster and then cut to
  the hero plate as a new scene (fault 53). `norefs` on the beat.
- **A reference is a FACE, not a scene.** A ref cut with 60% scene -- a
  legible sign, a vehicle, a sky -- was CUT TO mid-clip in beats of other
  films, and the transition frames read as attention artifacts (fault 70).
  Tight head crop, minimal background, nothing readable in it.

---

## Measuring a mouth (and why the number lied twice)

`show/mouth_open.py` scores aperture with insightface `buffalo_l`,
`landmark_2d_106`, mouth indices 52–71, as **aperture ÷ that clip's own resting
aperture**. The ratio matters — absolute aperture varies with framing.

Two failures worth carrying:

1. **A ranking without a control is not a ranking.** The metric called a take
   "flattest" at 1.63× and it was visibly talking. Only a control drawn from
   provably-still beats (1.11–1.32×) revealed the scale.
2. **The metric collapses on treated footage.** Under the CRT pass (which
   includes a roll), correlation against a known reference fell from 0.47–0.59 on
   clean renders to **0.07–0.23**. A reading of "250–500 ms late" taken from that
   was noise. The same trap caught a *different* metric later in the same build:
   a per-frame motion-energy correlation confidently identified the wrong picture
   source, and its control — the two candidates being uncorrelated with each
   other, r = 0.02 — proved only that it *could* discriminate on clean footage,
   not through the treatment.

**Validate a proxy on the treated artifact, not the clean one.** When a proxy
disagrees with a build log, look at two frames before believing either.

### The eye is the documented path; the metric is the optional confirmation

`insightface` is **not installed on a normal box**, and `mouth_open.py` is the
only thing in this repo that wants it. Its own docstring says the number is not
believed until it agrees with the eyes — so do the eye half first, and treat the
metric as a second opinion you may not be able to get:

1. Crop the first ~30 frames of `_work/clean_<sid>.mp4` to the face.
2. Tile them.
3. Pick the most closed, most square-on frame. That is `italk.START_FRAME[sid]`.

Two minutes per segment, no dependency, and it is what the metric is validated
*against*. `_probes/_open_strip.py` draws exactly this strip for every segment
with the first-speech frame marked, which is the version to run if the segments
are already synced.

**`START_FRAME` and `SHIFT` ship empty and must stay that way until you have
measured your own takes.** They are per-take measurements keyed by segment id,
and a segment id resolves in every season — a filled-in table inherited from
another reel anchors your first segment on somebody else's most-closed frame,
which is an arbitrary frame of yours. A measured number and a copied one look
identical in a file, so the empty state is the honest one.

**When a comment records a number measured on *this* season's takes, say so in
the comment.** The next clone cannot tell the difference otherwise, and that
ambiguity is the whole fault.

---

## Two speakers

**The script side is done and the render side is not.** Those are different
problems and it is worth being exact about which is which, because the first
costs nothing and the second costs a day.

### What works now

`identity.VOICES` is a table of **role → voice id**, and `script.LINES` names a
role rather than an id. So:

- **Any number of speakers in a script.** Two people in one beat is two lines
  with the same `sid` and different roles. `edit.py` lays them out in order with
  `extra` between them; `make_vo.py` renders each in its own voice and reports
  per-role totals; `script.speakers(sid)` says who is in a beat.
- **Off-camera speech is unrestricted.** A caller, a voice from the next room, a
  station announcement, a second narrator — none of that touches lip sync, and
  all of it works today.
- `contract.py`'s `cast` check catches a role with lines and no voice, a voice
  id with no lines (the previous film's actor, left in the table), and an empty
  id before it reaches the API.

The old model was `VOICE_ID` plus `VOICE_ID_2` with `assert len(guest_lines)
<= 1` welded into `script.py`. That cap was one film's editorial decision living
in the template's machinery; it is now `LINE_CAP`, declared per role by the
season that wants it.

### What does not work: two mouths moving in one shot

`italk.py` generates **the whole frame** from **one** audio driver. There is no
per-region drive, so a two-shot in which both people talk cannot be produced by
running it once. Two routes exist and **neither has been run on this stack**:

| route | what it needs | the risk |
|---|---|---|
| **Two passes and a composite** | run `italk.py` per speaker with that speaker's audio, then composite the two face regions with a mask. `_probes/it_sync.py`'s `boxes()` already finds the face boxes | InfiniteTalk regenerates the **whole shot** from the anchor, so the two passes differ everywhere, not just at the mouths. The composite seam is across a moving painted surface, which is the hardest kind |
| **The InfiniteTalk *Multi* patch** | `Wan2_1-InfiniteTalk-Multi_fp16.safetensors`, which is already on disk and unused. It takes per-speaker audio and per-speaker regions in one graph | unproven here. The single-speaker graph in `italk.py` took a day of measurement to get right, and none of that transfers to a node with a different input contract |

**The Multi patch is the one to try first** — it is the route that does not
require solving a compositing problem the model is actively working against, and
the model file is already sitting there.

### `show/italk_multi.py` — written, unproven, and safe to try

The Multi graph **is** in this repo, and **nothing in it has ever been run.** The
word UNPROVEN is at the top of the file and should stay there until somebody
deletes it because they watched a take.

A graph written against a node nobody has run is normally a file that looks like
a capability and is not one — this codebase has already paid for one of those
(`qc_feature.py` iterated attributes `feature.py` had not had for months, and
nothing noticed, because a checker that cannot run has never disagreed with
anything). Three things stop this being that file:

1. **It cannot submit a graph it has not checked.** Every run begins by asking
   the live ComfyUI what `WanInfiniteTalkToVideo` actually accepts
   (`/object_info`) and comparing it to the four guessed names in `ASSUME`. A
   mismatch prints what was assumed, what the node has instead, and *why we
   thought so* — then refuses. If `audio_encoder_output_2` is the missing one,
   it says outright that this whole approach is wrong and points at the
   two-pass route above.
2. **It writes `synced_multi_XX.mp4`, never `synced_XX.mp4`.** `assemble.py`
   reads the latter, so an unproven experiment cannot reach a bake by accident.
   Promoting a take is a rename you do yourself, after looking at it.
3. **`--dry` builds and structurally audits the graph without submitting** —
   dangling links, orphan nodes, no output. That will not tell you the picture
   is right, but when the first render fails it tells you whether to look at the
   graph or at the model.

**What was verified without a GPU, because it could be:** the per-speaker
driver tracks (`role_track()`) and the region masks. Both are exercised in the
docstrings' own terms and both had to be, because the first version of
`role_track` produced a **7.29 s track for a three-line role and a 2.65 s track
for a one-line role in the same segment** — the obvious `apad,atrim` spelling,
right answer for one input count and wrong for the other. Two files that both
existed and both played, one of them a driver two-thirds too short. It was found
by measuring where the energy in each track actually was; nothing else would
have found it.

**Each driver must run the whole segment.** A track that stops when its speaker
stops leaves the model unsignalled for the rest of the shot, and an unoccupied
mouth fills itself — the same failure this document records for undirected audio,
pointed at a speaker instead of at a shot.

**Who is where in the frame is set by eye** (`SPEAKER_RECT`) and there is no
honest way around it. `surface.py` finds a flat area of one colour, which a face
is not; a face detector would tell you where the faces are without telling you
*which one is which*, and getting that backwards produces a shot where both
people speak each other's lines — which reads as a sync failure rather than a
casting one and sends you looking in the wrong place for a day.

**The standing test applies unchanged and now applies per speaker:** at true
silence, every mouth in the frame is closed, judged by eye on the frames before
*each* speaker's first word. A two-shot where one mouth is right and the other is
chewing is worse than the single-speaker take it replaced.

---

## The two checks that must run before publishing a synced part

```
python which_source.py    # is the bake actually from the synced render?
python sync_probe.py      # does the delivered voice match the driver?
```

`which_source.py` is honest about its own limits — read its docstring. The
reliable version of that question is a **visual A/B of the mouth and the hands
at three frames**, against both candidate sources. It takes a minute and it is
never ambiguous.
