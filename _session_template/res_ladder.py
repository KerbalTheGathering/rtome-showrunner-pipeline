"""Does the style LoRA's texture actually hold detail at 720p vs 1080p? Free test, no API.

THE QUESTION. Buying 1080p instead of 720p costs +$28.55 across the season. That is only
worth paying if the style has detail up there to resolve. Photoreal would; a watercolour
illustration might not, and its one high-frequency feature -- paper grain -- is a thing we
have previously had to SUPPRESS with temporal denoise, so resolving more of it may be a
cost rather than a gain.

WHY THIS IS A FAIR PROXY AND WHERE IT IS NOT. The plate is 2432x1664, far above every
candidate, so downsampling it to each delivery size and back reproduces exactly the
detail loss the delivery size imposes. What it does NOT reproduce is Seedance's own
resampling and temporal compression, which can only make the real clip WORSE than this.
So this is an upper bound on the benefit: whatever difference you cannot see here, you
will certainly not see in the finished film.

Writes one strip per beat: the same 1:1 crop at each delivery size, all brought back to
a common size so they are compared at equal display area -- which is the only honest way
to look at this. Comparing a small image to a big one just shows you which is bigger.
"""

import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_still  # noqa: E402
import shot       # noqa: E402  -- which beats this film actually has

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_res_ladder")

# Delivery sizes, 4:3, as ByteDance actually returns them. 480p is MEASURED (Session #1
# ships 960x714, which inverts through the old assemble formula to a 752x560 source);
# the other two are that same multiple-of-16 grid scaled by 1.5 and 2.25.
SIZES = [
    ("480p  (what we shipped)", 752, 560),
    ("720p  ($23.19)", 1120, 832),
    ("1080p ($51.74)", 1680, 1248),
]

# A 1:1 inspection crop, in FINAL-delivery coordinates at the largest size. Kept small so
# the strip shows real pixels rather than a thumbnail -- the difference between 720p and
# 1080p is invisible at any fit-to-screen zoom, which is rather the point.
CROP = 420

# WHICH BEATS TO SHOW THE LADDER ON. Two is enough and two is the point: one
# wide and one close, because the resolution argument looks completely
# different on each. Taken from this film's OWN cut -- it was `["12", "01"]`,
# and beat 12 is a beat of the film this file was copied from. On a session
# with fewer than twelve beats gen_still.plate() exits with "no plate for beat
# '12'", which is the good case; on one with twelve it silently prices the
# wrong picture.
BEATS = [shot.CUT[0], shot.CUT[len(shot.CUT) // 2]] if len(shot.CUT) > 1 \
    else list(shot.CUT)


def ladder(sid: str) -> None:
    src = gen_still.plate(sid)
    im = Image.open(src).convert("RGB")

    # Centre-crop the plate to 4:3 first -- this is the same crop Seedance applies, so
    # the comparison starts from the frame we will actually be sold.
    w, h = im.size
    tw = min(w, int(h * 4 / 3))
    th = min(h, int(tw * 3 / 4))
    im = im.crop(((w - tw) // 2, (h - th) // 2, (w - tw) // 2 + tw, (h - th) // 2 + th))

    big_w, big_h = SIZES[-1][1], SIZES[-1][2]
    cx, cy = big_w // 2, int(big_h * 0.42)   # slightly above centre: faces sit there
    box = (cx - CROP // 2, cy - CROP // 2, cx + CROP // 2, cy + CROP // 2)

    tiles = []
    for label, dw, dh in SIZES:
        # down to the delivery size, then back up to the largest -- exactly what the
        # eye does when all three are played on the same screen.
        small = im.resize((dw, dh), Image.LANCZOS)
        shown = small.resize((big_w, big_h), Image.LANCZOS)
        tiles.append((label, shown.crop(box)))

    pad, bar = 12, 30
    strip = Image.new("RGB", (CROP * len(tiles) + pad * (len(tiles) + 1),
                              CROP + bar + pad * 2), (24, 24, 24))
    d = ImageDraw.Draw(strip)
    for i, (label, tile) in enumerate(tiles):
        x = pad + i * (CROP + pad)
        strip.paste(tile, (x, pad))
        d.text((x + 4, pad + CROP + 6), label, fill=(235, 235, 235))

    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, f"ladder_{sid}.png")
    strip.save(dst)
    print(f"  beat {sid}: {os.path.basename(src)} -> {os.path.basename(dst)}")


def main() -> int:
    for sid in BEATS:
        ladder(sid)
    print(f"\n  {OUT}   -- 1:1 crops, equal display area, no API spend")
    return 0


if __name__ == "__main__":
    sys.exit(main())
