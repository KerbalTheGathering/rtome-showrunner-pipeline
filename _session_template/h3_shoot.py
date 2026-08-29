"""Shoot the whole session on LOCAL H3 -- the REF2VA HYBRID, with the plate
and the real VO anchored as guides. No partner node, no money.

THIS REPLACED THE fl2va I2V SHOOTER (ninth reference season), which
shot from a first frame and threw H3's invented audio away. The old one is
in git history; what changed and why is learnings 50-57. Here:

  THE UNET IS THE REF2VA HYBRID (the operator's call, 2026-08-21: better at
  audio than fl2va, and it holds identity from reference pictures -- probed
  in _probes/h3_ref_probe.py, variant B). The turbo LoRA is fl2va's, applied
  at 0.75 the way the probe did, and it worked there.

  THE PLATE IS A GUIDE, NOT A REFERENCE. `MiniMaxH3AddGuide` anchors the
  plate at frame 0 of the latent -- that is the first frame, pinned -- while
  the ref2va slots carry <Picture 1> = the plate again (the look), <Picture
  2>/<Picture 3> = two identity plates of the man, and <Audio 1> = his voice.
  A beat with no man in it ("nochar") carries no identity pictures and no
  voice, and the prompt says so.

  THE VO IS THE SOUNDTRACK. The same guide node anchors a DRIVER track at
  frame 0: the beat's on-screen lines at the offsets edit.table() gives them,
  digital silence everywhere else -- and silence IS a signal: an anchored
  silent stretch is the strongest "his mouth is closed" this model accepts
  (docs/04_lipsync.md: H3 syncs faces to whatever audio it has, prompt or no
  prompt). Lines whose role is not in ON_SCREEN (a radio voice, a narrator,
  a voice in his head) are NOT in the driver: nobody on screen says them.
  The driver starts at the clip's in-point (edit ss), so the assembler's
  beat start and the model's frame 0 are the same instant.

  A CONTINUATION BEAT (NNx, shot.PLATE_ALIAS -> its parent) anchors the LAST
  22 FRAMES OF THE PARENT'S ACCEPTED CLIP at frame 0 instead of the plate, so
  the handoff carries velocity, not a standstill. Half a second of tail, one
  link, never a chain of them (the parent must be shot and accepted first).
  verify.py looks at every seam.

LENGTHS COME FROM edit.SECS, snapped UP to H3's 17k+5 frame grid at 24fps.

    python h3_shoot.py                 # every beat that has no clip yet
    python h3_shoot.py 03 07 12        # just these
    python h3_shoot.py --force 09      # re-render one that already exists
    python h3_shoot.py --rej=grewaman 10   # retire the old take, then re-shoot
    python h3_shoot.py --seed=N 10     # a re-roll (retire the old take first)
    python h3_shoot.py --no-strip      # skip the filmstrip after each clip
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
import script      # noqa: E402
import shot        # noqa: E402

HOST = season_paths.COMFY_URL
INPUT = season_paths.COMFY_INPUT
CLIPS = os.path.join(season_paths.COMFY_OUTPUT, f"{shot.NAME}_clips")
FF = season_paths.ff("ffmpeg")

CANVASES = season_paths.canvases(identity.season.W, identity.season.H)


def pick_canvas(length: int) -> tuple[int, int]:
    return season_paths.pick_canvas(length, identity.season.W, identity.season.H)


FPS = identity.season.FPS
SEED = shot.SEED

# --- the weights and the references, stated once for the season ---------------
H3_UNET = season.H3_UNET
H3_CLIP = "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"
H3_VIDEO_VAE = "minimax_h3_video_vae_fp16.safetensors"
H3_AUDIO_VAE = "minimax_h3_audio_vae_fp32.safetensors"
TURBO_LORA = "minimax_h3_turbo_6step_ema_fl2va_pruned.safetensors"
TURBO_W = 0.75                       # the probe's setting; it held
STEPS, SAMPLER, SCHED = 6, "er_sde", "beta57"
ID_REFS = season.H3_ID_REFS          # two identity plates, input-relative
VOICE_REF = season.H3_VOICE_REF      # 14.5 s of the clone, input-relative
TAIL_FRAMES = season.H3_TAIL_FRAMES  # the continuation's anchor; edit.RUNUP matches
# ROLES WHOSE LINES GO IN THE DRIVER: the people on screen. script.ON_SCREEN
# if the script declares it; otherwise every role (a single-character film).
# `is None`, NOT `or`: a script that declares ON_SCREEN = set() -- a fully
# narrated film, nobody's mouth moves -- is a DECLARATION, and `or` threw
# it away and drove every narrator line into the mouths anyway, the exact
# fault-52 invented-speech failure this set exists to prevent (fault 107).
_declared = getattr(script, "ON_SCREEN", None)
ON_SCREEN = (_declared if _declared is not None
             else {ln[2] for ln in script.LINES})


def grid(seconds: float) -> int:
    n = max(5, round(seconds * FPS))
    return n + (5 - (n % 17)) % 17


def existing(sid: str) -> list[str]:
    if not os.path.isdir(CLIPS):
        return []
    return sorted(f for f in os.listdir(CLIPS)
                  if f.startswith(f"s{sid}_") and f.endswith(".mp4")
                  and "_rej_" not in f)


def parent_of(sid: str) -> str | None:
    """The beat this one continues, or None. Only NNx beats continue."""
    src = getattr(shot, "PLATE_ALIAS", {}).get(sid)
    return src if (src and sid.endswith("x")) else None


# --- the driver: the beat's on-screen speech, in place, silence elsewhere -------
def _flag(sid: str, key: str):
    """A beat's own flag ("nochar", "norefs"), else its plate's.

    THE BEAT'S OWN ANSWER WINS. These were read off the ALIAS TARGET only,
    which is right for a beat simply reusing a picture and wrong for every
    beat that differs from the plate it borrows -- and a continuation beat
    (NNx) always borrows. It broke twice in one session on the film that
    found it: a continuation marked `nochar` still got identity references
    (with_man read its parent) while its driver was silenced (the driver
    read the beat), so H3 was handed a man to hold and no mouth to move and
    drifted into a distorted face; then `norefs`, set on a continuation that
    kept cutting to the reference's own background, did nothing at all
    because the parent did not say it (fault 86).

    TWO READERS OF ONE FACT MUST READ IT THE SAME WAY. That is the whole
    lesson: `with_man` and `driver()` now both come through here.

    An aliased graphics beat still inherits `nochar` from the plate it
    borrows, exactly as before, because it states no opinion of its own.
    """
    own = shot.BEAT[sid]
    if key in own:
        return own[key]
    return shot.BEAT[shot.PLATE_ALIAS.get(sid, sid)].get(key)


def driver(sid: str, row: dict, length: int) -> str:
    """Write <INPUT>/h3_<name>_<sid>_drive.wav -- silence where nobody on screen speaks."""
    roles = {ln[0]: ln[2] for ln in script.LINES}
    # A LINE OVER A "nochar" BEAT IS NARRATION, NOT SPEECH: he is not in the
    # picture, so anchoring his voice would hand H3 a voice and no mouth --
    # and H3 syncs faces to whatever audio it has (fault 53's poster face
    # chewed for exactly this reason). Anchored silence keeps an
    # illustration still; the mix lays the narration.
    on = set() if _flag(sid, "nochar") else ON_SCREEN
    t = row["ss"] + row["lead"]
    parts = []
    for lid in row["lines"]:
        d = edit.vo_dur(lid)
        if roles[lid] in on:
            parts.append((lid, t))
        t += d + row["extra"]
    # A BEAT WITH NOBODY SPEAKING ON SCREEN STILL GETS A DRIVER -- OF SILENCE.
    # One reference beat (a radio's line only) was shot with no audio
    # anchored and the model invented a voice and mouthed the radio's line
    # back at it; S1 06, whose driver was silence until his one word, kept
    # his mouth shut to the second. Anchored silence is the signal; absent
    # audio is an invitation. (The operator spotted it on s06. Fault 52.)
    total = length / FPS + 0.5
    name = f"h3_{shot.NAME.lower()}_{sid}_drive.wav"
    out = os.path.join(INPUT, name)
    cmd = [FF, "-y", "-v", "error",
           "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=mono:d={total:.3f}"]
    if not parts:
        cmd += ["-t", f"{total:.3f}", "-c:a", "pcm_s16le", out]
        subprocess.run(cmd, check=True)
        return name
    for lid, _ in parts:
        cmd += ["-i", os.path.join(edit.VO, f"{lid}.mp3")]
    chain = []
    for i, (_, off) in enumerate(parts, start=1):
        ms = int(round(off * 1000))
        chain.append(f"[{i}:a]aformat=sample_rates=48000:channel_layouts=mono,"
                     f"adelay={ms}|{ms}[d{i}]")
    mix = "".join(f"[d{i}]" for i in range(1, len(parts) + 1))
    chain.append(f"[0:a]{mix}amix=inputs={len(parts) + 1}:normalize=0:"
                 f"duration=first[a]")
    cmd += ["-filter_complex", ";".join(chain), "-map", "[a]",
            "-t", f"{total:.3f}", "-c:a", "pcm_s16le", out]
    subprocess.run(cmd, check=True)
    return name


def tail_clip(parent: str) -> str:
    """The TAIL_FRAMES frames of the parent's accepted clip that END AT THE CUT
    -- ss + beat (+ trans), the last frame the film shows of it -- as a tiny
    mp4 in INPUT. The first version took the clip's LAST frames, which are
    ~2 s past the cut: the continuation then replayed them after it."""
    src = os.path.join(CLIPS, existing(parent)[-1])
    prow = next(r for r in edit.table() if r["sid"] == parent)
    cut = round((prow["ss"] + prow["beat"] + prow["trans"]) * FPS)
    name = f"h3_{shot.NAME.lower()}_{parent}_tail.mp4"
    out = os.path.join(INPUT, name)
    subprocess.run([FF, "-y", "-v", "error", "-i", src,
                    "-vf", f"select=between(n\\,{cut - TAIL_FRAMES}\\,{cut - 1})",
                    "-vsync", "0", "-an", "-c:v", "libx264", "-crf", "12",
                    "-pix_fmt", "yuv420p", out], check=True)
    return name


# --- the graph ------------------------------------------------------------------
def build(prompt: str, guide: str, guide_is_clip: bool, plate_name: str,
          drive: str | None, length: int, prefix: str, size: tuple[int, int],
          seed: int, with_man: bool) -> dict:
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
    # ref2va: <Picture 1> the plate, [<Picture 2>, <Picture 3> the man,
    # <Audio 1> his voice]. AUTOGROW INPUTS ARE DOTTED PATHS (fault 45).
    refs = {"clip": ["13", 0], "vae": ["11", 0], "audio_vae": ["24", 0],
            "prompt": prompt, "width": size[0], "height": size[1],
            "length": length, "ref_image_size": "match",
            "ref_images.ref_image_0": ["1", 0]}
    if with_man:
        for i, r in enumerate(ID_REFS, start=1):
            g[f"4{i}"] = {"class_type": "LoadImage", "inputs": {"image": r}}
            refs[f"ref_images.ref_image_{i}"] = [f"4{i}", 0]
    # NO VOICE REFERENCE IS WIRED. A driver is always anchored (silence
    # where nobody on screen speaks), and a reference audio alongside an
    # anchored driver killed the sampler (audio-row mismatch 1160 vs 2254,
    # model.py:605). His voice IS the driver wherever he speaks.
    g["104"] = {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": refs}
    # the guide: the plate (or the parent's tail) at frame 0, plus the driver
    if guide_is_clip:
        g["2"] = {"class_type": "LoadVideo", "inputs": {"file": guide}}
        g["3"] = {"class_type": "GetVideoComponents", "inputs": {"video": ["2", 0]}}
        img = ["3", 0]
    else:
        img = ["1", 0]
    guide_in = {"positive": ["104", 0], "latent": ["104", 1], "vae": ["11", 0],
                "image": img, "frame_idx": 0}
    if drive:
        g["32"] = {"class_type": "LoadAudio", "inputs": {"audio": drive}}
        guide_in["audio_vae"] = ["24", 0]
        guide_in["audio"] = ["32", 0]
    g["105"] = {"class_type": "MiniMaxH3AddGuide", "inputs": guide_in}
    for nid, node in g.items():
        for k, v in node["inputs"].items():
            if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str):
                assert v[0] in g, f"{nid}.{k} -> missing node {v[0]}"
    return g


def _plate_hash(sid: str) -> str:
    """What picture this beat renders from, by CONTENT.

    Hashing the file rather than naming the beat catches both ways one
    picture reaches several beats: PLATE_ALIAS, and a MATERIALIZED copy (a
    beat whose plate is a byte-identical copy of another's -- which is how
    a continuation's parent escapes the forbidden alias chain).
    """
    import hashlib
    with open(gen_still.plate(sid), "rb") as fh:
        return hashlib.sha1(fh.read()).hexdigest()


def _canvas_groups() -> dict:
    """sid -> the canvas its whole picture-group renders on.

    A FILM CUTS BACK TO THE SAME SHOT AND THE AUDIENCE READS IT AS THE SAME
    SHOT. H3 RECOMPOSES PER CANVAS: the same plate at 1664x928 and at
    1152x640 comes back at visibly different scale and framing. So a
    repeated shot, rendered on whatever canvas each beat's own length could
    afford, BREATHES -- it sits closer, then further, then closer again, at
    every return. On the film that found this (fault 88) the refrain shot
    came back seven times across three canvases and the step card eight
    times across three; the operator saw it as "aspect ratio popping in and
    out of sync", which is the right complaint about the wrong quantity.

    THIS SUPERSEDES THE PAIR RULE OF FAULT 81. A parent and its NNx
    continuation are simply the commonest picture-group, and fixing only
    that pair was the same fault seen through a keyhole.

    THE GROUP TAKES THE CANVAS ITS LONGEST MEMBER CAN AFFORD, because that
    is the member the token budget constrains. Short beats give up some
    resolution and the film stops breathing -- the right way round: nobody
    sees the pixels of a four-second cutaway, and everybody sees the room
    change size.
    """
    rows = {r["sid"]: r for r in edit.table()}
    groups = {}
    for sid in rows:
        try:
            groups.setdefault(_plate_hash(sid), []).append(sid)
        except (FileNotFoundError, SystemExit):
            continue                      # no plate yet; shoot() will say so
    out = {}
    for members in groups.values():
        longest = max(grid(rows[m]["clip"]) for m in members)
        size = pick_canvas(longest)
        for m in members:
            out[m] = size
    return out


_GROUP_CANVAS = None


def group_canvas(sid: str, length: int) -> tuple[int, int]:
    """The canvas for this beat, decided by its picture-group."""
    global _GROUP_CANVAS
    if _GROUP_CANVAS is None:
        _GROUP_CANVAS = _canvas_groups()
    return _GROUP_CANVAS.get(sid) or pick_canvas(length)


def shoot(sid: str, seed: int = SEED) -> bool:
    row = next(r for r in edit.table() if r["sid"] == sid)
    secs = edit.SECS[sid]
    length = grid(secs)
    src = gen_still.plate(sid)
    plate_name = f"h3_{shot.NAME.lower()}_{sid}.png"
    shutil.copyfile(src, os.path.join(INPUT, plate_name))
    prefix = f"{shot.NAME}_clips/s{sid}"

    parent = parent_of(sid)
    if parent:
        if not existing(parent):
            print(f"  [{sid}] SKIP -- continues {parent}, which has no clip yet")
            return False
        guide, is_clip = tail_clip(parent), True
    else:
        guide, is_clip = plate_name, False
    # A DRIVER, OR NONE AT ALL -- season.H3_DRIVER. Anchored silence is the
    # right default for a film that writes its words (fault 52: absent audio
    # is an invitation to invent a voice). It is exactly wrong for a film
    # whose sound IS what H3 invents: the tenth season shot ten beats through
    # this line and got ten tracks of digital silence, cut into a film whose
    # one rule was that every sound comes out of this pass (fault 64).
    # "nodriver": HAND THIS BEAT NO AUDIO AT ALL. Anchored silence is the
    # right default for a face that must stay shut (fault 52) -- but it did
    # not hold on an ILLUSTRATED beat: drawn statesmen worked their mouths
    # through a silent driver, because a face plus an audio track is a
    # talking-head setup to this model however empty the track is. With no
    # driver H3 invents its own sound, which costs nothing on a film whose
    # mix drops the clip lane (identity.MIX_OPTS clips 0.0).
    drive = (driver(sid, row, length)
             if season.H3_DRIVER and not _flag(sid, "nodriver") else None)
    _b = None   # flags come from _flag(); see it for why
    # "norefs": he is in the plate only as a PICTURE (a poster, a photograph).
    # With the identity plates wired, one reference beat animated the
    # poster's face and then cut to the hero reference as a new scene (fault
    # 53). The references say "this man, alive"; a painted board wants
    # neither. No H3_ID_REFS declared = no references, ever.
    with_man = (bool(ID_REFS) and not _flag(sid, "nochar")
                and not _flag(sid, "norefs"))

    # ONE CANVAS PER PICTURE-GROUP -- see _canvas_groups(). Every beat that
    # renders from the same picture shares a canvas, which keeps a split
    # shot's seam clean (fault 81, the pair case) AND keeps a shot the film
    # returns to from changing size between returns (fault 88).
    size = group_canvas(sid, length)
    tok = season_paths.latent_m(length, size)
    print(f"  [{sid}] {os.path.basename(src):16s} {secs}s -> {length}f "
          f"({length / FPS:.2f}s) {size[0]}x{size[1]} {tok:.2f}M "
          f"{'cont<' + parent + ' ' if parent else ''}"
          f"{'man' if with_man else 'nochar'} ",
          end="", flush=True)
    g = build(motion.MOTION[sid], guide, is_clip, plate_name, drive, length,
              prefix, size, seed, with_man)
    req = urllib.request.Request(f"{HOST}/prompt", json.dumps({"prompt": g}).encode(),
                                 {"Content-Type": "application/json"})
    try:
        pid = json.load(urllib.request.urlopen(req))["prompt_id"]
    except urllib.error.HTTPError as e:
        print(f"SUBMIT REJECTED: {e.code} {e.read()[:600].decode(errors='replace')}")
        return False
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
                      f"{json.dumps(h[pid].get('status', {}))[:400]}")
                return False
            print(f"{files[-1]['filename']}  {el / 60:.1f} min ({el / length:.2f} s/f)")
            return True
        if time.time() - t0 > 3600:
            print("TIMEOUT after 60 min")
            return False


def main() -> int:
    solo.solo("clips", where=os.path.dirname(os.path.abspath(__file__)),
              force="--force" in sys.argv)
    rej = next((a.split("=", 1)[1] for a in sys.argv[1:]
                if a.startswith("--rej=")), None)
    seed = int(next((a.split("=", 1)[1] for a in sys.argv[1:]
                     if a.startswith("--seed=")), SEED))
    force = "--force" in sys.argv or rej is not None
    named = [a for a in sys.argv[1:] if not a.startswith("--")]
    want = named or list(shot.CUT)
    # A REJECTION NAMES ITS BEAT. `want` defaults to the whole film, which
    # is right for a shoot and catastrophic for --rej: a forgotten sid
    # retired every live take of every beat and queued hours of re-renders
    # (fault 126). Recoverable -- renames, not deletes -- but a whole-film
    # reshoot must be asked for in words, not implied by an omission.
    if rej is not None and not named:
        sys.exit(f"FAIL: --rej={rej} with no beat named would retire EVERY "
                 f"take in the film.\n  Name the beat(s): h3_shoot.py 05 "
                 f"--rej={rej}")

    known = ("--force", "--rej=", "--seed=", "--no-strip")
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

    print(f"  {shot.NAME} / Session #{shot.SESSION_NO}: {shot.TITLE}")
    print(f"  {len(todo)} beat(s) to shoot, {sum(edit.SECS[s] for s in todo)}s "
          f"of clip  seed {seed}"
          f"{'' if seed == SEED else f' (session seed is {SEED})'}"
          f"  [{H3_UNET.split('_pruned')[0]} turbo {TURBO_W} {STEPS}st "
          f"{SAMPLER}/{SCHED}]  -- LOCAL, $0.00")
    for s in skip:
        clip = existing(s)[-1]
        note = ("  <-- your --seed did NOT re-roll this; retire the take "
                "first (--rej=<reason>) or pass --force"
                if seed != SEED else "")
        # gen_still.plate() REFUSES when every take of a beat's plate is
        # retired -- correct for a shoot, wrong here: this loop only
        # REPORTS on beats being skipped, and it used to kill a run aimed
        # at a different beat because a bystander's plate was mid-re-roll
        # (fault 127). Say it and move on.
        try:
            stale = (os.path.getmtime(gen_still.plate(s))
                     > os.path.getmtime(os.path.join(CLIPS, clip)))
        except SystemExit:
            print(f"  [{s}] SKIP -- {clip} on disk  <-- its plate has no "
                  f"live take; re-roll gen_still.py before judging staleness")
            continue
        if stale:
            note = ("  <-- STALE: its plate is NEWER than this take -- the "
                    "picture changed under it; retire it (--rej=stale_plate) "
                    "and re-shoot" + note)
        print(f"  [{s}] SKIP -- {clip} on disk{note}")
    print()

    ok = sum(shoot(s, seed) for s in todo)

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
