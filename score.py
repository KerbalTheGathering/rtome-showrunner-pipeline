"""The season's score generator: ACE-Step 1.5 XL, local, free. One place.

Every tree's make_music.py calls `render(name, secs, cue, out_dir)` with a
CUE dict and gets an mp3 that is at least `secs` of live music. The graph is
the bundled turbo template (memory: ace-step-local-music): UNET turbo ->
ModelSamplingAuraFlow shift 3 -> KSampler 8 steps cfg 1 euler/simple;
DualCLIPLoader qwen_0.6b + qwen_4b type "ace"; TextEncodeAceStepAudio1.5
pins bpm / duration / timesignature / keyscale -- which is the point: the
cues are generated independently, so the KEY FAMILY is what makes them one
score (LOSS OF SIGNAL: D major for the world as briefed, D minor for the
void). A cue with {"silent": True} writes digital silence of the right
length: a span under nothing is an editorial choice, not a missing cue.
$0.00 a minute against ElevenLabs Music's $0.15; docs/03_audio.md.

    CUE = {"tags": "...", "bpm": 66, "key": "D major", "ts": "4", "seed": 1}

`usable_seconds` measures where the music actually stops (the template's
rule: a file that is the right length can still end in digital silence).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import season_paths                                                # noqa: E402
import season_identity as season                                   # noqa: E402

HOST = season_paths.COMFY_URL
UNET = "acestep_v1.5_xl_turbo_bf16.safetensors"
CLIP_A, CLIP_B = "qwen_0.6b_ace15.safetensors", "qwen_4b_ace15.safetensors"
VAE = "ace_1.5_vae.safetensors"
PAD = 15.0           # ACE fades out ~8 s before the requested end; measured on the first cue
INSTRUMENTAL = "[Instrumental]"


def graph(cue: dict, secs: float, prefix: str) -> dict:
    return {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": UNET, "weight_dtype": "default"}},
        "2": {"class_type": "ModelSamplingAuraFlow",
              "inputs": {"model": ["1", 0], "shift": 3.0}},
        "3": {"class_type": "DualCLIPLoader",
              "inputs": {"clip_name1": CLIP_A, "clip_name2": CLIP_B,
                         "type": "ace", "device": "default"}},
        "4": {"class_type": "TextEncodeAceStepAudio1.5",
              "inputs": {"clip": ["3", 0], "tags": cue["tags"],
                         # A cue may carry its own sung lyrics ("lyrics" key); the default
                         # stays instrumental. Added for HOW TO HAVE A DAY's
                         # sung stings, 2026-08-23 -- ACE 1.5 takes plain lines.
                         "lyrics": cue.get("lyrics", INSTRUMENTAL),
                         "seed": cue.get("seed", 1),
                         "bpm": cue["bpm"], "duration": float(secs),
                         "timesignature": cue.get("ts", "4"),
                         "language": "en", "keyscale": cue["key"],
                         "generate_audio_codes": True, "cfg_scale": 2.0,
                         "temperature": 0.85, "top_p": 0.9, "top_k": 0,
                         "min_p": 0.0}},
        "5": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["4", 0]}},
        "6": {"class_type": "EmptyAceStep1.5LatentAudio",
              "inputs": {"seconds": float(secs), "batch_size": 1}},
        "7": {"class_type": "KSampler",
              "inputs": {"model": ["2", 0], "seed": cue.get("seed", 1), "steps": 8,
                         "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple",
                         "denoise": 1.0, "positive": ["4", 0], "negative": ["5", 0],
                         "latent_image": ["6", 0]}},
        "8": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "9": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["7", 0], "vae": ["8", 0]}},
        "10": {"class_type": "SaveAudioMP3",
               "inputs": {"audio": ["9", 0], "filename_prefix": prefix, "quality": "320k"}},
    }


def usable_seconds(path: str, floor_db: float = -45.0) -> float:
    raw = subprocess.run([season_paths.ff("ffmpeg"), "-v", "error", "-i", path,
                          "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, "<i2").astype(np.float32) / 32768.0
    win, n = 8000, len(x) // 8000
    if not n:
        return 0.0
    rms = np.sqrt((x[:n * win].reshape(n, win) ** 2).mean(axis=1) + 1e-12)
    live = np.nonzero(20 * np.log10(rms) > floor_db)[0]
    return float((live[-1] + 1) * win / 16000.0) if len(live) else 0.0


def render(name: str, secs: float, cue: dict, out_dir: str, tag: str) -> str:
    """Generate `<out_dir>/<name>.mp3` of at least `secs` live seconds."""
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, f"{name}.mp3")
    if cue.get("silent"):
        # A CUE OF SILENCE: the mixer needs a file for every span, and a
        # span under nothing is an editorial choice, not a missing cue.
        subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error", "-f", "lavfi",
                        "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{secs + PAD:.2f}",
                        "-c:a", "libmp3lame", "-q:a", "0", dst], check=True)
        return dst
    sub = f"{season.SEASON_SLUG or 'season'}_score/{tag}_{name}"
    want = float(int(secs + PAD) + 1)
    req = urllib.request.Request(f"{HOST}/prompt",
                                 json.dumps({"prompt": graph(cue, want, sub)}).encode(),
                                 {"Content-Type": "application/json"})
    try:
        pid = json.load(urllib.request.urlopen(req))["prompt_id"]
    except urllib.error.HTTPError as e:
        sys.exit(f"FAIL: ACE submit rejected: {e.code} "
                 f"{e.read()[:800].decode(errors='replace')}")
    t0 = time.time()
    while True:
        time.sleep(5)
        h = json.load(urllib.request.urlopen(f"{HOST}/history/{pid}"))
        if pid in h:
            files = [f for o in h[pid].get("outputs", {}).values()
                     for f in o.get("audio", [])]
            if not files:
                sys.exit(f"FAIL: [{name}] ACE produced nothing -- "
                         f"{json.dumps(h[pid].get('status', {}))[:400]}")
            src = os.path.join(season_paths.COMFY_OUTPUT, files[-1].get("subfolder", ""),
                               files[-1]["filename"])
            break
        if time.time() - t0 > 1800:
            sys.exit(f"FAIL: [{name}] ACE timed out")
    # the mixer reads _music/<name>.mp3; keep the comfy copy as the raw take
    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error", "-i", src,
                    "-c:a", "libmp3lame", "-q:a", "0", dst], check=True)
    print(f" {time.time() - t0:.0f}s", end="")
    return dst
