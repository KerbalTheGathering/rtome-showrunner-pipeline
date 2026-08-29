"""The mouth-aperture measurement, season-level: landmarks, frames, one number.

EXTRACTED FROM show/mouth_open.py (fault 149). The measurement itself --
detect the largest face, take the 106-point landmarks, report the mouth
cluster's vertical spread over face height -- reads nothing from any tree,
but it lived in the show folder and `_session_template/mouth_scan.py`
imported it from there by appending `<season>/show` to sys.path. Two
faults in one line:

  * a season with `SHOW = False` has no show/ folder at all (a documented
    mode; parts.py tells you to delete it), so every film tree's mouth
    scan crashed on ModuleNotFoundError before measuring anything; and
  * show/mouth_open.py does `import shot` at module level, so importing
    it FROM A FILM TREE bound the FILM's shot.py where the show's was
    meant -- the exact cross-tree resolution class fault 37 and the
    motion.py SESSION assert exist to refuse, passing silently because
    every tree has a shot.py.

So the functions every tree needs live HERE, at the season root, where
both sides already look (the same argument that moved check_clip,
find_voice and sheet -- finding 140). show/mouth_open.py keeps its
show-specific work (anchor picking, the --check ground-truth gate) and
imports the measurement from here.

THE UNIT IS NEVER AN ABSOLUTE. Aperture does not compare across framings
(mouth_open.py --check established it); compare within one clip, or
between takes of the SAME beat, only.

    python mouth.py <clip.mp4>       # openness per second, printed
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import season_paths                                                # noqa: E402

import subprocess
import sys

import numpy as np

MOUTH = list(range(52, 72))     # the mouth cluster, confirmed by drawing it
_APP = None


def app():
    global _APP
    if _APP is None:
        try:
            from insightface.app import FaceAnalysis
        except ModuleNotFoundError:
            sys.exit(
                "FAIL: insightface is not importable in this python.\n"
                "  The landmark model lives in the ComfyUI venv on the "
                "machine this was\n  built on -- run this tool under that "
                "venv's python.exe rather than\n  installing a second copy "
                "of insightface.")
        a = FaceAnalysis(name="buffalo_l",
                         allowed_modules=["detection", "landmark_2d_106"],
                         providers=["CPUExecutionProvider"])
        a.prepare(ctx_id=-1, det_size=(640, 640))
        _APP = a
    return _APP


def size_of(path: str) -> tuple[int, int]:
    o = subprocess.run(
        [season_paths.ff("ffprobe"), "-v", "error", "-select_streams",
         "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0",
         path], capture_output=True, text=True, check=True).stdout.strip()
    w, h = o.split(",")[:2]
    return int(w), int(h)


def head(path: str, n: int) -> np.ndarray:
    """First n frames, BGR, decoded in one pass."""
    w, h = size_of(path)
    raw = subprocess.run(
        [season_paths.ff("ffmpeg"), "-v", "error", "-i", path,
         "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)


def grab(path: str, i: int) -> np.ndarray:
    w, h = size_of(path)
    raw = subprocess.run(
        [season_paths.ff("ffmpeg"), "-v", "error", "-i", path,
         "-vf", f"select=eq(n\\,{i})", "-frames:v", "1", "-f", "rawvideo",
         "-pix_fmt", "bgr24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3)


def openness(im: np.ndarray) -> float | None:
    """Vertical spread of the mouth landmarks over face height. None = no face."""
    fs = app().get(im)
    if not fs:
        return None
    f = max(fs, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]))
    lm = f.landmark_2d_106
    if lm is None:
        return None
    pts = lm[MOUTH]
    fh = float(f.bbox[3] - f.bbox[1])
    return float(pts[:, 1].max() - pts[:, 1].min()) / max(1e-6, fh)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if len(args) != 1:
        sys.exit("FAIL: pass exactly one clip path.\n"
                 "  This prints raw openness per second for ONE clip; the "
                 "judged, windowed\n  comparison between takes is "
                 "mouth_scan.py in the film tree.")
    path = args[0]
    if not _os.path.exists(path):
        sys.exit(f"FAIL: {path} does not exist")
    w, h = size_of(path)
    raw = subprocess.run(
        [season_paths.ff("ffmpeg"), "-v", "error", "-i", path,
         "-vf", "fps=1", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
        capture_output=True, check=True).stdout
    ims = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)
    for i, im in enumerate(ims):
        v = openness(im)
        print(f"  {i:>4}s  {'(no face)' if v is None else f'{v:.4f}'}")
    return 0


if __name__ == "__main__":
    if "-h" in sys.argv or "--help" in sys.argv:
        print(__doc__ or "(no usage doc)")
        raise SystemExit(0)
    raise SystemExit(main())
