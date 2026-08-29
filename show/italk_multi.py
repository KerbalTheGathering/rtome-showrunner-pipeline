"""TWO SPEAKERS IN ONE SHOT, on the InfiniteTalk *Multi* patch.

THE NODE CONTRACT IS NO LONGER GUESSED. A port of this file (a reference
season's clone, 2026-08-20) ran the Multi patch and proved it by
eye on a two-shot: each mouth articulates exactly inside its own line
window, and a silent-presence speaker holds a closed mouth on a
full-length silence track. Two findings from that run are baked in below:

  * `mode` is a COMFY_DYNAMICCOMBO_V3. Its "two_speakers" option carries
    the extra inputs, and in an API prompt an option's inputs are DOTTED
    PATHS -- mode.audio_encoder_output_2, mode.mask_1, mode.mask_2 --
    never flat keys. Flat keys are ACCEPTED and silently dropped: the
    first render steered both faces from channel 1 alone and nothing
    errored. Acceptance is not consumption; judge channel 2's mouth
    specifically, at frames inside ITS line window.
  * mask_1 / mask_2 are per-speaker MASK inputs (LoadImageMask output),
    one white face-rect each, mask_1 belonging to audio_encoder_output_1.

THE PIPELINE IN THIS PARTICULAR FILE (the show-tree plumbing around that
graph) is still unrun -- verify() re-reads the node every run and refuses
on drift, exactly as before.

WHAT IS KNOWN, AND IT IS NOT NOTHING:

  * `Wan2_1-InfiniteTalk-Multi_fp16.safetensors` exists on the disk this
    template came from and has never been loaded by anything here.
  * The CHAIN is the same problem `italk.py` already solved: 81 frames at 25fps
    per pass, `previous_frames` carrying the whole accumulated batch, the
    original plate re-anchoring every chunk, a fresh seed per chunk, and output
    [4] marking where a chained pass's NEW frames begin. All of that is
    imported from `italk.py` rather than restated, so a fix there is a fix here.
  * Each driver track must run the WHOLE SEGMENT, not just the speaker's own
    lines. A track that stops when its speaker does leaves the model with no
    signal for the rest of the shot, and an unoccupied mouth fills itself --
    the same failure `docs/04_lipsync.md` records for undirected audio.
    `role_track()` builds that, and it is the one part of this file that is
    testable without ComfyUI. Test it.

SO THIS FILE CANNOT SUBMIT A GRAPH IT HAS NOT CHECKED. Every run begins by
asking the live ComfyUI what `WanInfiniteTalkToVideo` actually accepts
(`/object_info`) and refusing, with a diff, on any assumption that does not
hold. A graph built on a guessed contract that is never checked is exactly the
`qc_feature.py` fault this repo has already paid for once: a file that looks
like a capability, iterating attributes that stopped existing, with nothing
able to notice.

    python italk_multi.py --check      # ask the node. DO THIS FIRST.
    python italk_multi.py --dry 04     # build and check the graph, submit nothing
    python italk_multi.py --test 04    # one 81-frame chunk of one segment
    python italk_multi.py 04           # the whole segment

IT WRITES synced_multi_XX.mp4 AND NEVER synced_XX.mp4. assemble.py reads the
latter, so an unproven experiment cannot become the shipped picture by
accident. Promote a take you have LOOKED AT by renaming it yourself.

THE STANDING TEST IS UNCHANGED AND NOW APPLIES PER SPEAKER: at true silence,
every mouth in the frame is closed. Check the frames before the first word of
EACH speaker, by eye, at full frame. A two-shot in which one mouth is right and
the other is chewing is worse than the single-speaker take it replaced.
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import season_paths                                                # noqa: E402


import json
import os
import shutil
import sys
import urllib.error
import urllib.request

from PIL import Image, ImageDraw                                   # noqa: E402

import assemble                                                    # noqa: E402
import edit                                                        # noqa: E402
import italk                                                       # noqa: E402
import script                                                      # noqa: E402
import shot                                                        # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "_work")
VO = os.path.join(HERE, "_vo")
OUT = os.path.join(HERE, "out")
HOST = season_paths.COMFY_URL
INPUT = season_paths.COMFY_INPUT

NODE = "WanInfiniteTalkToVideo"
# The graph id of the SaveVideo node -- named because audit() walks back
# from it, and because a bare "21" in a list is indistinguishable from a
# beat id to anything reading this file. residue.py said so.
SAVE = "21"

# THE MULTI PATCH. `italk.PATCH` is the Single one and this is deliberately a
# separate constant rather than a flag on that file: they are different weights
# with different inputs, and one file that silently switches between them is a
# file whose output you cannot attribute.
PATCH_MULTI = "Wan2_1-InfiniteTalk-Multi_fp16.safetensors"


# --------------------------------------------------------------------------
# THE CONTRACT, READ OFF THE LIVE NODE (2026-08-20).
# --------------------------------------------------------------------------
#
# `mode` is a COMFY_DYNAMICCOMBO_V3 whose "two_speakers" option carries three
# optional inputs -- audio_encoder_output_2, mask_1, mask_2 (per-speaker MASK,
# "required if using two audio inputs"). verify() still re-reads the node
# every run and refuses on drift. The original guessed table (multi_speaker /
# ref_target_masks and friends) did not survive contact and is gone.
MODE_MULTI = "two_speakers"
EXTRA_INPUTS = ("audio_encoder_output_2", "mask_1", "mask_2")


# --------------------------------------------------------------------------
# WHO IS WHERE IN THE FRAME. Set by eye. There is no detector for this.
# --------------------------------------------------------------------------
#
# (x0, y0, x1, y1) in frame fractions, per role, per segment. It is a face
# region, not a body: the model needs to know which mouth a track drives.
#
# BY EYE, OFF THE PLATE, AND THERE IS NO HONEST WAY AROUND IT. `surface.py`
# finds a flat area of one colour, which a face is not, and a face detector
# would tell you where the faces are without telling you WHICH ONE IS WHICH --
# and getting that backwards produces a shot where both people speak each
# other's lines, which reads as a sync failure rather than as a casting one and
# would send you looking in the wrong place for a day.
#
# Grab the plate (`_work/clean_<sid>.mp4`, frame italk.START_FRAME[sid]), open
# it, read the fractions off, and write them here with the role names from
# script.VOICES.
SPEAKER_RECT: dict[str, dict[str, tuple[float, float, float, float]]] = {
    # "04": {"host": (0.10, 0.18, 0.42, 0.62),
    #        "guest": (0.58, 0.20, 0.90, 0.64)},
}


def object_info(node: str) -> dict:
    """What the live ComfyUI says this node accepts.

    THE ONLY SOURCE OF TRUTH ABOUT A NODE IS THE NODE. Everything else --
    a docstring, a workflow found online, this file -- is a claim about it.
    """
    try:
        with urllib.request.urlopen(f"{HOST}/object_info/{node}",
                                    timeout=30) as r:
            got = json.load(r)
    except urllib.error.URLError as e:
        sys.exit(f"FAIL: cannot reach ComfyUI at {HOST} -- {e}\n"
                 f"  This file refuses to build a graph it has not checked "
                 f"against the\n  running node. Start ComfyUI and try again.")
    if node not in got:
        sys.exit(f"FAIL: {HOST} has no node called {node!r}.\n"
                 f"  The Multi patch is a MODEL FILE, not a node -- if the "
                 f"node itself is\n  missing, InfiniteTalk is not installed in "
                 f"this ComfyUI at all.")
    return got[node]


def inputs_of(info: dict) -> dict:
    """{name: spec} across required and optional, flattened."""
    ins = info.get("input", {})
    out = {}
    for group in ("required", "optional"):
        out.update(ins.get(group, {}))
    return out


def verify(quiet: bool = False) -> dict:
    """The mode is a V3 dynamic combo: its options each carry their own
    input set. Find the two_speakers option and confirm the three extra
    inputs live under it. Refuses, with what the node actually has, on any
    drift -- the original guessed contract did not survive first contact."""
    info = object_info(NODE)
    ins = inputs_of(info)
    bad = []

    if "audio_encoder_output_1" not in ins:
        bad.append("audio_encoder_output_1 is not an input of this node")

    spec = ins.get("mode")
    options, extra = [], {}
    if (isinstance(spec, list) and len(spec) > 1
            and isinstance(spec[1], dict) and "options" in spec[1]):
        for o in spec[1]["options"]:
            options.append(o.get("key"))
            if o.get("key") == MODE_MULTI:
                oi = o.get("inputs", {})
                extra = {**oi.get("required", {}), **oi.get("optional", {})}
    if MODE_MULTI not in options:
        bad.append(f"mode has no {MODE_MULTI!r} option -- it offers {options}")
    missing = [k for k in EXTRA_INPUTS if k not in extra]
    if missing and MODE_MULTI in options:
        bad.append(f"the {MODE_MULTI!r} option lacks {missing} -- it has "
                   f"{sorted(extra)}")

    if not quiet:
        print(f"  {NODE} on {HOST}\n")
        print(f"    mode options            {options}")
        print(f"    {MODE_MULTI} inputs    {sorted(extra) or 'NONE'}")
        print(f"\n    every top-level input:\n      "
              + "\n      ".join(sorted(ins)))

    if bad:
        print("\n  THE CONTRACT THIS FILE EXPECTS DOES NOT HOLD:\n")
        for b in bad:
            print(f"    {b}")
        sys.exit("FAIL: refusing to submit a graph built on a contract the "
                 "node does not have.")
    return {"mode": MODE_MULTI}


def role_track(sid: str, role: str) -> str:
    """One speaker's audio, on the SEGMENT's timeline, full length.

    THIS IS THE PART OF THE FILE THAT CAN BE TESTED WITHOUT A GPU, AND IT
    SHOULD BE. Play the two tracks against each other: each should carry that
    speaker's lines at exactly the offsets `edit.offsets()` gives them, and
    silence -- real silence, the full length -- everywhere else.

    WHY FULL LENGTH RATHER THAN JUST THE LINES. The driver has to say "this
    mouth is not moving now" for every frame the other person is talking. A
    track that simply stops leaves the model unsignalled for that stretch, and
    an unoccupied mouth fills itself. That is the same failure docs/04_lipsync
    records for undirected audio, pointed at a speaker instead of at a shot.
    """
    rows = [r for r in edit.table() if r["sid"] == sid]
    if not rows:
        sys.exit(f"FAIL: {sid} is not a segment of this reel")
    total = rows[0]["clip"]
    mine = [(lid, off) for lid, off in edit.offsets(sid)
            if script.BY_ID[lid][2] == role]
    dst = os.path.join(INPUT, f"itm_{sid}_{role}.wav")

    if not mine:
        # A SPEAKER WHO SAYS NOTHING IN THIS SEGMENT IS STILL IN THE SHOT and
        # still needs a track, or the node has one driver for two regions.
        # Silence of the right length is the correct answer, not no file.
        italk.ff("-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
                 "-t", f"{total:.3f}", dst)
        return dst

    ins, parts = [], []
    for n, (lid, off) in enumerate(mine):
        ins += ["-i", os.path.join(VO, f"{lid}.mp3")]
        # THE TAKE'S OWN LEADING AIR IS CUT BEFORE THE DELAY. edit.offsets()
        # is a SPEECH-start offset -- the single-speaker mix trims each take
        # to its speech (assemble.py: "LEADING SILENCE IS CUT, NOT PLACED
        # AROUND") before delaying it, and this file did not, so every line
        # here landed at off + its take's leading air: a per-take variable
        # lip lag against the board, the mix and the closed-mouth test, all
        # of which are built on off (fault 104).
        _, lead, _ = assemble.env(lid)
        ss = max(0.0, lead - 0.03)
        ms = int(round(off * 1000))
        parts.append(f"[{n}:a]atrim=start={ss:.3f},asetpts=PTS-STARTPTS,"
                     f"aresample=16000,aformat=channel_layouts=mono,"
                     f"adelay={ms}:all=1[d{n}]")
    # `apad=whole_dur=` AND `-t`, NOT `apad,atrim`. The first version of this
    # ended `amix,apad,atrim=0:{total}` -- the obvious spelling -- and it
    # produced the right length for a role with THREE lines and 2.652s of a
    # 7.292s segment for a role with ONE. Same filter chain, same segment,
    # answer depending on the input count. It was found by measuring where the
    # energy in both tracks actually was, which is the only way it could have
    # been found: both files existed, both played, and one of them was a
    # driver two-thirds too short.
    #
    # `whole_dur` is what assemble.py's mix already uses for the same job, and
    # `-t` on the OUTPUT is the unambiguous truncation -- a take that overruns
    # its own segment is cut rather than extending the clip.
    parts.append("".join(f"[d{n}]" for n in range(len(mine)))
                 + f"amix=inputs={len(mine)}:normalize=0,"
                 + f"apad=whole_dur={total:.3f}[out]")
    italk.ff(*ins, "-filter_complex", ";".join(parts), "-map", "[out]",
             "-t", f"{total:.3f}", "-ac", "1", "-ar", "16000", dst)
    return dst


def speaker_mask(sid: str, role: str) -> str:
    """A white rectangle where this speaker's face is, black everywhere else.

    THE SIMPLEST THING THAT COULD ENCODE "THIS TRACK DRIVES THAT MOUTH". If
    --check says the node wants boxes, an index, or nothing at all, this is the
    function to replace -- and the rest of the file is unaffected, which is why
    it is a function rather than four lines inside graph().
    """
    rects = SPEAKER_RECT.get(sid)
    if not rects:
        sys.exit(f"FAIL: segment {sid} has no SPEAKER_RECT.\n"
                 f"  Two tracks and no regions means the node cannot know "
                 f"which mouth is\n  which, and a fifty-fifty guess produces a "
                 f"shot where both people speak\n  each other's lines. Grab "
                 f"the plate and read the fractions off by eye --\n  see the "
                 f"note above SPEAKER_RECT.")
    if role not in rects:
        sys.exit(f"FAIL: segment {sid} has no rect for {role!r}. It has "
                 f"{sorted(rects)}")
    x0, y0, x1, y1 = rects[role]
    im = Image.new("L", (italk.GW, italk.GH), 0)
    ImageDraw.Draw(im).rectangle(
        [x0 * italk.GW, y0 * italk.GH, x1 * italk.GW, y1 * italk.GH], fill=255)
    dst = os.path.join(INPUT, f"itm_{sid}_{role}_mask.png")
    im.save(dst)
    return dst


def graph(img: str, tracks: list[tuple[str, str, str]], n_frames: int,
          prefix: str, seed: int, names: dict, scale: float = 1.0,
          prompt: str | None = None) -> dict:
    """The two-speaker chain. Structurally italk.graph() with two drivers.

    `tracks` is [(role, wav path, mask path), ...] and `names` is what
    verify() resolved -- the node's actual input names, never the assumed ones.

    THE CHAIN IS NOT REINVENTED HERE. Chunk length, motion frames, the
    re-anchor to the original plate, the per-chunk seed offset and the [4]
    batch-index trim are all italk.py's answers, imported. If the single-speaker
    path learns something, this inherits it.
    """
    if len(tracks) != 2:
        sys.exit(f"FAIL: this graph drives exactly two speakers, not "
                 f"{len(tracks)}. Three is a different node input again.")
    n_chunks = italk.chunks_for(n_frames)
    g = {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": italk.UNET, "weight_dtype": "default"}},
        "2": {"class_type": "LoraLoaderModelOnly",
              "inputs": {"model": ["1", 0], "lora_name": italk.LORA,
                         "strength_model": 1.0}},
        # THE ONE LINE THAT MAKES THIS THE MULTI PATH.
        "3": {"class_type": "ModelPatchLoader", "inputs": {"name": PATCH_MULTI}},
        "4": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": italk.CLIP, "type": "wan",
                         "device": "default"}},
        "5": {"class_type": "CLIPTextEncode",
              "inputs": {"clip": ["4", 0], "text": prompt or italk.PROMPT}},
        "6": {"class_type": "CLIPTextEncode",
              "inputs": {"clip": ["4", 0], "text": italk.NEG}},
        "7": {"class_type": "VAELoader", "inputs": {"vae_name": italk.VAE}},
        "8": {"class_type": "AudioEncoderLoader",
              "inputs": {"audio_encoder_name": italk.AENC}},
        "11": {"class_type": "LoadImage",
               "inputs": {"image": os.path.basename(img)}},
        "13": {"class_type": "KSamplerSelect",
               "inputs": {"sampler_name": "euler"}},
    }

    # ONE ENCODE AND ONE MASK PER SPEAKER. Both encoders share node 8's loaded
    # weights; only the audio differs.
    for i, (_role, wav, mask) in enumerate(tracks, start=1):
        g[f"a{i}"] = {"class_type": "LoadAudio",
                      "inputs": {"audio": os.path.basename(wav)}}
        g[f"e{i}"] = {"class_type": "AudioEncoderEncode",
                      "inputs": {"audio_encoder": ["8", 0],
                                 "audio": [f"a{i}", 0]}}
        g[f"m{i}"] = {"class_type": "LoadImageMask",
                      "inputs": {"image": os.path.basename(mask),
                                 "channel": "red"}}

    acc = None
    for k in range(n_chunks):
        it, sch, noi, cfg, smp, dec, new = (f"it{k}", f"sc{k}", f"no{k}",
                                            f"cg{k}", f"sp{k}", f"de{k}",
                                            f"nw{k}")
        # A V3 DYNAMIC COMBO'S OPTION INPUTS ARE DOTTED PATHS, NOT FLAT KEYS.
        # comfy_api/latest/_io.py parse_class_inputs() finalizes an option's
        # inputs as "<combo_id>.<input_id>" -- flat spellings are accepted
        # and silently dropped (measured: a two-speaker render steered
        # entirely by channel 1). Same dotted-path contract as the derive
        # graphs' ref_images.ref_image_0. mask_1 belongs to the speaker
        # driving audio_encoder_output_1.
        ins = {"mode": names["mode"], "model": ["2", 0],
               "model_patch": ["3", 0], "positive": ["5", 0],
               "negative": ["6", 0], "vae": ["7", 0],
               "width": italk.GW, "height": italk.GH, "length": italk.CHUNK,
               "audio_encoder_output_1": ["e1", 0],
               "mode.audio_encoder_output_2": ["e2", 0],
               "mode.mask_1": ["m1", 0], "mode.mask_2": ["m2", 0],
               "motion_frame_count": italk.MOTION, "audio_scale": scale,
               "start_image": ["11", 0]}
        if acc is not None:
            ins["previous_frames"] = acc
        g[it] = {"class_type": NODE, "inputs": ins}
        g[sch] = {"class_type": "BasicScheduler",
                  "inputs": {"model": [it, 0], "scheduler": "normal",
                             "steps": italk.STEPS, "denoise": 1.0}}
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
        g[new] = {"class_type": "ImageFromBatch",
                  "inputs": {"image": [dec, 0], "batch_index": [it, 4],
                             "length": 4096}}
        g[f"ab{k}"] = {"class_type": "ImageBatch",
                       "inputs": {"image1": acc, "image2": [new, 0]}}
        acc = [f"ab{k}", 0]

    # THE FIRST SPEAKER'S TRACK IS MUXED IN, NOT THE MIX. It is one of the two
    # things that drove the picture, so it is at least honestly aligned; the
    # real mix is assemble.py's job as always. Judge sync on the picture, not
    # on what this file happens to attach.
    g["20"] = {"class_type": "CreateVideo",
               "inputs": {"images": acc, "fps": float(italk.IT_FPS),
                          "audio": ["a1", 0]}}
    g[SAVE] = {"class_type": "SaveVideo",
               "inputs": {"video": ["20", 0], "filename_prefix": prefix,
                          "format": "auto", "codec": "auto"}}
    return g


def audit(g: dict) -> list[str]:
    """Everything structurally wrong with a graph, before it is submitted.

    THIS CANNOT TELL YOU THE PICTURE WILL BE RIGHT and does not claim to. What
    it catches is the class of fault that costs an hour of queue and comes back
    as a one-line ComfyUI error: a link to a node that is not in the graph, an
    output nobody consumes, a chain that is one pass short.

    IT IS WORTH HAVING HERE PRECISELY BECAUSE THIS FILE IS UNPROVEN. When the
    render fails -- and the first one will -- this is what tells you whether to
    look at the graph or at the model.
    """
    bad = []
    for nid, node in g.items():
        for name, val in node["inputs"].items():
            if (isinstance(val, list) and len(val) == 2
                    and isinstance(val[0], str)):
                if val[0] not in g:
                    bad.append(f"{nid}.{name} links to node {val[0]!r}, which "
                               f"is not in this graph")
    reached, stack = set(), [SAVE]
    if SAVE not in g:
        return bad + ["there is no SaveVideo node -- nothing would be written"]
    while stack:
        nid = stack.pop()
        if nid in reached:
            continue
        reached.add(nid)
        for val in g[nid]["inputs"].values():
            if (isinstance(val, list) and len(val) == 2
                    and isinstance(val[0], str) and val[0] in g):
                stack.append(val[0])
    for nid in sorted(set(g) - reached):
        bad.append(f"node {nid} ({g[nid]['class_type']}) feeds nothing that "
                   f"reaches the output -- it would be built and discarded")
    return bad


def stage(sid: str) -> tuple[str, list[tuple[str, str, str]]]:
    """The plate and one (role, wav, mask) per speaker, all in COMFY_INPUT."""
    roles = script.speakers(sid)
    if len(roles) != 2:
        sys.exit(f"FAIL: segment {sid} has {len(roles)} speaker(s) "
                 f"({roles or 'none'}), and this file drives exactly two.\n"
                 f"  One speaker is `python italk.py {sid}`, which is the "
                 f"proven path.")
    img = italk.plate(sid)
    return img, [(r, role_track(sid, r), speaker_mask(sid, r)) for r in roles]


def main() -> int:
    argv = sys.argv[1:]
    if "--check" in argv:
        verify()
        print("\n  Every assumption holds. That means the graph will be "
              "ACCEPTED, not\n  that it will be right -- nothing about the "
              "picture has been proven.")
        return 0

    want = [a for a in argv if not a.startswith("-")]
    if not want:
        sys.exit(__doc__.strip().splitlines()[0] + "\n\n"
                 "  python italk_multi.py --check      # ask the node first\n"
                 "  python italk_multi.py --test 04\n"
                 "  python italk_multi.py 04")
    bad = [s for s in want if s not in shot.CUT]
    if bad:
        sys.exit(f"FAIL: {bad} are not segments of this reel")

    # ALWAYS, BEFORE ANYTHING IS SUBMITTED. Not behind a flag: a check you have
    # to remember is a check that gets skipped, and the thing it prevents here
    # is an hour of GPU spent on a graph the node was never going to accept.
    names = verify(quiet=True)
    print(f"  contract checked against {HOST}: mode={names['mode']!r}, "
          f"per-speaker mask_1/mask_2")

    seed = next((int(a.split("=", 1)[1]) for a in argv
                 if a.startswith("--seed=")), italk.SEED)
    scale = next((float(a.split("=", 1)[1]) for a in argv
                  if a.startswith("--scale=")), 1.5)
    test = "--test" in argv
    # --dry BUILDS AND CHECKS THE GRAPH AND SUBMITS NOTHING. It is the
    # cheapest way to work on this file: everything except the model is
    # exercised, including the contract check against the live node.
    dry = "--dry" in argv
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)

    for sid in want:
        img, tracks = stage(sid)
        n_it = (italk.CHUNK if test
                else -(-edit.FRAMES[sid] * italk.IT_FPS // 24))
        print(f"  [{sid}] {' + '.join(r for r, _w, _m in tracks)}   "
              f"{n_it}f@25 -> {italk.chunks_for(n_it)} chunk(s)  x{scale} ...",
              end="", flush=True)
        g = graph(img, tracks, n_it, f"itm/{sid}", seed, names, scale=scale)
        wrong = audit(g)
        if wrong:
            print()
            for w in wrong:
                print(f"    {w}")
            sys.exit(f"FAIL: the graph for {sid} is not well formed. Nothing "
                     f"was submitted.")
        if dry:
            print(f" {len(g)} nodes, structurally sound, NOT submitted")
            json.dump(g, open(os.path.join(WORK, f"itm_{sid}.json"), "w"),
                      indent=1)
            print(f"    -> {os.path.join(WORK, f'itm_{sid}.json')}")
            continue
        got = italk.submit(g, f"multi {sid}")
        # NEVER synced_{sid}.mp4 -- see the header. assemble.py reads that name
        # and an unproven take must not be able to reach a bake by accident.
        dst = os.path.join(WORK, f"synced_multi_{sid}.mp4"
                           if not test else f"itm_test_{sid}.mp4")
        shutil.copy2(got, dst)
        print(f" -> {os.path.basename(dst)}")

    print("\n  NOW LOOK AT IT, AND LOOK AT BOTH MOUTHS.\n"
          "  The standing test is per speaker: at true silence, every mouth in\n"
          "  the frame is closed. Grab the frames before each speaker's first\n"
          "  word -- `edit.offsets()` says where those are -- and check them at\n"
          "  full frame. A take where one mouth is right and the other is\n"
          "  chewing is worse than the single-speaker version it replaced.\n\n"
          "  If it works, say so in this file's header and delete the word\n"
          "  UNPROVEN. If it does not, write down WHAT you saw before you\n"
          "  change a number -- that is the whole difference between this "
          "taking\n  a day and taking a week.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
