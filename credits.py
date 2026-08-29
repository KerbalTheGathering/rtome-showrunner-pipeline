"""THE END CREDITS: a roll, in the film's own face, joined as the last part.

Everything this film was made with belongs on screen once, by name -- the
pipeline, the models, and the people who trained the LoRAs the two painters
ARE. The dial is the whole idea of the film and two strangers on the internet
built both ends of it; a description-box mention is not a credit.

HOW IT JOINS. It is a PART, not a tail glued onto Act III: 1920x1080, 24 fps,
h264/yuv420p at the season CRF, with a sample-locked PCM mix beside it, so
parts.py can hand it to feature.py like every other part and the join's
dip-to-black lands on it too. Nothing about the films changes.

THE ROLL IS COMPUTED, NOT TIMED BY HAND. The block list below decides the
length: everything is laid out into one tall image, then scrolled past the
frame at SPEED px/second with a beat of held black at each end. Change the
text and the runtime follows.

    python credits.py              # render out/credits.mp4 + _work/credits.wav
    python credits.py --sheet      # one PNG of the whole roll, to proof-read
    python credits.py --no-music   # silent (the music needs ComfyUI up)

THE BLOCK LIST BELOW IS EXAMPLE CONTENT AND THIS FILE REFUSES TO RENDER WHILE
IT SAYS SO. Credits name PEOPLE. Every other example in this repo costs a
re-render when it ships by accident; this one credits a stranger for someone
else's work, or fails to credit the person whose LoRA the film is made of. So
`EXAMPLE_CONTENT = True` sits at the top, `preflight.py` refuses the season
while it is there, and main() refuses too -- delete the line when the list is
this film's.

ATTRIBUTION IS RESEARCH, NOT RECALL. A LoRA's .safetensors carries no author
field (checked: `ss_*` and `modelspec.*` keys have the base model, the
trigger and the training run, never a name). Whoever made it is on the page
you downloaded it from, and that is the only place to get it right from. A
wrong credit is worse than no credit.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import season_identity as season                                   # noqa: E402
import season_paths                                                # noqa: E402

# See the docstring: this file names people, so it fails loud until the list
# below is the film's own. Delete this line when it is.
EXAMPLE_CONTENT = True

OUT = os.path.join(HERE, "out")
WORK = os.path.join(HERE, "_work")
MUSIC = os.path.join(HERE, "_music")
W, H, FPS, CRF = season.W, season.H, season.FPS, season.CRF

# --- the roll -----------------------------------------------------------------
# THE ROLL. (heading, [lines]); `None` is a blank line, the layout's only
# spacer. A heading with no lines is a standalone title beat.
#
# EVERY REPLACEABLE STRING BELOW SAYS "EXAMPLE" OUT LOUD, and that is the
# point. `EXAMPLE_CONTENT`, preflight and main()'s refusal are three locks on
# the same door, but locks get picked: somebody will delete the marker to see
# what the roll looks like, render it, and move on. If that render ever
# reaches an audience it must be unmistakable rather than plausible -- a roll
# that reads "EXAMPLE CREATOR" is a mistake anybody spots in a frame, and one
# that reads like a real name is a mistake nobody spots at all. A placeholder
# that could pass for a credit is worse than no placeholder.
#
# The tool blocks are true of any film this repo assembles and are a
# reasonable default. The names are not: replace them, credit every LoRA and
# every voice by the name its creator publishes under, and delete
# EXAMPLE_CONTENT above.
AUTHOR = "EXAMPLE AUTHOR"        # replace: how your name should read on screen

CREDITS: list[tuple[str, list]] = [
    ("", ["EXAMPLE CREDITS -- REPLACE BEFORE RENDERING"]),
    ("", [season.SEASON_TITLE]),
    ("WRITTEN, DIRECTED AND CUT BY", [AUTHOR]),
    ("THE CAST", [
        "EXAMPLE CHARACTER  —  EXAMPLE VOICE",
        "EXAMPLE CHARACTER  —  EXAMPLE VOICE",
        None,
        "synthesised with EXAMPLE VOICE VENDOR"]),
    ("THE LOOK", [
        "EXAMPLE LORA — what it does in this film",
        "an EXAMPLE BASE MODEL LoRA by EXAMPLE CREATOR",
        None,
        "EXAMPLE LORA — what it does in this film",
        "an EXAMPLE BASE MODEL LoRA by EXAMPLE CREATOR"]),
    ("STILLS", ["EXAMPLE IMAGE MODEL"]),
    ("MOTION AND SYNC", ["EXAMPLE VIDEO MODEL", "run locally, on one GPU"]),
    ("SCORE", ["EXAMPLE MUSIC MODEL", "generated locally, cue by cue"]),
    ("FINISHING", ["Real-ESRGAN  ·  ffmpeg  ·  ComfyUI"]),
    ("ASSEMBLED BY", [
        "the rtome showrunner pipeline",
        "plates, direction, edit, mix, titles and join",
        None,
        "github.com/KerbalTheGathering/rtome-showrunner-pipeline"]),
    ("", ["Every likeness and every voice in this film",
          "is the author’s own or synthetic.",
          "No other person is depicted or cloned."]),
    ("", [season.SEASON_TITLE, "EXAMPLE YEAR"]),
]

# --- the look of the roll ------------------------------------------------------
INK = (238, 233, 222)            # bone, the thumbnails' ink and the card's
DIM = (150, 146, 138)            # headings sit back from their names
SPEED = 100                      # px/s: readable at 44px type, and 68s of
                                 # credits on a 10-minute film is not a
                                 # tribute, it is an exit queue
HEAD_PX, LINE_PX = 30, 44        # type sizes
GAP_HEAD, GAP_LINE, GAP_BLOCK = 16, 12, 62
LEAD, TAIL = 1.6, 2.6            # seconds of black before and after the roll


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    # The film's own display face, so the credits read as part of the film and
    # not as a different document. FONT_DISPLAY is Franklin Gothic Condensed.
    for name in ((["FRAHV.TTF"] if bold else []) + [season.FONT_DISPLAY, "arialbd.ttf"]):
        try:
            return ImageFont.truetype(os.path.join(season_paths.FONT_DIR, name), size)
        except OSError:
            continue
    sys.exit("FAIL: no display font for the credits")


def build_roll() -> Image.Image:
    """The whole crawl as one tall image, centred."""
    fh, fl = font(HEAD_PX, bold=True), font(LINE_PX)
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    y = 0
    for head, lines in CREDITS:
        if head:
            y += HEAD_PX + GAP_HEAD
        for ln in lines:
            y += (LINE_PX + GAP_LINE) if ln else (LINE_PX // 2)
        y += GAP_BLOCK
    roll = Image.new("RGB", (W, max(y, H)), (0, 0, 0))
    d = ImageDraw.Draw(roll)
    y = 0
    for head, lines in CREDITS:
        if head:
            tw = probe.textlength(head, font=fh)
            d.text(((W - tw) / 2, y), head, font=fh, fill=DIM)
            y += HEAD_PX + GAP_HEAD
        for ln in lines:
            if not ln:
                y += LINE_PX // 2
                continue
            tw = probe.textlength(ln, font=fl)
            d.text(((W - tw) / 2, y), ln, font=fl, fill=INK)
            y += LINE_PX + GAP_LINE
        y += GAP_BLOCK
    return roll


def seconds(roll: Image.Image) -> float:
    return LEAD + (roll.height + H) / SPEED + TAIL


def music(secs: float) -> str | None:
    """A cue of its own, in the coda's key: the film ends in D major."""
    # A CUE ON DISK IS REUSED. score.render() always submits, so a rebuild
    # with the cue already rendered died on a ComfyUI connection refusal
    # before reaching the part that needed fixing -- fault 100's second
    # trap, recorded on the mural film and never landed here (fault 116).
    # Delete the file to re-roll the music.
    have = os.path.join(MUSIC, "credits.mp3")
    if os.path.exists(have) and os.path.getsize(have) > 0:
        print(f"  (reusing {have} -- delete it to re-roll the cue)")
        return have
    import score
    # In the season's key family, and slow: an end title is the film letting
    # go, not a reprise of its loudest cue.
    cue = {"tags": "end title music, slow, warm, unhurried, valedictory, fading "
                   "to nothing, instrumental, no vocals",
           "bpm": 60, "key": "D major", "ts": "4", "seed": 4307}
    return score.render("credits", secs, cue, MUSIC, season.SEASON)


def example_lines() -> list[str]:
    """Every line still carrying the word EXAMPLE.

    THE SECOND LOCK, AND THE ONE THAT SURVIVES IMPATIENCE. Deleting
    `EXAMPLE_CONTENT` is one keystroke and somebody will do it to see the roll
    move; this reads the roll ITSELF, so a half-filled list -- the author
    replaced, the LoRA creators still EXAMPLE -- is caught by the thing that
    is actually wrong rather than by a marker somebody forgot.
    """
    out = []
    for head, lines in CREDITS:
        for ln in [head] + [x for x in lines if x]:
            if "EXAMPLE" in ln.upper():
                out.append(ln)
    return out


def main() -> int:
    left = example_lines()
    if EXAMPLE_CONTENT or left:
        why = ("`EXAMPLE_CONTENT = True` is still declared"
               if EXAMPLE_CONTENT else
               f"{len(left)} line(s) still say EXAMPLE")
        sys.exit(
            f"FAIL: credits.py is still the template's example roll -- {why}.\n"
            + "".join(f"    {ln}\n" for ln in left[:6])
            + "  Credits name PEOPLE. Fill CREDITS in with this film's own --\n"
              "  look every LoRA creator up on the page you downloaded the\n"
              "  weights from, because the file itself carries no author --\n"
              "  and delete the `EXAMPLE_CONTENT = True` line at the top.")
    roll = build_roll()
    n = int(round(seconds(roll) * FPS))
    # THE PICTURE OWNS THE LENGTH AND THE MIX IS CUT TO IT, to the sample.
    # Written the other way round first (wav = the float, picture = round(float
    # * fps)) and `-shortest` trimmed a frame off the video: feature.py's
    # mix-vs-picture check refused the part over 27 ms. A part's two streams
    # come from ONE number, and it is a whole number of frames.
    secs = n / FPS
    print(f"  {len(CREDITS)} blocks, roll {roll.height}px, "
          f"{secs:.1f}s at {SPEED}px/s ({n} frames)")

    if "--sheet" in sys.argv:
        os.makedirs(OUT, exist_ok=True)
        p = os.path.join(OUT, "credits_sheet.png")
        roll.save(p)
        print(f"  -> {p}")
        return 0

    os.makedirs(OUT, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)
    frames = os.path.join(WORK, "_credits_frames")
    # shutil, not `cmd /c rmdir`: spawning cmd raises FileNotFoundError on
    # any POSIX host (fault 115), and the stale frames it exists to clear
    # matter -- a previous longer run's c_%05d.png files are consecutive
    # with the fresh ones, and only -shortest was saving the mp4 from them.
    if os.path.isdir(frames):
        shutil.rmtree(frames)
    os.makedirs(frames, exist_ok=True)
    canvas = Image.new("RGB", (W, H), (0, 0, 0))
    for i in range(n):
        t = i / FPS
        im = canvas.copy()
        # the roll enters from the bottom edge after LEAD and leaves the top
        top = int(round((t - LEAD) * SPEED)) - H
        if -H < top < roll.height:
            box = (0, max(0, top), W, min(roll.height, top + H))
            piece = roll.crop(box)
            im.paste(piece, (0, max(0, -top)))
        im.save(os.path.join(frames, f"c_{i:05d}.png"))
        if i % 240 == 0:
            print(f"    drew {i}/{n}")

    wav = os.path.join(WORK, "credits.wav")
    mp3 = None if "--no-music" in sys.argv else music(secs)
    ff = season_paths.ff("ffmpeg")
    if mp3:
        # THE MIX OWNS THE LENGTH, exactly as every part's does: the music is
        # trimmed to the picture and faded, never the other way round.
        subprocess.run([ff, "-y", "-v", "error", "-i", mp3,
                        "-af", f"atrim=0:{secs:.3f},asetpts=PTS-STARTPTS,"
                               f"afade=t=in:st=0:d=1.2,"
                               f"afade=t=out:st={max(0.0, secs - 3.0):.3f}:d=3.0,"
                               f"volume=0.55,apad",
                        "-t", f"{secs:.3f}", "-ac", "2", "-ar", str(season.A_RATE),
                        "-c:a", "pcm_s16le", wav], check=True)
    else:
        subprocess.run([ff, "-y", "-v", "error", "-f", "lavfi", "-i",
                        f"anullsrc=r={season.A_RATE}:cl=stereo",
                        "-t", f"{secs:.3f}", "-c:a", "pcm_s16le", wav], check=True)

    mp4 = os.path.join(OUT, "credits.mp4")
    subprocess.run([ff, "-y", "-v", "error", "-framerate", str(FPS),
                    "-i", os.path.join(frames, "c_%05d.png"), "-i", wav,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(CRF),
                    "-c:a", "aac", "-b:a", "320k", "-shortest",
                    "-movflags", "+faststart", mp4], check=True)

    # ALIGN THE MIX TO THE DELIVERED PICTURE (fault 100, landed as fault
    # 116). On some roll lengths image2 muxes one frame fewer than were
    # drawn -- deterministically, so the join's "it is stale, rebuild it"
    # advice reproduces the mismatch byte for byte. The delivered mp4 is
    # the artifact that is hardest to rebuild honestly, so the wav is cut
    # to ITS frame count, sample-exact, and the picture is stream-copied.
    got = int(subprocess.run(
        [season_paths.ff("ffprobe"), "-v", "error", "-select_streams", "v:0",
         "-count_frames", "-show_entries", "stream=nb_read_frames",
         "-of", "csv=p=0", mp4],
        capture_output=True, text=True, check=True).stdout.strip())
    if got != n:
        print(f"  image2 muxed {got} frames of the {n} drawn -- cutting the "
              f"mix to the delivered picture")
        end_sample = int(round(got / FPS * season.A_RATE))
        trim = wav + ".trim.wav"
        subprocess.run([ff, "-y", "-v", "error", "-i", wav,
                        "-af", f"atrim=end_sample={end_sample}",
                        "-c:a", "pcm_s16le", trim], check=True)
        os.replace(trim, wav)
        remux = mp4 + ".remux.mp4"
        subprocess.run([ff, "-y", "-v", "error", "-i", mp4, "-i", wav,
                        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "320k",
                        "-movflags", "+faststart", remux], check=True)
        os.replace(remux, mp4)
        secs = got / FPS
    print(f"\n  {secs:.2f}s, {W}x{H} at {FPS}fps, {got} frames delivered")
    print(f"  MP4 {os.path.getsize(mp4) / 1e6:.2f} MB  -> {mp4}")
    print(f"  mix {os.path.getsize(wav) / 1e6:.1f} MB  -> {wav}")
    print("\n  feature.py picks it up as the last part; run it to rejoin.")
    return 0


if __name__ == "__main__":
    # -h/--help prints the docstring -- the usage has always lived
    # there; this makes it reachable without opening the file
    # (finding 146). Before main(), so no lock is taken and no
    # argument guard fires first.
    import sys as _hsys
    if "-h" in _hsys.argv or "--help" in _hsys.argv:
        print(__doc__ or "(no usage doc)")
        raise SystemExit(0)
    sys.exit(main())
