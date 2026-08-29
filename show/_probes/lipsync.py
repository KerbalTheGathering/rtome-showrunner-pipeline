"""Kling lip sync for the six bounty reports, in chunks, and back to 24fps.

WHY CHUNKS. KlingLipSyncAudioToVideoNode takes video "between 2s and 10s in
length" and every segment runs 13.6-17.2s. Each one is cut at a SILENCE between
two spoken lines, so the join lands on a closed mouth in a locked-off shot --
the least visible place a seam can fall. Five segments split in two; segment 05
has no gap that leaves both halves under ten seconds, so it splits in three.

WHY THE CLEAN PICTURE. Lip sync runs on the ungraded, untyped bake. The board
type is drawn at full resolution afterwards, so it never goes through a video
model, and Kling never sees the scanlines. The audio it listens to is VO-only
for the same reason -- the node wants clearly distinguishable vocals and the
brass sting sits under the first four seconds.

WHAT COMES BACK IS NOT WHAT WENT IN, AND THIS IS THE PART THAT WOULD HAVE
SHIPPED BROKEN. Kling returned 1440x1072 at 30fps for a 1440x1080 24fps input:
eight pixels of height gone and a frame rate the rest of the season does not
use. Neither is visible in a frame grab. Both would have broken the feature cut
-- which joins thirteen parts by stream copy and requires them identical -- and
the 30fps would have slid the board type off the words it is timed to. So every
return is forced back to exact geometry, rate and FRAME COUNT before it is used.

    python lipsync.py --dry        # plan and price it, submit nothing
    python lipsync.py              # do it
    python lipsync.py 03 06        # just these
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


import glob
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

import edit
import script
import shot

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(os.path.dirname(HERE), "_work")   # the SHOW tree's, not _probes' (fault 122)
FF = season_paths.FFMPEG
HOST = season_paths.COMFY_URL
ENV = season_paths.ENV_FILE
INPUT = season_paths.COMFY_INPUT
COMFY_OUT = season_paths.COMFY_OUTPUT

FPS = 24
W, H = 1440, 1080
MIN_S, MAX_S = 2.0, 10.0
CENTS_EACH = 14.0            # measured, not the 10c on the price badge


# --------------------------------------------------------------------------

def api_key() -> str:
    for line in open(ENV, encoding="utf-8"):
        if line.startswith("API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("FAIL: no API_KEY in .env")


def balance(key: str) -> float | None:
    req = urllib.request.Request("https://api.comfy.org/customers/balance",
                                 headers={"X-API-KEY": key})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            d = json.load(r)
    except Exception:                                        # noqa: BLE001
        return None
    for k in ("balance_micros", "balance", "amount_micros"):
        if k in d:
            return float(d[k])
    return None


def auth_stable(key: str, probes: int = 3) -> bool:
    ok = sum(balance(key) is not None or 0 for _ in range(1))
    ok = 0
    for i in range(probes):
        if balance(key) is not None:
            ok += 1
        if i < probes - 1:
            time.sleep(3)
    print(f"  auth probes: {ok}/{probes} answered")
    return ok == probes


def splits(sid: str) -> list[float]:
    """Cut points, in seconds, chosen in the silences between spoken lines."""
    r = next(x for x in edit.table() if x["sid"] == sid)
    offs = edit.offsets(sid)
    clip = r["clip"]
    gaps = []
    for i in range(len(offs) - 1):
        lid, off = offs[i]
        gaps.append((off + edit.speech(lid) + offs[i + 1][1]) / 2.0)

    # Fewest chunks that all fit the cap; among those, the most even split.
    best = None
    for n in (2, 3, 4):
        from itertools import combinations
        for combo in combinations(gaps, n - 1):
            bounds = [0.0, *combo, clip]
            lens = [b - a for a, b in zip(bounds, bounds[1:])]
            if all(MIN_S <= x <= MAX_S for x in lens):
                spread = max(lens) - min(lens)
                if best is None or spread < best[1]:
                    best = (list(combo), spread)
        if best:
            return best[0]
    sys.exit(f"FAIL: segment {sid} has no gap pattern that fits "
             f"{MIN_S}-{MAX_S}s chunks -- it cannot be lip synced as written")


def chunks(sid: str) -> list[tuple[float, float]]:
    r = next(x for x in edit.table() if x["sid"] == sid)
    bounds = [0.0, *splits(sid), r["clip"]]
    return list(zip(bounds, bounds[1:]))


def kling(vid: str, aud: str, prefix: str, key: str) -> str:
    g = {
        "1": {"class_type": "LoadVideo", "inputs": {"file": os.path.basename(vid)}},
        "2": {"class_type": "LoadAudio", "inputs": {"audio": os.path.basename(aud)}},
        "3": {"class_type": "KlingLipSyncAudioToVideoNode",
              "inputs": {"video": ["1", 0], "audio": ["2", 0],
                         "voice_language": "en"}},
        "4": {"class_type": "SaveVideo",
              "inputs": {"video": ["3", 0], "filename_prefix": prefix,
                         "format": "auto", "codec": "auto"}},
    }
    body = json.dumps({"prompt": g,
                       "extra_data": {"api_key_comfy_org": key}}).encode()
    try:
        pid = json.load(urllib.request.urlopen(urllib.request.Request(
            f"{HOST}/prompt", body,
            {"Content-Type": "application/json"})))["prompt_id"]
    except urllib.error.HTTPError as e:
        sys.exit(f"FAIL: submit rejected {e.code}\n"
                 f"{e.read()[:1000].decode(errors='replace')}")
    t0 = time.time()
    while True:
        time.sleep(10)
        h = json.load(urllib.request.urlopen(f"{HOST}/history/{pid}"))
        if pid in h:
            files = [f for o in h[pid].get("outputs", {}).values()
                     for f in o.get("videos", []) + o.get("images", [])]
            if not files:
                sys.exit(f"FAIL after {time.time()-t0:.0f}s: "
                         + json.dumps(h[pid].get("status", {}))[:900])
            # THE SUBFOLDER IS A SEPARATE FIELD. `filename` is the basename
            # only, so joining it to the output root finds nothing whenever the
            # prefix contains a directory -- which this one does. It cost a
            # paid call to learn, because the crash landed AFTER the money.
            f = files[-1]
            return os.path.join(COMFY_OUT, f.get("subfolder", ""),
                                f["filename"])
        if time.time() - t0 > 1200:
            sys.exit("FAIL: timed out waiting on Kling")


def normalise(src: str, dst: str, want_frames: int) -> None:
    """Force Kling's return back to exact geometry, rate AND frame count.

    `-frames:v` alone only truncates. It cannot lengthen, and every chunk comes
    back SHORT: Kling returns ~0.03s less than it was given, and 30->24fps
    costs another frame or two. Concatenated, that is not a cosmetic shortfall
    -- the audio sits at absolute offsets in the mix, so a picture that loses
    five frames across a segment ends up running a fifth of a second AHEAD of
    the voice it was synced to. Visible, on a mouth.

    So `tpad` clones the final frame first and `-frames:v` then cuts to the
    exact number. The hold lands at the END of a chunk, which is a silence
    between two spoken lines -- that is what the split points were chosen for,
    and it means the padding sits on a closed mouth with nothing moving.
    """
    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                    "-i", src,
                    "-vf", f"scale={W}:{H}:flags=lanczos,fps={FPS},"
                           "tpad=stop_mode=clone:stop_duration=1",
                    "-frames:v", str(want_frames),
                    "-an", "-c:v", "libx264", "-crf", "14", "-preset", "slow",
                    "-pix_fmt", "yuv420p", dst], check=True)


def main() -> int:
    want = [a for a in sys.argv[1:] if not a.startswith("-")] or list(shot.CUT)
    dry = "--dry" in sys.argv
    os.makedirs(WORK, exist_ok=True)

    plan = {sid: chunks(sid) for sid in want}
    n_calls = sum(len(v) for v in plan.values())
    print(f"  {'seg':>4} {'chunks':>7}  windows")
    for sid, cs in plan.items():
        print(f"  {sid:>4} {len(cs):>7}  " +
              "  ".join(f"{a:.2f}-{b:.2f} ({b-a:.2f}s)" for a, b in cs))
    print(f"\n  {n_calls} Kling calls x {CENTS_EACH:.0f}c = "
          f"${n_calls * CENTS_EACH / 100:.2f}")
    if dry:
        print("  --dry: nothing submitted")
        return 0

    key = api_key()
    if not auth_stable(key):
        sys.exit("FAIL: comfy.org auth is flapping -- a 401 during polling "
                 "bills for a result that never arrives. Nothing submitted.")
    b0 = balance(key)
    print(f"  balance before: {b0}\n")

    for sid, cs in plan.items():
        clean = os.path.join(WORK, f"clean_{sid}.mp4")
        vo = os.path.join(WORK, f"vo_{sid}.wav")
        for p in (clean, vo):
            if not os.path.exists(p):
                sys.exit(f"FAIL: {p} missing -- run "
                         f"`python assemble.py --clean {sid}` first")
        pieces = []
        for i, (a, b) in enumerate(cs):
            out = os.path.join(WORK, f"ls_{sid}_{i}.mp4")
            want_frames = round((b - a) * FPS)

            # NEVER BUY A CHUNK TWICE. This run already died once between the
            # paid call and the file being read, so a re-run has to be free for
            # everything already bought. Two levels: a finished normalised
            # chunk, and a raw Kling return still sitting in output/ls_out from
            # a crashed attempt.
            if os.path.exists(out):
                print(f"  [{sid}.{i}] have it, skipping")
                pieces.append(out)
                continue
            prior = sorted(glob.glob(os.path.join(
                COMFY_OUT, "ls_out", f"{sid}_{i}_*.mp4")))
            if prior:
                print(f"  [{sid}.{i}] reusing paid return "
                      f"{os.path.basename(prior[-1])}", end="")
                normalise(prior[-1], out, want_frames)
                pieces.append(out)
                print(f" -> {want_frames}f")
                continue

            vid = os.path.join(INPUT, f"ls_{sid}_{i}.mp4")
            aud = os.path.join(INPUT, f"ls_{sid}_{i}.wav")
            subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                            "-ss", f"{a:.3f}", "-t", f"{b-a:.3f}", "-i", clean,
                            "-an", "-c:v", "libx264", "-crf", "14",
                            "-preset", "slow", "-pix_fmt", "yuv420p", vid],
                           check=True)
            subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                            "-ss", f"{a:.3f}", "-t", f"{b-a:.3f}", "-i", vo,
                            "-ac", "2", "-ar", "44100", aud], check=True)
            print(f"  [{sid}.{i}] {b-a:.2f}s  {os.path.getsize(vid)/1e6:.1f} MB "
                  "-> Kling ...", end="", flush=True)
            got = kling(vid, aud, f"ls_out/{sid}_{i}", key)
            normalise(got, out, want_frames)
            pieces.append(out)
            print(f" {want_frames}f")

        lst = os.path.join(WORK, f"ls_{sid}.txt")
        with open(lst, "w", encoding="utf-8") as fh:
            for p in pieces:
                fh.write(f"file '{p}'\n")
        dst = os.path.join(WORK, f"synced_{sid}.mp4")
        subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                        "-f", "concat", "-safe", "0", "-i", lst,
                        "-c", "copy", dst], check=True)
        want_total = edit.FRAMES[sid]
        got_total = int(subprocess.run(
            [season_paths.ff("ffprobe"), "-v", "error", "-select_streams",
             "v:0", "-count_frames", "-show_entries", "stream=nb_read_frames",
             "-of", "csv=p=0", dst],
            capture_output=True, text=True, check=True).stdout.strip())
        flag = "" if abs(got_total - want_total) <= 2 else "   <-- MISMATCH"
        print(f"  [{sid}] joined {len(pieces)} chunks -> {got_total}f "
              f"(want {want_total}f){flag}\n")

    b1 = balance(key)
    if b0 and b1:
        print(f"  spent {b0-b1:.0f}c on {n_calls} calls")
    print("  now: python assemble.py --synced")
    return 0


if __name__ == "__main__":
    # -h/--help prints the docstring -- the usage has always lived
    # there; this makes it reachable without opening the file
    # (finding 146). Before main(), so no lock is taken and no
    # argument guard fires first.
    import sys as _hsys
    if "-h" in _hsys.argv or "--help" in _hsys.argv:
        print(__doc__ or "(no usage doc)")
        raise SystemExit(0)
    sys.exit(main())
