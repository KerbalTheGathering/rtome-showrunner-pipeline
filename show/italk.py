"""Re-shoot the announcer on WAN 2.1 InfiniteTalk, driven by Dale's actual voice.

WHY THIS AND NOT A LIP-SYNC PASS. Both patch approaches were tried and measured.
Kling does not track this voice at all -- eight of ten frames at TRUE SILENCE
have the mouth open, half the peak-speech frames are shut -- and it repaints
42.6% of the frame to do it. Local Wav2Lip does track the voice, but it rebuilds
the mouth from a 96x96 crop and the user's verdict on it was "it's not clean".

InfiniteTalk is not a patch. It GENERATES the shot from the plate with the audio
as a driver, at the model's own resolution, so there is no mouth region pasted
over anything and nothing to feather.

AND IT ANSWERS THE OTHER NOTE AT THE SAME TIME. "The animation isn't always
hitting, especially when the southern news guy talks -- it's not great, and
repetitive feeling." That is not a sync defect and no sync pass would have
touched it: it is six segments of one locked-off medium shot with one gesture
vocabulary, because H3 was given a still and a sentence and invented the rest.
Here the motion is driven by the speech itself, so the beats land where the
words do and each segment moves differently because each one says something
different.

HOW IT RUNS. WanInfiniteTalkToVideo makes 81 frames at a time at 25fps -- 3.24s
-- and chains: each chunk takes the tail of the previous one as `previous_frames`
and continues. A 17.2s segment is six chunks. The audio is encoded ONCE for the
whole segment and the node takes the slice it needs, which is what keeps the
lip timing continuous across a join.

    lightx2v distill, so cfg 1.0 and FOUR steps. Not a corner cut -- that is
    what the distilled LoRA is for, and the reference workflow ships this way.

    THE PLATE IS THE FIRST FRAME OF THE SHIPPED CLIP, not the Krea2 still. The
    stills are 2432x1664 and the finished segments are 4:3; taking frame zero of
    clean_XX.mp4 means the framing, the crop and the 01/02 mirror are already
    exactly what shipped, with nothing to re-derive.

    python italk.py --test        # one 81-frame chunk of segment 01
    python italk.py 03            # one whole segment
    python italk.py               # all six
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402
import solo                                                        # noqa: E402


import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

import edit
import identity
import shot

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "_work")
OUT = os.path.join(HERE, "out")
FF = season_paths.FFMPEG
HOST = season_paths.COMFY_URL
INPUT = season_paths.COMFY_INPUT
COMFY_OUT = season_paths.COMFY_OUTPUT

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
IT_FPS = 25                  # InfiniteTalk's rate, like Wav2Lip's. Convert after.
FPS = float(identity.season.FPS)   # the season's clock; never typed (fault 112)
STEPS = 4
SEED = 704122

UNET = "Wan2_1-I2V-14B-480p_fp8_e4m3fn_scaled_KJ.safetensors"
LORA = "lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors"
PATCH = "Wan2_1-InfiniTetalk-Single_fp16.safetensors"
CLIP = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
VAE = "Wan2_1_VAE_bf16.safetensors"
AENC = "wav2vec2-chinese-base_fp16.safetensors"

# ONE PROMPT, DELIBERATELY THIN. The audio is the motion driver; a long shot
# description here competes with it and is how a locked-off news desk starts
# drifting. It says the frame is still and who is in it, and stops.
PROMPT = (
    "A television news presenter, an older man in a plaid jacket, seated behind "
    "a desk, speaking directly to the camera. Locked-off static camera, no "
    "camera movement. Painted illustration, flat even television studio light."
)
NEG = ""

# PER-SEGMENT ADDITIONS, AND ONLY WHERE ONE IS EARNED.
#
# Segment 03 is the only plate where he sits with his HANDS CLASPED TOGETHER
# high in frame, and it broke twice in the same place for the same reason: the
# hands deform whenever they MOVE. Seed 704122 swelled them into a smooth pale
# blob at 13.2s; seed 518447 fixed that spot exactly and then, at 14.5s, opened
# them into an oversized flipper with the fingers webbed together. Two takes
# failing the same way is this project's signal that the fault is not the seed
# and re-rolling is a lottery.
#
# So the hands get what the net and the idle hand got: a CONSERVED POSITION and
# a job, phrased as what stays rather than what must not happen, and named as
# still true in the last frame. Interlocked fingers at this scale are simply
# past what a 480p model reconstructs, so the fix is to stop asking it to
# re-draw them mid-gesture rather than to hope for a kinder roll.
PROMPT_EXTRA: dict[str, str] = {
    "03": (" His two hands stay clasped together in front of him exactly as "
           "they are in the first frame, one hand holding the other, resting in "
           "the same place the whole time, and they are still clasped together "
           "in that same place in the last frame."),
}

# WHICH FRAME OF THE OLD CLIP ANCHORS THE NEW TAKE. Zero by default, and that is
# not always safe: the anchor's mouth becomes the segment's opening mouth, so a
# plate caught mid-vowel opens on an open mouth over silence -- the exact defect
# this whole pass exists to remove, reintroduced by the anchor.
#
# H3 has him talking in nearly every frame, so a closed one has to be FOUND. 02
# is the one that needed it: f0 is a wide-open cavity, f25 is a clean lip line.
#
# EARLY, THOUGH. H3 pushes in about 6% across a clip and the board type is drawn
# at coordinates measured off the original framing, so an anchor from late in
# the take starts the segment tighter and walks the type off the felt. f55 and
# f90 are also closed and both are visibly larger. Checked by eye at 3x.
#
# AND 02 WAS NOT THE ONLY ONE THAT NEEDED IT -- it was the only one CHECKED.
# 01, 04 and 05 all shipped opening on a mouth already hanging open over the
# lead-in silence, 01 for the whole 0.40s before he says a word: the exact
# defect the paragraph above describes, left in three segments because the
# anchor was only ever examined on the segment that made it obvious. Found by
# putting frames 0-9 of all six against the typed lead from edit.offsets().
# The right values are the most closed frame in the first 60 of each clean
# take, ranked by mouth_open.py and then confirmed by eye at full frame for
# pose and hands, all inside 1.1s so the push-in constraint above still holds.
#
# ===== EVERY NUMBER IN THIS TABLE IS A MEASUREMENT OF *THIS SEASON'S* TAKES.
#
# It shipped filled in -- {"01": 27, "02": 25, "04": 14, "05": 5} -- and those
# are frame numbers found on ANOTHER ACTOR IN ANOTHER ROOM. A segment id
# resolves in every season, so a clone inherits them silently: its own 01 and
# 02 get anchored on somebody else's most-closed frame, which is an arbitrary
# frame of its own take, and the defect this table exists to remove is
# reintroduced by the table.
#
# A MEASURED NUMBER AND A COPIED ONE LOOK IDENTICAL IN A FILE. So it ships
# EMPTY, and anything empty is a job to do rather than a value to trust:
# `python mouth_open.py` ranks the candidates, then LOOK at the frames.
# Zero is the safe default and it is what every unfilled segment gets.
START_FRAME: dict[str, int] = {}

# HOW MANY FRAMES TO DELAY THE PICTURE AGAINST THE VOICE, per segment.
#
# Segment 04 came back with the mouth consistently AHEAD of the audio: its three
# lines measure -125ms, -125ms and -83ms independently, while every other
# segment scatters around zero the way noise does (01 is +0/+0/-42). A lead is
# the direction the ear forgives least once it passes about 125ms, and 04 sits
# on that line, which is what "some seem off to the audio" was pointing at.
#
# NOT A RE-RENDER. The offset is a whole number of finished frames, so it is
# corrected by moving them -- `--shift-only` rebuilds synced_XX.mp4 from the raw
# already on disk. A re-render would roll a different take and could not be
# checked against the one that was measured.
#
# AND THE TYPE DOES NOT MOVE. bake() draws the board lines by FRAME INDEX and
# mix() builds the audio from edit.offsets() independently, so shifting the
# picture inside the clip slides the mouth without touching either.
#
# Direction confirmed by injecting a known shift into a segment that measures
# zero and checking the tool recovered it: +3f read as +125ms, -3f as -125ms.
#
# ===== ALSO MEASURED ON THIS SEASON'S TAKES, AND ALSO SHIPPED FILLED IN.
# {"04": 3} moves segment 04's picture three frames against its voice on the
# strength of a lag measured on a different render. Empty is the honest state:
# `python sync_probe.py` measures the lag on the takes you actually have.
SHIFT: dict[str, int] = {}


def chunks_for(n25: int) -> int:
    """How many passes it takes to reach `n25` frames at 25fps.

    ONLY THE FIRST CHUNK YIELDS 81 FRAMES. Every chained one re-decodes the
    motion frames it was handed and those get trimmed, so it contributes
    81 - motion_frame_count = 72. Dividing the target by 81 undercounts, and it
    undercounts SILENTLY: segments 02 and 04 came back eight frames short, which
    is a tenth of a second of board type sitting on the wrong word. Caught only
    because the frame count is asserted against the mix after every render.
    """
    if n25 <= CHUNK:
        return 1
    return 1 + -(-(n25 - CHUNK) // (CHUNK - MOTION))


def ff(*a: str) -> None:
    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error", *a],
                   check=True)


def graph(img: str, aud: str, n_frames: int, prefix: str, seed: int,
          prev: str | None = None, scale: float = 1.0,
          prompt: str | None = None) -> dict:
    """One graph, with as many chained 81-frame passes as the segment needs.

    THE CHAIN IS BUILT HERE RATHER THAN ACROSS SUBMISSIONS, and the reason is
    generation loss. `previous_frames` is not the last few frames -- it is the
    WHOLE accumulated batch, because that is how the node knows where it is in
    the audio. Handing that between separate jobs means writing it to a video
    and reading it back, so every chunk would re-encode all of its predecessors
    and the picture would degrade down the segment. In one graph it stays a
    tensor. Costs resumability, buys a clean image; a failed segment is six
    minutes, and it is free.

    `start_image` is the ORIGINAL plate on every chunk, not the previous tail.
    That is what stops a six-link chain drifting off the character -- the model
    is re-anchored to Dale each pass and only the continuation comes from the
    accumulated frames.
    """
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
              "inputs": {"clip": ["4", 0], "text": prompt or PROMPT}},
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
               "start_image": ["11", 0]}
        if acc is not None:
            ins["previous_frames"] = acc
        g[it] = {"class_type": "WanInfiniteTalkToVideo", "inputs": ins}
        g[sch] = {"class_type": "BasicScheduler",
                  "inputs": {"model": [it, 0], "scheduler": "normal",
                             "steps": STEPS, "denoise": 1.0}}
        # A FRESH SEED PER CHUNK. Reusing one across six passes correlates the
        # noise between them, which shows up as the same micro-gesture landing
        # every 3.24 seconds -- the exact "repetitive" note this is meant to fix.
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
        # THE FIFTH OUTPUT IS WHERE THIS CHUNK'S NEW FRAMES BEGIN. A chained
        # pass decodes the motion frames it was handed as well as the ones it
        # made, and appending those would stutter the join every 3.24s.
        g[new] = {"class_type": "ImageFromBatch",
                  "inputs": {"image": [dec, 0], "batch_index": [it, 4],
                             "length": 4096}}
        g[f"ab{k}"] = {"class_type": "ImageBatch",
                       "inputs": {"image1": acc, "image2": [new, 0]}}
        acc = [f"ab{k}", 0]

    # THE AUDIO GOES IN HERE, NOT AT ASSEMBLE TIME. Muxing the driver into the
    # raw means the file that comes out of the graph can be watched with sound
    # immediately -- a take can be judged for sync before anything is upscaled,
    # typed, tubed or cut. It is the SAME wav the model was driven by (node 9),
    # so what you hear is exactly what shaped the lips, in guaranteed alignment;
    # a prettier 96kHz copy muxed in later would only add a chance to misalign.
    # The 25->24 conversion below still passes -an, so synced_XX.mp4 stays mute
    # and assemble.py remains the one place the real mix is built.
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
        if time.time() - t0 > 3600:
            sys.exit(f"FAIL: {label} timed out")


def plate(sid: str) -> str:
    """The anchor frame from the shipped clean bake, at the generation size."""
    src = os.path.join(WORK, f"clean_{sid}.mp4")
    if not os.path.exists(src):
        sys.exit(f"FAIL: {src} missing -- run `assemble.py --clean {sid}`")
    n = START_FRAME.get(sid, 0)
    dst = os.path.join(INPUT, f"it_{sid}_start.png")
    ff("-i", src, "-vf", f"select=eq(n\\,{n}),scale={GW}:{GH}:flags=lanczos",
       "-frames:v", "1", dst)
    return dst


def audio(sid: str, secs: float | None = None) -> str:
    src = os.path.join(WORK, f"vo_{sid}.wav")
    if not os.path.exists(src):
        sys.exit(f"FAIL: {src} missing")
    dst = os.path.join(INPUT, f"it_{sid}.wav")
    ff(*(["-t", f"{secs:.3f}"] if secs else []), "-i", src,
       "-ac", "1", "-ar", "16000", dst)
    return dst


def main() -> int:
    # ONE COPY OF THIS STAGE AT A TIME, refused at entry rather than at the
    # point of damage. `busy()` below already stops two renders overlapping;
    # it cannot stop two PROCESSES from waiting on each other forever. See
    # solo.py -- four copies of a batch tool once deadlocked on their own
    # correct queue guard, at 0% GPU, with nothing in any log.
    solo.solo("lipsync", where=HERE, force="--force" in sys.argv)
    test = "--test" in sys.argv
    want = [a for a in sys.argv[1:] if not a.startswith("-")] or list(shot.CUT)
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)

    # AUDIO_SCALE IS THE LIP AMPLITUDE. At the default 1.0 the silence test
    # passes -- the mouth is shut when nobody is talking, which is the defect
    # Kling failed -- but the openings during speech are small for a man selling
    # something at volume. It is the one knob worth sweeping before a two-hour
    # render, so --scale takes a list.
    #
    # THE DEFAULT IS THE VALUE THAT SHIPPED. All six segments were rendered at
    # 1.5 after that sweep, but the default here stayed 1.0, so re-rendering a
    # segment without remembering the flag would quietly rebuild it with lips
    # that move less than the five around it -- a mismatch no assert would
    # catch and no frame count would flag. A knob that has been decided belongs
    # in the file, not in the shell history.
    scales = [1.5]
    for a in sys.argv[1:]:
        if a.startswith("--scale="):
            scales = [float(x) for x in a.split("=", 1)[1].split(",")]

    if test:
        sid = want[0] if want else "01"
        img, aud = plate(sid), audio(sid, secs=CHUNK / IT_FPS)
        for s in scales:
            print(f"  [{sid}] {CHUNK}f at {GW}x{GH}, audio_scale {s} ...",
                  end="", flush=True)
            got = submit(graph(img, aud, CHUNK, f"it_test/{sid}", SEED,
                               scale=s), f"test {sid} @{s}")
            dst = os.path.join(OUT, f"italk_test_{s:.2f}.mp4")
            shutil.copy2(got, dst)
            print(f" -> {os.path.basename(dst)}")
        return 0

    scale = scales[0]
    shift_only = "--shift-only" in sys.argv
    # A GLITCHED TAKE IS A SEED PROBLEM, NOT A PROMPT ONE. Segment 03 came back
    # with the hands fused into one mass and grey patches eaten out of the
    # jacket -- nothing the thin prompt or the plate asks for, and the plate's
    # own first frame is clean. Re-rolling needs a different base seed; without
    # this flag --force would faithfully rebuild the same defect.
    seed = SEED
    for a in sys.argv[1:]:
        if a.startswith("--seed="):
            seed = int(a.split("=", 1)[1])
    for sid in want:
        want_f = edit.FRAMES[sid]
        # Ceiling, not round: asking for exactly enough 25fps frames and then
        # converting down leaves nothing for the rate change to lose.
        n_it = -(-want_f * IT_FPS // int(FPS))
        n_chunks = chunks_for(n_it)
        dst = os.path.join(WORK, f"synced_{sid}.mp4")
        raw = os.path.join(WORK, f"it_raw_{sid}.mp4")
        if os.path.exists(dst) and not shift_only and "--force" not in sys.argv:
            # A SYNC OLDER THAN ITS PICTURE IS NOT "HAVE IT". This skip is an
            # idempotency shortcut, and it once kept four v1 renders alive
            # through a full recast: every plate and take upstream had been
            # replaced, this line said "have it" four times, and only a
            # face-check on the bake caught it. Same class as the h3_shoot
            # --seed skip (fault 44): a requested re-render silently not
            # running. The clean bake is this render's anchor source, so its
            # mtime is the honest freshness test.
            clean = os.path.join(WORK, f"clean_{sid}.mp4")
            if (os.path.exists(clean)
                    and os.path.getmtime(clean) > os.path.getmtime(dst)):
                print(f"  [{sid}] synced render predates clean_{sid}.mp4 -- "
                      f"the picture changed under it; re-rendering")
            else:
                print(f"  [{sid}] have it, skipping (--force to redo)")
                continue
        if shift_only:
            # Re-derive from the raw already on disk. The shift below is a whole
            # number of finished frames, so there is nothing to regenerate and
            # nothing that can come back different.
            if not os.path.exists(raw):
                sys.exit(f"FAIL: {raw} missing -- cannot shift without it")
            print(f"  [{sid}] shift {SHIFT.get(sid, 0):+d}f from raw ...",
                  end="", flush=True)
        else:
            print(f"  [{sid}] {want_f}f@{FPS:g} = {n_it}f@{IT_FPS} -> {n_chunks} chunks "
                  f"x{scale} ...", end="", flush=True)
            img, aud = plate(sid), audio(sid)
            got = submit(graph(img, aud, n_it, f"it/{sid}", seed, scale=scale,
                               prompt=PROMPT + PROMPT_EXTRA.get(sid, "")),
                         sid)
            shutil.copy2(got, raw)
        # IT_FPS -> season FPS, then cut to the EXACT frame count the mix is
        # built against. The chunking overshoots by design (six 81s covers
        # 430), and a segment that runs long puts the board type off the
        # words it is timed to. The season rate, not a typed 24 (fault 112).
        vf = f"fps={float(FPS):g}"
        k = SHIFT.get(sid, 0)
        if k:
            # Hold the first frame k times and let the -frames:v cut take k off
            # the tail. The tail is the 1.20s of silence after he stops, so the
            # frames lost are frames of a man sitting still.
            vf += f",tpad=start={k}:start_mode=clone"

        # THE VOICE IS CUT IN THE SAME CALL AS THE PICTURE, AND SHIPS WITH IT.
        #
        # The graph muxes the driver into the raw already, but only at 16 kHz
        # mono -- that is what the model listens to, not something to deliver.
        # What matters is that node 9's audio IS `vo_{sid}.wav` starting at
        # t=0, so the full-quality file is the same timeline at better
        # resolution, and cutting it here to the same frame count in the same
        # invocation means the picture and the voice cannot be produced apart
        # or fall out of step later.
        #
        # A SIDECAR WAV RATHER THAN A MUXED TRACK, deliberately: an AAC track
        # inside the mp4 would put an encoder priming delay between the render
        # and the bake, which is precisely the class of shift this whole change
        # exists to eliminate. assemble.py refuses to bake without it and
        # refuses to bake if it is older than the picture.
        #
        # 25 -> 24 does not retime anything. `fps` drops frames to hit a rate;
        # the wall clock is untouched, so the voice needs no compensation for
        # the conversion, only the same end cut.
        drv = os.path.join(WORK, f"vo_{sid}.wav")
        rate = int(subprocess.run(
            [season_paths.ff("ffprobe"), "-v", "error", "-select_streams",
             "a:0", "-show_entries", "stream=sample_rate", "-of", "csv=p=0",
             drv], capture_output=True, text=True, check=True).stdout.strip())
        if rate % 24:
            sys.exit(f"FAIL: {drv} is {rate} Hz, which does not divide into 24 "
                     f"frames -- the cut would land between samples")
        wav = os.path.join(WORK, f"synced_{sid}.wav")
        ff("-i", raw, "-i", drv,
           "-map", "0:v:0", "-vf", vf, "-frames:v", str(want_f), "-an",
           "-c:v", "libx264", "-crf", "14", "-preset", "slow",
           "-pix_fmt", "yuv420p", dst,
           "-map", "1:a:0", "-af", f"apad,atrim=end_sample={want_f * rate // 24}",
           "-c:a", "pcm_s16le", wav)
        n = subprocess.run(
            [season_paths.ff("ffprobe"), "-v", "error", "-select_streams",
             "v:0", "-count_frames", "-show_entries", "stream=nb_read_frames",
             "-of", "csv=p=0", dst], capture_output=True, text=True,
            check=True).stdout.strip()
        flag = "" if int(n) == want_f else f"   <-- got {n}, want {want_f}"
        print(f" -> {os.path.basename(dst)}{flag}")
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
