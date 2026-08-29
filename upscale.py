"""THE UPSCALE -- every H3 clip, once, before it is baked.

H3 shoots at 864x480 and the delivery is 1920x1080; a Lanczos stretch of 2.2x
was the whole upscale, and it looked like it (the operator, v9: "is there a
better upscale we can do?"). A single-frame A/B against RealESRGAN x4 then
down to delivery height was not close: edges, the helmet ring, the type on
the dials. It is per-frame and deterministic, so there is nothing to flicker.

IT RUNS ONCE PER CLIP INTO A CACHE, NOT ONCE PER BAKE. The act assemblers
re-bake on every note, and a bake that paid an hour of GPU each time would be
abandoned by the third note. `clip(path)` returns the cached upscaled clip at
`<clips>/_up/<name>__<mtime>.mp4`, near-lossless (x264 crf 10, 4:4:4), at
delivery HEIGHT with the source's own aspect -- fit_aspect() does the rest
exactly as it did for the 480p frames. A clip reshot gets a new mtime and a
new cache entry; rejected takes are never touched.

THE MODEL RUNS IN THE COMFYUI VENV (torch + spandrel live there, not in the
project python), as a worker subprocess of this same file, frames in and out
over ffmpeg pipes -- no PNGs on the way. season_identity.UPSCALE names the
model under models/upscale_models; None restores the Lanczos stretch.
"""
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import season_paths                                                # noqa: E402

VENV_PY = os.path.join(season_paths.COMFY, ".venv", "Scripts", "python.exe")
MODELS = os.path.join(season_paths.COMFY, "models", "upscale_models")


def _cfg():
    import season_identity as season
    return getattr(season, "UPSCALE", None), season.W, season.H


def _out_size(src_w, src_h, W, H):
    """What size the upscaled clip is written at.

    A frame off the video model's canvas ladder is SQUEEZED (framing.unsqueeze:
    864x480 is 1.8, the delivery 1.777) and the bake used to un-squeeze it by
    exact size before the fit. The upscaled frame is no longer that exact
    size, so the un-squeeze happens here instead: a ladder rung comes out at
    the delivery exactly; anything else keeps its own aspect at delivery
    height and meets fit_aspect() as it always did.
    """
    if (src_w, src_h) in {(int(a), int(b)) for a, b in season_paths.canvases(W, H)}:
        return W, H
    return int(round(src_w * H / src_h / 2)) * 2, H


def clip(path: str) -> str:
    """The upscaled twin of an H3 clip, made if it is not cached."""
    model, W, H = _cfg()
    if not model:
        return path
    if not os.path.exists(os.path.join(MODELS, model)):
        sys.exit(f"FAIL: season_identity.UPSCALE names {model}, which is not in "
                 f"{MODELS}\n  Fetch it (RealESRGAN_x2plus.pth from the "
                 "xinntao/Real-ESRGAN GitHub releases) or set UPSCALE = None.")
    sw, sh, _, _ = _probe(path)
    ow, oh = _out_size(sw, sh, W, H)
    d = os.path.join(os.path.dirname(path), "_up")
    os.makedirs(d, exist_ok=True)
    st = os.stat(path)
    name = os.path.splitext(os.path.basename(path))[0]
    dst = os.path.join(d, f"{name}__{int(st.st_mtime)}.mp4")
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        return dst
    print(f"    upscale {os.path.basename(path)} -> {model} ... ", end="", flush=True)
    tmp = dst + ".part.mp4"
    subprocess.run([VENV_PY, os.path.abspath(__file__), "--worker", path, tmp,
                    os.path.join(MODELS, model), str(ow), str(oh)], check=True)
    os.replace(tmp, dst)
    print(f"{os.path.getsize(dst) / 1e6:.0f} MB")
    return dst


def _probe(path):
    out = subprocess.run([season_paths.ff("ffprobe"), "-v", "error",
                          "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate,nb_frames",
                          "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout
    w, h, fr, n = out.strip().split(",")
    return int(w), int(h), fr, int(n)


def _worker(src, dst, model_path, ow, oh):
    import numpy as np
    import torch
    import spandrel
    from PIL import Image
    w, h, fr, n = _probe(src)
    m = spandrel.ModelLoader().load_from_file(model_path).eval().cuda().half()
    ff = season_paths.ff("ffmpeg")
    rd = subprocess.Popen([ff, "-v", "error", "-i", src, "-f", "rawvideo",
                           "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    wr = subprocess.Popen([ff, "-y", "-v", "error", "-f", "rawvideo",
                           "-pix_fmt", "rgb24", "-s", f"{ow}x{oh}", "-r", fr,
                           "-i", "-", "-an", "-c:v", "libx264", "-preset",
                           "medium", "-crf", "10", "-pix_fmt", "yuv444p", dst],
                          stdin=subprocess.PIPE)
    size = w * h * 3
    done = 0
    with torch.no_grad():
        while True:
            buf = rd.stdout.read(size)
            if len(buf) < size:
                break
            x = torch.frombuffer(bytearray(buf), dtype=torch.uint8).reshape(h, w, 3)
            x = x.cuda().permute(2, 0, 1)[None].half() / 255
            y = m(x)[0].clamp(0, 1)
            # the x4 picture is bigger than delivery -- down to delivery height
            # with antialiasing, which is the Lanczos step the stretch used to be
            y = torch.nn.functional.interpolate(y[None].float(), size=(oh, ow),
                                                mode="bicubic", antialias=True,
                                                align_corners=False)[0]
            out = (y.clamp(0, 1) * 255).round().byte().permute(1, 2, 0).cpu().numpy()
            wr.stdin.write(out.tobytes())
            done += 1
    wr.stdin.close()
    rd.wait()
    wr.wait()
    if wr.returncode or done == 0 or (n and abs(done - n) > 1):
        sys.exit(f"FAIL: upscale wrote {done} frames of {n} ({src})")


if __name__ == "__main__":
    # -h/--help prints the docstring -- the usage has always lived
    # there; this makes it reachable without opening the file
    # (finding 146). Before main(), so no lock is taken and no
    # argument guard fires first.
    import sys as _hsys
    if "-h" in _hsys.argv or "--help" in _hsys.argv:
        print(__doc__ or "(no usage doc)")
        raise SystemExit(0)
    if sys.argv[1:2] == ["--worker"]:
        _worker(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]), int(sys.argv[6]))
    else:
        for p in sys.argv[1:]:
            print(clip(p))
