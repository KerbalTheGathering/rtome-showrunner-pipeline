"""Getting a picture of one shape into a frame of another, without assuming.

WHY THIS IS A FILE. `assemble.py` carried `fit_aspect()`, which centre-cropped.
That is the right default and it was the only answer: the crop was `(sw - cw) //
2`, a literal 2 in the middle of an expression, and there was nowhere to say
otherwise. A film whose subject sits low in a taller plate lost its subject, and
the fix was to edit the assembler -- which is shared by every season that ever
clones this template.

It also could not pad. A vertical delivery cut from horizontal plates has to
choose between losing most of the frame and putting bars on it, and the template
could only do the first.

THE THREE ANSWERS, and they are the only three there are:

    crop      fill the frame and lose the overflow      (the default)
    pad       fit the whole picture, bars in the rest
    stretch   distort until it fits

`stretch` is in the library because a library that refuses to name the wrong
answer makes people implement it themselves, somewhere worse. It is never right
for picture. It is occasionally right for a graphic that was authored to the
wrong ratio.

THE ANCHOR IS WHERE THE KEPT PART COMES FROM, as fractions of the leftover
space: `0.0` is flush against the left/top edge, `1.0` flush against the
right/bottom, `0.5` centred. Names exist for the nine obvious ones and a tuple
works for anything else -- `(0.5, 0.35)` keeps a little above centre, which is
where faces are.

    python framing.py             # what is available
    python framing.py --sheet     # every fit x anchor, to out/framing.png

NAMED ONCE, IN identity.py:

    FIT = "crop"
    FIT_OPTS = {"anchor": "top"}

and overridden per beat, where a crop is usually actually wrong:

    # shot.py
    FIT_BEATS = {"07": {"anchor": (0.5, 0.2)}}
"""
from __future__ import annotations

import importlib.util
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))

FITS: dict[str, dict] = {}

# The nine obvious ones. Anything else is a tuple.
ANCHORS: dict[str, tuple[float, float]] = {
    "centre": (0.5, 0.5), "center": (0.5, 0.5),
    "left": (0.0, 0.5), "right": (1.0, 0.5),
    "top": (0.5, 0.0), "bottom": (0.5, 1.0),
    "topleft": (0.0, 0.0), "topright": (1.0, 0.0),
    "bottomleft": (0.0, 1.0), "bottomright": (1.0, 1.0),
}


def register(name: str, **defaults):
    """Add a fit to the library. `defaults` are its settings."""
    def wrap(fn):
        if name in FITS:
            raise ValueError(
                f"two fits are called {name!r}. A name is how identity.py asks "
                f"for one, so the second would silently win.")
        # A bare IndexError from inside the registry explained nothing
        # (fault 125). The first docstring line IS what the sheet prints,
        # so an entry without one is refused in a sentence.
        doc = (fn.__doc__ or "").strip().splitlines()
        if not doc:
            raise SystemExit(
                f"FAIL: fit {name!r} has no docstring. The first line is "
                f"what the library prints for it -- write one sentence.")
        FITS[name] = {"fn": fn, "defaults": defaults, "doc": doc[0]}
        return fn
    return wrap


def get(name: str) -> dict:
    f = FITS.get(name)
    if f is None:
        raise SystemExit(
            f"FAIL: there is no fit called {name!r}.\n"
            f"  The library has: {', '.join(sorted(FITS))}\n"
            f"  `python framing.py` describes each one. It is named in "
            f"identity.FIT.\n"
            f"  `python contract.py` catches this before anything is baked.")
    return f


def settings(name: str, opt: dict | None = None) -> dict:
    d = get(name)["defaults"]
    s = dict(d)
    s.update(opt or {})
    unknown = sorted(set(s) - set(d))
    if unknown:
        raise SystemExit(
            f"FAIL: fit {name!r} was given settings it does not have: "
            f"{unknown}.\n  It takes: {sorted(d) or '(none)'}")
    return s


def anchor_xy(a) -> tuple[float, float]:
    """A name or a pair of fractions, always out as a pair of fractions.

    REFUSES A FRACTION OUTSIDE 0..1 rather than clamping. `anchor=(0, 1.5)` is
    somebody meaning pixels, and clamping it to the bottom edge would give them
    a plausible-looking frame that is not the one they asked for.
    """
    if isinstance(a, (tuple, list)):
        if len(a) != 2:
            raise SystemExit(f"FAIL: anchor {a!r} is not a pair.")
        ax, ay = float(a[0]), float(a[1])
        if not (0.0 <= ax <= 1.0 and 0.0 <= ay <= 1.0):
            raise SystemExit(
                f"FAIL: anchor {a!r} is outside 0..1. It is a fraction of the "
                f"leftover space,\n  not a pixel offset: (0.5, 0.35) keeps a "
                f"little above centre.")
        return ax, ay
    if a not in ANCHORS:
        raise SystemExit(
            f"FAIL: there is no anchor called {a!r}.\n"
            f"  Named ones: {', '.join(sorted(ANCHORS))}\n"
            f"  Or give a pair of fractions, e.g. (0.5, 0.35).")
    return ANCHORS[a]


def unsqueeze(im: Image.Image, w: int, h: int,
              sources) -> Image.Image:
    """Undo the squash a render canvas put on a picture. Call BEFORE any fit.

    A VIDEO MODEL SQUASHES AN OFF-ASPECT PLATE; IT DOES NOT CROP IT. Measured
    on eight shots across four style LoRAs -- clip frame zero against the source
    plate resized three ways -- and squash fit 2-3x better than either crop,
    unanimously. So a canvas whose ratio is not the delivery's hands back a
    picture distorted by exactly that difference, and `crop` cannot see it:
    cropping to the delivery ratio trims the edges and keeps the distortion.
    A drawn circle through the 2.40 path came out 1.030 wide-to-tall before
    this existed and 1.000 after. See season_paths.canvases() for the five
    seasons that shipped without noticing.

    THE TEST IS THE EXACT SIZE, NOT AN APPROXIMATE ASPECT. `sources` is the
    season's own canvas ladder, so this fires on a frame that came off the
    video model and on nothing else. A plate is 2432x1664 and a bake frame is
    delivery-sized; neither is ever a rung, and matching on "looks a bit
    off-aspect" would have un-squeezed a picture somebody framed that way on
    purpose.

    The long edge is kept and the short one moved, so this only ever adds
    pixels -- an un-squeeze that scaled DOWN would throw away detail to correct
    a ratio, and the fit immediately after is resampling to delivery size
    anyway.
    """
    if im.size not in {(int(a), int(b)) for a, b in sources}:
        return im
    sw, sh = im.size
    want = int(w) / int(h)
    if abs(sw / sh - want) <= 1e-4:
        return im
    if sw / sh > want:                      # canvas too wide: picture squeezed
        return im.resize((sw, max(1, round(sw / want))), Image.LANCZOS)
    return im.resize((max(1, round(sh * want)), sh), Image.LANCZOS)


def apply(name: str, im: Image.Image, w: int, h: int,
          opt: dict | None = None) -> Image.Image:
    """Fit `im` into exactly `w` x `h`. Always returns that size."""
    out = get(name)["fn"](im, int(w), int(h), settings(name, opt))
    if out.size != (int(w), int(h)):
        raise SystemExit(
            f"FAIL: fit {name!r} returned {out.size} for a {w}x{h} frame. "
            f"Every fit must\n  return exactly the size it was asked for -- "
            f"the bake writes frames straight to\n  disk and ffmpeg would "
            f"refuse the sequence halfway through.")
    return out


# --------------------------------------------------------------------------
# the library
# --------------------------------------------------------------------------


@register("crop", anchor="centre")
def _crop(im, w, h, o):
    """Fill the frame and lose the overflow. The default, and usually right."""
    ax, ay = anchor_xy(o["anchor"])
    sw, sh = im.size
    if abs(sw / sh - w / h) > 1e-3:
        if sw / sh > w / h:
            cw = round(sh * w / h)
            x = int((sw - cw) * ax)
            im = im.crop((x, 0, x + cw, sh))
        else:
            ch = round(sw * h / w)
            y = int((sh - ch) * ay)
            im = im.crop((0, y, sw, y + ch))
    return im.resize((w, h), Image.LANCZOS)


@register("pad", anchor="centre", colour=(0, 0, 0))
def _pad(im, w, h, o):
    """Fit the whole picture inside the frame; bars in `colour`."""
    ax, ay = anchor_xy(o["anchor"])
    sw, sh = im.size
    s = min(w / sw, h / sh)
    nw, nh = max(1, round(sw * s)), max(1, round(sh * s))
    out = Image.new("RGB", (w, h), tuple(o["colour"]))
    out.paste(im.resize((nw, nh), Image.LANCZOS),
              (int((w - nw) * ax), int((h - nh) * ay)))
    return out


@register("stretch")
def _stretch(im, w, h, o):
    """Distort until it fits. Never right for picture; sometimes for graphics."""
    return im.resize((w, h), Image.LANCZOS)


# --------------------------------------------------------------------------
# a season's own fits
# --------------------------------------------------------------------------
#
# DROP A `framing_extra.py` BESIDE YOUR identity.py, the same extension point as
# devices_extra.py and grades_extra.py. A fit that blurs a scaled-up copy of the
# picture into the bars instead of filling them flat is about six lines and is
# the sort of thing exactly one season ever wants.
_LOADED: set[str] = set()


def load_extra(folder: str) -> str | None:
    """Import `<folder>/framing_extra.py` if it is there. Idempotent."""
    path = os.path.join(folder, "framing_extra.py")
    if not os.path.exists(path) or path in _LOADED:
        return None
    _LOADED.add(path)
    spec = importlib.util.spec_from_file_location("framing_extra", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["framing_extra"] = mod
    spec.loader.exec_module(mod)
    return path


def main() -> int:
    print(f"  {len(FITS)} fit(s):\n")
    for name in sorted(FITS):
        f = FITS[name]
        print(f"  {name:<10} {f['doc']}")
        if f["defaults"]:
            print(f"  {'':<10} settings: "
                  + ", ".join(f"{k}={v!r}" for k, v in
                              sorted(f["defaults"].items())))
    print(f"\n  anchors: {', '.join(sorted(ANCHORS))}, or (x, y) fractions")
    print("\n  Named in identity.py:  FIT = \"crop\"\n"
          "                         FIT_OPTS = {\"anchor\": \"top\"}\n"
          "  and per beat in shot.py:  FIT_BEATS = {\"07\": {\"anchor\": "
          "(0.5, 0.2)}}")
    if "--sheet" not in sys.argv:
        return 0

    from PIL import ImageDraw
    # A SOURCE WHOSE PARTS ARE TELLABLE APART, because the only question a fit
    # sheet answers is "which bit did I lose".
    sw, sh = 480, 270
    src = Image.new("RGB", (sw, sh), (28, 30, 34))
    d = ImageDraw.Draw(src)
    for i, (x0, x1, c, tag) in enumerate((
            (0, sw // 3, (196, 86, 60), "L"),
            (sw // 3, 2 * sw // 3, (86, 140, 78), "C"),
            (2 * sw // 3, sw, (40, 96, 132), "R"))):
        d.rectangle([x0, 0, x1 - 1, sh - 1], fill=c)
        d.text((x0 + 8, 8), tag + " TOP", fill="white")
        d.text((x0 + 8, sh - 18), tag + " BOT", fill="white")
    d.ellipse([sw // 2 - 26, 24, sw // 2 + 26, 76], outline="white", width=3)

    # TWO ROWS, BECAUSE AN ANCHOR HAS TWO HALVES AND ONLY ONE OF THEM EVER
    # BINDS. Cropping a wide source into a tall frame uses the x and ignores
    # the y entirely -- so a one-row sheet showing `(0.5, 0.35)` next to
    # `centre` draws two identical pictures and teaches the wrong thing.
    tall = src.rotate(90, expand=True)
    cells = [("crop", "topleft"), ("crop", "centre"), ("crop", "right"),
             ("crop", (0.5, 0.35)), ("pad", "centre"), ("pad", "bottom"),
             ("stretch", None)]
    w, h = 160, 200
    cw, ch = max(w, h) + 12, max(w, h) + 30
    sheet = Image.new("RGB", (cw * len(cells), ch * 2), (16, 16, 18))
    dd = ImageDraw.Draw(sheet)
    for r, (source, frame) in enumerate(((src, (w, h)), (tall, (h, w)))):
        fw, fh = frame
        for i, (name, anch) in enumerate(cells):
            opt = {} if anch is None else {"anchor": anch}
            sheet.paste(apply(name, source, fw, fh, opt),
                        (i * cw + 6, r * ch + 24))
            dd.text((i * cw + 6, r * ch + 6), f"{name} {anch if anch else ''}",
                    fill="#ffdd99")
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    dst = os.path.join(ROOT, "out", "framing.png")
    sheet.save(dst)
    print(f"\n  {len(cells)} fit(s) x 2 source shapes -> {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
