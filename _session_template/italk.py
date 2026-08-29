"""Re-shoot one beat on WAN 2.1 InfiniteTalk so the character actually says the line.

WHAT IS DIFFERENT ABOUT THIS FILM. The season is narrated in voiceover and every
beat of it is deliberately a mouth that does NOT move -- an outside critique
opened with "a mouth moving under VO reads as a mistake", and five sessions of
re-shoots exist to enforce that. Beat 12 is the exception the user asked for, and
it earns it: he is reading a name out of the ledger in his hands, so the line IS
the action in the frame rather than commentary laid over it.

SO THE DEFAULT STAYS SILENT AND THIS IS OPT-IN PER BEAT. `TALKING` below is the
whole list. Nothing here runs unless a beat is in it.

HOW IT RUNS -- lifted from BIGSHOT_src/italk.py, which is where all of this was
paid for. WanInfiniteTalkToVideo makes 81 frames at a time at 25fps and chains,
each chunk taking the whole accumulated batch as `previous_frames` so the node
knows where it is in the audio. The chain is built inside ONE graph: handing it
between submissions means writing frames to a video and reading them back, so
every chunk would re-encode all its predecessors. lightx2v distill, so cfg 1.0
and four steps.

    IT REPLACES THE WHOLE CLIP, NOT THE MOUTH. InfiniteTalk generates the shot
    from the anchor frame with the audio as a driver, so the beat's own motion
    (the rain, the page, the reflections) is regenerated too. That is the point
    -- nothing is pasted over anything -- but it means the take has to be judged
    as a whole shot, not just at the lips.

    THE OUTPUT IS THE FULL 8s CLIP, NOT THE 6.68s BEAT. assemble.py enters every
    clip at `ss` and takes `beat` seconds, so a replacement cut to the beat would
    be entered 0.35s in and come out short at the tail. Generating the clip's own
    length leaves every number downstream untouched.

    python italk.py --probe      # one 81-frame chunk, to see the character hold
    python italk.py 12           # the beat
    python italk.py 12 --seed=N  # a different roll of the same words
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402
import solo                                                        # noqa: E402


import json
import math
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

import edit
import identity
import make_video
import script
import shot        # which beats this film actually has

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "_work")
VO = os.path.join(HERE, "_vo")
FF = season_paths.FFMPEG
HOST = season_paths.COMFY_URL
INPUT = season_paths.COMFY_INPUT
COMFY_OUT = season_paths.COMFY_OUTPUT
CLIPS = make_video.outdir()

# THE PIXEL BUDGET IS THE FACT ABOUT THE MODEL; THE ASPECT IS THE SEASON'S.
#
# This was `GW, GH = 768, 576` -- 4:3, both divisible by 16, about 10% over the
# 480p model's native pixel count, and the size H3 shoots at, so the upscale to
# the delivery size is the same one every other part of the season goes
# through. All of that is still true and only the LAST clause depends on the
# aspect, which is why the pair is now derived: a 16:9 season would have synced
# its host at 4:3 and been squashed on the way back out, and nothing measures
# the shape of a mouth.
#
# For a 4:3 season this returns 768x576 exactly.
IT_PIXELS = 768 * 576
GW, GH = season_paths.at_aspect(identity.season.W, identity.season.H, IT_PIXELS)
CHUNK = 81                   # frames per pass, fixed by the node
MOTION = 9                   # tail frames handed to the next chunk
IT_FPS = 25                  # InfiniteTalk's rate. Convert after.
# THE SEASON'S RATE, DERIVED. `24` was typed in eleven files beside a
# season_identity.FPS that already said so -- and feature.py asserts every
# part matches, so a season at another rate would have been caught only
# after every part was baked.
FPS = identity.season.FPS
STEPS = 4
SEED = 704122
SCALE = 1.5                  # audio_scale: lip amplitude, swept on the season

UNET = "Wan2_1-I2V-14B-480p_fp8_e4m3fn_scaled_KJ.safetensors"
LORA = "lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors"
PATCH = "Wan2_1-InfiniTetalk-Single_fp16.safetensors"
CLIP = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
VAE = "Wan2_1_VAE_bf16.safetensors"
AENC = "wav2vec2-chinese-base_fp16.safetensors"

# WHICH BEATS SPEAK ON CAMERA. See the docstring: this is the exception list for
# a film whose whole discipline is closed mouths.
#
# EMPTY, BECAUSE A BEAT ID BELONGS TO A FILM. This shipped as {"12"} -- beat 12
# of the film this example was lifted from -- and beat 12 exists in any session
# that has twelve beats, so a clone inherited the exception without inheriting
# the reason for it. Nothing fails: the tool simply lip-syncs a beat nobody
# asked it to, or refuses to sync the one that does speak because the id it was
# told about is somebody else's.
TALKING: set[str] = set()

assert TALKING <= set(shot.CUT), (
    f"TALKING names beats this film does not have: "
    f"{sorted(TALKING - set(shot.CUT))}")

# ONE PROMPT PER BEAT, DELIBERATELY THIN. The audio is the motion driver and a
# long shot description competes with it. It names who is in frame so the
# character holds across a three-link chain, and it pins the hands.
#
# THE HANDS ARE PINNED BEFORE THEY FAIL, NOT AFTER. This model's known break is
# hands that MOVE -- the bounty announcer's clasped hands swelled into a pale
# blob on one seed and a webbed flipper on the next, and two takes failing the
# same way is this project's signal that re-rolling is a lottery. He is holding
# an open ledger in both hands here, which is the same shape of problem, so the
# clause that fixed it goes in from the start: a conserved position, phrased as
# what stays, and named as still true in the last frame.
#
# ONE ENTRY PER BEAT IN `TALKING` AND NO OTHERS -- asserted below, because a
# prompt left behind by another film is a paragraph of somebody else's room
# handed to the model as the description of yours. The example that shipped
# here was beat 12 of a different session, in a teal-green suit, in a rain-wet
# brick street.
PROMPT: dict[str, str] = {
    # "12": (
    #     "A man in a tailored teal-green suit with a clear round glass dome "
    #     "over his head, standing in a rain-wet brick street at night, reading "
    #     "aloud from the open ledger he is holding. Locked-off static camera, "
    #     "no camera movement. Painted illustration, flat layered colour and "
    #     "ink linework. His two hands stay holding the open ledger in front of "
    #     "him exactly as they are in the first frame, at the same height and "
    #     "in the same place the whole time, and they are still holding it in "
    #     "that same place in the last frame."
    # ),
}
NEG = ""

assert set(PROMPT) == TALKING, (
    f"PROMPT and TALKING disagree about which beats speak: "
    f"{sorted(set(PROMPT) ^ TALKING)}. Every talking beat needs its own thin "
    f"prompt, and a prompt for a beat that does not talk is another film's "
    f"room left in this one.")

# WHICH FRAME OF THE EXISTING CLIP ANCHORS THE TAKE. The anchor's mouth becomes
# the take's opening mouth, so a frame caught mid-vowel opens on an open mouth
# over the lead-in silence -- which is the defect this whole approach exists to
# avoid, reintroduced by the anchor. Beat 12 needs no offset: he reads silently
# through the original and frames 0-29 measure 0.086-0.095 aperture, a 10% band
# against the 1.6x that means a moving mouth. Frame 0 also keeps the replacement
# aligned frame-for-frame with the clip it stands in for.
START_FRAME: dict[str, int] = {}


def chunks_for(n25: int) -> int:
    """How many passes it takes to reach `n25` frames at 25fps.

    ONLY THE FIRST CHUNK YIELDS 81. Every chained one re-decodes the motion
    frames it was handed and those get trimmed, so it contributes 81 - MOTION.
    Dividing by 81 undercounts, and it undercounts silently.
    """
    if n25 <= CHUNK:
        return 1
    return 1 + -(-(n25 - CHUNK) // (CHUNK - MOTION))


def ff(*a: str) -> None:
    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error", *a],
                   check=True)


def probe(path: str, stream: str) -> str:
    return subprocess.run(
        [season_paths.ff("ffprobe"), "-v", "error", "-show_entries",
         stream, "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True).stdout.strip()


def row(sid: str) -> dict:
    return next(r for r in edit.table() if r["sid"] == sid)


def anchor(sid: str) -> str:
    """The first frame, taken from the clip this take replaces."""
    src = make_video.clip(sid)
    n = START_FRAME.get(sid, 0)
    dst = os.path.join(INPUT, f"it_{sid}_start.png")
    ff("-i", src, "-vf", f"select=eq(n\\,{n}),scale={GW}:{GH}:flags=lanczos",
       "-frames:v", "1", dst)
    return dst


def driver(sid: str, secs: float, only: float | None = None) -> str:
    """The wav that shapes the lips: the beat's audio, laid out in CLIP time.

    THE SILENCE IN FRONT IS LOAD-BEARING AND IT IS TWO THINGS ADDED TOGETHER.
    assemble.py enters the clip at `ss` and the line starts `lead` seconds after
    that, so the voice belongs at ss + lead into the generated clip -- not at
    zero, and not at `lead`. Getting it wrong does not fail: it produces a man
    who starts talking before the cut reaches him.
    """
    r = row(sid)
    lids = r["lines"]
    if len(lids) != 1:
        sys.exit(f"FAIL: beat {sid} carries {len(lids)} lines; this builds one")
    src = os.path.join(VO, f"{lids[0]}.mp3")
    if not os.path.exists(src):
        sys.exit(f"FAIL: {src} missing -- run make_vo.py")
    head = r["ss"] + r["lead"]
    dst = os.path.join(INPUT, f"it_{sid}.wav")
    ff("-i", src, "-af",
       f"adelay={int(round(head * 1000))}|{int(round(head * 1000))},"
       f"apad=whole_dur={secs:.3f}",
       "-t", f"{secs:.3f}", "-ac", "1", "-ar", "16000", dst)
    got = float(probe(dst, "format=duration"))
    if abs(got - secs) > 0.05:
        sys.exit(f"FAIL: driver is {got:.2f}s against {secs:.2f}s wanted")
    print(f"       voice at {head:.2f}s into a {got:.2f}s driver "
          f"({lids[0]}.mp3, {r['speech']:.2f}s)")
    if only:
        cut = os.path.join(INPUT, f"it_{sid}_probe.wav")
        ff("-t", f"{only:.3f}", "-i", dst, "-ac", "1", "-ar", "16000", cut)
        return cut
    return dst


def graph(img: str, aud: str, n_frames: int, prefix: str, seed: int,
          prompt: str, scale: float = SCALE) -> dict:
    n_chunks = chunks_for(n_frames)
    g = {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": UNET, "weight_dtype": "default"}},
        "2": {"class_type": "LoraLoaderModelOnly",
              "inputs": {"model": ["1", 0], "lora_name": LORA,
                         "strength_model": 1.0}},
        "3": {"class_type": "ModelPatchLoader", "inputs": {"name": PATCH}},
        "4": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": CLIP, "type": "wan", "device": "default"}},
        "5": {"class_type": "CLIPTextEncode",
              "inputs": {"clip": ["4", 0], "text": prompt}},
        "6": {"class_type": "CLIPTextEncode",
              "inputs": {"clip": ["4", 0], "text": NEG}},
        "7": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "8": {"class_type": "AudioEncoderLoader",
              "inputs": {"audio_encoder_name": AENC}},
        "9": {"class_type": "LoadAudio",
              "inputs": {"audio": os.path.basename(aud)}},
        "10": {"class_type": "AudioEncoderEncode",
               "inputs": {"audio_encoder": ["8", 0], "audio": ["9", 0]}},
        "11": {"class_type": "LoadImage",
               "inputs": {"image": os.path.basename(img)}},
        "13": {"class_type": "KSamplerSelect",
               "inputs": {"sampler_name": "euler"}},
    }

    acc = None
    for k in range(n_chunks):
        it, sch, noi, cfg, smp, dec, new = (f"it{k}", f"sc{k}", f"no{k}",
                                            f"cg{k}", f"sp{k}", f"de{k}",
                                            f"nw{k}")
        ins = {"mode": "single_speaker", "model": ["2", 0],
               "model_patch": ["3", 0], "positive": ["5", 0],
               "negative": ["6", 0], "vae": ["7", 0],
               "width": GW, "height": GH, "length": CHUNK,
               "audio_encoder_output_1": ["10", 0],
               "motion_frame_count": MOTION, "audio_scale": scale,
               # The ORIGINAL anchor on every chunk, never the previous tail --
               # that is what stops a chain drifting off the character.
               "start_image": ["11", 0]}
        if acc is not None:
            ins["previous_frames"] = acc
        g[it] = {"class_type": "WanInfiniteTalkToVideo", "inputs": ins}
        g[sch] = {"class_type": "BasicScheduler",
                  "inputs": {"model": [it, 0], "scheduler": "normal",
                             "steps": STEPS, "denoise": 1.0}}
        # A fresh seed per chunk: one seed across the chain correlates the noise
        # and lands the same micro-gesture every 3.24s.
        g[noi] = {"class_type": "RandomNoise",
                  "inputs": {"noise_seed": seed + k * 7919}}
        g[cfg] = {"class_type": "CFGGuider",
                  "inputs": {"model": [it, 0], "positive": [it, 1],
                             "negative": [it, 2], "cfg": 1.0}}
        g[smp] = {"class_type": "SamplerCustomAdvanced",
                  "inputs": {"noise": [noi, 0], "guider": [cfg, 0],
                             "sampler": ["13", 0], "sigmas": [sch, 0],
                             "latent_image": [it, 3]}}
        g[dec] = {"class_type": "VAEDecode",
                  "inputs": {"samples": [smp, 0], "vae": ["7", 0]}}
        if acc is None:
            acc = [dec, 0]
            continue
        # The fifth output is where this chunk's NEW frames begin; appending the
        # re-decoded motion frames stutters the join every 3.24s.
        g[new] = {"class_type": "ImageFromBatch",
                  "inputs": {"image": [dec, 0], "batch_index": [it, 4],
                             "length": 4096}}
        g[f"ab{k}"] = {"class_type": "ImageBatch",
                       "inputs": {"image1": acc, "image2": [new, 0]}}
        acc = [f"ab{k}", 0]

    # THE AUDIO GOES IN AT GENERATION TIME. It is the same wav the model was
    # driven by (node 9), so the take can be judged for sync the moment it lands
    # -- before anything is upscaled or cut -- in guaranteed alignment.
    g["20"] = {"class_type": "CreateVideo",
               "inputs": {"images": acc, "fps": float(IT_FPS),
                          "audio": ["9", 0]}}
    g["21"] = {"class_type": "SaveVideo",
               "inputs": {"video": ["20", 0], "filename_prefix": prefix,
                          "format": "auto", "codec": "auto"}}
    return g


def submit(g: dict, label: str) -> str:
    body = json.dumps({"prompt": g}).encode()
    try:
        pid = json.load(urllib.request.urlopen(urllib.request.Request(
            f"{HOST}/prompt", body,
            {"Content-Type": "application/json"})))["prompt_id"]
    except urllib.error.HTTPError as e:
        sys.exit(f"FAIL: {label} rejected {e.code}\n"
                 f"{e.read()[:2000].decode(errors='replace')}")
    t0 = time.time()
    while True:
        time.sleep(6)
        h = json.load(urllib.request.urlopen(f"{HOST}/history/{pid}"))
        if pid in h:
            fs = [f for o in h[pid].get("outputs", {}).values()
                  for f in o.get("videos", []) + o.get("gifs", [])
                  + o.get("images", [])]
            if not fs:
                sys.exit(f"FAIL: {label} after {time.time()-t0:.0f}s\n"
                         + json.dumps(h[pid].get("status", {}), indent=1)[:2000])
            print(f" {time.time()-t0:.0f}s", end="", flush=True)
            return os.path.join(COMFY_OUT, fs[-1].get("subfolder", ""),
                                fs[-1]["filename"])
        if time.time() - t0 > 5400:
            sys.exit(f"FAIL: {label} timed out")


def next_take(sid: str) -> str:
    have = [f for f in os.listdir(CLIPS) if f.startswith(f"s{sid}_")]
    n = max((int(f[4:9]) for f in have if f[4:9].isdigit()), default=0) + 1
    return os.path.join(CLIPS, f"s{sid}_{n:05d}_.mp4")


def main() -> int:
    # ONE COPY OF THIS STAGE AT A TIME, refused at entry rather than at the
    # point of damage. `busy()` below already stops two renders overlapping;
    # it cannot stop two PROCESSES from waiting on each other forever. See
    # solo.py -- four copies of a batch tool once deadlocked on their own
    # correct queue guard, at 0% GPU, with nothing in any log.
    solo.solo("lipsync", where=HERE, force="--force" in sys.argv)
    seed = int(next((a.split("=", 1)[1] for a in sys.argv[1:]
                     if a.startswith("--seed=")), SEED))
    scale = float(next((a.split("=", 1)[1] for a in sys.argv[1:]
                        if a.startswith("--scale=")), SCALE))
    known = ("--probe", "--seed=", "--scale=")
    junk = [a for a in sys.argv[1:]
            if a.startswith("--") and not a.startswith(known)]
    if junk:
        sys.exit(f"FAIL: unknown flag(s) {junk}. Known: {', '.join(known)}")

    want = [a for a in sys.argv[1:] if not a.startswith("--")] or sorted(TALKING)
    bad = [s for s in want if s not in TALKING]
    if bad:
        sys.exit(f"FAIL: {bad} not in TALKING. This film's beats are silent by "
                 "default -- add the beat there deliberately, with a reason.")
    os.makedirs(WORK, exist_ok=True)

    for sid in want:
        src = make_video.clip(sid)
        secs = float(probe(src, "format=duration"))
        want_f = int(probe(src, "stream=nb_frames").split()[0])
        # Ceiling: asking for exactly enough 25fps frames and converting down
        # leaves nothing for the rate change to lose.
        n_it = math.ceil(secs * IT_FPS)
        n_chunks = chunks_for(n_it)
        print(f"  [{sid}] replacing {os.path.basename(src)} "
              f"({want_f}f@{FPS} = {secs:.2f}s)")
        print(f"       {n_it}f@{IT_FPS} -> {n_chunks} chunk(s) at {GW}x{GH}, "
              f"audio_scale {scale}, seed {seed}")

        if "--probe" in sys.argv:
            img = anchor(sid)
            aud = driver(sid, secs, only=CHUNK / IT_FPS)
            print("       probe ...", end="", flush=True)
            got = submit(graph(img, aud, CHUNK, f"it_probe/{sid}", seed,
                               PROMPT[sid], scale), f"probe {sid}")
            dst = os.path.join(WORK, f"it_probe_{sid}.mp4")
            shutil.copy2(got, dst)
            print(f" -> {dst}")
            continue

        img, aud = anchor(sid), driver(sid, secs)
        print("       generating ...", end="", flush=True)
        got = submit(graph(img, aud, n_it, f"it/{sid}", seed, PROMPT[sid],
                           scale), sid)
        raw = os.path.join(WORK, f"it_raw_{sid}.mp4")
        shutil.copy2(got, raw)

        # IT_FPS -> season FPS, cut to the frame count the clip it replaces
        # had. The chunking overshoots by design and a clip that runs long
        # would push every beat after it. The season rate, NOT a typed 24:
        # this file derives FPS four lines from the top under a comment about
        # "24 typed in eleven files" and then typed it here anyway -- on a
        # 25 or 30 fps season the take converted to the wrong clock while
        # -frames:v counted frames measured at the right one (fault 112).
        dst = next_take(sid)
        ff("-i", raw, "-vf", f"fps={float(FPS):g}", "-frames:v", str(want_f),
           "-c:v", "libx264", "-crf", "14", "-preset", "slow",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "320k", dst)
        n = int(probe(dst, "stream=nb_frames").split()[0])
        if n != want_f:
            sys.exit(f"FAIL: {os.path.basename(dst)} is {n}f, wanted {want_f}")
        print(f"       -> {os.path.basename(dst)}  {n}f, "
              f"{os.path.getsize(dst)/1e6:.1f} MB")
        # SAID OUT LOUD BECAUSE IT IS ALREADY TRUE. This lands in the clip
        # directory with no `_rej_`, so it is the highest-numbered survivor and
        # make_video.clip() picks it from this moment -- before anybody has
        # looked at it. Judge it now: retire the take it replaces if it is kept,
        # or `_rej_` THIS one if it is not.
        print(f"       IT IS NOW THE SELECTED TAKE for beat {sid} "
              f"(was {os.path.basename(src)}). Judge it before building.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
