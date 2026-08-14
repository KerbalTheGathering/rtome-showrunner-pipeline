"""The look, as a library you pick from rather than a function you edit.

WHY THIS IS A FILE. `assemble.py` carried a function called `flatten()` that was
one season's grade -- saturation to about half, a lifted black, a five per cent
wash toward warm white -- with its tuning notes in the docstring. It was good,
and it was also the only look the template could express. `shot.GRADED` named
WHICH beats got it; nothing named WHAT it was, because there was nothing to
name. A film that wanted its flat beats to go cold instead of warm, or a film
that wanted a look on every frame, edited the assembler.

That is the same shape the transitions were in before ../devices.py, and this is
the same fix. The carried look is here as `flat`, tuned exactly as it was; it is
just no longer everybody's.

WHAT A GRADE IS. One function over one picture:

    fn(im, o) -> Image        # RGB in, RGB out, same size

  o    this grade's settings, merged over its registered defaults

NO GEOMETRY, ON PURPOSE. A grade may not know the frame size, the beat, or where
in the film it is. Everything here is per-pixel and stateless, which is what
makes it safe to run on the outgoing layer of a transition, on a card's
treatment, and on a still in the QC sheet and get the same answer three times.
Anything that needs to know where it is belongs in a device.

TWO NAMES, BECAUSE THERE ARE TWO QUESTIONS:

    identity.GRADE       the look every beat gets
    identity.GRADED_AS   the look the beats in shot.GRADED get INSTEAD

One grade per frame, ever. They do not stack. Stacking `bleach` under `flat`
gives you neither, and the film where that happened would be very hard to read
back to a cause.

    python grades.py               # what is available, and its settings
    python grades.py --sheet       # render every grade to out/grades.png

A LOOK IS NOT A FIX. If the plates are wrong, grading them is the expensive way
round -- see docs/05_prompting.md. The grade is for saying something the picture
cannot say on its own, and `none` is a real answer.
"""
from __future__ import annotations

import importlib.util
import os
import sys

from PIL import Image, ImageChops, ImageEnhance, ImageOps

ROOT = os.path.dirname(os.path.abspath(__file__))

GRADES: dict[str, dict] = {}


def register(name: str, **defaults):
    """Add a grade to the library. `defaults` are its settings."""
    def wrap(fn):
        if name in GRADES:
            raise ValueError(
                f"two grades are called {name!r}. A name is how identity.py "
                f"asks for one, so the second would silently win.")
        GRADES[name] = {"fn": fn, "defaults": defaults,
                        "doc": (fn.__doc__ or "").strip().splitlines()[0]}
        return fn
    return wrap


def get(name: str) -> dict:
    g = GRADES.get(name)
    if g is None:
        raise SystemExit(
            f"FAIL: there is no grade called {name!r}.\n"
            f"  The library has: {', '.join(sorted(GRADES))}\n"
            f"  `python grades.py` describes each one; `--sheet` draws them.\n"
            f"  It is named in identity.GRADE or identity.GRADED_AS.\n"
            f"  `python contract.py` catches this before anything is baked.")
    return g


def settings(name: str, opt: dict | None = None) -> dict:
    s = dict(get(name)["defaults"])
    s.update(opt or {})
    unknown = sorted(set(s) - set(get(name)["defaults"]))
    if unknown:
        raise SystemExit(
            f"FAIL: grade {name!r} was given settings it does not have: "
            f"{unknown}.\n  It takes: {sorted(get(name)['defaults']) or '(none)'}"
            f"\n  A setting that is ignored is worse than one that is wrong -- "
            f"you would\n  spend the bake wondering why it did nothing.")
    return s


def apply(name: str, im: Image.Image, opt: dict | None = None) -> Image.Image:
    """Run one grade. Refuses on a name it does not have.

    `none` is free: it is an identity function and the caller does not have to
    branch around it. That matters because the alternative -- `if GRADE !=
    "none"` at every call site -- is four places that have to agree.
    """
    return get(name)["fn"](im, settings(name, opt))


# --------------------------------------------------------------------------
# the library
# --------------------------------------------------------------------------


@register("none")
def _none(im, o):
    """The picture, untouched. The default, and a real answer."""
    return im


@register("flat", colour=0.55, lift=26, ceil=240, contrast=0.90,
          wash=(250, 245, 232), amount=0.05)
def _flat(im, o):
    """The same world painted without conviction. The carried look.

    TUNED ON A REAL FILM AND THE NUMBERS ARE THE ARGUMENT. Saturation goes to
    about half rather than out, because a near-monochrome layer reads as a
    fault in the file rather than as a place with nothing in it. The black is
    lifted and the ceiling pulled down so there is no true black and no true
    white anywhere in the frame -- that, more than the desaturation, is what
    makes it read as flat rather than as broken.

    `wash` is the colour the whole frame moves toward, five per cent of the
    way. Warm white was this season's; a cold one is `(228, 236, 250)` and
    changes what the flatness means without changing what it is.
    """
    im = ImageEnhance.Color(im).enhance(o["colour"])
    lift, ceil = o["lift"], o["ceil"]
    lut = [min(255, lift + int(v * (ceil - lift) / 255)) for v in range(256)]
    im = im.point(lut * 3)
    im = ImageEnhance.Contrast(im).enhance(o["contrast"])
    if o["amount"] <= 0.0:
        return im
    wash = Image.new("RGB", im.size, tuple(o["wash"]))
    return ImageChops.blend(im, wash, o["amount"])


@register("mono", tint=None, black=(0, 0, 0), contrast=1.0)
def _mono(im, o):
    """All the colour out, and optionally one colour back in.

    `tint` is what white becomes: `(255, 226, 178)` is sepia, `(206, 224, 255)`
    is the cold end of the same idea. `None` leaves it neutral.
    """
    g = im.convert("L")
    im = (ImageOps.colorize(g, tuple(o["black"]), tuple(o["tint"]))
          if o["tint"] else g.convert("RGB"))
    if o["contrast"] != 1.0:
        im = ImageEnhance.Contrast(im).enhance(o["contrast"])
    return im


@register("bleach", colour=0.35, contrast=1.15)
def _bleach(im, o):
    """Bleach bypass: the luminance laid back over the colour. Hard, silvery.

    The overlay is what does the work -- it steepens the middle and leaves the
    ends, so shadows block up and highlights go chalky while the midtones keep
    just enough colour to say what things are.
    """
    lum = im.convert("L").convert("RGB")
    out = ImageChops.overlay(ImageEnhance.Color(im).enhance(o["colour"]), lum)
    return (ImageEnhance.Contrast(out).enhance(o["contrast"])
            if o["contrast"] != 1.0 else out)


@register("balance", k=0.10, gain=1.0)
def _balance(im, o):
    """Warm or cold, and nothing else. `k` positive is warm, negative is cold.

    THE SMALLEST GRADE THAT IS STILL A GRADE, and usually the right one. A film
    whose look is "slightly warmer than the plates came out" wants this and not
    `flat`, and the difference between +0.06 and +0.20 is the difference
    between a look and a filter.
    """
    k, gain = o["k"], o["gain"]
    r = [min(255, int(v * gain * (1.0 + 0.6 * k))) for v in range(256)]
    g = [min(255, int(v * gain * (1.0 + 0.1 * k))) for v in range(256)]
    b = [min(255, int(v * gain * (1.0 - 0.6 * k))) for v in range(256)]
    return im.point(r + g + b)


@register("night", k=-0.35, gain=0.45, lift=16, colour=0.55)
def _night(im, o):
    """Day for night: cold, down, and desaturated, with the black lifted.

    THE LIFT IS THE PART PEOPLE LEAVE OUT and it is why most day-for-night
    reads as an underexposure. Real night has no black in it either; it has a
    floor you can see into.
    """
    im = ImageEnhance.Color(im).enhance(o["colour"])
    im = _balance(im, {"k": o["k"], "gain": o["gain"]})
    lift = o["lift"]
    return im.point([min(255, lift + int(v * (255 - lift) / 255))
                     for v in range(256)] * 3)


# --------------------------------------------------------------------------
# a season's own grades
# --------------------------------------------------------------------------
#
# DROP A `grades_extra.py` BESIDE YOUR identity.py and it is imported here,
# once, before anything asks for a grade -- the same extension point devices.py
# and the same reason: a look nobody else will ever want should not be a merge
# conflict in a shared file.
#
#     # S3_HARBOUR/grades_extra.py
#     import grades
#
#     @grades.register("salt", colour=0.7, k=-0.08)
#     def _salt(im, o):
#         """Everything a little bleached and a little cold. Sun off water."""
#         return grades.apply("balance", grades.apply(
#             "mono", im, {"tint": (255, 252, 244), "contrast": 0.95}),
#             {"k": o["k"]})
_LOADED: set[str] = set()


def load_extra(folder: str) -> str | None:
    """Import `<folder>/grades_extra.py` if it is there. Idempotent."""
    path = os.path.join(folder, "grades_extra.py")
    if not os.path.exists(path) or path in _LOADED:
        return None
    _LOADED.add(path)
    spec = importlib.util.spec_from_file_location("grades_extra", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["grades_extra"] = mod
    spec.loader.exec_module(mod)
    return path


def _swatch(w: int, h: int) -> Image.Image:
    """Something with a known answer in it: a ramp, primaries, and a skin tone.

    A GRADE SHEET DRAWN ON A PRETTY PICTURE TELLS YOU NOTHING. What you need to
    see is where the black went, whether the ramp still separates at both ends,
    and what happened to a face -- so those are the three things in the frame.
    """
    im = Image.new("RGB", (w, h))
    px = im.load()
    band = h // 3
    swatches = [(196, 86, 60), (40, 96, 132), (86, 140, 78), (222, 196, 96),
                (140, 92, 150), (232, 232, 228)]
    skin = (214, 168, 136)
    for x in range(w):
        v = int(255 * x / max(1, w - 1))
        for y in range(band):
            px[x, y] = (v, v, v)
        c = swatches[min(len(swatches) - 1, x * len(swatches) // w)]
        for y in range(band, band * 2):
            px[x, y] = c
        f = x / max(1, w - 1)
        for y in range(band * 2, h):
            px[x, y] = (int(skin[0] * (0.45 + 0.75 * f)),
                        int(skin[1] * (0.45 + 0.75 * f)),
                        int(skin[2] * (0.45 + 0.75 * f)))
    return im


def main() -> int:
    print(f"  {len(GRADES)} grade(s):\n")
    for name in sorted(GRADES):
        g = GRADES[name]
        print(f"  {name:<10} {g['doc']}")
        if g["defaults"]:
            print(f"  {'':<10} settings: "
                  + ", ".join(f"{k}={v!r}" for k, v in
                              sorted(g["defaults"].items())))
    print("\n  Named in identity.py:  GRADE = \"none\"      # every beat\n"
          "                         GRADED_AS = \"flat\"  # the shot.GRADED ones\n"
          "                         GRADE_OPTS = {\"wash\": (228, 236, 250)}")
    if "--sheet" not in sys.argv:
        return 0

    from PIL import ImageDraw
    w, h = 300, 210
    base = _swatch(w, h)
    names = sorted(GRADES)
    sheet = Image.new("RGB", (w * min(4, len(names)),
                              (h + 18) * ((len(names) + 3) // 4)), (16, 16, 18))
    d = ImageDraw.Draw(sheet)
    for i, name in enumerate(names):
        x, y = (i % 4) * w, (i // 4) * (h + 18)
        d.text((x + 6, y + 4), name, fill="#ffdd99")
        sheet.paste(apply(name, base.copy()), (x, y + 18))
    out = os.path.join(ROOT, "out")
    os.makedirs(out, exist_ok=True)
    dst = os.path.join(out, "grades.png")
    sheet.save(dst)
    print(f"\n  {len(names)} grade(s) -> {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
