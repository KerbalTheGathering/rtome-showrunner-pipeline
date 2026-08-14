# 08 — The season this came from

Every number and rule in these documents was measured on one finished season.
This page says what that season was, at the level of detail that is useful to
you — its shape, its stack, and the decisions it made — without reproducing its
content. The films themselves are not part of this repo.

---

## Shape

Six short films of about two minutes each, plus a wordless cold open and six
interstitials. **861 seconds / 14.4 minutes, thirteen parts, 1440×1080, 24 fps,
about 16,000 frames of picture.**

A recurring character takes a job in each film; each job goes wrong in a
different way. The films move geographically across the season, and the last one
breaks the format the first five establish — which is the slot the whole
structure is paying for.

The wraparound was a cheap local television show: a presenter behind a desk in
front of a felt letterboard, announcing the job you were about to watch fail.
One interstitial in front of every film.

## Stack

| Job | What was used |
|---|---|
| plates | Krea2 in ComfyUI, 1216×832 latent → 2432×1664 |
| style | one gouache/watercolour LoRA @ 0.85 — **no trigger word**, because the tensors were unet-only |
| character | one character LoRA @ 0.90 |
| motion | MiniMax H3, **local and free**, with a 6-step turbo LoRA (euler / beta57 / 6 steps). Measured better than the 20-step baseline as well as cheaper |
| lip sync | WAN 2.1 InfiniteTalk, local — see `04_lipsync.md` for the full node list |
| narration | ElevenLabs `eleven_v3` |
| music | ElevenLabs music endpoint |
| paid video, where used at all | Seedance 1.5 Pro (~$0.30/clip, first-frame only), Luma Ray 3.2 (can place the plate last or mid-clip), Kling lip sync (~$0.14/call, **rejected** — see `04_lipsync.md`) |

Hardware: RTX 4090 / 24 GB, 16-core CPU, 128 GB RAM, NVMe. torch 2.9.0+cu130
with SageAttention 2.2 (2.95× over SDPA). Python 3.13 caps you at the torch-2.9
wheel, and the wheel *named* for torch 2.10 is mislabelled.

**Almost all of it was local and free.** The paid surface was narration (~1 % of
an ElevenLabs Pro month per film) and a small number of partner video calls.

## The show layer, specifically

Worth reading even if your wraparound is nothing like it, because the
constraints generalise.

- **The type is drawn with PIL at bake resolution**, line by line, each line
  appearing at the offset of the VO line that says it — taken from
  `edit.offsets()` so the board and the voice cannot disagree — and appearing as
  a **hard cut**, not a fade. Somebody is slapping letters onto felt; a dissolve
  would make it a graphic. The plate is generated with the board deliberately
  blank.
- **The television is a signal chain, not an overlay** (`show/crt.py`):
  bandwidth-limited luma and chroma, lifted black, bloom, tube curvature with
  black corners, scanlines, aperture grille, rolling hum bar. A light touch is
  *invisible* — 5 % scanlines at 1440×1080 read as nothing, and the segments
  came out looking like the same painted illustration as the films, only
  brighter.
- **A phosphor triad is chroma, and `yuv420p` eats it.** Judge fine tube
  patterns at 1:1 only. Draw the cabinet *around* the picture, not over it.
- **The last interstitial has an empty board** and needs no special case: its
  `BOARD_TYPE` is an empty tuple and the drawing loop has nothing to iterate.
- **The share cut is a lanczos downscale**, and that matters more than usual: a
  2.25-pixel scanline is 0.44 cycles/pixel, far above what survives a halving,
  so a naive scaler folds it back as moiré crawling over the presenter's jacket.

## Decisions worth stealing, or deliberately not

- **One narrator doing every voice.** Cheap, coherent, and it makes the show's
  host a deliberate exception rather than one voice among many.
- **A refrain composition closing every film.** Spent once per film, at the end.
  Opening on it made the bookend read as a default.
- **Alternating register between films** so the running order has a shape.
- **The last film breaks the format.** Everything else exists so that lands.
- **Shoot locally first, always.** The local model was measured against the paid
  one and won on quality as well as price. The paid vendors were kept for the
  specific thing each does that the local one cannot — see `05_prompting.md` on
  choosing a vendor by *where the plate sits in the clip*.

## Film grain, if you use it

The reference season did **not** grain its films — it used a per-beat sharpen
for one stock that arrived softer than the rest, gated on a measured width
threshold (`02_traps.md` explains why that threshold has to be measured rather
than guessed). But the grain numbers were measured on a sister project and are
worth carrying:

- Grain goes on **last, over the whole joined picture**, in one pass. Three
  picture sources graded separately means every cut announces where it came from.
- **Luma only** (`noise=c0s=N:c0f=t+u`) and **temporal**. Real grain is silver
  halide, not dye; chroma grain reads as video noise from the wrong decade, and
  static grain reads as dirt on the lens.
- Grain is maximally incompressible, so **choose the CRF by measuring grain
  survival, not file size.** Measured on a held still, where all inter-frame
  difference is grain by construction:

  | CRF | grain surviving | size |
  |---|---|---|
  | 21 | 100 % | 250 MB |
  | 23 | 76 % | 92 MB |
  | 25 | 47 % | 28 MB |
  | 27 | 6 % | 15 MB |

  **23 is the knee.** Never "fix" the size by lowering the grain constant
  instead — at 27 the film is effectively ungrained while still carrying a
  `noise` filter in the chain, which looks like the filter is doing its job.

---

## Claims about the real world

The reference season touched real places, one real occupation, and — at the
level of *premise only* — one real person and one real animal. None of that
reached the screen, and the way it was kept off the screen is the part worth
copying:

- **A real person is not a character.** Where a premise came from someone real,
  the film invented the name, the face and every line, and asserted that in code
  rather than in a note.
- **An invented name is not automatically safe.** A name that sounds regionally
  right is exactly the kind that belongs to a real person or firm in that
  region. Check what you invented.
- **Where a film touched a real event in which something was harmed**, it named
  nothing, blamed nobody, quoted nobody and used no adjective — and the script
  asserted the absence of the name, so the constraint could not be edited away
  by someone who did not know it was there.
- **You are unreliable about what currently exists.** Any claim of the form "X is
  still there" must be verified before it goes into a prompt or a line.
  Historical detail is much safer than present tense.

If you clone this for anything touching a real person, place or event: **put the
constraint in an assert, not in a comment.** A comment is a hope; an assert is a
build failure.
