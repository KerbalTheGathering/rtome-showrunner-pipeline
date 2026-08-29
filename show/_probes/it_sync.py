"""Does the announcer's mouth actually follow the voice? Six segments, measured.

WHY NOT sync_qc.py. That tool finds the mouth by differencing the clean bake
against the synced one, which only works because Kling REPAINTS a region and
leaves the rest alone. InfiniteTalk generates the whole frame from the plate, so
that difference is the entire picture and the box it returns is meaningless.

THE PROXY PROBLEM, AND HOW THIS ONE IS KEPT HONEST. An earlier pass measured
"openness" as the dark-pixel fraction inside a mouth box and it read flat across
frames where the mouth had been watched opening wide -- it was measuring the
moustache. So this uses mouth MOTION energy (mean absolute frame-to-frame
difference inside the box) and then refuses to interpret it until it has passed
two checks that do not depend on the proxy being right:

    GROUND TRUTH   Where the speech is, is not thresholded out of the audio --
                   it is read from edit.offsets() and edit.speech(), the same
                   numbers the segment length was built from. Motion must be
                   clearly higher inside speech than inside the typed gaps.

    A CONTROL BOX  The same measurement on the UPPER face. If the mouth tracks
                   the voice and the forehead does not, the mouth is doing the
                   work. If both track it equally, what looks like lip sync is
                   the whole head moving with the audio -- which is exactly what
                   "off to the audio" feels like even when the timing is right.

Only after both pass does the lag sweep mean anything. Then the eyes decide, on
the frames at TRUE SILENCE, which is the standing test in this project.

    python it_sync.py              # all six, synced (pre-CRT)
    python it_sync.py --shipped    # the baked bounty segments instead
    python it_sync.py 01 03
"""
from __future__ import annotations

import os as _os, sys as _sys
# THREE DIRNAMES REACH THE SEASON ROOT FROM HERE, TWO ONLY REACH show/. This
# preamble was copied verbatim from show/*.py, which lives one level higher --
# so `import season_paths` failed outright and every probe in this folder was
# unrunnable. Nothing noticed, because nothing in this repo imported them.
_here = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:0] = [_os.path.dirname(_here),                     # show/ -- edit, script
                 _os.path.dirname(_os.path.dirname(_here))]   # the season root
import season_paths                                                # noqa: E402


import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import edit
import script

HERE = os.path.dirname(os.path.abspath(__file__))
FF = season_paths.FFMPEG
WORK = os.path.join(os.path.dirname(HERE), "_work")   # the SHOW tree's, not _probes' (fault 122)
OUT = os.path.join(os.path.dirname(HERE), "out")      # the SHOW tree's, not _probes' (fault 122)
FONT = season_paths.font("arialbd.ttf")

FPS = 24.0
LAG = 12                      # +-half a second is well past anything audible
MIN_SPEECH_RATIO = 1.5        # below this the motion proxy is not measuring speech
GUARD = 3                     # frames dropped either side of a speech edge


def frames_gray(path: str, w: int, h: int) -> np.ndarray:
    p = subprocess.run(
        [season_paths.ff("ffmpeg"), "-v", "error", "-i", path,
         "-vf", f"scale={w}:{h}:flags=bilinear", "-f", "rawvideo",
         "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(p, np.uint8).reshape(-1, h, w).astype(np.float32)


def size_of(path: str) -> tuple[int, int]:
    out = subprocess.run(
        [season_paths.ff("ffprobe"), "-v", "error", "-select_streams",
         "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0",
         path], capture_output=True, text=True, check=True).stdout.strip()
    w, h = out.split(",")[:2]
    return int(w), int(h)


def envelope(sid: str, nf: int) -> np.ndarray:
    """Per-frame VO loudness from the exact wav InfiniteTalk was driven with."""
    wav = os.path.join(WORK, f"vo_{sid}.wav")
    if not os.path.exists(wav):
        sys.exit(f"FAIL: {wav} missing")
    with wave.open(wav) as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        pcm = np.frombuffer(w.readframes(n), np.int16).astype(np.float32)
    if ch > 1:
        pcm = pcm.reshape(-1, ch).mean(axis=1)
    out = np.zeros(nf, np.float32)
    step = sr / FPS
    for i in range(nf):
        seg = pcm[int(i * step):int((i + 1) * step)]
        if seg.size:
            out[i] = math.sqrt(float(np.mean(seg * seg))) / 32768.0
    return out


def truth(sid: str, nf: int):
    """Speech / silence per frame from the TYPED edit, not from a threshold.

    Returns (speech mask, silence mask, list of (start, end) silent spans).
    Guarded: frames within GUARD of an edge belong to neither, so a mouth that
    is closing on the last syllable is not counted as a failure.
    """
    sp = np.zeros(nf, bool)
    spans = []
    t_end = 0.0
    for lid, t0 in edit.offsets(sid):
        d = edit.speech(lid)
        a, b = int(round(t0 * FPS)), int(round((t0 + d) * FPS))
        sp[max(0, a):min(nf, b)] = True
        if a > t_end:
            spans.append((int(t_end), a))
        t_end = b
    if t_end < nf:
        spans.append((int(t_end), nf))

    grow = sp.copy()
    for k in range(1, GUARD + 1):
        grow[k:] |= sp[:-k]
        grow[:-k] |= sp[k:]
    return sp, ~grow, spans


def boxes(path: str, w: int, h: int):
    """Find the face once, from the median of several frames.

    Detection LOCATES; it never decides whether a mouth is open. Returns a mouth
    box (lower part of the face) and an upper-face control box.
    """
    from insightface.app import FaceAnalysis
    app = FaceAnalysis(name="buffalo_l", allowed_modules=["detection"],
                       providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=-1, det_size=(640, 640))

    n = int(subprocess.run(
        [season_paths.ff("ffprobe"), "-v", "error", "-select_streams",
         "v:0", "-count_frames", "-show_entries", "stream=nb_read_frames",
         "-of", "csv=p=0", path], capture_output=True, text=True,
        check=True).stdout.strip())
    hits = []
    for i in np.linspace(n * 0.15, n * 0.85, 7).astype(int):
        raw = subprocess.run(
            [season_paths.ff("ffmpeg"), "-v", "error", "-i", path,
             "-vf", f"select=eq(n\\,{i})", "-frames:v", "1", "-f", "rawvideo",
             "-pix_fmt", "bgr24", "-"], capture_output=True, check=True).stdout
        W, H = size_of(path)
        im = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
        fs = app.get(im)
        if fs:
            f = max(fs, key=lambda x: (x.bbox[2] - x.bbox[0]) *
                    (x.bbox[3] - x.bbox[1]))
            hits.append([f.bbox[0] / W, f.bbox[1] / H,
                         f.bbox[2] / W, f.bbox[3] / H])
    if not hits:
        sys.exit(f"FAIL: no face found in {os.path.basename(path)}")
    x0, y0, x1, y1 = np.median(np.array(hits), axis=0)
    fh = y1 - y0
    mouth = (x0, y0 + 0.52 * fh, x1, y1 + 0.06 * fh)
    upper = (x0, y0, x1, y0 + 0.45 * fh)

    def px(b):
        return (max(0, int(b[0] * w)), max(0, int(b[1] * h)),
                min(w, int(b[2] * w)), min(h, int(b[3] * h)))
    return px(mouth), px(upper), (x0, y0, x1, y1)


def energy(a: np.ndarray, b) -> np.ndarray:
    """Mean absolute frame-to-frame difference inside a box, per frame."""
    x0, y0, x1, y1 = b
    c = a[:, y0:y1, x0:x1]
    d = np.abs(np.diff(c, axis=0)).mean(axis=(1, 2))
    return np.concatenate([[d[0]], d])


def lagged(x: np.ndarray, y: np.ndarray, lo=-LAG, hi=LAG):
    def r(a, b):
        a, b = a - a.mean(), b - b.mean()
        d = float(np.sqrt((a * a).sum() * (b * b).sum()))
        return float((a * b).sum() / d) if d else 0.0
    out = []
    for k in range(lo, hi + 1):
        out.append((k, r(x[k:], y[:len(y) - k]) if k > 0 else
                    (r(x, y) if k == 0 else r(x[:k], y[-k:]))))
    return out


def one(sid: str, shipped: bool) -> dict:
    path = (os.path.join(OUT, f"bounty_{sid}.mp4") if shipped
            else os.path.join(WORK, f"synced_{sid}.mp4"))
    if not os.path.exists(path):
        sys.exit(f"FAIL: {path} missing")
    W, H = size_of(path)
    w, h = 480, int(round(480 * H / W))
    a = frames_gray(path, w, h)
    nf = len(a)

    mb, ub, face = boxes(path, w, h)
    env = envelope(sid, nf)
    sp, si, spans = truth(sid, nf)

    m = energy(a, mb)
    u = energy(a, ub)

    # PROXY VALIDATION -- does the mouth signal know where the speech is?
    ratio = float(m[sp].mean() / max(1e-9, m[si].mean())) if si.any() else 0.0
    uratio = float(u[sp].mean() / max(1e-9, u[si].mean())) if si.any() else 0.0

    rm = lagged(m, env)
    ru = lagged(u, env)
    best_m = max(rm, key=lambda t: t[1])
    at0 = dict(rm)[0]

    # THE LAG NUMBER ABOVE IS BIASED AND MUST NOT BE READ AS TIMING. `m` is a
    # frame-to-frame DIFFERENCE -- a derivative -- and a derivative peaks on the
    # rising edge, before the thing it is differentiating. Correlated against a
    # raw envelope it reports the mouth as early even when the sync is perfect.
    # Differentiating the envelope the same way puts both signals in the same
    # domain, so whatever offset survives is an offset and not an artifact.
    denv = np.abs(np.diff(env))
    denv = np.concatenate([[denv[0]], denv])
    rd = lagged(m, denv)
    best_d = max(rd, key=lambda t: t[1])

    return dict(sid=sid, path=path, n=nf, w=w, h=h, mouth=mb, upper=ub,
                face=face, env=env, denv=denv, m=m, u=u, sp=sp, si=si,
                spans=spans, ratio=ratio, uratio=uratio, best=best_m, at0=at0,
                best_d=best_d, d_at0=dict(rd)[0],
                best_u=max(ru, key=lambda t: t[1]))


def silence_frames(r: dict, k: int = 4) -> list[int]:
    """The deepest point of the longest typed silences -- the silence test."""
    got = []
    for a, b in sorted(r["spans"], key=lambda s: s[1] - s[0], reverse=True):
        if b - a < 2 * GUARD + 2:
            continue
        got.append((a + b) // 2)
        if len(got) >= k:
            break
    return sorted(got)


def speech_frames(r: dict, k: int = 3) -> list[int]:
    e = r["env"].copy()
    e[~r["sp"]] = -1
    return sorted(np.argsort(e)[-k:].tolist())


def sheet(rows: list[dict], shipped: bool) -> None:
    """Mouth crops at true silence and at peak speech, for the eyes."""
    CW, CH = 190, 150
    f = ImageFont.truetype(FONT, 15)
    fb = ImageFont.truetype(FONT, 18)
    cols = 7
    out = Image.new("RGB", (24 + cols * (CW + 8), len(rows) * (CH + 56) + 10),
                    (16, 16, 18))
    d = ImageDraw.Draw(out)
    for j, r in enumerate(rows):
        y = 10 + j * (CH + 56)
        sfs = silence_frames(r)
        pfs = speech_frames(r)
        picks = [(i, "SILENT", (255, 90, 70)) for i in sfs] + \
                [(i, "SPEECH", (110, 220, 130)) for i in pfs]
        d.text((12, y), f"segment {r['sid']}   mouth/speech {r['ratio']:.2f}x  "
                        f"forehead {r['uratio']:.2f}x   r={r['at0']:+.2f}@0  "
                        f"best {r['best'][1]:+.2f}@{r['best'][0]:+d}f",
               font=fb, fill=(235, 232, 226))
        x0, y0, x1, y1 = r["mouth"]
        for c, (i, tag, col) in enumerate(picks[:cols]):
            raw = subprocess.run(
                [season_paths.ff("ffmpeg"), "-v", "error", "-i", r["path"],
                 "-vf", f"select=eq(n\\,{i}),scale={r['w']}:{r['h']}",
                 "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                capture_output=True, check=True).stdout
            im = Image.fromarray(
                np.frombuffer(raw, np.uint8).reshape(r["h"], r["w"], 3), "RGB")
            crop = im.crop((x0, y0, x1, y1)).resize((CW, CH), Image.LANCZOS)
            px = 24 + c * (CW + 8)
            out.paste(crop, (px, y + 26))
            ImageDraw.Draw(out).rectangle(
                [px, y + 26, px + CW - 1, y + 26 + CH - 1], outline=col, width=2)
            d.text((px + 2, y + 26 + CH + 2),
                   f"{tag} {i/FPS:5.2f}s", font=f, fill=col)
    p = os.path.join(OUT, "it_sync_mouths.png" if not shipped
                     else "it_sync_mouths_shipped.png")
    out.save(p)
    print(f"  -> {p}")


def curves(rows: list[dict], shipped: bool) -> None:
    W, PH = 1180, 150
    f = ImageFont.truetype(FONT, 15)
    out = Image.new("RGB", (W, len(rows) * (PH + 34) + 10), (16, 16, 18))
    for j, r in enumerate(rows):
        y = 10 + j * (PH + 34)
        pl = Image.new("RGB", (W - 24, PH), (26, 26, 30))
        pd = ImageDraw.Draw(pl)
        pw = W - 24
        # typed speech bands behind the curves
        for a, b in [(int(np.flatnonzero(r["sp"])[0]), 0)] if False else []:
            pass
        run = None
        for i, v in enumerate(np.append(r["sp"], False)):
            if v and run is None:
                run = i
            elif not v and run is not None:
                pd.rectangle([run * pw / r["n"], 0, i * pw / r["n"], PH],
                             fill=(38, 44, 38))
                run = None
        for s, col in ((r["env"], (90, 190, 255)), (r["m"], (255, 190, 80)),
                       (r["u"], (130, 130, 140))):
            v = s - s.min()
            v = v / max(1e-9, v.max())
            pd.line([(k * pw / len(v), PH - 4 - t * (PH - 10))
                     for k, t in enumerate(v)], fill=col, width=1)
        out.paste(pl, (12, y + 22))
        ImageDraw.Draw(out).text(
            (12, y + 2), f"segment {r['sid']}    green band = typed speech    "
                         f"blue = VO    orange = mouth motion    grey = forehead",
            font=f, fill=(235, 232, 226))
    p = os.path.join(OUT, "it_sync_curves.png" if not shipped
                     else "it_sync_curves_shipped.png")
    out.save(p)
    print(f"  -> {p}")


def main() -> int:
    shipped = "--shipped" in sys.argv
    want = [a for a in sys.argv[1:] if not a.startswith("-")] or list(script.SIDS)
    rows = []
    print(f"  {'seg':>4} {'frames':>7} {'mouth/sp':>9} {'fore/sp':>8} "
          f"{'d-lag':>6} {'d-r':>7} {'raw lag':>8}   verdict")
    for sid in want:
        r = one(sid, shipped)
        rows.append(r)
        bad = []
        if r["ratio"] < MIN_SPEECH_RATIO:
            bad.append("PROXY-FLAT")
        # NOT a defect on its own, and it was reported as one once. A high
        # forehead ratio means the head is STILL during the silences and moves
        # during speech, which is what a talking head should do; it only
        # matters if the lips are meanwhile doing nothing. Motion energy cannot
        # tell those apart, so this now says where to look instead of judging.
        if r["uratio"] >= r["ratio"] * 0.85:
            bad.append("head>=mouth: check it_articulate.py")
        if abs(r["best_d"][0]) > 2:
            bad.append(f"LAG{r['best_d'][0]:+d}f={r['best_d'][0]/FPS*1000:+.0f}ms")
        print(f"  {sid:>4} {r['n']:>7} {r['ratio']:>9.2f} {r['uratio']:>8.2f} "
              f"{r['best_d'][0]:>+6d} {r['best_d'][1]:>+7.2f} "
              f"{r['best'][0]:>+8d}   {' '.join(bad) if bad else 'ok'}")
    sheet(rows, shipped)
    curves(rows, shipped)
    print("\n  A number here only narrows WHERE to look. The frames decide.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
