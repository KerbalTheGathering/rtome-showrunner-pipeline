"""Buy the clips. One vendor, one call per beat, length derived per beat.

SEEDANCE ONLY. It conditions on the FIRST frame, which is all any beat here
needs -- nothing requires its plate placed late or mid-clip, so there is no
reason to pay Ray's flat per-clip rate. Read off `price_badge`: seedance-1-5-pro
at 480p is quoted per TEN seconds and scaled linearly by duration, so an 11s clip
is 0.12 * 11/10 = $0.132 and there is no penalty for buying the length the beat
actually needs. `duration` is an INT slider from 3 to 12 seconds -- NOT a fixed
4s minimum, which is what an older copy of this file claimed and what the plan
was costed against.

LENGTHS COME FROM edit.py AND ARE NOT TYPED HERE. A clip is sized by its beat and
the beat is sized by its measured VO take, so re-rolling a line and forgetting to
resize its clip is not a mistake this file can make.

AUTH. Partner nodes read the credential from `extra_data.api_key_comfy_org` in
the POST body; ComfyUI does not read `.env` itself. It is read at runtime so it
never lands on a command line. A failed partner call bounces before reaching the
vendor and costs nothing -- a transient InternalServiceError has been seen and
the balance did not move for it.

IDEMPOTENT PER BEAT, and rejects are renamed `*_rej_<reason>` rather than deleted
because the resolver skips them. A rejected clip renamed in place otherwise still
satisfies "already on disk" and silently blocks the re-buy.
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402
import solo                                                        # noqa: E402


import json
import os
import sys
import time
import urllib.error
import urllib.request

import edit
import gen_still
import motion
import shot

HOST = season_paths.COMFY_URL
ENV = season_paths.ENV_FILE

SD_MODEL = "seedance-1-5-pro-251215"
SD_RES = "480p"
# PINNED, NOT "adaptive". Our plates are 2432x1664 = 1.4615, and no Seedance option
# matches that -- "adaptive" quietly resolved it to 752x560 = 1.343, i.e. it picked 4:3
# and cropped about 9% off the plate's width, on every clip of both shipped films,
# without ever saying so. 4:3 is therefore not a change: it is what we have always been
# getting, now stated out loud so it cannot drift between sessions or resolutions.
# 16:9 is the alternative and it is a CREATIVE call, not a fix -- it would use the full
# plate width and crop the height instead, changing the shape of the whole season.
SD_ASPECT = "4:3"
SD_RATE_PER_10S = {"480p": 0.12, "720p": 0.26, "1080p": 0.58}

SEED = 771244
MIN_CENTS = 60


def outdir() -> str:
    return os.path.join(season_paths.COMFY_OUTPUT, f"{shot.NAME}_clips")


def cost_cents(sid: str) -> float:
    return SD_RATE_PER_10S[SD_RES] * edit.SECS[sid] / 10 * 100


def api_key() -> str:
    for line in open(ENV, encoding="utf-8"):
        if line.startswith("API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("FAIL: no API_KEY in .env")


def balance(key: str) -> float | None:
    """Cents. Named `_micros` by the API and it is not micros."""
    req = urllib.request.Request("https://api.comfy.org/customers/balance",
                                 headers={"X-API-KEY": key})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.load(r).get("effective_balance_micros")
    except Exception as e:                                   # noqa: BLE001
        print(f"  (balance unavailable: {e})")
        return None


def auth_stable(key: str, probes: int = 3) -> bool:
    """Is comfy.org's auth actually up, or just up sometimes?

    A SINGLE SUCCESSFUL CHECK DOES NOT MEAN AUTHENTICATED. comfy.org has been
    seen returning {"message":"Invalid Comfy API key"} to roughly two calls in
    three while the key was perfectly valid -- three probes seconds apart came
    back 401, OK, 401. One probe would have passed on the second and reported a
    healthy service.

    That flap is expensive rather than merely annoying, because the node creates
    the vendor task FIRST and polls for the result after: a 401 that lands in
    the polling window leaves a clip generated, billed and unreachable. That is
    exactly how 23.58c went missing with no file to show for it. A 401 that
    lands earlier costs nothing, which is why the failure looks intermittent in
    the balance as well as in the log.

    So the gate is unanimity, not a majority: every probe must pass before any
    money is committed. False alarms are free and cost a retry in a minute; a
    false all-clear costs a clip per beat until somebody notices.
    """
    for i in range(probes):
        if balance(key) is None:
            print(f"  auth probe {i+1}/{probes} FAILED")
            return False
        if i + 1 < probes:
            time.sleep(3)
    return True


def graph(sid: str, prompt: str, src: str, prefix: str) -> dict:
    return {
        # Path-based load: plates live in output/, not input/, and ComfyUI caches
        # its input listing, so a fresh file is missing from LoadImage's combo.
        "1": {"class_type": "Image Load",
              "inputs": {"image_path": src, "RGBA": "false",
                         "filename_text_extension": "false"}},
        "2": {"class_type": "ByteDanceImageToVideoNode",
              "inputs": {"model": SD_MODEL, "prompt": prompt,
                         "image": ["1", 0], "resolution": SD_RES,
                         "aspect_ratio": SD_ASPECT,
                         "duration": edit.SECS[sid],
                         "seed": SEED, "camera_fixed": True,
                         "watermark": False, "generate_audio": False}},
        "9": {"class_type": "SaveVideo",
              "inputs": {"video": ["2", 0], "filename_prefix": prefix,
                         "format": "auto", "codec": "auto"}},
    }


def busy() -> int:
    with urllib.request.urlopen(f"{HOST}/queue", timeout=10) as r:
        q = json.load(r)
    return len(q["queue_running"]) + len(q["queue_pending"])


def existing(sid: str) -> list[str]:
    # `.mp4` and non-empty, like h3_shoot.existing() and check_clip's: any
    # other file that lands in the clips folder matching s{sid}_* (a
    # sidecar, a zero-byte failed mux) sorted last and became "the clip"
    # for assemble, italk and mouth_scan (fault 123).
    d = outdir()
    if not os.path.isdir(d):
        return []
    return sorted(f for f in os.listdir(d)
                  if f.startswith(f"s{sid}_") and f.endswith(".mp4")
                  and "_rej_" not in f
                  and os.path.getsize(os.path.join(d, f)) > 0)


def clip(sid: str) -> str:
    got = existing(sid)
    if not got:
        sys.exit(f"FAIL: no clip for beat {sid} in {outdir()} -- run make_video.py")
    return os.path.join(outdir(), got[-1])


def buy(sid: str, key: str) -> int:
    src = gen_still.plate(sid)
    have, t0 = existing(sid), time.time()
    print(f"  [{sid}] {os.path.basename(src)}  "
          f"({edit.SECS[sid]}s, {cost_cents(sid):.1f}c)")

    body = json.dumps({
        "prompt": graph(sid, motion.MOTION[sid], src, f"{shot.NAME}_clips/s{sid}"),
        "extra_data": {"api_key_comfy_org": key},
    }).encode()
    req = urllib.request.Request(f"{HOST}/prompt", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            pid = json.load(r).get("prompt_id", "?")
    except urllib.error.HTTPError as e:
        print(f"       !! submit rejected: {e.code} "
              f"{e.read()[:700].decode(errors='replace')}")
        return 1
    print(f"       queued {pid[:8]} ...", end="", flush=True)

    while busy():
        if time.time() - t0 > 1200:
            print(" TIMEOUT (job may still be running server-side)")
            return 1
        time.sleep(5)

    got = [f for f in existing(sid) if f not in have]
    if not got:
        print(f" NO OUTPUT after {time.time()-t0:.0f}s -- check the server log; "
              "an auth failure bounces before reaching the vendor and is free")
        return 1
    print(f" {got[-1]}  {time.time()-t0:.0f}s")
    return 0


def main() -> int:
    # ONE COPY OF THIS STAGE AT A TIME, refused at entry rather than at the
    # point of damage. `busy()` below already stops two renders overlapping;
    # it cannot stop two PROCESSES from waiting on each other forever. See
    # solo.py -- four copies of a batch tool once deadlocked on their own
    # correct queue guard, at 0% GPU, with nothing in any log.
    solo.solo("clips", where=os.path.dirname(os.path.abspath(__file__)),
              force="--force" in sys.argv)
    only = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--beat=")]
    todo = [s for s in shot.CUT
            if (not only or s in only)
            and (not existing(s) or "--force" in sys.argv)]
    for s in shot.CUT:
        if s in todo:
            continue
        have = existing(s)
        if have:
            print(f"  [{s}] SKIP -- {have[-1]} on disk")
    if not todo:
        print("  nothing to buy")
        return 0

    key = api_key()
    # BEFORE ANY MONEY IS COMMITTED. See auth_stable() -- a flapping auth service
    # bills for clips it will not let you collect, and the old code read the
    # balance exactly once, which is the one probe that cannot see a flap.
    if not auth_stable(key):
        print("FAIL: comfy.org auth is not answering reliably right now -- it is "
              "rejecting a valid key intermittently. Nothing submitted. Wait for "
              "it to settle and run again; a 401 during POLLING bills for a clip "
              "that never arrives.")
        return 1

    before = balance(key)
    total = sum(cost_cents(s) for s in todo)
    secs = sum(edit.SECS[s] for s in todo)
    if before is not None:
        print(f"  balance before: {before:.2f} cents (${before/100:.2f})")
        if before < MIN_CENTS or before < total:
            print(f"FAIL: balance will not cover {total:.1f}c; not submitting")
            return 1
    print(f"  buying {len(todo)} clip(s), {secs}s of video "
          f"-- {total:.1f}c total (${total/100:.2f})\n")

    for sid in todo:
        if buy(sid, key):
            return 1

    # Billing settles a few seconds after the clip returns, so an immediate read
    # lies -- it once reported 0.00 for a clip that cost 15, which reads as "this
    # tier is free". Poll until it moves; never print zero.
    if before is not None:
        for _ in range(20):
            time.sleep(4)
            after = balance(key)
            if after is not None and after < before:
                print(f"\n  balance after:  {after:.2f} cents (${after/100:.2f})")
                print(f"  THIS RUN COST: {before-after:.2f} cents "
                      f"(${(before-after)/100:.2f}) for {len(todo)} clip(s)")
                break
        else:
            print("\n  THIS RUN COST: UNCONFIRMED (balance had not settled)")

    done = [s for s in shot.CUT if existing(s)]
    print(f"\n{len(done)}/{len(shot.CUT)} clips on disk")
    missing = [s for s in shot.CUT if s not in done]
    if missing:
        print(f"  (no clip yet for: {', '.join(missing)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
