"""UNTESTED: probe the Minimax H3 LATENT upscaler on one beat, against a control.

NOTHING IN THIS FILE HAS SHIPPED IN A FILM. It is hooked up so the next
season can test it in one command; treat every number in it as a starting
point, not a finding, until a filmstrip says otherwise.

WHAT IT PROBES. `Comfyui_Minimax_h3_latent_Upscaler` (github.com/LBH-123-AI;
weights: huggingface.co/LBH-123-AI/Minimax_h3_latent_Upscaler) upscales H3's
24-channel latent directly, skipping the VAE round-trip. Its own README is
plain about the trade: **"saves time, not VRAM"** -- the refinement still
runs at target resolution, so the token budget (`season_paths.BUDGET_M`)
still governs and pick_canvas's ladder is not obsoleted. If it holds, the
prize is the base pass running at a quarter of the tokens.

THE SHAPE, TAKEN FROM THE AUTHOR'S OWN r2v EXAMPLE WORKFLOW (in the node
repo's workflow_templates/): a TWO-PASS hires-fix, not an insert --

    base sampler at HALF canvas, on the FIRST half of the sigma schedule
      -> LTXVSeparateAVLatent           (split video from audio latent)
      -> MinimaxH3LatentUpscaler3D x2   (video latent only)
      -> LTXVConcatAVLatent             (audio latent rejoined, untouched)
      -> refine sampler on a short manual sigma tail, at FULL resolution
      -> decode as normal

The refine tail ("0.9035, 0.6316, 0.3158, 0.0000") is the example's own;
--refine-sigmas overrides it. The base/refine split point on our 6-step
turbo schedule defaults to 3 (--split=N); the example splits its 8 at 4.

CONTRACTS ARE READ, NOT GUESSED (italk_multi's discipline; fault 45's
dotted paths). Every class this graph needs is checked against the live
/object_info before anything is submitted, and the upscaler's dynamic
`mode` combo is sent as dotted keys ("mode": "scale by multiplier",
"mode.scale": ...). If the node is not registered, the answer is a
sentence about restarting ComfyUI, not a 400.

OUTPUT LANDS IN <NAME>_latprobe/, never in <NAME>_clips -- a probe result
must not be resolvable as a take (the --filtered discipline). The control
is the same beat, same seed, on the film's normal single pass, so the
comparison is honest. Judge on filmstrips, middle frames included.

    python lat_probe.py 03            # probe + control for one beat
    python lat_probe.py 03 --dry      # print both graphs, submit nothing
    python lat_probe.py 03 --no-ctl   # skip the control render
    python lat_probe.py 03 --scale=2.0 --split=3 --seed=N
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import season_paths  # noqa: E402
import solo          # noqa: E402
import edit          # noqa: E402
import gen_still     # noqa: E402
import h3_shoot      # noqa: E402
import motion        # noqa: E402
import shot          # noqa: E402

HOST = season_paths.COMFY_URL
INPUT = season_paths.COMFY_INPUT

UPSCALER = "MinimaxH3LatentUpscaler3D"
UPSCALE_MODEL = "minimax_h3_latent_upscaler_3d_fp16.safetensors"
# The author's example refine tail, verbatim. Untested here.
REFINE_SIGMAS = "0.9035, 0.6316, 0.3158, 0.0000"
NEEDED = (UPSCALER, "LTXVSeparateAVLatent", "LTXVConcatAVLatent",
          "ManualSigmas", "SplitSigmas")


def busy() -> int:
    with urllib.request.urlopen(f"{HOST}/queue", timeout=10) as r:
        q = json.load(r)
    return len(q["queue_running"]) + len(q["queue_pending"])


def object_info(cls: str) -> dict | None:
    try:
        with urllib.request.urlopen(f"{HOST}/object_info/{cls}",
                                    timeout=15) as r:
            d = json.load(r)
    except (urllib.error.URLError, OSError) as e:
        sys.exit(f"FAIL: cannot read {HOST}/object_info -- is ComfyUI up? "
                 f"({e})")
    return d.get(cls)


def check_contract() -> None:
    """Refuse to submit a graph whose node contract is not on the server."""
    missing = [c for c in NEEDED if object_info(c) is None]
    if missing:
        sys.exit(
            f"FAIL: the server at {HOST} does not register {missing}.\n"
            f"  The node package installs to custom_nodes/"
            f"Comfyui_Minimax_h3_latent_Upscaler and needs a ComfyUI\n"
            f"  RESTART to register. LTXV/ManualSigmas come from packs "
            f"already in this stack.")
    info = object_info(UPSCALER)
    opts = info["input"]["required"].get("model_name", [[]])[0]
    if isinstance(opts, list) and UPSCALE_MODEL not in opts:
        sys.exit(
            f"FAIL: the server does not list {UPSCALE_MODEL} for the "
            f"upscaler.\n  It belongs in ComfyUI/models/"
            f"latent_upscale_models/ -- the server sees: {opts[:6]}")


def half(size: tuple[int, int]) -> tuple[int, int]:
    return (max(32, round(size[0] / 64) * 32),
            max(32, round(size[1] / 64) * 32))


def surgery(g: dict, seed: int, scale: float, split: int,
            refine: str) -> dict:
    """Splice the two-pass hires-fix onto h3_shoot's proven ref2va graph."""
    # base pass takes only the FIRST `split` steps of the film's schedule
    g["200"] = {"class_type": "SplitSigmas",
                "inputs": {"sigmas": ["9", 0], "step": split}}
    g["14"]["inputs"]["sigmas"] = ["200", 0]          # high_sigmas
    g["201"] = {"class_type": "LTXVSeparateAVLatent",
                "inputs": {"av_latent": ["14", 0]}}
    # THE DYNAMIC COMBO'S OPTION INPUTS ARE DOTTED PATHS (fault 45): a flat
    # "scale" key would be silently dropped and the node would run at its
    # default.
    g["202"] = {"class_type": UPSCALER,
                "inputs": {"latent": ["201", 0], "model_name": UPSCALE_MODEL,
                           "mode": "scale by multiplier", "mode.scale": scale,
                           "align": 32, "enable_temporal_chunking": True,
                           "force_unload": True, "device": "cuda",
                           "precision": "fp16"}}
    # the audio latent is rejoined UNTOUCHED -- the upscaler is spatial and
    # has no business near the audio channels
    g["203"] = {"class_type": "LTXVConcatAVLatent",
                "inputs": {"video_latent": ["202", 0],
                           "audio_latent": ["201", 1]}}
    g["204"] = {"class_type": "ManualSigmas", "inputs": {"sigmas": refine}}
    g["206"] = {"class_type": "SamplerCustomAdvanced",
                "inputs": {"noise": ["15", 0], "guider": ["16", 0],
                           "sampler": ["17", 0], "sigmas": ["204", 0],
                           "latent_image": ["203", 0]}}
    g["10"]["inputs"]["samples"] = ["206", 0]         # video decode
    g["23"]["inputs"]["samples"] = ["206", 0]         # audio decode
    return g


def submit(g: dict, label: str) -> str | None:
    req = urllib.request.Request(f"{HOST}/prompt",
                                 json.dumps({"prompt": g}).encode(),
                                 {"Content-Type": "application/json"})
    try:
        pid = json.load(urllib.request.urlopen(req))["prompt_id"]
    except urllib.error.HTTPError as e:
        print(f"\nSUBMIT REJECTED ({label}): {e.code} "
              f"{e.read()[:600].decode(errors='replace')}")
        return None
    t0, tick = time.time(), 60.0
    while time.time() - t0 < 5400:
        time.sleep(10)
        if time.time() - t0 > tick:
            print(f" {(time.time() - t0) / 60:.0f}m", end="", flush=True)
            tick += 60
        h = json.load(urllib.request.urlopen(f"{HOST}/history/{pid}"))
        if pid in h:
            files = [f for o in h[pid].get("outputs", {}).values()
                     for f in o.get("images", []) + o.get("videos", [])]
            if not files:
                print(f"\nFAILED ({label}) after {time.time() - t0:.0f}s -- "
                      f"{json.dumps(h[pid].get('status', {}))[:400]}")
                return None
            el = time.time() - t0
            print(f" {files[-1]['filename']}  {el / 60:.1f} min")
            return os.path.join(season_paths.COMFY_OUTPUT,
                                files[-1].get("subfolder", ""),
                                files[-1]["filename"])
    print(f"\nTIMEOUT ({label})")
    return None


def main() -> int:
    named = [a for a in sys.argv[1:] if not a.startswith("--")]
    named += [a.split("=", 1)[1] for a in sys.argv[1:]
              if a.startswith("--beat=")]
    known = ("--dry", "--no-ctl")
    bad = [a for a in sys.argv[1:]
           if a.startswith("--") and not a.startswith(
               ("--beat=", "--seed=", "--scale=", "--split=",
                "--refine-sigmas=")) and a not in known]
    if bad:
        sys.exit(f"FAIL: unrecognised argument(s) {bad} -- see the "
                 f"docstring (python lat_probe.py --help)")
    if len(named) != 1:
        sys.exit("FAIL: probe exactly ONE beat: python lat_probe.py 03")
    sid = named[0].zfill(2)
    if sid not in shot.CUT:
        sys.exit(f"FAIL: {sid!r} is not a beat of this film "
                 f"({list(shot.CUT)})")
    arg = {k: v for k, v in (a[2:].split("=", 1) for a in sys.argv[1:]
                             if a.startswith("--") and "=" in a)}
    seed = int(arg.get("seed", shot.SEED))
    scale = float(arg.get("scale", 2.0))
    split = int(arg.get("split", 3))
    refine = arg.get("refine-sigmas", REFINE_SIGMAS)
    dry = "--dry" in sys.argv

    row = next(r for r in edit.table() if r["sid"] == sid)
    length = h3_shoot.grid(edit.SECS[sid])
    src = gen_still.plate(sid)
    plate_name = f"h3_{shot.NAME.lower()}_{sid}.png"
    full = h3_shoot.group_canvas(sid, length)
    base = half(full)
    drive = (h3_shoot.driver(sid, row, length)
             if h3_shoot.season.H3_DRIVER
             and not h3_shoot._flag(sid, "nodriver") else None)
    with_man = (bool(h3_shoot.ID_REFS)
                and not h3_shoot._flag(sid, "nochar")
                and not h3_shoot._flag(sid, "norefs"))

    tok_base = season_paths.latent_m(length, base)
    tok_full = season_paths.latent_m(length, full)
    print(f"  [{sid}] UNTESTED latent-upscale probe: base "
          f"{base[0]}x{base[1]} ({tok_base:.2f}M) x{scale:.2f} -> refine at "
          f"~{full[0]}x{full[1]} ({tok_full:.2f}M), split {split} of "
          f"{h3_shoot.STEPS}")
    if tok_full > season_paths.BUDGET_M:
        print(f"  !! refine runs at {tok_full:.2f}M against the "
              f"{season_paths.BUDGET_M:.2f}M budget -- the README's own "
              f"caveat is 'saves time, not VRAM'. Probe a SHORTER beat.")

    probe_g = surgery(
        h3_shoot.build(motion.MOTION[sid], plate_name, False, plate_name,
                       drive, length, f"{shot.NAME}_latprobe/s{sid}_lat",
                       base, seed, with_man),
        seed, scale, split, refine)
    ctl_g = h3_shoot.build(motion.MOTION[sid], plate_name, False, plate_name,
                           drive, length,
                           f"{shot.NAME}_latprobe/s{sid}_ctl",
                           full, seed, with_man)
    if dry:
        print(json.dumps(probe_g, indent=1))
        print("\n  --dry: nothing submitted (control graph omitted; it is "
              "h3_shoot's own, unmodified)")
        return 0

    solo.solo("latprobe", where=os.path.dirname(os.path.abspath(__file__)))
    n = busy()
    if n:
        sys.exit(f"FAIL: {n} prompt(s) already queued -- one render at a "
                 f"time, on a shared card.")
    check_contract()
    shutil.copyfile(src, os.path.join(INPUT, plate_name))
    print("  probe   ...", end="", flush=True)
    got = submit(probe_g, "probe")
    ctl = None
    if "--no-ctl" not in sys.argv:
        print("  control ...", end="", flush=True)
        ctl = submit(ctl_g, "control")
    print()
    if got:
        print(f"  probe  : {got}")
    if ctl:
        print(f"  control: {ctl}")
    print("  Judge on FILMSTRIPS, middle frames included -- and listen: "
          "the audio\n  latent was rejoined untouched, and whether that "
          "survives the refine\n  pass is exactly what this probe exists "
          "to find out. Log the verdict\n  in learnings.md either way.")
    return 0 if got else 1


if __name__ == "__main__":
    import sys as _hsys
    if "-h" in _hsys.argv or "--help" in _hsys.argv:
        print(__doc__ or "(no usage doc)")
        raise SystemExit(0)
    sys.exit(main())
