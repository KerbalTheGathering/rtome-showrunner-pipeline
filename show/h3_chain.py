"""The show's H3 shooter for segments WITHOUT FACES, as CHAINED PIECES.
(a reference season's control-room inserts; ported as a sibling of h3_shoot.py,
which stays the faced lane -- base clip, then InfiniteTalk.)

THE ROOM HAD NO FACES. The controllers are seen from behind, so the lane this
tree was built for -- a capped base clip, then InfiniteTalk regenerating the
whole segment from the voice -- has nothing to sync. The segments are shot
at FULL LENGTH instead and baked `--raw`.

A segment longer than H3's ~15 s trained range is shot as a CHAIN: piece 0
opens on the plate; each later piece opens on the last H3_TAIL_FRAMES frames
of the piece before it (anchored at frame 0, the way the acts' NNx beats
continue), and the pieces are joined with those anchored frames dropped, so
nothing is shown twice. Two links at most on the longest segment (25.7 s =
15 + 11). A chain is acceptable HERE because the room is static and nobody
in it has a face; the acts allow one link, on a line boundary, for a reason.

Every piece gets a SILENT driver -- the voices on the loop belong to men who
are turned away, and an unanchored clip invents a voice and a mouth for it.

    python h3_shoot.py                 # every segment without a clip
    python h3_shoot.py 02              # just this one
    python h3_shoot.py --rej=why 03    # retire the old take, then re-shoot
"""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import season_paths  # noqa: E402
import season_identity as season  # noqa: E402
import solo  # noqa: E402
import check_clip  # noqa: E402
import edit        # noqa: E402
import identity    # noqa: E402
import gen_still   # noqa: E402
import motion      # noqa: E402
import shot        # noqa: E402

HOST = season_paths.COMFY_URL
INPUT = season_paths.COMFY_INPUT
CLIPS = os.path.join(season_paths.COMFY_OUTPUT, f"{shot.NAME}_clips")
PARTS = os.path.join(CLIPS, "_parts")
FF = season_paths.ff("ffmpeg")
FPS = identity.season.FPS
SEED = shot.SEED

H3_UNET = season.H3_UNET
H3_CLIP = "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"
H3_VIDEO_VAE = "minimax_h3_video_vae_fp16.safetensors"
H3_AUDIO_VAE = "minimax_h3_audio_vae_fp32.safetensors"
TURBO_LORA = "minimax_h3_turbo_6step_ema_fl2va_pruned.safetensors"
TURBO_W = 0.75
STEPS, SAMPLER, SCHED = 6, "er_sde", "beta57"
TAIL = season.H3_TAIL_FRAMES
PIECE_MAX = 362                      # the top of H3's trained range, on the grid


def grid(n: int) -> int:
    return n + (5 - (n % 17)) % 17


def pick_canvas(length: int) -> tuple[int, int]:
    return season_paths.pick_canvas(length, identity.season.W, identity.season.H)


def existing(sid: str) -> list[str]:
    if not os.path.isdir(CLIPS):
        return []
    # A ZERO-BYTE FILE IS NOT A TAKE. A failed join once left one behind
    # and the next run SKIPped the segment as shot.
    return sorted(f for f in os.listdir(CLIPS)
                  if f.startswith(f"s{sid}_") and f.endswith(".mp4")
                  and "_rej_" not in f
                  and os.path.getsize(os.path.join(CLIPS, f)) > 0)


def pieces(total: int) -> list[int]:
    """Piece lengths (on the grid) whose NEW frames cover `total`."""
    out, covered = [], 0
    while covered < total:
        need = total - covered + (TAIL if out else 0)
        n = min(PIECE_MAX, grid(need))
        out.append(n)
        covered += n - (TAIL if len(out) > 1 else 0)
    return out


def silence(name: str, secs: float) -> str:
    out = os.path.join(INPUT, name)
    subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                    f"anullsrc=r=48000:cl=mono:d={secs:.3f}", "-t", f"{secs:.3f}",
                    "-c:a", "pcm_s16le", out], check=True)
    return name


def tail_of(part_path: str, name: str) -> str:
    out = os.path.join(INPUT, name)
    subprocess.run([FF, "-y", "-v", "error", "-sseof", f"-{(TAIL + 2) / FPS:.3f}",
                    "-i", part_path, "-vf", f"select=gte(n\\,0)", "-vsync", "0",
                    "-frames:v", str(TAIL), "-an", "-c:v", "libx264", "-crf", "12",
                    "-pix_fmt", "yuv420p", out], check=True)
    return name


def build(prompt, guide, guide_is_clip, plate_name, drive, length, prefix, size, seed):
    g = {
        "6":  {"class_type": "UNETLoader",
               "inputs": {"unet_name": H3_UNET, "weight_dtype": "default"}},
        "13": {"class_type": "CLIPLoader",
               "inputs": {"clip_name": H3_CLIP, "type": "minimax", "device": "default"}},
        "11": {"class_type": "VAELoader", "inputs": {"vae_name": H3_VIDEO_VAE}},
        "24": {"class_type": "VAELoader", "inputs": {"vae_name": H3_AUDIO_VAE}},
        "30": {"class_type": "LoraLoaderModelOnly",
               "inputs": {"model": ["6", 0], "lora_name": TURBO_LORA,
                          "strength_model": TURBO_W}},
        "1":  {"class_type": "LoadImage", "inputs": {"image": plate_name}},
        "104": {"class_type": "MiniMaxH3ReferenceToVideo",
                "inputs": {"clip": ["13", 0], "vae": ["11", 0], "audio_vae": ["24", 0],
                           "prompt": prompt, "width": size[0], "height": size[1],
                           "length": length, "ref_image_size": "match",
                           "ref_images.ref_image_0": ["1", 0]}},
        "32": {"class_type": "LoadAudio", "inputs": {"audio": drive}},
        "16": {"class_type": "BasicGuider",
               "inputs": {"model": ["30", 0], "conditioning": ["105", 0]}},
        "17": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": SAMPLER}},
        "9":  {"class_type": "BasicScheduler",
               "inputs": {"model": ["30", 0], "scheduler": SCHED,
                          "steps": STEPS, "denoise": 1.0}},
        "15": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "14": {"class_type": "SamplerCustomAdvanced",
               "inputs": {"noise": ["15", 0], "guider": ["16", 0], "sampler": ["17", 0],
                          "sigmas": ["9", 0], "latent_image": ["104", 1]}},
        "10": {"class_type": "VAEDecode", "inputs": {"samples": ["14", 0], "vae": ["11", 0]}},
        "23": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["14", 0], "vae": ["24", 0]}},
        "91": {"class_type": "CreateVideo",
               "inputs": {"images": ["10", 0], "audio": ["23", 0], "fps": FPS, "bit_depth": 8}},
        "92": {"class_type": "SaveVideo",
               "inputs": {"video": ["91", 0], "filename_prefix": prefix,
                          "format": "auto", "codec": "auto"}},
    }
    if guide_is_clip:
        g["2"] = {"class_type": "LoadVideo", "inputs": {"file": guide}}
        g["3"] = {"class_type": "GetVideoComponents", "inputs": {"video": ["2", 0]}}
        img = ["3", 0]
    else:
        img = ["1", 0]
    g["105"] = {"class_type": "MiniMaxH3AddGuide",
                "inputs": {"positive": ["104", 0], "latent": ["104", 1],
                           "vae": ["11", 0], "audio_vae": ["24", 0],
                           "image": img, "audio": ["32", 0], "frame_idx": 0}}
    return g


def submit(g: dict) -> str | None:
    req = urllib.request.Request(f"{HOST}/prompt", json.dumps({"prompt": g}).encode(),
                                 {"Content-Type": "application/json"})
    try:
        pid = json.load(urllib.request.urlopen(req))["prompt_id"]
    except urllib.error.HTTPError as e:
        print(f"SUBMIT REJECTED: {e.code} {e.read()[:600].decode(errors='replace')}")
        return None
    t0 = time.time()
    while time.time() - t0 < 3600:
        time.sleep(10)
        h = json.load(urllib.request.urlopen(f"{HOST}/history/{pid}"))
        if pid in h:
            files = [f for o in h[pid].get("outputs", {}).values()
                     for f in o.get("images", []) + o.get("videos", [])]
            if not files:
                print(f"FAILED after {time.time() - t0:.0f}s -- "
                      f"{json.dumps(h[pid].get('status', {}))[:400]}")
                return None
            print(f"{files[-1]['filename']}  {(time.time() - t0) / 60:.1f} min")
            return os.path.join(season_paths.COMFY_OUTPUT, files[-1].get("subfolder", ""),
                                files[-1]["filename"])
    print("TIMEOUT")
    return None


def shoot(sid: str, seed: int = SEED) -> bool:
    total = edit.FRAMES[sid]
    src = gen_still.plate(sid)
    plate_name = f"h3_{shot.NAME.lower()}_{sid}.png"
    shutil.copyfile(src, os.path.join(INPUT, plate_name))
    os.makedirs(PARTS, exist_ok=True)
    take = len([f for f in os.listdir(CLIPS) if f.startswith(f"s{sid}_")]) + 1
    lens = pieces(total)
    print(f"  [{sid}] {os.path.basename(src)}  {total}f ({total / FPS:.1f}s) in "
          f"{len(lens)} piece(s) {lens}")
    parts = []
    # ONE CANVAS FOR THE WHOLE CHAIN, chosen for the longest piece: a short
    # second piece picked a larger canvas and the concat refused the join.
    size = pick_canvas(max(lens))
    for k, n in enumerate(lens):
        drive = silence(f"h3_{shot.NAME.lower()}_{sid}_silence.wav", n / FPS + 0.5)
        if k == 0:
            guide, is_clip = plate_name, False
        else:
            guide, is_clip = tail_of(parts[-1], f"h3_{shot.NAME.lower()}_{sid}_tail.mp4"), True
        print(f"       piece {k}: {n}f {size[0]}x{size[1]} "
              f"{season_paths.latent_m(n, size):.2f}M ", end="", flush=True)
        out = submit(build(motion.MOTION[sid], guide, is_clip, plate_name, drive, n,
                           f"{shot.NAME}_clips/_parts/s{sid}_t{take:02d}_p{k}",
                           size, seed + k))
        if not out:
            return False
        parts.append(out)
    # join: piece 0 whole, later pieces from frame TAIL on; no audio (the mix is VO)
    dst = os.path.join(CLIPS, f"s{sid}_{take:05d}_.mp4")
    cmd = [FF, "-y", "-v", "error"]
    for p in parts:
        cmd += ["-i", p]
    fl = "".join(f"[{i}:v]select=gte(n\\,{0 if i == 0 else TAIL}),setpts=N/FRAME_RATE/TB[v{i}];"
                 for i in range(len(parts)))
    fl += "".join(f"[v{i}]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=1:a=0[v]"
    cmd += ["-filter_complex", fl, "-map", "[v]", "-r", str(FPS), "-an",
            "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", dst]
    subprocess.run(cmd, check=True)
    got = int(subprocess.run([season_paths.ff("ffprobe"), "-v", "error", "-select_streams",
                              "v:0", "-count_frames", "-show_entries",
                              "stream=nb_read_frames", "-of", "csv=p=0", dst],
                             capture_output=True, text=True, check=True).stdout.strip())
    print(f"       joined -> {os.path.basename(dst)}  {got}f (segment needs {total}f)")
    return got >= total


def main() -> int:
    solo.solo("clips", where=os.path.dirname(os.path.abspath(__file__)),
              force="--force" in sys.argv)
    rej = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--rej=")), None)
    seed = int(next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--seed=")), SEED))
    force = "--force" in sys.argv or rej is not None
    want = [a for a in sys.argv[1:] if not a.startswith("--")] or list(shot.CUT)
    known = ("--force", "--rej=", "--seed=", "--no-strip")
    junk = [a for a in sys.argv[1:] if a.startswith("--") and not a.startswith(known)]
    if junk:
        sys.exit(f"FAIL: unknown flag(s) {junk}. Known: {', '.join(known)}")
    bad = [s for s in want if s not in shot.CUT]
    if bad:
        sys.exit(f"FAIL: {bad} are not segments")
    os.makedirs(CLIPS, exist_ok=True)
    if rej:
        for sid in want:
            for f in existing(sid):
                stem = f[:-4].rstrip("_")
                os.rename(os.path.join(CLIPS, f), os.path.join(CLIPS, f"{stem}__rej_{rej}.mp4"))
                print(f"  [{sid}] retired {f} -> {stem}__rej_{rej}.mp4")
    todo = [s for s in want if force or not existing(s)]
    for s in want:
        if s not in todo:
            print(f"  [{s}] SKIP -- {existing(s)[-1]} on disk")
    print(f"  {shot.NAME}: {len(todo)} segment(s), full length, chained; seed {seed}")
    ok = sum(shoot(s, seed) for s in todo)
    if "--no-strip" not in sys.argv:
        for s in todo:
            if check_clip.existing(s):
                try:
                    check_clip.strip(s)
                except Exception as e:                           # noqa: BLE001
                    print(f"  [{s}] no filmstrip: {e}")
    print(f"\n  {ok}/{len(todo)} shot.")
    return 0 if ok == len(todo) else 1


if __name__ == "__main__":
    sys.exit(main())
