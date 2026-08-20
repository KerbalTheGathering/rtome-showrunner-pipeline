"""Shoot the whole session on LOCAL H3. No partner node, no money, no balance check.

WHY THIS REPLACES make_video.py HERE. Sessions #4 and #5 each bought one Seedance
pass and then fixed their faults on H3 for nothing. The 6-step turbo LoRA closed
what was left of the gap: on Session #4 beat 11, same seed and same plate, turbo
H3 returned the SAME drift (1.06x vs 1.05x), BETTER colour hold (0.442 vs 0.427
end saturation) and a LOWER frame residual (35.7 vs 39.9) than the 20-step
baseline -- in 3.5 minutes instead of 8.3. Free, faster, and no worse, so the
buy has nothing left to be for.

IT WRITES STRAIGHT INTO THE SESSION'S CLIP DIRECTORY. h3_test.py renders to
output/video and needs promote_h3.py to file the result, because there it is
REPLACING a bought clip and the take it supersedes has to be retired with a
reason. Here there is nothing to supersede on a first pass, so the clip lands as
`s<sid>_00001_` where the assembler already looks. Re-rolls after this still go
through h3_test.py + promote_h3.py so the `_rej_` history stays honest.

LENGTHS COME FROM edit.SECS, snapped UP to H3's 17k+5 frame grid at 24fps. Never
down: a clip one frame short of its beat is a black frame in the cut.

    python h3_shoot.py                 # every beat that has no clip yet
    python h3_shoot.py 03 07 12        # just these
    python h3_shoot.py --force 09      # re-render one that already exists
    python h3_shoot.py --rej=grewaman 10   # retire the old take, then re-shoot
    python h3_shoot.py --slow          # 20-step baseline instead of turbo
    python h3_shoot.py --no-strip      # skip the filmstrip after each clip
"""

import glob
import json
import os
import shutil
import sys
import time
import urllib.request

# THE SEASON ROOT, THEN THIS TREE. `import edit` puts season_paths in
# sys.modules and that is NOT the same thing as putting it in this module's
# namespace: every use of season_paths below was a NameError, in three copies
# of this file, on the first frame anybody tried to shoot. smoke.py exists
# because nothing else in the repo could see it.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import season_paths  # noqa: E402
import solo  # noqa: E402
import check_clip  # noqa: E402  -- the filmstrip after every shoot
import edit        # noqa: E402
import identity    # noqa: E402  (the season's delivery geometry)
import gen_still   # noqa: E402
import motion      # noqa: E402
import shot        # noqa: E402

HOST = season_paths.COMFY_URL
INPUT = season_paths.COMFY_INPUT
CLIPS = os.path.join(season_paths.COMFY_OUTPUT, f"{shot.NAME}_clips")

# THE TOP OF THE LADDER, DERIVED. For a 4:3 season that is 1024x768 -- exactly
# 4:3 and the largest true 4:3 canvas H3 offers (768 is its short-edge cap;
# both edges are multiples of 32). The assembler lifts it to the season's
# delivery size, which every part of the season bakes to.

# THE CANVAS IS CHOSEN FROM THE TOKEN BUDGET, NOT BY HAND, PER CLIP.
#
# The measurements and the ceiling live in season_paths.py -- they are facts
# about the CARD, not about this session, and two other copies of this file had
# no budget at all while a third carried a different number in a comment. See
# season_paths.BUDGET_M for what was measured and what it cost not to have it.
#
# THE LADDER IS DERIVED FROM THE SEASON'S DELIVERY ASPECT, so a season that is
# not 4:3 does not silently shoot 4:3 sources.
BUDGET_M = season_paths.BUDGET_M
CANVASES = season_paths.canvases(identity.season.W, identity.season.H)


def pick_canvas(length: int) -> tuple[int, int]:
    """Largest canvas at the delivery aspect that stays under the ceiling."""
    return season_paths.pick_canvas(length, identity.season.W,
                                    identity.season.H)


# THE SEASON'S RATE, DERIVED. `24` was typed in eleven files beside a
# season_identity.FPS that already said so -- and feature.py asserts every
# part matches, so a season at another rate would have been caught only
# after every part was baked.
FPS = identity.season.FPS
SEED = shot.SEED

# THE 6-STEP TURBO LORA, with its card's settings verbatim: euler / beta57 / 6
# steps, and the strength SCHEDULED rather than pinned -- 4.00 falling to 1.00
# across 0.100..0.990. It wants to dominate early so six steps cover the ground
# twenty were doing, then back off so the last steps are mostly the base model.
# SCG's node does it by bypass-mode injection, which is what makes it work at
# all on our INT8 unet; a normal LoraLoader patches weights and cannot.
TURBO_LORA = "minimax_h3_turbo_6step_ema_fl2va_pruned.safetensors"
TURBO_STEPS, TURBO_SAMPLER, TURBO_SCHED = 6, "euler", "beta57"
TURBO_TAPER = dict(strength_start=4.00, strength_end=1.00,
                   start_percent=0.100, end_percent=0.990,
                   interpolation="linear", cutoff_outside_window=True)
BASE_STEPS, BASE_SAMPLER, BASE_SCHED = 20, "res_multistep", "simple"


def grid(seconds: float) -> int:
    """H3's 17k+5 frame grid at 24fps -- the workflow's own expression, in python."""
    n = max(5, round(seconds * FPS))
    return n + (5 - (n % 17)) % 17


def existing(sid: str) -> list[str]:
    if not os.path.isdir(CLIPS):
        return []
    return sorted(f for f in os.listdir(CLIPS)
                  if f.startswith(f"s{sid}_") and f.endswith(".mp4")
                  and "_rej_" not in f)


def build(prompt: str, image_name: str, length: int, prefix: str,
          turbo: bool = True, size: tuple[int, int] = CANVASES[0],
          seed: int = SEED) -> dict:
    msrc = "30" if turbo else "6"
    steps = TURBO_STEPS if turbo else BASE_STEPS
    sampler = TURBO_SAMPLER if turbo else BASE_SAMPLER
    sched = TURBO_SCHED if turbo else BASE_SCHED

    g = {
        "6":  {"class_type": "UNETLoader",
               "inputs": {"unet_name": "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
                          "weight_dtype": "default"}},
        "13": {"class_type": "CLIPLoader",
               "inputs": {"clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
                          "type": "minimax", "device": "default"}},
        "11": {"class_type": "VAELoader",
               "inputs": {"vae_name": "minimax_h3_video_vae_fp16.safetensors"}},
        "24": {"class_type": "VAELoader",
               "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"}},
        "1":  {"class_type": "LoadImage", "inputs": {"image": image_name}},
        # first_frame only; `last_frame` is left unwired on purpose.
        "104": {"class_type": "MiniMaxH3ImageToVideo",
                "inputs": {"clip": ["13", 0], "vae": ["11", 0], "prompt": prompt,
                           "width": size[0], "height": size[1], "length": length,
                           "first_frame": ["1", 0]}},
        "16": {"class_type": "BasicGuider",
               "inputs": {"model": [msrc, 0], "conditioning": ["104", 0]}},
        "17": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": sampler}},
        "9":  {"class_type": "BasicScheduler",
               "inputs": {"model": [msrc, 0], "scheduler": sched,
                          "steps": steps, "denoise": 1.0}},
        "15": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "14": {"class_type": "SamplerCustomAdvanced",
               "inputs": {"noise": ["15", 0], "guider": ["16", 0], "sampler": ["17", 0],
                          "sigmas": ["9", 0], "latent_image": ["104", 1]}},
        # The SAME latent decodes twice, through two different VAEs -- H3 is
        # omni-modal and carries picture and sound in one tensor. The audio is
        # discarded downstream; the film's sound is VO and score.
        "10": {"class_type": "VAEDecode", "inputs": {"samples": ["14", 0], "vae": ["11", 0]}},
        "23": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["14", 0], "vae": ["24", 0]}},
        "91": {"class_type": "CreateVideo",
               "inputs": {"images": ["10", 0], "audio": ["23", 0], "fps": FPS, "bit_depth": 8}},
        "92": {"class_type": "SaveVideo",
               "inputs": {"video": ["91", 0], "filename_prefix": prefix,
                          "format": "auto", "codec": "auto"}},
    }
    if turbo:
        # CLIP is deliberately NOT wired: the node applies a LoRA to CLIP
        # statically when connected, and our text encoder is a separate
        # quantised Qwen3-VL that this LoRA has nothing to say about.
        g["30"] = {"class_type": "SCGLoRAScheduler",
                   "inputs": {"model": ["6", 0], "lora_name": TURBO_LORA,
                              **TURBO_TAPER}}
    return g


def shoot(sid: str, turbo: bool, seed: int = SEED) -> bool:
    secs = edit.SECS[sid]
    length = grid(secs)
    src = gen_still.plate(sid)

    # DERIVED, NEVER TYPED. A hardcoded session name in a file that gets copied
    # between trees is the bug that put Session #4's renders into Session #5's
    # filename namespace.
    name = f"h3_{shot.NAME.lower()}_{sid}.png"
    shutil.copyfile(src, os.path.join(INPUT, name))
    prefix = f"{shot.NAME}_clips/s{sid}"

    size = pick_canvas(length)
    tok = season_paths.latent_m(length, size)
    print(f"  [{sid}] {os.path.basename(src):16s} {secs}s -> {length}f "
          f"({length / FPS:.2f}s) {size[0]}x{size[1]} {tok:.2f}M ",
          end="", flush=True)
    body = json.dumps({"prompt": build(motion.MOTION[sid], name, length,
                                       prefix, turbo, size, seed)}).encode()
    req = urllib.request.Request(f"{HOST}/prompt", body,
                                 {"Content-Type": "application/json"})
    try:
        pid = json.load(urllib.request.urlopen(req))["prompt_id"]
    except Exception as e:                                   # noqa: BLE001
        print(f"SUBMIT FAILED: {e}")
        return False

    t0 = time.time()
    while True:
        time.sleep(10)
        h = json.load(urllib.request.urlopen(f"{HOST}/history/{pid}"))
        if pid in h:
            outs = h[pid].get("outputs", {})
            files = [f for o in outs.values()
                     for f in o.get("images", []) + o.get("videos", [])]
            el = time.time() - t0
            if not files:
                print(f"FAILED after {el:.0f}s -- "
                      f"{json.dumps(h[pid].get('status', {}))[:240]}")
                return False
            print(f"{files[-1]['filename']}  {el / 60:.1f} min "
                  f"({el / length:.2f} s/f)")
            return True
        if time.time() - t0 > 3600:
            print("TIMEOUT after 60 min")
            return False


def main() -> int:
    # ONE COPY OF THIS STAGE AT A TIME, refused at entry rather than at the
    # point of damage. `busy()` below already stops two renders overlapping;
    # it cannot stop two PROCESSES from waiting on each other forever. See
    # solo.py -- four copies of a batch tool once deadlocked on their own
    # correct queue guard, at 0% GPU, with nothing in any log.
    solo.solo("clips", where=os.path.dirname(os.path.abspath(__file__)),
              force="--force" in sys.argv)
    turbo = "--slow" not in sys.argv
    # A REASON RETIRES THE OLD TAKE INSTEAD OF LEAVING IT BESIDE THE NEW ONE.
    # The resolver takes the highest-numbered non-reject file, so a bare --force
    # would work -- but a clip directory of unexplained numbers is a directory
    # of mysteries six weeks later. Session #6's reads as its own history
    # (`_rej_wrongmotion`, `_rej_neverateit`), and that is worth typing.
    rej = next((a.split("=", 1)[1] for a in sys.argv[1:]
                if a.startswith("--rej=")), None)
    # `--seed` WAS MISSING FROM THIS COPY AND ITS ABSENCE WAS SILENT. The flag
    # starts with "--", so `want` filtered it out and nothing rejected it: three
    # runs asking for three seeds all rendered the session seed, ComfyUI served
    # the identical graph from cache in 12 seconds each, and `--rej` retired the
    # freshly-made file every time -- so the beat ended with FOUR rejects and no
    # take at all. Only the "14/15 beats now have a clip" line said so.
    #
    # Hence the unknown-flag guard below. A no-op flag on a generator is worse
    # than an error: it looks like a result.
    seed = int(next((a.split("=", 1)[1] for a in sys.argv[1:]
                     if a.startswith("--seed=")), SEED))
    force = "--force" in sys.argv or rej is not None
    want = [a for a in sys.argv[1:] if not a.startswith("--")] or list(shot.CUT)

    known = ("--slow", "--force", "--rej=", "--seed=", "--no-strip")
    junk = [a for a in sys.argv[1:]
            if a.startswith("--") and not a.startswith(known)]
    if junk:
        sys.exit(f"FAIL: unknown flag(s) {junk} -- this script would have "
                 f"ignored them silently. Known flags: {', '.join(known)}")

    bad = [s for s in want if s not in shot.CUT]
    if bad:
        sys.exit(f"FAIL: {bad} are not beats in this session")

    if rej:
        for sid in want:
            for f in existing(sid):
                stem = f[:-4].rstrip("_")
                os.rename(os.path.join(CLIPS, f),
                          os.path.join(CLIPS, f"{stem}__rej_{rej}.mp4"))
                print(f"  [{sid}] retired {f} -> {stem}__rej_{rej}.mp4")

    todo = [s for s in want if force or not existing(s)]
    skip = [s for s in want if s not in todo]

    mode = (f"TURBO {TURBO_STEPS}st {TURBO_SAMPLER}/{TURBO_SCHED}"
            if turbo else f"base {BASE_STEPS}st {BASE_SAMPLER}/{BASE_SCHED}")
    print(f"  {shot.NAME} / Session #{shot.SESSION_NO}: {shot.TITLE}")
    print(f"  {len(todo)} beat(s) to shoot, {sum(edit.SECS[s] for s in todo)}s "
          f"of clip  seed {seed}"
          f"{'' if seed == SEED else f' (session seed is {SEED})'}"
          f"  [{mode}]  -- LOCAL, $0.00")
    # A SEED THAT WAS ASKED FOR AND NOT USED IS HOW A RE-ROLL GETS REPORTED
    # THAT NEVER RAN (fault 44): `h3_shoot.py 07 --seed=N` on a beat with a
    # take on disk printed a bare SKIP, and the bare SKIP reads as "shot
    # with your seed" to anyone scanning for the beat id. The skip is
    # CORRECT -- takes are never overwritten -- so the message now says
    # what the re-roll actually needs.
    # A CLIP OUTLIVES THE PLATE IT WAS SHOT FROM (fault 49): re-making a
    # plate (re-roll, face swap) retires the old PLATE with a reason, but the
    # accepted clip shot from it stays the highest non-reject take and every
    # downstream stage keeps eating it. Three beats of a delivered feature
    # carried a pre-swap face this way. italk.py re-renders on staleness
    # because a synced render is a deterministic derivation; a clip is a
    # reviewed lottery take, so nothing here retires it unasked -- but the
    # SKIP must say the plate changed, or the staleness is invisible until
    # someone screenshots the wrong face.
    for s in skip:
        clip = existing(s)[-1]
        note = ("  <-- your --seed did NOT re-roll this; retire the take "
                "first (--rej=<reason>) or pass --force"
                if seed != SEED else "")
        stale = (os.path.getmtime(gen_still.plate(s))
                 > os.path.getmtime(os.path.join(CLIPS, clip)))
        if stale:
            note = ("  <-- STALE: its plate is NEWER than this take -- the "
                    "picture changed under it; retire it (--rej=stale_plate) "
                    "and re-shoot" + note)
        print(f"  [{s}] SKIP -- {clip} on disk{note}")
    print()

    ok = sum(shoot(s, turbo, seed) for s in todo)

    # A FILMSTRIP FOR EVERY CLIP THAT LANDED, WITHOUT BEING ASKED. Motion
    # breaks in the MIDDLE of a clip -- a galaxy that darkens into a black rag,
    # a prop that grows -- and the first frame is the plate, which is the one
    # frame guaranteed to look right. A review step you have to remember is a
    # review step that gets skipped, so it is not a separate command any more.
    if "--no-strip" not in sys.argv:
        for s in todo:
            if check_clip.existing(s):
                try:
                    check_clip.strip(s)
                except Exception as e:                           # noqa: BLE001
                    print(f"  [{s}] no filmstrip: {e}")
    print(f"\n  {ok}/{len(todo)} shot.  "
          f"{sum(1 for s in shot.CUT if existing(s))}/{len(shot.CUT)} "
          f"beats now have a clip in {CLIPS}")
    return 0 if ok == len(todo) else 1


if __name__ == "__main__":
    sys.exit(main())
