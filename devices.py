"""Transitions, as a library you pick from rather than a chain you edit.

WHY THIS IS A FILE AND NOT AN `if kind ==` LADDER. It was a ladder, in
assemble.py, over four names -- and the ladder was right about one thing: it
hard-failed on a name it did not know rather than falling through to a default,
because an `else` on that lookup is how one film once rendered another film's
device with nothing failing anywhere.

But it meant ADDING A DEVICE WAS EDITING THE ASSEMBLER: the largest, most
load-bearing file in a part folder, shared by every season that ever clones this
template, in order to say that your film wipes diagonally. So the four devices
that one season happened to need were machinery, and a fifth that yours needs is
a merge conflict.

Here they are values in a table. A season adds one by writing a function and
registering it -- in `devices_extra.py` beside its own edit.py if it is that
film's alone, which nothing shared ever has to know about.

WHAT A DEVICE IS. One function over two pictures and a number:

    fn(incoming, outgoing, e, ctx, opt) -> Image

  incoming   the frame of the beat being cut TO
  outgoing   the frame of the beat being cut FROM, live, not frozen
  e          eased progress, 0.0 = entirely outgoing, 1.0 = entirely incoming
  ctx        {"w", "h", "fit", "cream", "ink"} -- the bake geometry and palette
  opt        this transition's own settings, merged over the device's defaults

THE OUTGOING FRAMES ARE LIVE. edit.py buys each transition source enough clip to
supply real frames past the end of its own beat, which is why a device gets a
picture rather than a still. A frozen under-layer reads as a hitch, and it is
the sort of thing nobody can name when they see it.

    python devices.py              # what is available, and its settings
    python devices.py --sheet      # render every device to out/devices.png

A DEVICE USED ONCE IS A TRICK; USED TWICE, POINTED THE OTHER WAY, IT IS A RHYME.
The library being large is not permission to spend it. A film that runs every
device is a device demo and none of them mean anything.
"""
from __future__ import annotations

import importlib.util
import math
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw

ROOT = os.path.dirname(os.path.abspath(__file__))

DEVICES: dict[str, dict] = {}


def register(name: str, **defaults):
    """Add a device to the library. `defaults` are its settings."""
    def wrap(fn):
        if name in DEVICES:
            raise ValueError(
                f"two devices are called {name!r}. A name is how edit.py asks "
                f"for one, so the second would silently win.")
        # A bare IndexError from inside the registry explained nothing
        # (fault 125). The first docstring line IS what the sheet prints,
        # so an entry without one is refused in a sentence.
        doc = (fn.__doc__ or "").strip().splitlines()
        if not doc:
            raise SystemExit(
                f"FAIL: device {name!r} has no docstring. The first line is "
                f"what the library prints for it -- write one sentence.")
        DEVICES[name] = {"fn": fn, "defaults": defaults, "doc": doc[0]}
        return fn
    return wrap


def apply(kind: str, incoming: Image.Image, outgoing: Image.Image,
          e: float, ctx: dict, opt: dict | None = None) -> Image.Image:
    """Run one device. Refuses on a name it does not have.

    NOT A SILENT FALLBACK, EVER. The branch this replaced was once
    `else: portal_in`, and a tree whose transitions were named "sweep" would
    have rendered another session's sign portal without failing anything --
    the same shape of bug as a copied motion table and just as invisible until
    somebody watched it.
    """
    d = DEVICES.get(kind)
    if d is None:
        raise SystemExit(
            f"FAIL: there is no transition device called {kind!r}.\n"
            f"  The library has: {', '.join(sorted(DEVICES))}\n"
            f"  `python devices.py` describes each one. To add your own, see "
            f"the note\n  on devices_extra.py at the bottom of that file's "
            f"docstring.\n"
            f"  `python contract.py` catches this before anything is rendered.")
    settings = dict(d["defaults"])
    settings.update(opt or {})
    unknown = sorted(set(settings) - set(d["defaults"]))
    if unknown:
        raise SystemExit(
            f"FAIL: transition {kind!r} was given settings it does not have: "
            f"{unknown}.\n  It takes: {sorted(d['defaults']) or '(none)'}\n"
            f"  A setting that is ignored is worse than one that is wrong -- "
            f"you would\n  spend the render wondering why it did nothing.")
    return d["fn"](incoming, outgoing, e, ctx, settings)


# --------------------------------------------------------------------------
# masks. All of them return L-mode: 255 where the INCOMING shot shows.
# --------------------------------------------------------------------------

def edge_mask(w: int, h: int, e: float, angle: float = 0.0,
              soft: float = 0.10) -> Image.Image:
    """A straight edge at `angle` degrees, travelling across the frame.

    NUMPY RATHER THAN A RESIZED ONE-PIXEL ROW. The row trick works and is
    faster, and it only works for a VERTICAL edge -- which is why the device
    it was written for could only ever go left to right. An angle is the
    difference between one device and a family of them.

    `soft` is the blend width as a fraction of the travel, and NARROW IS
    USUALLY RIGHT: at 0.22 the changeover region is wide enough to show both
    pictures at once, which reads as a cross-dissolve rather than as an edge
    going past. If you want a dissolve, ask for one.
    """
    a = math.radians(angle)
    xs = np.arange(w, dtype=np.float32)[None, :]
    ys = np.arange(h, dtype=np.float32)[:, None]
    d = xs * math.cos(a) + ys * math.sin(a)
    lo, hi = float(d.min()), float(d.max())
    s = max(2.0, (hi - lo) * soft)
    pos = lo - s + e * ((hi - lo) + 2 * s)
    m = np.clip(1.0 - (d - (pos - s / 2.0)) / s, 0.0, 1.0)
    return Image.fromarray((m * 255).astype(np.uint8), "L")


def edge_glow(w: int, h: int, e: float, angle: float = 0.0,
              soft: float = 0.10, bar: float = 2.2) -> Image.Image:
    """A soft bright band centred exactly on `edge_mask`'s travelling edge."""
    a = math.radians(angle)
    xs = np.arange(w, dtype=np.float32)[None, :]
    ys = np.arange(h, dtype=np.float32)[:, None]
    d = xs * math.cos(a) + ys * math.sin(a)
    lo, hi = float(d.min()), float(d.max())
    s = max(2.0, (hi - lo) * soft)
    pos = lo - s + e * ((hi - lo) + 2 * s)
    half = s * bar / 2.0
    m = np.clip(1.0 - np.abs(d - pos) / half, 0.0, 1.0) ** 2
    return Image.fromarray((m * 255).astype(np.uint8), "L")


def iris_mask(w: int, h: int, e: float, cx: float = 0.5, cy: float = 0.5,
              soft: float = 0.02) -> Image.Image:
    """A circle growing from (cx, cy) until it covers the frame."""
    xs = np.arange(w, dtype=np.float32)[None, :] - cx * w
    ys = np.arange(h, dtype=np.float32)[:, None] - cy * h
    d = np.sqrt(xs * xs + ys * ys)
    full = float(d.max())
    s = max(2.0, full * soft)
    r = e * (full + s)
    m = np.clip((r - d) / s + 0.5, 0.0, 1.0)
    return Image.fromarray((m * 255).astype(np.uint8), "L")


_BANDM: dict[tuple, Image.Image] = {}


def band_mask(w: int, h: int, e: float, bands: int = 9,
              stagger: float = 0.045, vertical: bool = True) -> Image.Image:
    """`bands` strips, each snapping open in turn, staggered across the frame.

    Quantised to 1/240 and cached: a 0.8s wipe only ever needs about twenty
    distinct states and rebuilding nine rectangles a frame is pointless.
    """
    q = round(e * 240)
    key = (w, h, q, bands, stagger, vertical)
    m = _BANDM.get(key)
    if m is not None:
        return m
    t = q / 240.0
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    span = 1.0 - stagger * (bands - 1)
    step = (w if vertical else h) / bands
    for b in range(bands):
        p = max(0.0, min(1.0, (t - b * stagger) / max(1e-6, span)))
        if p <= 0.0:
            continue
        a0 = b * step
        # Each band opens from its own leading edge, so the reveal reads as a
        # column passing rather than as a dissolve.
        if vertical:
            d.rectangle([a0, 0, a0 + step * p, h], fill=255)
        else:
            d.rectangle([0, a0, w, a0 + step * p], fill=255)
    _BANDM[key] = m
    return m


def lerp_rect(a, b, e, w, h):
    return [int(round(v)) for v in
            ((a[0] + (b[0] - a[0]) * e) * w, (a[1] + (b[1] - a[1]) * e) * h,
             (a[2] + (b[2] - a[2]) * e) * w, (a[3] + (b[3] - a[3]) * e) * h)]


FULL = (0.0, 0.0, 1.0, 1.0)


# --------------------------------------------------------------------------
# the library
# --------------------------------------------------------------------------

@register("cut")
def _cut(im, under, e, ctx, o):
    """A hard cut. Nothing is drawn; the change happens on one frame."""
    return im if e >= 0.5 else under


@register("dissolve")
def _dissolve(im, under, e, ctx, o):
    """A straight cross-dissolve. The default when a join needs softening."""
    return Image.blend(under, im, e)


@register("fade", colour=None, hold=0.0)
def _fade(im, under, e, ctx, o):
    """Out through a colour and in again -- a dip to black, or to white."""
    col = o["colour"] or ctx["ink"]
    flat = Image.new("RGB", (ctx["w"], ctx["h"]), col)
    half = 0.5 - o["hold"] / 2.0
    if e < half:
        return Image.blend(under, flat, e / max(1e-6, half))
    if e > 1.0 - half:
        return Image.blend(flat, im, (e - (1.0 - half)) / max(1e-6, half))
    return flat


@register("wipe", angle=0.0, soft=0.02, seam=0, seam_colour=None)
def _wipe(im, under, e, ctx, o):
    """A straight edge travelling across the frame, at any angle."""
    out = Image.composite(im, under, edge_mask(ctx["w"], ctx["h"], e,
                                               o["angle"], max(1e-3, o["soft"])))
    if o["seam"]:
        # A drawn line on the edge, so the device reads as one hard mark
        # rather than as a soft changeover.
        m = edge_glow(ctx["w"], ctx["h"], e, o["angle"],
                      max(1e-3, o["soft"]), bar=o["seam"] * 0.02)
        line = Image.new("RGB", out.size, o["seam_colour"] or ctx["cream"])
        out = Image.composite(line, out, m.point(lambda v: 255 if v > 200 else 0))
    return out


@register("sweep", angle=0.0, soft=0.10, glow=0.80, bar=2.2, colour=None)
def _sweep(im, under, e, ctx, o):
    """A soft travelling edge with a bar of light riding on it.

    The picture changes UNDER the light, so the change and the light are one
    event rather than two. The soft edge is the whole device and it is narrow
    on purpose -- see edge_mask.
    """
    out = Image.composite(im, under,
                          edge_mask(ctx["w"], ctx["h"], e, o["angle"],
                                    o["soft"]))
    g = edge_glow(ctx["w"], ctx["h"], e, o["angle"], o["soft"], o["bar"])
    lit = ImageChops.screen(out, Image.new("RGB", out.size,
                                           o["colour"] or ctx["cream"]))
    return Image.composite(lit, out, g.point(lambda v: int(v * o["glow"])))


@register("rows", bands=9, stagger=0.045, seam=2, vertical=True, colour=None)
def _rows(im, under, e, ctx, o):
    """Vertical bands snapping open in turn -- one seam played as a chord."""
    w, h = ctx["w"], ctx["h"]
    out = Image.composite(im, under,
                          band_mask(w, h, e, o["bands"], o["stagger"],
                                    o["vertical"]))
    if o["seam"]:
        d = ImageDraw.Draw(out)
        col = o["colour"] or ctx["cream"]
        span = 1.0 - o["stagger"] * (o["bands"] - 1)
        step = (w if o["vertical"] else h) / o["bands"]
        for b in range(o["bands"]):
            p = max(0.0, min(1.0, (e - b * o["stagger"]) / max(1e-6, span)))
            if 0.0 < p < 1.0:
                a0 = b * step + step * p
                if o["vertical"]:
                    d.rectangle([a0 - o["seam"] / 2, 0, a0 + o["seam"] / 2, h],
                                fill=col)
                else:
                    d.rectangle([0, a0 - o["seam"] / 2, w, a0 + o["seam"] / 2],
                                fill=col)
    return out


@register("iris", cx=0.5, cy=0.5, soft=0.02, close=False)
def _iris(im, under, e, ctx, o):
    """A circle opening on the incoming shot -- or closing on the outgoing."""
    m = iris_mask(ctx["w"], ctx["h"], 1.0 - e if o["close"] else e,
                  o["cx"], o["cy"], o["soft"])
    return (Image.composite(under, im, m) if o["close"]
            else Image.composite(im, under, m))


@register("push", angle=0.0)
def _push(im, under, e, ctx, o):
    """The incoming shot pushes the outgoing one out of frame.

    PASTE ONTO A FRESH CANVAS, NOT ImageChops.offset. offset() WRAPS -- the
    first version of this used it and the outgoing shot's left edge came back
    round on the right, so a quarter of the way through the join you were
    looking at three pictures. The devices contact sheet showed it at a glance
    and no description of the code would have.

    The incoming sits exactly one screen ahead along the direction of travel,
    so `angle` gives push-left, push-up and the diagonals for free.
    """
    w, h = ctx["w"], ctx["h"]
    a = math.radians(o["angle"])
    dx, dy = int(round(math.cos(a) * w * e)), int(round(math.sin(a) * h * e))
    ox, oy = int(round(math.cos(a) * w)), int(round(math.sin(a) * h))
    out = Image.new("RGB", (w, h), ctx["ink"])
    out.paste(under, (-dx, -dy))
    out.paste(im, (ox - dx, oy - dy))
    return out


@register("portal_out", rect=None, border=3, edge=None)
def _portal_out(im, under, e, ctx, o):
    """A rectangle in the outgoing shot grows until it IS the incoming one."""
    return _panel(under.copy(), im, lerp_rect(o["rect"] or FULL, FULL, e,
                                              ctx["w"], ctx["h"]), ctx, o)


@register("portal_in", rect=None, border=3, edge=None)
def _portal_in(im, under, e, ctx, o):
    """The outgoing shot shrinks into a rectangle of the incoming one."""
    return _panel(im.copy(), under, lerp_rect(FULL, o["rect"] or FULL, e,
                                              ctx["w"], ctx["h"]), ctx, o)


def _panel(base, inner, rect, ctx, o):
    x0, y0, x1, y1 = rect
    pw, ph = max(2, x1 - x0), max(2, y1 - y0)
    b = o["border"]
    d = ImageDraw.Draw(base)
    d.rectangle([x0 - b, y0 - b, x1 + b - 1, y1 + b - 1], fill=ctx["ink"])
    base.paste(ctx["fit"](inner, pw, ph), (x0, y0))
    d.rectangle([x0 - 1, y0 - 1, x1, y1], outline=o["edge"] or ctx["cream"],
                width=1)
    return base


# --------------------------------------------------------------------------
# a season's own devices
# --------------------------------------------------------------------------
#
# DROP A `devices_extra.py` BESIDE YOUR edit.py and it is imported here, once,
# before anything asks for a device. That is the whole extension point: a film
# with a device nobody else will ever want does not have to edit this file, and
# a merge from upstream cannot lose it.
#
#     # S3_HARBOUR/devices_extra.py
#     import devices
#
#     @devices.register("waterline", soft=0.004)
#     def _waterline(im, under, e, ctx, o):
#         """A hard horizontal line rising -- the tide coming in."""
#         return Image.composite(im, under, devices.edge_mask(
#             ctx["w"], ctx["h"], e, angle=90.0, soft=o["soft"]))
_LOADED: set[str] = set()


def load_extra(folder: str) -> str | None:
    """Import `<folder>/devices_extra.py` if it is there. Idempotent."""
    path = os.path.join(folder, "devices_extra.py")
    if not os.path.exists(path) or path in _LOADED:
        return None
    _LOADED.add(path)
    spec = importlib.util.spec_from_file_location("devices_extra", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["devices_extra"] = mod
    spec.loader.exec_module(mod)
    return path


def main() -> int:
    print(f"  {len(DEVICES)} device(s):\n")
    for name in sorted(DEVICES):
        d = DEVICES[name]
        print(f"  {name:<12} {d['doc']}")
        if d["defaults"]:
            print(f"  {'':<12} settings: "
                  + ", ".join(f"{k}={v!r}" for k, v in
                              sorted(d["defaults"].items())))
    print("\n  A device is asked for by name in edit.TRANSITIONS:\n"
          '    ("03", "04", "wipe", 0.7, {"angle": 20.0, "seam": 3})\n'
          "  The fifth element is optional and is that transition's settings.")
    if "--sheet" not in sys.argv:
        return 0

    # A CONTACT SHEET OF EVERY DEVICE, ON TWO PICTURES YOU CANNOT MISTAKE FOR
    # EACH OTHER. It answers the only question a description cannot: what does
    # it look like a third of the way through?
    w, h = 320, 240
    a = Image.new("RGB", (w, h), (196, 86, 60))
    b = Image.new("RGB", (w, h), (40, 96, 132))
    for im, tag in ((a, "OUT"), (b, "IN")):
        d = ImageDraw.Draw(im)
        for i in range(0, w, 40):
            d.line([(i, 0), (i, h)], fill=(255, 255, 255), width=1)
        d.text((12, 12), tag, fill=(255, 255, 255))
    ctx = {"w": w, "h": h, "cream": (247, 240, 224), "ink": (24, 20, 18),
           "fit": lambda im, pw, ph: im.resize((pw, ph), Image.LANCZOS)}
    steps = [0.0, 0.25, 0.5, 0.75, 1.0]
    names = sorted(DEVICES)
    sheet = Image.new("RGB", (w * len(steps), (h + 18) * len(names)),
                      (16, 16, 18))
    dd = ImageDraw.Draw(sheet)
    for r, name in enumerate(names):
        y = r * (h + 18)
        opt = {"rect": (0.30, 0.25, 0.62, 0.70)} if "portal" in name else {}
        dd.text((6, y + 4), name, fill="#ffdd99")
        for c, e in enumerate(steps):
            sheet.paste(apply(name, b, a, e, ctx, opt), (c * w, y + 18))
    out = os.path.join(ROOT, "out")
    os.makedirs(out, exist_ok=True)
    dst = os.path.join(out, "devices.png")
    sheet.save(dst)
    print(f"\n  {len(names)} device(s) x {len(steps)} steps -> {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
