"""Where the tools and the machine live. The only file with a path in it.

EVERY SCRIPT IN THIS REPO USED TO CARRY ITS OWN COPY of the ffmpeg directory,
the ComfyUI root and the font folder -- thirty-nine hard-coded absolute paths
across forty files, all of them pointing at one particular Windows box. That is
fine for one machine and useless to anybody else, and it is the same shape of
problem as identity being typed in five files: a value that means one thing,
written down in many places.

So it is stated once, here, and every path is overridable from the ENVIRONMENT
so you never have to edit a tracked file to run this on your own machine.

    set SEASON_FFMPEG=C:\\ffmpeg\\bin
    set SEASON_COMFYUI=D:\\ComfyUI\\ComfyUI
    set SEASON_DELIVER=%USERPROFILE%\\Videos

or on a POSIX box:

    export SEASON_FFMPEG=/usr/bin
    export SEASON_COMFYUI=$HOME/ComfyUI

    python season_paths.py        # print what this machine resolves to,
                                  # and say which pieces are missing
"""
from __future__ import annotations

import os
import shutil
import sys


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default) or default


# --------------------------------------------------------------------------
# ffmpeg
# --------------------------------------------------------------------------
#
# A DIRECTORY, not an executable, because every script needs both ffmpeg and
# ffprobe out of it. If ffmpeg is on PATH this resolves to wherever that is,
# which is the sane default on a POSIX box and often true on Windows too.
def _ffmpeg_dir() -> str:
    got = os.environ.get("SEASON_FFMPEG")
    if got:
        return got
    on_path = shutil.which("ffmpeg")
    if on_path:
        return os.path.dirname(on_path)
    return r"C:\ffmpeg\bin"


FFMPEG = _ffmpeg_dir()
EXE = ".exe" if os.name == "nt" else ""


def ff(tool: str = "ffmpeg") -> str:
    """Absolute path to ffmpeg or ffprobe, whichever this call wants."""
    return os.path.join(FFMPEG, tool + EXE)


# --------------------------------------------------------------------------
# ComfyUI
# --------------------------------------------------------------------------
COMFY = _env("SEASON_COMFYUI", r"C:\ComfyUI\ComfyUI")
COMFY_URL = _env("SEASON_COMFY_URL", "http://127.0.0.1:8188")
COMFY_INPUT = os.path.join(COMFY, "input")
COMFY_OUTPUT = os.path.join(COMFY, "output")

# CREDENTIALS ARE READ FROM THIS FILE AT RUNTIME AND NEVER PUT ON A COMMAND
# LINE. It holds `API_KEY=` (comfy.org) and `ELEVENLABS_API_KEY=`. It is not in
# this repo, it must never be committed, and .gitignore says so.
ENV_FILE = _env("SEASON_ENV", os.path.join(COMFY, ".env"))

# --------------------------------------------------------------------------
# Fonts and delivery
# --------------------------------------------------------------------------
FONT_DIR = _env("SEASON_FONTS",
                r"C:\Windows\Fonts" if os.name == "nt"
                else "/usr/share/fonts/truetype")

# Where finished work is copied. Defaults to a folder in the user's home rather
# than to a cloud drive -- the machine this was written on synced to
# a cloud-sync folder, which is a preference, not a fact about the pipeline.
DELIVER = _env("SEASON_DELIVER", os.path.join(os.path.expanduser("~"), "Videos"))


# --------------------------------------------------------------------------
# What this card can hold
# --------------------------------------------------------------------------
#
# BUDGET A SHOT IN `frames x (w/8) x (h/8)`. Measured on one 24GB card in one
# evening, with a WAN 2.1 14B model also resident in ComfyUI:
#
#     3.61M  thrashed twice, once for 33 minutes
#     2.95M  thrashed
#     2.77M  fine, twice
#     2.36M / 2.15M / 2.06M  fine
#
# The line is between 2.77M and 2.95M. I found it by guessing three times and
# being wrong twice, which is the argument for pick_canvas() existing: the
# ceiling is not a property of the card, it moves with whatever else is cached,
# and a per-clip judgement call is a coin toss that costs half an hour when it
# loses. THE TELL is SHARED GPU memory climbing while dedicated pins near
# 24 GB -- at 99% utilisation a thrash looks exactly like work, which is why
# the first one ran so long.
#
# IT LIVES HERE, ONCE, BECAUSE IT IS A FACT ABOUT THE MACHINE and not about any
# season. Two of the three h3_shoot.py copies had no budget at all and chose a
# canvas by hand with `--small`; one clip went over the line at 2.99M and took
# 12.7 minutes against 3.0 and 1.8 either side. Nothing failed and nothing
# warned. A third copy carried a DIFFERENT ceiling (3.7M) in a comment calling
# 3.61M "proven", which is the figure the measurements above say thrashed.
#
# Override on a bigger or smaller card without editing a tracked file:
#     set SEASON_LATENT_BUDGET_M=4.5
BUDGET_M = float(_env("SEASON_LATENT_BUDGET_M", "2.80"))

# H3's short edge caps at 768 and its long edge at 1024 on this stack. BOTH
# EDGES MUST BE MULTIPLES OF 32: 832x624 is true 4:3 with both edges multiples
# of 16 and dies instantly on a tensor-shape error.
SHORT_CAP, LONG_CAP = 768, 1024
CANVAS_LADDER = (1.0, 0.875, 0.75)


def _snap32(n: float) -> int:
    """Nearest multiple of 32, rounding a dead heat UP.

    `round()` IS BANKER'S ROUNDING and a dead heat is not a rare input here --
    every ratio whose short edge lands on x.5 steps hits it, and 2.40:1 does at
    400. Banker's sent that DOWN to 384 and half-up sends it to 416; neither is
    more correct as geometry, but "nearest, ties up" is what every reader
    assumes this function does, and a rounding rule nobody expects is a bad
    thing to have underneath a ladder.

    It matters less than it looks now that _fit_grid() below tries BOTH grid
    neighbours rather than trusting one snap. That is the real fix; this is
    just the function no longer surprising anybody.
    """
    return max(32, int(n / 32.0 + 0.5) * 32)


# HOW MANY 32-PIXEL STEPS THE SEARCH MAY GIVE UP TO BUY THE ASPECT. Two, and
# never upward: a rung that grows to find a better ratio stops descending, and
# the ladder exists to get UNDER the latent ceiling. Giving up 64px of long edge
# costs ~12% of the pixels and is what turns a 2.56% squash into an exact fit.
_GRID_BACKOFF = 2


def _fit_grid(long_target: float, ratio: float) -> tuple[int, int]:
    """The 32-grid (long, short) nearest `long_target` whose OWN ratio is nearest.

    SNAPPING TWO EDGES INDEPENDENTLY CANNOT PRESERVE AN ARBITRARY RATIO, and
    that is what this replaces -- see canvases() for what it cost. Searching a
    couple of steps down the long edge instead finds the pair that actually sits
    at the delivery aspect where one exists: 2.40:1 has an exact answer at
    960x400 and the independent snap returned 1024x416, which is 2.4615.

    Ties go to the LARGER canvas, so an aspect that already lands exactly keeps
    the biggest pair that does -- 4:3 stays 1024x768 rather than sliding to
    960x720.
    """
    l0 = _snap32(long_target)
    best = None
    for k in range(_GRID_BACKOFF + 1):
        lo = min(LONG_CAP, l0 - 32 * k)
        if lo < 32:
            break
        # BOTH GRID NEIGHBOURS, NOT ONE SNAP. A snap commits to whichever side
        # of the short edge is nearer in PIXELS, and the question here is which
        # side is nearer in RATIO -- not the same thing, and on a long aspect
        # one 32-step of short edge is several percent. Trying both is two
        # divisions and removes the rounding rule from the answer entirely.
        base = int(lo / ratio / 32.0) * 32
        for sh in (base, base + 32):
            if sh < 32 or sh > SHORT_CAP:
                continue
            # ROUNDED BEFORE COMPARING. Two pairs that are both exact differ in
            # the sixteenth decimal place on float division, and an unrounded
            # key makes the tie-break on area unreachable.
            key = (round(abs(lo / sh - ratio) / ratio, 6), -(lo * sh))
            if best is None or key < best[0]:
                best = (key, (lo, sh))
    if best is None:                      # an aspect so extreme the caps cross
        return max(32, l0), SHORT_CAP
    return best[1]


def canvases(w: int, h: int) -> tuple[tuple[int, int], ...]:
    """Render canvases at the DELIVERY aspect, largest first.

    DERIVED FROM THE SEASON'S OWN GEOMETRY rather than typed as three 4:3
    tuples. 1440x1080 already appears in season_identity, in dims() and in
    every contact sheet's tile geometry; three of those derive and this one did
    not, so a season that was not 4:3 would have rendered 4:3 sources and
    letterboxed itself at the bake without anything saying so.

    AND FOR FIVE SEASONS IT DID NOT RETURN THE DELIVERY ASPECT EITHER. It
    snapped both edges independently to a multiple of 32, which cannot preserve
    an arbitrary ratio, and nothing measured the result against the docstring
    above. Measured:

        4:3    1440x1080  ->  1024x768   0.00%
        16:9   1920x1080  ->  1024x576   0.00%
        2.39   1482x602   ->  1024x416  -0.01%
        2.40   2688x1120  ->  1024x416  +2.56%      <- squashed

    THAT IS WHY IT RAN CLEAN FOR FIVE SEASONS. 4:3 and 16:9 snap exactly, and
    the 2.39 season's own delivery was itself 2.4618:1 -- the canvas aspect --
    so its plates were already the shape the canvas wanted. The function had
    only ever been asked for aspects that happened to agree with it.

    Ask for a true 2.40 and every plate handed to the video model is squeezed
    2.56% before the model sees it. THE MODEL SQUASHES; IT DOES NOT CROP --
    measured on eight shots across four style LoRAs, clip frame zero against the
    plate resized three ways, and squash fit 2-3x better than either crop,
    8 of 8. Nothing in the bake un-squeezed it: fit_aspect() -> framing.apply()
    fits by CROPPING, which preserves the distortion and trims the edges too.

    The repo already knew this failure by name. at_aspect(), directly below,
    exists because a typed 768x576 "would have synced at 4:3 and been squashed
    on the way back out". The lip-sync path was fixed for exactly this. The
    plate path was not.

    SO: the long edge is searched a couple of 32-steps down, both short-edge
    neighbours are tried at each, and THE LADDER IS DERIVED FROM THE PAIR THAT
    WON rather than from the pre-search one. Measured after:

        4:3    1024x768  896x672  768x576     0.00%  0.00%  0.00%
        16:9   1024x576  864x480  736x416     0.00% +1.25% -0.48%
        2.39   1024x416  864x352  704x288    -0.01% -0.29% -0.70%
        2.40    992x416  832x352  704x288    -0.64% -1.52% +1.85%

    EVERY RUNG IS THE SAME OR BETTER and no rung 0 moved on a shape a season
    has actually shipped, which is the property that made this safe to change:
    4:3 and 16:9 and 2.39 all keep the canvas their existing clips were shot
    on. 16:9's lower rungs improve most (-3.57% to -0.48% at the bottom), and
    those are rungs pick_canvas() reaches on a long beat, so they were being
    used.

    A RESIDUAL SURVIVES AND IS SUPPOSED TO. 2.40's exact pair on a 32-grid is
    768x320, three quarters of the long edge -- a quarter of the resolution
    given up to save 0.64% of ratio, which is a bad trade when the bake can
    simply undo the squeeze. So the search is bounded and framing.unsqueeze()
    finishes the job at the bake, before any crop. What the search buys is that
    the model SEES something close to the composition it was handed, and that
    the un-squeeze is a 0.6% resample rather than a 2.6% one.

    `python season_paths.py` prints the error per rung, so a season whose
    aspect the grid handles badly can see it before it shoots anything.
    """
    ratio = max(w, h) / min(w, h)
    long0, _ = _fit_grid(min(LONG_CAP, _snap32(SHORT_CAP * ratio)), ratio)
    out = []
    for r in CANVAS_LADDER:
        lo, sh = _fit_grid(long0 * r, ratio)
        out.append((lo, sh) if w >= h else (sh, lo))
    return tuple(out)


def aspect_error(w: int, h: int) -> tuple[float, ...]:
    """How far each rung's own aspect sits from the delivery aspect, as a fraction.

    SIGNED, because the direction says which way the picture is distorted.
    Positive is a canvas WIDER than the delivery: the plate is stretched
    sideways to fill it, so everything in the delivered film comes back too
    wide by that fraction. Negative is the same fault the other way. Measured
    end to end on a drawn circle, 2.40 delivery: the canvas this returned
    before the search fix put a 1.030 circle on screen, and 0.990 after -- both
    1.000 once framing.unsqueeze() runs.

    Printed rather than asserted. A tolerance tight enough to catch the 2.40
    season (~0.2%) refuses 16:9's lower rungs, which are the best the 32-grid
    has and are corrected at the bake anyway -- and `docs/06_verification.md`
    is explicit that a check which refuses correct work costs as much as one
    that passes wrong work, because the response to it is to widen it until it
    stops complaining.
    """
    want = w / h
    return tuple((cw / ch - want) / want for cw, ch in canvases(w, h))


def at_aspect(w: int, h: int, pixels: int, multiple: int = 16) -> tuple[int, int]:
    """The size at the w:h aspect nearest `pixels`, both edges a multiple.

    FOR A MODEL WITH A NATIVE PIXEL COUNT RATHER THAN A NATIVE SIZE. The lip
    sync runs at 768x576 -- 4:3, both divisible by 16, about 10% over the 480p
    model's native count -- and that pair was typed, so a season that is not
    4:3 would have synced at 4:3 and been squashed on the way back out. The
    pixel budget is the fact about the model; the aspect is a fact about the
    season, and the size is what falls out of the two.

    For 4:3 at 768x576's own budget this returns 768x576 exactly.
    """
    scale = (pixels * w / h) ** 0.5
    cw = max(multiple, int(round(scale / multiple)) * multiple)
    ch = max(multiple, int(round(cw * h / w / multiple)) * multiple)
    return cw, ch


def latent_m(length: int, size: tuple[int, int]) -> float:
    """Millions of latent tokens for `length` frames on this canvas."""
    return length * (size[0] // 8) * (size[1] // 8) / 1e6


def pick_canvas(length: int, w: int, h: int,
                budget_m: float | None = None) -> tuple[int, int]:
    """Largest canvas at the delivery aspect whose latent stays under the
    ceiling. The smallest rung is returned even if it is over -- a refusal
    belongs in the caller, which knows what the clip is for."""
    ladder = canvases(w, h)
    for size in ladder:
        if latent_m(length, size) <= (budget_m or BUDGET_M):
            return size
    return ladder[-1]


def font(name: str) -> str:
    """A font file by name, from FONT_DIR. Fails loudly rather than at draw time.

    A MISSING FONT IS NOT A CRASH, IT IS A TOFU BOX IN A FINISHED FILM -- PIL
    will happily substitute and carry on. So it is checked here, once, where the
    message can say what to set.
    """
    p = os.path.join(FONT_DIR, name)
    if not os.path.exists(p):
        sys.exit(f"FAIL: no font at {p}\n"
                 f"  Set SEASON_FONTS to a directory containing {name}, or "
                 f"change the font this part asks for.")
    return p


def check() -> list[str]:
    """Everything this machine is missing, as a list of sentences."""
    bad = []
    for tool in ("ffmpeg", "ffprobe"):
        if not os.path.exists(ff(tool)):
            bad.append(f"{tool} not found at {ff(tool)} -- set SEASON_FFMPEG")
    if not os.path.isdir(COMFY):
        bad.append(f"ComfyUI not found at {COMFY} -- set SEASON_COMFYUI")
    if not os.path.exists(ENV_FILE):
        bad.append(f"no credentials file at {ENV_FILE} -- set SEASON_ENV. It "
                   f"needs API_KEY= and ELEVENLABS_API_KEY=")
    if not os.path.isdir(FONT_DIR):
        bad.append(f"no font directory at {FONT_DIR} -- set SEASON_FONTS")
    return bad


if __name__ == "__main__":
    print(f"  ffmpeg    {FFMPEG}")
    print(f"  comfyui   {COMFY}")
    print(f"  comfy url {COMFY_URL}")
    print(f"  input     {COMFY_INPUT}")
    print(f"  output    {COMFY_OUTPUT}")
    print(f"  creds     {ENV_FILE}")
    print(f"  fonts     {FONT_DIR}")
    print(f"  deliver   {DELIVER}")
    print(f"  latent    {BUDGET_M:.2f}M token budget; 4:3 ladder "
          + " ".join(f"{w}x{h}" for w, h in canvases(4, 3)))
    # THE LADDER WITH ITS ERROR, because for five seasons the docstring said
    # "at the DELIVERY aspect" and nothing ever printed whether it was. A
    # season that is not one of the shapes below can put its own numbers in
    # here before it shoots: anything past about 1% is worth knowing about,
    # and framing.unsqueeze() is what corrects it at the bake.
    print("  canvases  delivery -> ladder, and each rung's aspect error")
    for label, (w, h) in (("4:3   ", (1440, 1080)), ("16:9  ", (1920, 1080)),
                          ("2.39  ", (1482, 602)), ("2.40  ", (2688, 1120))):
        rungs = " ".join(f"{cw}x{ch} {e * 100:+.2f}%" for (cw, ch), e
                         in zip(canvases(w, h), aspect_error(w, h)))
        print(f"    {label} {w}x{h}  {rungs}")
    problems = check()
    if problems:
        print("\n  MISSING:")
        for b in problems:
            print(f"    {b}")
        sys.exit(1)
    print("\n  all present")
