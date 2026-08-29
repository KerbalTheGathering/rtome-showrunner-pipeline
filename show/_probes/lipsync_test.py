"""ONE Kling lip-sync call, on one eight-second chunk, for about ten cents.

THE UNKNOWN IS NOT THE PLUMBING, IT IS THE FACE. Kling's lip sync is trained on
photographic people. Dale is a painted illustration with heavy dark linework and
a grey moustache over his mouth, and there is no way to reason about whether the
model will re-draw that mouth convincingly or smear it into something rubbery.
So: buy one chunk, look at it, and only then decide whether to build a pipeline
for twelve of them.

WHY A CHUNK AND NOT A SEGMENT. The node takes video "between 2s and 10s in
length" and every segment runs 13.6-17.2s, so the real pipeline has to split
each one in two anyway. This tests the same shape the real thing will use.

AUTH IS PROBED THREE TIMES BEFORE ANY MONEY MOVES. comfy.org has been seen
returning "Invalid Comfy API key" to roughly two calls in three while the key was
perfectly valid, and a 401 during POLLING bills for a clip that never arrives.

    python lipsync_test.py
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


import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")      # the SHOW tree's, not _probes' (fault 122)
WORK = os.path.join(os.path.dirname(HERE), "_work")   # the SHOW tree's, not _probes' (fault 122)
FF = season_paths.FFMPEG
HOST = season_paths.COMFY_URL
ENV = season_paths.ENV_FILE
INPUT = season_paths.COMFY_INPUT

SID = "01"
FROM_S, LEN_S = 4.0, 8.0        # inside the VO, clear of the sting


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
    """One successful probe cannot see a flap. Three, seconds apart, can."""
    ok = 0
    for i in range(probes):
        if balance(key) is not None:
            ok += 1
        if i < probes - 1:
            time.sleep(3)
    print(f"  auth probes: {ok}/{probes} answered")
    return ok == probes


def main() -> int:
    os.makedirs(WORK, exist_ok=True)
    src = os.path.join(OUT, f"bounty_{SID}.mp4")
    if not os.path.exists(src):
        sys.exit(f"FAIL: {src} missing")

    vid = os.path.join(INPUT, "ls_test.mp4")
    aud = os.path.join(INPUT, "ls_test.wav")
    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                    "-ss", str(FROM_S), "-t", str(LEN_S), "-i", src,
                    "-an", "-c:v", "libx264", "-crf", "16", "-preset", "slow",
                    "-pix_fmt", "yuv420p", vid], check=True)
    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                    "-ss", str(FROM_S), "-t", str(LEN_S), "-i", src,
                    "-vn", "-ac", "2", "-ar", "44100", aud], check=True)
    print(f"  chunk {os.path.getsize(vid)/1e6:.1f} MB video, "
          f"{os.path.getsize(aud)/1e6:.1f} MB audio")

    key = api_key()
    if not auth_stable(key):
        sys.exit("FAIL: comfy.org auth is flapping. Nothing submitted -- a 401 "
                 "during polling bills for a result that never arrives.")
    b0 = balance(key)
    print(f"  balance before: {b0}")

    g = {
        "1": {"class_type": "LoadVideo", "inputs": {"file": "ls_test.mp4"}},
        "2": {"class_type": "LoadAudio", "inputs": {"audio": "ls_test.wav"}},
        "3": {"class_type": "KlingLipSyncAudioToVideoNode",
              "inputs": {"video": ["1", 0], "audio": ["2", 0],
                         "voice_language": "en"}},
        "4": {"class_type": "SaveVideo",
              "inputs": {"video": ["3", 0], "filename_prefix": "lipsync_test",
                         "format": "auto", "codec": "auto"}},
    }
    body = json.dumps({"prompt": g,
                       "extra_data": {"api_key_comfy_org": key}}).encode()
    try:
        pid = json.load(urllib.request.urlopen(urllib.request.Request(
            f"{HOST}/prompt", body, {"Content-Type": "application/json"})))["prompt_id"]
    except urllib.error.HTTPError as e:
        sys.exit(f"FAIL: submit rejected {e.code}\n"
                 f"{e.read()[:1200].decode(errors='replace')}")
    print(f"  submitted {pid[:8]} ...", end="", flush=True)

    t0 = time.time()
    while True:
        time.sleep(10)
        h = json.load(urllib.request.urlopen(f"{HOST}/history/{pid}"))
        if pid in h:
            outs = h[pid].get("outputs", {})
            files = [f for o in outs.values()
                     for f in o.get("videos", []) + o.get("images", [])]
            if not files:
                print(f" FAILED after {time.time()-t0:.0f}s")
                print(json.dumps(h[pid].get("status", {}))[:1500])
                return 1
            print(f" {files[-1]['filename']}  {time.time()-t0:.0f}s")
            break
        if time.time() - t0 > 900:
            print(" TIMEOUT")
            return 1

    b1 = balance(key)
    print(f"  balance after:  {b1}"
          + (f"   (spent {b0-b1:.2f})" if b0 and b1 else ""))
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
