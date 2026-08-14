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
    return max(32, int(round(n / 32.0)) * 32)


def canvases(w: int, h: int) -> tuple[tuple[int, int], ...]:
    """Render canvases at the DELIVERY aspect, largest first.

    DERIVED FROM THE SEASON'S OWN GEOMETRY rather than typed as three 4:3
    tuples. 1440x1080 already appears in season_identity, in dims() and in
    every contact sheet's tile geometry; three of those derive and this one did
    not, so a season that was not 4:3 would have rendered 4:3 sources and
    letterboxed itself at the bake without anything saying so.
    """
    if w >= h:
        cw = min(LONG_CAP, _snap32(SHORT_CAP * w / h))
        ch = _snap32(cw * h / w)
        if ch > SHORT_CAP:
            ch = SHORT_CAP
            cw = _snap32(ch * w / h)
    else:
        ch = min(LONG_CAP, _snap32(SHORT_CAP * h / w))
        cw = _snap32(ch * w / h)
        if cw > SHORT_CAP:
            cw = SHORT_CAP
            ch = _snap32(cw * h / w)
    return tuple((_snap32(cw * r), _snap32(ch * r)) for r in CANVAS_LADDER)


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
    problems = check()
    if problems:
        print("\n  MISSING:")
        for b in problems:
            print(f"    {b}")
        sys.exit(1)
    print("\n  all present")
