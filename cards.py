"""Title and end cards, as a library with a PLAIN DEFAULT.

WHY THIS IS A FILE. The template's title card was one season's signature welded
into the assembler: the frame opens broken along a hard diagonal, slipped, out
of sync and drained of colour, and all three faults resolve as the type lands.
It is a good card. It is also emphatically not what most films want, and it was
the only one on offer -- so a season whose title should simply fade up over the
first shot had to read four hundred lines of compositing to find out how to
stop it doing that.

So: `plain` is the default and does the obvious thing, the signature card is one
option among several, and a season picks by name in identity.py.

    TITLE_CARD = "plain"                    # or "lower_third", "over_colour",
    TITLE_CARD_OPTS = {"cy": 0.44}          # "break_diagonal"
    END_CARD_STYLE = "corner"

A CARD IS TWO THINGS AND MOST CARDS ARE ONLY THE FIRST:

  layout(o, n) -> [(cx, cy, anchor, slip), ...]     where each of n lines goes,
                                         in frame fractions, with the anchor it
                                         is drawn on and the largest lateral
                                         displacement the treatment will apply
                                         to it.
  treat(im, e, ctx, o) -> (im, offset)   an optional effect on the PICTURE over
                                         the head of the opening beat, `e`
                                         running 0..1 across `fix` seconds.

THE LAYOUT IS ONE FUNCTION AND EVERYTHING ELSE ASKS IT. The drawing asks it;
so does the assembler's fit, which sizes the type to the space the anchor
leaves, and so does the assembler's check that what was actually drawn is on
the frame. Those three used to be three sets of numbers seventy lines apart --
and they disagreed, once, on the very first thing anybody sees: a title sized
to a 0.90w cap and centred at 0.60w spans 0.15w to 1.05w, so the last letter
was off the frame. Deriving all three from one declaration makes that
impossible rather than merely unlikely.

`ctx` carries {"w", "h", "text", "fonts", "stroke", "cream", "ink", "fit",
"flatten", "neighbour"}. `neighbour(dj)` hands back the opening beat's frame
`dj` away from this one, already fitted -- only the cards that read adjacent
frames use it, and only they should.

THE TIMING IS THE CARD'S, AND IT IS WORTH KNOWING. `fix + hold + out` is how
long the card is on screen, and it does NOT shrink to fit a short opening beat:
the reference season's card ran 5.6s over whatever the first beat was. Choose
leads as editorial register, never as room for the card -- and if the card does
not fit, shorten the CARD.

    python cards.py            # what is available, and its settings
    python cards.py --sheet    # render every card to out/cards.png
"""
from __future__ import annotations

import math
import os
import sys

from PIL import Image, ImageChops, ImageDraw

ROOT = os.path.dirname(os.path.abspath(__file__))

CARDS: dict[str, dict] = {}


def register(name: str, fix: float = 0.0, hold: float = 2.7,
             out: float = 0.8, treat=None, **defaults):
    """Add a card. `fix` is seconds of picture treatment before the type lands.

    The decorated function is the card's LAYOUT: `(o, n) -> [(cx, cy, anchor,
    slip), ...]`, one entry per line of type.
    """
    def wrap(fn):
        if name in CARDS:
            raise ValueError(f"two cards are called {name!r}")
        CARDS[name] = {"layout": fn, "treat": treat,
                       "defaults": dict(defaults, fix=fix, hold=hold, out=out),
                       "doc": (fn.__doc__ or "").strip().splitlines()[0]}
        return fn
    return wrap


def get(name: str) -> dict:
    c = CARDS.get(name)
    if c is None:
        raise SystemExit(
            f"FAIL: there is no card called {name!r}.\n"
            f"  The library has: {', '.join(sorted(CARDS))}\n"
            f"  `python cards.py` describes each one. It is named in "
            f"identity.TITLE_CARD.")
    return c


def settings(name: str, opt: dict | None = None) -> dict:
    c = get(name)
    s = dict(c["defaults"])
    s.update(opt or {})
    unknown = sorted(set(s) - set(c["defaults"]))
    if unknown:
        raise SystemExit(
            f"FAIL: card {name!r} was given settings it does not have: "
            f"{unknown}.\n  It takes: {sorted(c['defaults'])}")
    return s


def seconds(name: str, opt: dict | None = None) -> float:
    """How long this card is on screen, end to end."""
    s = settings(name, opt)
    return s["fix"] + s["hold"] + s["out"]


def layout(name: str, n: int, opt: dict | None = None) -> list[tuple]:
    """(cx, cy, anchor, slip) per line. The one declaration everything asks."""
    got = get(name)["layout"](settings(name, opt), n)
    if len(got) < n:
        raise SystemExit(
            f"FAIL: card {name!r} lays out {len(got)} line(s) and was given "
            f"{n}.\n  Some cards want an exact number -- break_diagonal wants "
            f"two, because\n  the two lines sitting either side of the break "
            f"IS the device.")
    return got[:n]


def limit(cx: float, anchor: str, slip: float, margin: float = 0.03) -> float:
    """Widest a block may be at this anchor and stay on frame, as a fraction.

    DERIVED FROM THE ANCHOR, NOT TYPED NEXT TO IT. `slip` is paid out of the
    same budget because the treatment's displacement is worst on frame one,
    which is exactly where the clipping showed.
    """
    slip = abs(slip)
    if anchor[0] == "m":
        return 2.0 * max(0.0, min(cx, 1.0 - cx) - slip - margin)
    if anchor[0] == "r":
        return max(0.0, cx - slip - margin)
    return max(0.0, 1.0 - cx - slip - margin)


def span(cx: float, anchor: str, slip: float, width: float) -> tuple:
    """(left, right) of a block of `width` at this anchor, in frame fractions.

    What the assembler measures AFTER fitting. limit() constrains the fit, but
    the fit and the draw are two separate statements and that seam is exactly
    where the last bug came through.
    """
    s = abs(slip)
    if anchor[0] == "m":
        return cx - width / 2 - s, cx + width / 2 + s
    if anchor[0] == "r":
        return cx - width - s, cx + s
    return cx - s, cx + width + s


def draw(name: str, im, texts, ctx: dict, alpha: float,
         off=(0.0, 0.0), opt: dict | None = None):
    """The type, at the positions layout() declares."""
    ox, oy = off
    for (cx, cy, anchor, slip), text, font in zip(
            layout(name, len(texts), opt), texts, ctx["fonts"]):
        # THE SIGN OF `slip` IS WHICH WAY THIS LINE MOVES with the treatment.
        # A card with no treatment has slip 0 and the offset does nothing.
        s = 0.0 if slip == 0 else (1.0 if slip > 0 else -1.0)
        im = ctx["text"](im, text, font,
                         round(ctx["w"] * cx + s * ox),
                         round(ctx["h"] * cy + s * oy),
                         ctx["stroke"], anchor=anchor, alpha=alpha)
    return im


def treat(name: str, im, e: float, ctx: dict, opt: dict | None = None):
    """(picture, type displacement). Identity for a card with no treatment."""
    fn = get(name)["treat"]
    if fn is None:
        return im, (0.0, 0.0)
    return fn(im, e, ctx, settings(name, opt))


# --------------------------------------------------------------------------
# the library
# --------------------------------------------------------------------------

def _stack(o, n, anchor):
    """n lines, one under the other, centred on o["cy"]."""
    return [(o["cx"], o["cy"] + (i - (n - 1) / 2.0) * o["gap"], anchor, 0.0)
            for i in range(n)]


@register("plain", hold=2.7, out=0.8, cx=0.5, cy=0.5, gap=0.13)
def _plain(o, n):
    """Type fades up over the picture, holds, fades out. The default."""
    return _stack(o, n, "mm")


@register("lower_third", hold=2.7, out=0.8, cx=0.08, cy=0.80, gap=0.10)
def _lower_third(o, n):
    """Left-aligned near the bottom, out of the way of a face."""
    return _stack(o, n, "lm")


@register("corner", hold=2.5, out=0.6, cx=0.955, cy=0.90, gap=0.10)
def _corner(o, n):
    """Right-aligned at the bottom. What an end card usually wants."""
    return _stack(o, n, "rm")


def _colour_treat(im, e, ctx, o):
    """The picture goes away under flat colour, so the type sits on nothing."""
    flat = Image.new("RGB", (ctx["w"], ctx["h"]), o["colour"] or ctx["ink"])
    return Image.blend(im, flat, e), (0.0, 0.0)


@register("over_colour", fix=0.6, hold=3.0, out=0.8, treat=_colour_treat,
          cx=0.5, cy=0.5, gap=0.13, colour=None)
def _over_colour(o, n):
    """The picture goes under flat colour and the type sits on that.

    FOR A TITLE THAT IS NOT OVER ANYTHING. The colour arrives across `fix`
    seconds, so the first shot is still seen before the card takes it.
    """
    return _stack(o, n, "mm")


# --------------------------------------------------------------------------
# THE SIGNATURE CARD, kept because it is good and demoted because it is one
# season's. The frame opens BROKEN along a hard diagonal -- slipped, out of
# sync with itself and drained of colour -- and all three faults resolve
# together as the type lands. A season needs a signature that recurs; this was
# that season's, and it should not be everybody's by default.
# --------------------------------------------------------------------------

_DIAG: dict[tuple, Image.Image] = {}


def diag_mask(w, h, k):
    key = (w, h, k)
    m = _DIAG.get(key)
    if m is None:
        c = w / 2 + k * h / 2
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).polygon(
            [(0, 0), (c, 0), (c - k * h, h), (0, h)], fill=255)
        _DIAG[key] = m
    return m


def _break_treat(im, e, ctx, o):
    """Two copies of the picture, offset either side of a hard diagonal."""
    w, h = ctx["w"], ctx["h"]
    e = 1.0 - (1.0 - e) ** 3
    r = 1.0 - e
    d = o["slip"] * w * r
    sk = int(round(o["skew"] * r))
    a = ctx["neighbour"](-sk)
    b = ctx["neighbour"](sk)
    if r > 0.001:
        b = Image.blend(b, ctx["flatten"](b), r * 0.85)
    n = math.hypot(1.0, o["k"])
    ox, oy = d / n, d * o["k"] / n
    a = ImageChops.offset(a, int(round(-ox)), int(round(-oy)))
    b = ImageChops.offset(b, int(round(ox)), int(round(oy)))
    out = Image.composite(a, b, diag_mask(w, h, o["k"]))
    if r > 0.02:
        c = w / 2 + o["k"] * h / 2
        ImageDraw.Draw(out).line([(c, 0), (c - o["k"] * h, h)],
                                 fill=ctx["cream"], width=o["seam"])
    return out, (ox, oy)


@register("break_diagonal", fix=2.1, hold=2.7, out=0.8, treat=_break_treat,
          k=0.42, slip=0.060, skew=9, seam=2, cx1=0.30, cy1=0.30,
          cx2=0.52, cy2=0.68)
def _break_diagonal(o, n):
    """The frame opens broken along a diagonal and resolves as the type lands.

    THE TWO LINES SIT EITHER SIDE OF THE BREAK and are displaced with it in
    opposite directions, which is why this card declares explicit positions
    rather than a stack: the layout IS the device. It wants exactly two lines.

    THE SLIP IS THE HORIZONTAL COMPONENT of the displacement along the
    diagonal, and it is largest on the first frame. limit() charges the type
    for it, which is the whole reason it is declared here rather than assumed
    to be zero.

    cx2 IS 0.52 AND NOT 0.60 ON PURPOSE. Holding 0.60 forces the type down to
    0.63w to stay on frame, and the title should not shrink to pay for a
    horizontal push that is not doing the work: what puts the second line on
    the far side of the break is its VERTICAL position, not its x.
    """
    slip = o["slip"] / math.hypot(1.0, o["k"])
    return [(o["cx1"], o["cy1"], "mm", -slip),
            (o["cx2"], o["cy2"], "mm", slip)]


def main() -> int:
    print(f"  {len(CARDS)} card(s):\n")
    for name in sorted(CARDS):
        c = CARDS[name]
        d = c["defaults"]
        print(f"  {name:<16} {c['doc']}")
        print(f"  {'':<16} {d['fix'] + d['hold'] + d['out']:.1f}s on screen "
              f"(fix {d['fix']:.1f} + hold {d['hold']:.1f} + out {d['out']:.1f})"
              + ("   treats the picture" if c["treat"] else ""))
        rest = {k: v for k, v in sorted(d.items())
                if k not in ("fix", "hold", "out")}
        if rest:
            print(f"  {'':<16} settings: "
                  + ", ".join(f"{k}={v!r}" for k, v in rest.items()))
    print("\n  Named in identity.py:  TITLE_CARD = \"plain\"\n"
          "                         TITLE_CARD_OPTS = {\"cy\": 0.44}\n"
          "                         END_CARD_STYLE = \"corner\"")
    if "--sheet" not in sys.argv:
        return 0

    from PIL import ImageFont
    import season_paths
    w, h = 480, 360
    try:
        f1 = ImageFont.truetype(season_paths.font("arialbd.ttf"), 34)
        f2 = ImageFont.truetype(season_paths.font("arialbd.ttf"), 26)
    except SystemExit:
        f1 = f2 = ImageFont.load_default()

    def text(im, s, font, cx, cy, stroke, anchor="mm", alpha=1.0):
        lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(lay).text((cx, cy), s, font=font, anchor=anchor,
                                 fill=(247, 240, 224, int(255 * alpha)),
                                 stroke_width=stroke,
                                 stroke_fill=(24, 20, 18, int(255 * alpha)))
        return Image.alpha_composite(im.convert("RGBA"), lay).convert("RGB")

    base = Image.new("RGB", (w, h), (58, 92, 84))
    d = ImageDraw.Draw(base)
    for i in range(0, w, 48):
        d.line([(i, 0), (i, h)], fill=(84, 122, 112), width=2)
    ctx = {"w": w, "h": h, "text": text, "fonts": [f1, f2], "stroke": 2,
           "cream": (247, 240, 224), "ink": (24, 20, 18),
           "flatten": lambda im: im.convert("L").convert("RGB"),
           "fit": lambda im, pw, ph: im.resize((pw, ph), Image.LANCZOS),
           "neighbour": lambda dj: base.copy()}
    names = sorted(CARDS)
    steps = [0.0, 0.5, 1.0]
    sheet = Image.new("RGB", (w * len(steps), (h + 18) * len(names)),
                      (16, 16, 18))
    dd = ImageDraw.Draw(sheet)
    for r, name in enumerate(names):
        y = r * (h + 18)
        dd.text((6, y + 4), name, fill="#ffdd99")
        for c, e in enumerate(steps):
            im, off = treat(name, base.copy(), e, ctx)
            im = draw(name, im, ["SESSION #3", "THE HARBOUR"], ctx,
                      min(1.0, e * 1.6), off)
            sheet.paste(im, (c * w, y + 18))
        for cx, cy, anch, sl in layout(name, 2):
            dd.text((w * len(steps) - 190, y + 4),
                    f"limit {limit(cx, anch, sl):.2f}w", fill="#8899aa")
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    dst = os.path.join(ROOT, "out", "cards.png")
    sheet.save(dst)
    print(f"\n  {len(names)} card(s) x {len(steps)} steps -> {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
