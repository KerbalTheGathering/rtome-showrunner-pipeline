"""Plate-versus-clip contact sheet, with the aspect handled correctly.

WHY THIS IS A FILE AND NOT A ONE-LINER EACH TIME. The plates are 2432x1664 =
1.4615 and the clips come back 1112x834 = 1.3333, and the obvious way to build a
comparison sheet -- resize both to the same cell -- SQUASHES THE PLATE and makes
every figure in it look taller and smaller than the clip beside it. That read as
a camera push-in on Session #4's two-shot, which is the one fault that would
have meant re-buying a beat that cannot be re-rolled for free. It was my sheet,
not the clip.

So the plate is CENTRE-CROPPED to the clip's ratio first, which is exactly what
Seedance does to it on the way in. What is compared is then what the model
actually saw against what it actually returned.

    python qc.py              # every beat that has a clip
    python qc.py 07 08 14     # just these
"""

import glob
import os
import subprocess
import sys

from PIL import Image, ImageDraw

# THE SEASON ROOT, THEN THIS TREE. `import edit` puts season_paths in
# sys.modules and that is NOT the same thing as putting it in this module's
# namespace: every use of season_paths below was a NameError, in three copies
# of this file, on the first frame anybody tried to shoot. smoke.py exists
# because nothing else in the repo could see it.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import season_paths  # noqa: E402
import framing     # noqa: E402  (the film's own crop, not a fresh one)
import edit        # noqa: E402
import identity    # noqa: E402  (the delivery aspect)
import gen_still   # noqa: E402
import shot        # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
TMP = os.path.join(OUT, "_qcframes")
CLIPS = os.path.join(season_paths.COMFY_OUTPUT, f"{shot.NAME}_clips")

# THE COMPARISON CELL IS THE SEASON'S ASPECT, DERIVED. It was `560, 420` --
# 4:3 typed into the one tool whose entire docstring is about not squashing a
# picture into the wrong ratio.
TW = 560
TH = round(TW * identity.season.H / identity.season.W)
AT = (0.5, 0.9)      # fractions of the beat to sample, as well as frame one


def clip_for(sid: str) -> str | None:
    got = sorted(f for f in glob.glob(os.path.join(CLIPS, f"s{sid}_*.mp4"))
                 if "_rej_" not in os.path.basename(f))
    return got[-1] if got else None


def frame(path: str, t: float, dst: str) -> str:
    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                    "-ss", str(t), "-i", path, "-frames:v", "1", dst],
                   check=True)
    return dst


def main() -> int:
    want = [a for a in sys.argv[1:] if not a.startswith("-")] or list(shot.CUT)
    have = [s for s in want if clip_for(s)]
    if not have:
        sys.exit(f"FAIL: no clips yet in {CLIPS}")
    os.makedirs(TMP, exist_ok=True)

    cols = 1 + len(AT)
    sheet = Image.new("RGB", (TW * cols, (TH + 20) * len(have)), "black")
    d = ImageDraw.Draw(sheet)
    for i, sid in enumerate(have):
        y = i * (TH + 20)
        # THE PLATE AS THE FILM WILL FRAME IT. This read
        # `assemble.fit_aspect`, which was a centre crop and nothing else --
        # so a film that crops to the top was reviewed on a picture nobody
        # would ever see. It is identity.FIT now, with this beat's own
        # override if shot.FIT_BEATS gives it one, out of ../framing.py.
        # (In show/qc.py it was worse than wrong: assemble.py in this tree has
        # no fit_aspect at all, so the line was an AttributeError.)
        plate = framing.apply(
            identity.FIT, Image.open(gen_still.plate(sid)).convert("RGB"),
            TW, TH, dict(identity.FIT_OPTS,
                         **getattr(shot, "FIT_BEATS", {}).get(sid, {})))
        sheet.paste(plate, (0, y + 20))
        d.text((6, y + 5), f"{sid}  PLATE ({TW}x{TH} crop)", fill="white")

        c, dur = clip_for(sid), edit.SECS[sid]
        for j, fr in enumerate(AT):
            t = dur * fr
            im = Image.open(frame(c, t, os.path.join(TMP, f"{sid}_{j}.png")))
            # THE CLIP THROUGH THE SAME FIT AS THE PLATE (fault 136). The
            # plate side was fixed to framing.apply and the clip side kept
            # a bare resize into the season-aspect cell -- on any season
            # whose clips are not already that shape (Seedance is pinned
            # 4:3) that is the docstring's own fault reintroduced on the
            # right-hand columns: a distortion of my sheet, not the clip.
            im = framing.apply(
                identity.FIT, im.convert("RGB"), TW, TH,
                dict(identity.FIT_OPTS,
                     **getattr(shot, "FIT_BEATS", {}).get(sid, {})))
            sheet.paste(im, (TW * (j + 1), y + 20))
            d.text((TW * (j + 1) + 6, y + 5), f"{sid}  CLIP {t:.1f}s of {dur}s",
                   fill="#ffdd99")

    dst = os.path.join(OUT, f"qc_{'_'.join(have) if len(have) < 5 else 'all'}.png")
    sheet.save(dst)
    print(f"  {len(have)} beat(s) -> {dst}  ({sheet.size[0]}x{sheet.size[1]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
