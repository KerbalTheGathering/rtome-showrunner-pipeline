"""Render the two plates on the local Krea2 stack.

Krea2 is LOCAL, so posting straight to /prompt needs no ComfyOrg credential.
The Ray 3.2 calls in make_loop.py are partner nodes and carry the key explicitly.

ONE AT A TIME, WITH THE QUEUE VERIFIED EMPTY BETWEEN. Queueing two Krea2 renders
together walks a 24GB card to its ceiling and the sampler starts offloading every
step -- measured, 2.5 s/step becoming 170 s/step, i.e. a 22-minute image. Free
VRAM cannot predict it (a loaded model legitimately sits at ~21GB used with ~3GB
free and the NEXT render is fast), so the gate is the measured DURATION: queue
it, watch the clock, interrupt past SLOW_S. Note /interrupt does not give the
memory back -- if it fires, kill main.py and let the watchdog relaunch.

Idempotent per beat: a plate already on disk is skipped, so re-running after one
beat fails costs nothing. Rejects are renamed `*_rej_<reason>` rather than
deleted and the selector skips them, because a re-roll is not always better.
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import json
import os
import sys
import time
import urllib.request

import shot

# --obj renders the FLAT SECOND LAYER of the five device beats: same seed, same
# latent, same LoRAs, same words, only the style block swapped. It writes to its
# own directory so one layer can never be resolved as the other by accident.
OBJ = "--obj" in sys.argv
OUT = os.path.join(season_paths.COMFY_OUTPUT,
                   f"{shot.OBJ_NAME if OBJ else shot.NAME}")
HOST = season_paths.COMFY_URL

# A cold load is ~120-150s, so anything under ~200s cannot distinguish "still
# loading the 12GB unet" from "offloading every step". 300 leaves room for a
# cold load plus a healthy render and still catches the 22-minute image.
SLOW_S = 300


def graph(prompt: str, prefix: str, seed: int) -> dict:
    """Krea2-Turbo, filter bypass -> style LoRA -> [character LoRA] -> sampler.

    LoRA ORDER IS NOT ARBITRARY: the character LoRA sits LAST, closest to the
    sampler, so the face is the final thing applied rather than something the
    style LoRA gets to overwrite. SaveImage points straight at the VAE decode --
    no post chain, see shot.py.

    THIS FILM HAS NO CHARACTER LORA, so the sampler and the text encoder read off
    whatever is actually last in the chain rather than a hard-coded node id, and
    node 59 is OMITTED ENTIRELY rather than run at strength 0 -- a zeroed loader
    still loads the file and still costs VRAM on a card already carrying a 12GB
    unet, and it makes the graph lie about what is applied.
    """
    def _tail(idx: int = 0) -> list:
        """Last node in the LoRA chain, whichever loaders actually exist.

        THIS FILM HAS NEITHER LORA, so the chain can end at the filter bypass
        itself. The two-way version of this helper hard-coded "52" as the
        fallback and would have pointed the sampler at a node that is not in
        the graph -- a submit-time error, but only because ComfyUI validates
        links; it is the same class of bug as a resolver matching zero files
        and still reporting a pass.
        """
        if shot.CHAR_LORA:
            return ["59", idx]
        if shot.STYLE_LORA:
            return ["52", idx]
        return ["51", idx]

    g = {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": "krea2TurboFP8_krea2TURBO.safetensors",
                         "weight_dtype": "fp8_e4m3fn"}},
        "2": {"class_type": "KSampler",
              "inputs": {"seed": seed, "steps": 8, "cfg": 1, "sampler_name": "er_sde",
                         "scheduler": "simple", "denoise": 1, "model": _tail(0),
                         "positive": ["45", 0], "negative": ["28", 0],
                         "latent_image": ["65", 0]}},
        "4": {"class_type": "VAELoader",
              "inputs": {"vae_name": "Wan2.1_VAE_upscale2x_imageonly_real_v1.safetensors"}},
        "8": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["45", 0]}},
        "13": {"class_type": "CLIPLoader",
               "inputs": {"clip_name": "qwen3vl_4b_fp8_scaled.safetensors",
                          "type": "krea2", "device": "cpu"}},
        "16": {"class_type": "SaveImageAdvanced",
               "inputs": {"filename_prefix": prefix, "format": "png",
                          "format.bit_depth": "8-bit",
                          "format.input_color_space": "sRGB", "images": ["53", 0]}},
        "28": {"class_type": "ConditioningKrea2Rebalance",
               "inputs": {"multiplier": 5,
                          "per_layer_weights": "1.0,1.0,1.0,1.0,1.0,1.0,1.0,2.5,5.0,1.1,4.0,1.0",
                          "conditioning": ["8", 0]}},
        "45": {"class_type": "TextEncodeKrea2",
               "inputs": {"prompt": prompt, "vision_megapixels": 3,
                          "mask_padding": 0, "clip": _tail(1)}},
        "51": {"class_type": "LoraLoader",
               "inputs": {"lora_name": "krea2filterbypass3.safetensors",
                          "strength_model": 100, "strength_clip": 100,
                          "model": ["1", 0], "clip": ["13", 0]}},
        "53": {"class_type": "VAEUtils_VAEDecodeTiled",
               "inputs": {"upscale": -1, "tile": False, "tile_size": 512,
                          "overlap": 64, "temporal_size": 4096,
                          "temporal_overlap": 64, "samples": ["2", 0], "vae": ["4", 0]}},
        "65": {"class_type": "EmptySD3LatentImage",
               "inputs": {"width": shot.LATENT[0], "height": shot.LATENT[1],
                          "batch_size": 1}},
    }
    # Each loader is added only if its file is actually set, so the graph never
    # carries a loader at strength 0 and _tail() never points at a node that is
    # not there. The COWRIE copy of this file lost node 52 while its indentation
    # was being repaired -- harmless there (no style LoRA) and an immediate
    # dangling-link failure here, which is why the link check runs before submit.
    if shot.STYLE_LORA:
        g["52"] = {"class_type": "LoraLoader",
                   "inputs": {"lora_name": shot.STYLE_LORA,
                              "strength_model": shot.STYLE_W,
                              "strength_clip": shot.STYLE_W,
                              "model": ["51", 0], "clip": ["51", 1]}}
    if shot.CHAR_LORA:
        # WHAT THE CHARACTER LORA CHAINS FROM DEPENDS ON WHETHER THERE IS A
        # STYLE LORA, and this used to be hard-coded to "52".
        #
        # _tail() immediately below handles all three combinations with great
        # care, and its docstring says the two-way version "would have pointed
        # the sampler at a node that is not in the graph". This line had the
        # exact fault that comment describes: a film with a CHARACTER LoRA and
        # NO style LoRA built node 59 pointing at node 52, which was never
        # added -- HTTP 400 at submit, every time, for that one combination.
        #
        # Nothing caught it because no film had tried it. The reference season
        # ran style-only or neither; the first film to want a character
        # likeness without a season style was the first to hit it.
        _base = "52" if shot.STYLE_LORA else "51"
        g["59"] = {"class_type": "LoraLoader",
                   "inputs": {"lora_name": shot.CHAR_LORA,
                              "strength_model": shot.CHAR_W,
                              "strength_clip": shot.CHAR_W,
                              "model": [_base, 0], "clip": [_base, 1]}}
    return g


def busy() -> int:
    with urllib.request.urlopen(f"{HOST}/queue", timeout=10) as r:
        q = json.load(r)
    return len(q["queue_running"]) + len(q["queue_pending"])


def existing(sid: str) -> list[str]:
    """Takes on disk for one beat, EXCLUDING rejects."""
    if not os.path.isdir(OUT):
        return []
    return sorted(f for f in os.listdir(OUT)
                  if f.startswith(sid + "_") and f.endswith(".png")
                  and "_rej_" not in f)


def plate(sid: str) -> str:
    """Highest-numbered non-reject take for a beat.

    Resolved, never typed: a re-roll cannot leave anything downstream pointing
    at a stale file -- the bug class that once had a checker match zero files
    and still print a pass.
    """
    # An ALIASED beat has no plate of its own on purpose: two shots that must
    # match need one plate, not two prompts. Every gen_still.py resolves it the
    # same way -- this one did not have the branch at all, and a mechanism that
    # exists in one of three copies is not a mechanism.
    sid = getattr(shot, "PLATE_ALIAS", {}).get(sid, sid)
    have = existing(sid)
    if not have:
        sys.exit(f"FAIL: no plate for beat {sid!r} in {OUT} -- run gen_still.py")
    return os.path.join(OUT, have[-1])


def render(sid: str, prompt: str, what: str, seed: int) -> int:
    n = busy()
    if n:
        print(f"FAIL: {n} prompt(s) already queued. One Krea2 render at a time.")
        return 1

    name = shot.OBJ_NAME if OBJ else shot.NAME
    body = json.dumps({"prompt": graph(prompt, f"{name}\\{sid}", seed)}).encode()
    req = urllib.request.Request(f"{HOST}/prompt", data=body,
                                 headers={"Content-Type": "application/json"})
    have, t0 = existing(sid), time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            pid = json.load(r).get("prompt_id", "?")
    except urllib.error.HTTPError as e:
        print(f"  !! submit rejected: {e.code} "
              f"{e.read()[:600].decode(errors='replace')}")
        return 1
    except Exception as e:                                   # noqa: BLE001
        print(f"  !! submit failed: {e}")
        return 1
    print(f"  [{sid}] {what}\n       seed {seed} queued {pid[:8]} ...",
          end="", flush=True)

    while busy():
        if time.time() - t0 > SLOW_S:
            try:
                urllib.request.urlopen(
                    urllib.request.Request(f"{HOST}/interrupt", data=b"{}",
                                           headers={"Content-Type": "application/json"}),
                    timeout=15)
            except Exception:                                # noqa: BLE001
                pass
            print(f" ABORTED at {time.time()-t0:.0f}s")
            print(f"\nFAIL: ran past {SLOW_S}s (healthy is 30-40s) -- the sampler "
                  "is offloading every step. /interrupt does NOT give the memory "
                  "back: kill main.py, let the watchdog relaunch, re-run.")
            return 1
        time.sleep(4)

    got = [f for f in existing(sid) if f not in have]
    if not got:
        print(f" NO OUTPUT after {time.time()-t0:.0f}s -- check _comfy_startup.log")
        return 1
    print(f" {got[-1]}  {time.time()-t0:.0f}s")
    return 0


def main() -> int:
    force = "--force" in sys.argv
    only = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--beat=")]
    # --seed= ON THE COMMAND LINE OVERRIDES EVERYTHING; WITHOUT IT, THE
    # PER-BEAT TABLE WINS.
    #
    # THIS WAS BROKEN AND IT WAS BROKEN QUIETLY. `seed` from here went to the
    # renderer for every normal plate, and `shot.plate_seed(sid)` -- the
    # function whose entire job is to resolve a per-beat seed -- was consulted
    # ONLY on the `--obj` branch. So `shot.PLATE_SEED`, whose own comment reads
    # "Any beat re-rolled with --seed= must be written down here", had NO
    # EFFECT WHATSOEVER on the beat it was written down for.
    #
    # Nothing failed. Writing the re-roll down was the documented and
    # disciplined thing to do, it looked like it worked, and the next render
    # of that beat quietly used the film-wide default instead. The book and
    # the picture disagreed, and the book was the thing everybody trusted.
    #
    # Found by a fork that re-rolled three plates, recorded all three, and
    # noticed the log still printing the old seed.
    seed = shot.SEED
    seed_given = False
    for a in sys.argv[1:]:
        if a.startswith("--seed="):
            seed = int(a.split("=", 1)[1])
            seed_given = True

    beats = [b for b in shot.BEATS if not OBJ or b["sid"] in shot.OBJ]
    for b in beats:
        sid = b["sid"]
        if only and sid not in only:
            continue
        if sid in getattr(shot, "PLATE_ALIAS", {}):
            print(f"  [{sid}] ALIAS -- takes beat "
                  f"{shot.PLATE_ALIAS[sid]}'s plate, nothing to render")
            continue
        have = existing(sid)
        if have and not force:
            print(f"  [{sid}] SKIP -- {have[-1]} on disk (--force to re-roll)")
            continue
        # obj_prompt asserts the style block was present and is gone afterwards,
        # so a silently unpatched plate cannot reach the renderer. The flat layer
        # must also match its twin's SEED or the two compositions diverge and the
        # wipe has nothing to wipe between -- see shot.PLATE_SEED.
        rc = render(sid, shot.obj_prompt(sid) if OBJ else b["prompt"],
                    b["what"],
                    seed if seed_given else shot.plate_seed(sid))
        if rc:
            return rc

    print("\nPASS: " + "  |  ".join(
        f"{b['sid']} -> {os.path.basename(plate(b['sid']))}" for b in beats))
    return 0


if __name__ == "__main__":
    sys.exit(main())
