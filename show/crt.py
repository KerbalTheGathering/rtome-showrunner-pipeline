"""The tube. Everything that turns a flat render into a picture on a CRT.

SPLIT OUT OF assemble.py because it grew from three lines into a chain, and
because tvtest.py has to be able to run it at several strengths on one frame
without dragging the whole bake with it.

THE ORDER IS PHYSICAL AND IT IS THE WHOLE TRICK. A CRT look assembled in the
wrong order reads as a filter laid on top of a digital image; assembled in the
order the signal actually travels it reads as a photograph of a television.

    1. SIGNAL    horizontal luma bandwidth, chroma bandwidth, colour-carrier
                 misregistration. This is the broadcast chain, and it happens
                 BEFORE anything to do with the screen.
    2. LEVELS    lifted black, warm phosphor, oversaturated colour. A tube in a
                 lit room has never shown a true black in its life.
    3. BLOOM     highlights spilling past their own edges through the glass.
    4. ROLL      vertical hold failing and recovering as the set cuts in. A SYNC
                 fault, so it moves the picture and not the raster -- it happens
                 before the geometry and the scanlines stay where they are.
    5. CURVE     the tube's geometry -- and the black rounded corners, which are
                 the single strongest tell that this is a box and not a window.
    6. MASK      scanlines and aperture grille, drawn in SCREEN space (see
                 below), plus the edge falloff that hugs the curved boundary.
    7. HUM       a slow bright band rolling up the picture, mains frequency
                 beating against the field rate.
    8. CABINET   bezel, inner lip, and a reflection in the glass. This is the
                 only step that is about the ROOM rather than the signal.

THE PICTURE IS RENDERED SMALL AND THE CABINET IS DRAWN AROUND IT, rather than a
bezel being laid over a full-size frame. Overlaying would crop the outer six
percent, and the board type is right-aligned near the right edge -- the frame
that loses "$300" to a bezel is the frame the whole segment exists for. So the
tube is rendered at the opening's size and composited in. Everything inside it
stays whole, and the scanlines land at native pixel pitch instead of being
resampled by a downscale.

MASK AFTER CURVE, NOT BEFORE, AND THAT IS A DELIBERATE INACCURACY. On a real
tube the phosphor stripes are ON the curved glass, so they curve too. Warping
them here means resampling a 4-pixel pattern through a near-identity transform,
which beats against itself and lays blotchy moire across the picture. Flat
scanlines over a curved image are very hard to notice; moire is not.

THE GRILLE IS MOSTLY LUMA, NOT RGB, AND THAT IS FORCED BY THE CODEC. A true
phosphor triad is pure chroma detail at a 3-pixel pitch, and every one of these
files is yuv420p -- chroma is subsampled 2x horizontally before it is even
quantised, so an RGB triad arrives at the viewer as grey mush plus artefacts.
So the grille darkens between stripes (luma, which survives) and only tints
them (chroma, which does not). TINT is how much of the lie you want.

    from crt import tube, PRESETS
    im = tube(im, "tube", frame_index)
"""
from __future__ import annotations

import math

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import identity                                    # noqa: E402

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

# --------------------------------------------------------------------------
# presets
# --------------------------------------------------------------------------
#
# hsoft        horizontal luma bandwidth, as a fraction of full. NTSC active
#              luma is about 440 samples across a line, which on a 1440-wide
#              frame would be 0.30 -- unusably soft for a show whose entire
#              point is a legible number on a board. These are compromises.
# bleed        chroma horizontal resolution divisor. 4 means the colour is
#              carried at a quarter of the luma's detail, which is roughly
#              honest and is what makes red edges smear.
# chroma       subpixel Cb/Cr misregistration, the coloured fringe on an edge.
# lift         black level. A CRT's black is the grey of unlit phosphor.
# warm/sat     phosphor cast and NTSC's famously hot colour.
# bloom*       highlight spill: strength, gaussian radius, luma threshold.
# curve        barrel constant. The bulge.
# zoom         overscan. Consumer sets threw 5-10% of the picture off the edge
#              of the tube; here it also stops the curve from opening black
#              slivers along the straight edges, leaving black only in corners.
# scan*        scanline depth and pitch in pixels. 2.25 puts 480 lines on a
#              1080-tall frame, which is what NTSC actually had.
# grille*      aperture grille depth and pitch, and TINT (see the header).
# gain         how much of the mask's overall dimming to claw back. 1.0 keeps
#              the original brightness and clips highlights; less leaves it
#              reading dimmer, which is what a tube looks like.
# vig          corner falloff. edge is the darkening right at the glass rim.
# hum          rolling bright band: depth, then seconds for one pass up frame.
# roll         frames of failing vertical hold at the head of a segment, the
#              cycles it travels in that time, and the darkness of the blanking
#              bar riding the seam. Eases out, so it slows into the lock.
# bezel        cabinet inset per side, as a fraction. sheen is the reflection.

PRESETS: dict[str, dict] = {
    # What shipped: fine scanlines, a one-pixel smear, a mild vignette. Kept so
    # the comparison sheet has an honest "before" and not a reconstruction.
    "signed": dict(
        hsoft=1.00, bleed=0, chroma=1.0,
        lift=0.000, warm=0.00, sat=1.06,
        bloom=0.00, bloom_r=6, bloom_thr=0.65,
        curve=0.000, zoom=1.00,
        scan=0.055, scan_pitch=2.0,
        grille=0.00, grille_pitch=4.0, tint=0.0,
        gain=0.0,
        vig=0.16, edge=0.00,
        hum=0.000, hum_secs=7.0,
        roll=0, roll_cycles=1.15, roll_bar=0.0,
        bezel=0.000, sheen=0.000,
    ),
    # The recommendation. Reads unmistakably as a tube from across a room and
    # still lets you read "$300" without leaning in.
    "tube": dict(
        hsoft=0.82, bleed=4, chroma=1.4,
        lift=0.045, warm=0.02, sat=1.12,
        bloom=0.22, bloom_r=7, bloom_thr=0.62,
        curve=0.090, zoom=1.10,
        scan=0.20, scan_pitch=2.25,
        grille=0.10, grille_pitch=4.0, tint=0.45,
        gain=0.85,
        vig=0.22, edge=0.45,
        hum=0.022, hum_secs=7.0,
        roll=14, roll_cycles=1.15, roll_bar=0.12,
        bezel=0.055, sheen=0.055,
    ),
    # Further: a smaller, older, more tired set. Softer signal, deeper lines,
    # more bulge. Costs legibility on the two information lines.
    "heavy": dict(
        hsoft=0.68, bleed=6, chroma=2.0,
        lift=0.062, warm=0.035, sat=1.18,
        bloom=0.32, bloom_r=9, bloom_thr=0.55,
        curve=0.135, zoom=1.14,
        scan=0.32, scan_pitch=2.25,
        grille=0.18, grille_pitch=4.0, tint=0.55,
        gain=0.80,
        vig=0.30, edge=0.60,
        hum=0.035, hum_secs=6.0,
        roll=14, roll_cycles=1.15, roll_bar=0.12,
        bezel=0.055, sheen=0.055,
    ),
}

# 5.5% PER SIDE, NOT THE 6% THE SHEET OFFERED, and the difference is the number.
# The cabinet costs the picture 11% of its width, which the two information
# lines can afford and "$200 AND A CABIN" -- the longest money line in the reel,
# already width-limited on the felt before any of this -- very nearly cannot.
# Checked against that line rather than against a comfortable one.

# THE SEASON'S RATE, DERIVED. `24` was typed in eleven files beside a
# season_identity.FPS that already said so -- and feature.py asserts every
# part matches, so a season at another rate would have been caught only
# after every part was baked.
FPS = float(identity.season.FPS)

_LUT: dict[tuple, list[int]] = {}
_MASK: dict[tuple, np.ndarray] = {}
_MESH: dict[tuple, list] = {}
_HUM: dict[tuple, np.ndarray] = {}
_CAB: dict[tuple, tuple] = {}


def _key(name: str, w: int, h: int) -> tuple:
    return (name, w, h)


# --------------------------------------------------------------------------
# 1. signal
# --------------------------------------------------------------------------

def _signal(im: Image.Image, P: dict) -> Image.Image:
    """Bandwidth-limit luma and chroma separately, then misregister the colour.

    Done in YCbCr because that is where the losses actually happen. Blurring
    RGB would soften the picture; blurring only Cb and Cr smears the COLOUR
    across a sharp edge, which is the thing you recognise.
    """
    w, h = im.size
    y, cb, cr = im.convert("YCbCr").split()

    if P["hsoft"] < 1.0:
        nw = max(2, int(round(w * P["hsoft"])))
        y = y.resize((nw, h), Image.BILINEAR).resize((w, h), Image.BILINEAR)

    if P["bleed"] > 1:
        nw = max(2, w // int(P["bleed"]))
        cb = cb.resize((nw, h), Image.BILINEAR).resize((w, h), Image.BILINEAR)
        cr = cr.resize((nw, h), Image.BILINEAR).resize((w, h), Image.BILINEAR)

    d = P["chroma"]
    if d:
        # fillcolor=128 is NEUTRAL grey in a chroma plane. The default 0 would
        # paint a hard green column down one edge and magenta down the other --
        # invisible in a thumbnail, lurid at full size. The overscan crop would
        # have hidden it anyway; relying on that is how it survives to a preset
        # with less zoom.
        cb = cb.transform((w, h), Image.AFFINE, (1, 0, d, 0, 1, 0),
                          Image.BILINEAR, fillcolor=128)
        cr = cr.transform((w, h), Image.AFFINE, (1, 0, -d, 0, 1, 0),
                          Image.BILINEAR, fillcolor=128)

    return Image.merge("YCbCr", (y, cb, cr)).convert("RGB")


# --------------------------------------------------------------------------
# 2. levels -- a 256-entry lookup per channel, built once
# --------------------------------------------------------------------------

def _lut(name: str, P: dict) -> list[int]:
    got = _LUT.get(name)
    if got is not None:
        return got
    lift, warm = P["lift"], P["warm"]
    tint = (1.0 + warm, 1.0 + warm * 0.15, 1.0 - warm)
    table: list[int] = []
    for c in range(3):
        for i in range(256):
            x = i / 255.0
            x = lift + (1.0 - lift) * x            # unlit phosphor is not black
            x = min(1.0, x * tint[c])
            table.append(int(round(x * 255)))
    _LUT[name] = table
    return table


# --------------------------------------------------------------------------
# 3. bloom
# --------------------------------------------------------------------------

def _bloom(im: Image.Image, P: dict) -> Image.Image:
    s = P["bloom"]
    if s <= 0:
        return im
    a = np.asarray(im, np.float32) / 255.0
    lum = a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114
    thr = P["bloom_thr"]
    m = np.clip((lum - thr) / max(1e-3, 1.0 - thr), 0.0, 1.0)
    hi = (a * m[..., None] * 255.0).astype(np.uint8)
    g = np.asarray(
        Image.fromarray(hi, "RGB").filter(ImageFilter.GaussianBlur(P["bloom_r"])),
        np.float32) / 255.0
    # Screen, not add: glass scatters light onto a lit area without ever
    # pushing it past white, and add clips into flat white plates.
    out = 1.0 - (1.0 - a) * (1.0 - np.clip(g * s, 0.0, 1.0))
    return Image.fromarray((out * 255.0 + 0.5).astype(np.uint8), "RGB")


# --------------------------------------------------------------------------
# 4. vertical roll on the cut-in
# --------------------------------------------------------------------------

def _roll(im: Image.Image, P: dict, i: int) -> Image.Image:
    """Vertical hold failing and recovering as the set arrives on the segment.

    EASED, NOT LINEAR. A constant-speed roll that stops dead is a scrolling
    graphic; a real vertical hold drifts fast, slows, and settles, so the
    displacement decays as a square and the picture creeps the last few pixels
    into place. It travels 1.15 frame heights, which crosses the seam exactly
    once -- one roll, not a flutter and not a spin.

    Content wraps, and the join between the bottom of one field and the top of
    the next is DARK: that gap is the vertical blanking interval, and without it
    the wrap looks like a torn JPEG rather than a television.
    """
    n = P["roll"]
    if not n or i >= n:
        return im
    h = im.height
    p = i / float(n)
    off = int(round(h * P["roll_cycles"] * (1.0 - p) ** 2)) % h
    if not off:
        return im
    a = np.roll(np.asarray(im), off, axis=0)
    k = P["roll_bar"]
    if k:
        # SCALED TO THE PICTURE, not a fixed pixel count. Seventeen rows was the
        # first guess and it disappeared: a bar has to be a few percent of the
        # height to read as blanking rather than as a compression seam.
        g = max(6, int(round(h * 0.022)))
        d = np.arange(-g, g + 1)
        prof = k + (1.0 - k) * (np.abs(d) / (g + 1.0)) ** 1.5
        bar = np.ones(h, np.float32)
        rows = (off + d) % h
        bar[rows] = np.minimum(bar[rows], prof.astype(np.float32))
        a = (a * bar[:, None, None]).astype(np.uint8)
    return Image.fromarray(a, "RGB")


# --------------------------------------------------------------------------
# 5. curvature
# --------------------------------------------------------------------------

def _src(x: float, y: float, w: int, h: int, k: float, z: float) -> tuple:
    """Where on the flat render a point on the curved glass is looking."""
    u = (x / (w / 2.0) - 1.0) / z
    v = (y / (h / 2.0) - 1.0) / z
    f = 1.0 + k * (u * u + v * v)
    return ((u * f + 1.0) * w / 2.0, (v * f + 1.0) * h / 2.0)


def _mesh(name: str, w: int, h: int, P: dict) -> list:
    """A quad mesh approximating the barrel warp.

    PIL's MESH transform is C and takes about a millisecond; doing the same
    remap in numpy per frame costs a quarter of a second, times two and a half
    thousand frames. The warp varies smoothly, so a 36-pixel cell is far below
    the visible error.
    """
    key = _key(name, w, h)
    got = _MESH.get(key)
    if got is not None:
        return got
    k, z = P["curve"], P["zoom"]
    nx, ny = max(1, w // 36), max(1, h // 36)
    data = []
    for j in range(ny):
        for i in range(nx):
            x0, x1 = w * i / nx, w * (i + 1) / nx
            y0, y1 = h * j / ny, h * (j + 1) / ny
            nw_ = _src(x0, y0, w, h, k, z)
            sw_ = _src(x0, y1, w, h, k, z)
            se_ = _src(x1, y1, w, h, k, z)
            ne_ = _src(x1, y0, w, h, k, z)
            data.append(((int(x0), int(y0), int(math.ceil(x1)),
                          int(math.ceil(y1))),
                         nw_ + sw_ + se_ + ne_))
    _MESH[key] = data
    return data


# --------------------------------------------------------------------------
# 6. mask -- scanlines, grille, coverage, edge falloff, vignette
# --------------------------------------------------------------------------

def _mask(name: str, w: int, h: int, P: dict) -> np.ndarray:
    key = _key(name, w, h)
    got = _MASK.get(key)
    if got is not None:
        return got

    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)

    # scanlines: a soft beam profile, not alternating rows. Alternating rows at
    # a 1-pixel pitch is a texture; a cosine at 2.25 is a raster.
    line = 0.5 + 0.5 * np.cos(2.0 * math.pi * yy / P["scan_pitch"])
    line = 1.0 - P["scan"] * (1.0 - line)

    gp = P["grille_pitch"]
    lum = 1.0 - P["grille"] * (
        1.0 - (0.5 + 0.5 * np.cos(2.0 * math.pi * xx / gp)))
    cols = np.stack(
        [1.0 - P["grille"] * (1.0 - (0.5 + 0.5 * np.cos(
            2.0 * math.pi * (xx - p) / gp))) for p in (0.0, gp / 3.0, 2 * gp / 3.0)],
        axis=1)
    t = P["tint"]
    grille = (1.0 - t) * lum[:, None] + t * cols            # (w, 3)

    m = line[:, None, None] * grille[None, :, :]
    if P["gain"]:
        m = m * (1.0 / float(m.mean())) ** P["gain"]

    u = xx / (w - 1.0) * 2.0 - 1.0
    v = yy / (h - 1.0) * 2.0 - 1.0

    # COVERAGE is computed from the same warp the mesh uses, not guessed. It is
    # what antialiases the tube's rounded corner: the mesh transform fills
    # out-of-range with hard black, and a hard black arc across a 1440-wide
    # frame stairsteps visibly.
    k, z = P["curve"], P["zoom"]
    su = u[None, :] / z
    sv = v[:, None] / z
    f = 1.0 + k * (su * su + sv * sv)
    su, sv = su * f, sv * f
    inside = np.minimum(1.0 - np.abs(su), 1.0 - np.abs(sv)) * (w / 2.0)
    cover = np.clip(inside / 1.5 + 0.5, 0.0, 1.0)
    if P["edge"]:
        cover = cover * (1.0 - P["edge"] * (1.0 - np.clip(inside / 16.0, 0.0, 1.0)))

    r = np.sqrt(u[None, :] ** 2 + v[:, None] ** 2) / math.sqrt(2.0)
    vig = 1.0 - P["vig"] * np.clip(r - 0.42, 0.0, None) / 0.58

    m = (m * (cover * vig)[:, :, None]).astype(np.float32)
    _MASK[key] = m
    return m


# --------------------------------------------------------------------------
# 7. hum bar
# --------------------------------------------------------------------------

def _hum(name: str, h: int, P: dict, i: int) -> np.ndarray | None:
    """A soft bright band drifting up the picture once every hum_secs.

    NOT an interlace flicker, which is the other obvious thing to reach for and
    is wrong: alternating the field phase per frame at 24fps is a 12 Hz strobe,
    and 12 Hz on a modern panel is a headache rather than a memory.
    """
    if not P["hum"]:
        return None
    period = max(1, int(round(P["hum_secs"] * FPS)))
    key = (name, h, i % period)
    got = _HUM.get(key)
    if got is not None:
        return got
    yy = np.arange(h, dtype=np.float32) / h
    p = (yy + (i % period) / period) % 1.0
    band = np.exp(-(((p - 0.5) / 0.16) ** 2))
    out = (1.0 + P["hum"] * band).astype(np.float32)[:, None, None]
    _HUM[key] = out
    return out


# --------------------------------------------------------------------------
# 8. cabinet -- bezel, inner lip, reflection
# --------------------------------------------------------------------------

def _screen(W: int, H: int, b: float) -> tuple[int, int]:
    w, h = int(round(W * (1.0 - 2 * b))), int(round(H * (1.0 - 2 * b)))
    return w - w % 2, h - h % 2


def _cabinet(name: str, W: int, H: int, P: dict) -> tuple:
    """The plastic, the opening, and the reflection. Built once per size."""
    key = _key(name, W, H)
    got = _CAB.get(key)
    if got is not None:
        return got

    w, h = _screen(W, H, P["bezel"])
    x0, y0 = (W - w) // 2, (H - h) // 2

    # Plastic, lit from above the way a set in a room is. Not a flat fill: a
    # perfectly even bezel reads as a matte laid on the video, which is the
    # exact impression this is meant to destroy.
    vy = (np.arange(H, dtype=np.float32) / H)[:, None]
    top = np.array([46.0, 43.0, 41.0], np.float32)
    bot = np.array([17.0, 16.0, 17.0], np.float32)
    bg = top * (1.0 - vy)[..., None] + bot * vy[..., None]      # (H,1,3)
    bg = np.repeat(bg, W, axis=1)
    ux = np.abs(np.arange(W, dtype=np.float32) / (W - 1.0) * 2.0 - 1.0)
    bg *= (1.0 - 0.35 * np.clip(ux - 0.80, 0, None) / 0.20)[None, :, None]

    # The opening, antialiased by drawing it four times oversize. A hard-edged
    # rounded rect at this radius stairsteps along the curve, and a stairstepped
    # bezel is worse than no bezel.
    S = 4
    m = Image.new("L", (W * S, H * S), 0)
    r = int(min(w, h) * 0.085) * S
    ImageDraw.Draw(m).rounded_rectangle(
        [x0 * S, y0 * S, (x0 + w) * S - 1, (y0 + h) * S - 1], radius=r, fill=255)
    open_ = np.asarray(m.resize((W, H), Image.LANCZOS), np.float32) / 255.0

    # A bevelled lip around the opening, bright at the top and dark at the
    # bottom -- the only thing in the cabinet that says which way is up.
    m2 = Image.new("L", (W * S, H * S), 0)
    g = 7 * S
    ImageDraw.Draw(m2).rounded_rectangle(
        [x0 * S - g, y0 * S - g, (x0 + w) * S - 1 + g, (y0 + h) * S - 1 + g],
        radius=r + g, fill=255)
    lip = np.clip(np.asarray(m2.resize((W, H), Image.LANCZOS), np.float32) / 255.0
                  - open_, 0.0, 1.0)
    lipcol = (92.0 - 74.0 * vy)[..., None]
    bg = bg * (1.0 - lip[..., None]) + lipcol * lip[..., None]

    # The reflection: a wide soft band and a narrow bright one, up and to the
    # left, static because a window does not move when the picture does.
    u = np.arange(w, dtype=np.float32) / w
    v = np.arange(h, dtype=np.float32) / h
    d = 0.72 * (1.0 - u)[None, :] + 0.68 * (1.0 - v)[:, None]
    band = (np.exp(-(((d - 1.02) / 0.19) ** 2)) * 0.62 +
            np.exp(-(((d - 1.20) / 0.055) ** 2)) * 0.38)
    sheen = (band * P["sheen"] * 255.0).astype(np.float32)[:, :, None]

    got = (bg.astype(np.float32), open_.astype(np.float32), sheen, x0, y0, w, h)
    _CAB[key] = got
    return got


def _fit(name: str, a: np.ndarray, W: int, H: int, P: dict) -> Image.Image:
    bg, open_, sheen, x0, y0, w, h = _cabinet(name, W, H, P)
    out = bg.copy()
    sub = out[y0:y0 + h, x0:x0 + w]
    mm = open_[y0:y0 + h, x0:x0 + w][..., None]
    # ADDITIVE, not screen: a reflection is light arriving at the glass from the
    # room, so it lifts the black corners as much as the picture. Screening it
    # would leave the corners perfectly black and only the bright areas lit,
    # which is what a reflection never does.
    lit = np.clip(a + sheen, 0.0, 255.0)
    out[y0:y0 + h, x0:x0 + w] = lit * mm + sub * (1.0 - mm)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


# --------------------------------------------------------------------------

def tube(im: Image.Image, name: str = "tube", i: int = 0) -> Image.Image:
    """Put one frame on the television. `i` is the frame index, for the hum."""
    P = PRESETS[name]
    W, H = im.size
    b = P["bezel"]
    if b:
        w, h = _screen(W, H, b)
        im = im.resize((w, h), Image.LANCZOS)
    else:
        w, h = W, H

    im = _signal(im, P)
    if P["lift"] or P["warm"]:
        im = im.point(_lut(name, P))
    if P["sat"] != 1.0:
        im = ImageEnhance.Color(im).enhance(P["sat"])
    im = _bloom(im, P)
    im = _roll(im, P, i)
    if P["curve"]:
        im = im.transform((w, h), Image.MESH, _mesh(name, w, h, P), Image.BICUBIC)

    a = np.asarray(im, np.float32) * _mask(name, w, h, P)
    hum = _hum(name, h, P, i)
    if hum is not None:
        a = a * hum
    if not b:
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")
    return _fit(name, a, W, H, P)
