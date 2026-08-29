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
import solo                                                        # noqa: E402


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

# THE PLAIN GRAPH IS PRODUCTION; --filtered OPTS BACK INTO THE TWO NODES AS
# THE PROBE. See graph() for the A/B that decided it and the two seasons
# that confirmed it in production. The probe still writes to its OWN
# directory, the same discipline --obj uses: a probe render that could be
# resolved as a film plate is how an A/B ends up in the cut.
FILTERED = "--filtered" in sys.argv
PLAIN = not FILTERED
OUT = os.path.join(season_paths.COMFY_OUTPUT,
                   f"{shot.OBJ_NAME if OBJ else shot.NAME}"
                   + ("_filtered" if FILTERED else ""))
HOST = season_paths.COMFY_URL

# A cold load is ~120-150s, so anything under ~200s cannot distinguish "still
# loading the 12GB unet" from "offloading every step". 300 leaves room for a
# cold load plus a healthy render and still catches the 22-minute image.
SLOW_S = 300


def graph(prompt: str, prefix: str, seed: int,
          style: tuple[str, float] | None = None) -> dict:
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

    TWO NODES IN HERE WENT UNMEASURED FOR SIX SEASONS, and the plain graph --
    the shipping default now; `--filtered` restores them -- omits both:

        node 51   krea2filterbypass3.safetensors, at strength 100/100
        node 28   ConditioningKrea2Rebalance, multiplier 5 with a twelve-value
                  per-layer weight list, applied to the NEGATIVE conditioning
                  -- which is itself a ConditioningZeroOut of the positive

    A fork's render harness omitted both deliberately, on the grounds that
    they degrade Krea2. That was a claim from somewhere else about a graph
    that had produced every plate in six seasons here, so the flag existed to
    settle it with a render rather than an argument:

        python gen_still.py --beat=07              # plain -- the graph as it ships NOW
        python gen_still.py --beat=07 --filtered   # the old pair, as the probe

    Same seed, same latent, same LoRAs, same words. `--filtered` renders into
    its own `<NAME>_filtered` directory -- the discipline `--obj` already
    uses -- so a probe can never be resolved as a film plate.

    WHAT THE COMPARISON FOUND, two seeds, one prompt, no LoRAs, everything else
    byte-identical -- a painted night interior with brass, glass, a named
    optical part and a figure:

                        A (as ships)        B (--plain)
        near-black       15.3% / 21.5%       0.21% / 0.77%   of the frame
        detail (lapvar)  0.0074 / 0.0076     0.0095 / 0.0121
        saturation       0.236 / 0.297       0.188 / 0.217
        the fresnel lens generic lantern     rendered as asked
                         at BOTH seeds       at BOTH seeds

    THE LENS IS THE FINDING. The prompt names "the great fresnel lens" and A
    returned an ordinary storm lantern at both seeds while B drew the concentric
    prism rings at both. That is docs/05_prompting.md's "a specific prop falls
    back to a generic" -- the failure that costs re-rolls -- and here it tracks
    the graph rather than the words or the seed.

    B also holds 30-60% more high-frequency detail and does not crush a fifth of
    the frame to black. A is more saturated and more contrasty, and that is a
    LOOK: grades.py produces it on purpose, from a picture that still has the
    shadow information in it.

    AGAINST B: A honoured "the only light is the lamp itself" better; B lit the
    room ambiently at both seeds. And B renders "on textured paper" as a literal
    sheet with margins showing, which a full-bleed plate does not want.

    THE DEFAULT MOVED, AND ON THE TERMS THIS DOCSTRING SET. The paragraph
    that used to end it said: the A/B was two seeds, one prompt, NO LoRA --
    run it on your own film, with your own LoRAs, before you move the
    default. Two seasons then did exactly that in production: a 37-beat
    music video and a seven-part news satire both shot plain into their
    plate directories (the satire with a character LoRA loaded in its cold
    open), and the props their prompts named arrived as asked. So plain is
    the template's production graph now, `--filtered` is the probe, and the
    A/B above is the record of why. The old look is not lost: A's contrast
    and saturation are a LOOK, and grades.py produces it on purpose from a
    picture that still has the shadow information in it.
    """
    # WHERE THE CHAIN STARTS, AS A PAIR, because --plain deletes the node that
    # everything else used to hang off. Every loader below chains from this
    # rather than from a literal "51" -- the third time this file has had to
    # learn that lesson; node 59's comment is the second.
    root = (["51", 0], ["51", 1]) if not PLAIN else (["1", 0], ["13", 0])
    # THE STYLE IS THE BEAT'S, NOT THE FILM'S, when the film has registers
    # (identity.REGISTERS / shot.REGISTER). Resolved once here so every test
    # below asks the same question; the sampler and the encoder cannot
    # disagree about which look was loaded.
    style_lora, style_w = style if style is not None else (shot.STYLE_LORA, shot.STYLE_W)

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
        if style_lora:
            return ["52", idx]
        return list(root[idx])

    g = {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": "krea2TurboFP8_krea2TURBO.safetensors",
                         "weight_dtype": "fp8_e4m3fn"}},
        "2": {"class_type": "KSampler",
              "inputs": {"seed": seed, "steps": 8, "cfg": 1, "sampler_name": "er_sde",
                         "scheduler": "simple", "denoise": 1, "model": _tail(0),
                         "positive": ["45", 0],
                         # WITHOUT THE REBALANCE THE NEGATIVE IS THE ZEROED
                         # CONDITIONING ITSELF, which is what node 28 was being
                         # handed anyway. It is not "no negative": at cfg 1 the
                         # negative is barely consulted either way, which is
                         # half of why nobody could hear the difference.
                         "negative": ["28", 0] if not PLAIN else ["8", 0],
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
        "45": {"class_type": "TextEncodeKrea2",
               "inputs": {"prompt": prompt, "vision_megapixels": 3,
                          "mask_padding": 0, "clip": _tail(1)}},
        "53": {"class_type": "VAEUtils_VAEDecodeTiled",
               "inputs": {"upscale": -1, "tile": False, "tile_size": 512,
                          "overlap": 64, "temporal_size": 4096,
                          "temporal_overlap": 64, "samples": ["2", 0], "vae": ["4", 0]}},
        "65": {"class_type": "EmptySD3LatentImage",
               "inputs": {"width": shot.LATENT[0], "height": shot.LATENT[1],
                          "batch_size": 1}},
    }
    # THE TWO UNMEASURED NODES, ADDED ONLY WHEN THEY ARE WANTED. Same discipline
    # as the LoRA loaders below: a node that is not being used is absent from the
    # graph rather than present and neutralised, so the graph never lies about
    # what was applied. See the docstring for what --plain is for.
    if not PLAIN:
        g["51"] = {"class_type": "LoraLoader",
                   "inputs": {"lora_name": "krea2filterbypass3.safetensors",
                              "strength_model": 100, "strength_clip": 100,
                              "model": ["1", 0], "clip": ["13", 0]}}
        g["28"] = {"class_type": "ConditioningKrea2Rebalance",
                   "inputs": {"multiplier": 5,
                              "per_layer_weights":
                                  "1.0,1.0,1.0,1.0,1.0,1.0,1.0,2.5,5.0,1.1,"
                                  "4.0,1.0",
                              "conditioning": ["8", 0]}}
    # Each loader is added only if its file is actually set, so the graph never
    # carries a loader at strength 0 and _tail() never points at a node that is
    # not there. The COWRIE copy of this file lost node 52 while its indentation
    # was being repaired -- harmless there (no style LoRA) and an immediate
    # dangling-link failure here, which is why the link check runs before submit.
    if style_lora:
        g["52"] = {"class_type": "LoraLoader",
                   "inputs": {"lora_name": style_lora,
                              "strength_model": style_w,
                              "strength_clip": style_w,
                              "model": list(root[0]), "clip": list(root[1])}}
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
        # AND IT IS `root` NOW, NOT "51", for the same reason one step further:
        # --plain removes node 51 as well, so the literal that replaced the
        # first literal would have had the identical fault under the new flag.
        base = (["52", 0], ["52", 1]) if style_lora else root
        g["59"] = {"class_type": "LoraLoader",
                   "inputs": {"lora_name": shot.CHAR_LORA,
                              "strength_model": shot.CHAR_W,
                              "strength_clip": shot.CHAR_W,
                              "model": list(base[0]), "clip": list(base[1])}}

    # EVERY LINK POINTS AT A NODE THAT IS IN THE GRAPH. This file has shipped
    # the opposite twice -- node 59 -> node 52 for the character-LoRA-only
    # combination, and the COWRIE copy losing node 52 outright -- and both were
    # HTTP 400s at submit that only surfaced because ComfyUI validates links.
    # Four combinations of two LoRAs times two settings of --plain is eight
    # graphs, and no film exercises more than one of them.
    for _nid, _node in g.items():
        for _k, _v in _node["inputs"].items():
            if isinstance(_v, list) and len(_v) == 2 and isinstance(_v[0], str):
                assert _v[0] in g, (
                    f"node {_nid}.{_k} links to node {_v[0]}, which is not in "
                    f"this graph (style={bool(style_lora)} "
                    f"char={bool(shot.CHAR_LORA)} plain={PLAIN})")
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
    # An ALIASED beat has no plate of its own on purpose -- Session #3's beat 07
    # is the same corner as 03 and takes the same picture, because asking two
    # renders to agree on a composition does not work. Resolved here so every
    # downstream file (storyboard, motion, make_video, assemble) inherits it
    # without knowing about it.
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

    # THE WRITE PREFIX HONOURED --obj AND NOT THE PROBE FLAG, AND THAT BROKE
    # THE ONE THING THE PROBE EXISTS FOR. `OUT` above appends the probe
    # suffix; this line did not, so a probe render was written STRAIGHT INTO
    # THE FILM'S PLATE DIRECTORY while the poller watched an empty probe
    # folder and reported "NO OUTPUT after 20s". (The probe was spelled
    # --plain then; it is --filtered now that plain ships. Same trap.)
    #
    # TWO FAILURES AT ONCE, AND ONLY THE HARMLESS ONE IS VISIBLE. `plate()`
    # resolves a beat by taking `have[-1]`, the LAST file for that sid -- so
    # the probe becomes the plate the film is shot from, and the thing that
    # tells you is a message saying the render failed.
    #
    # Found on the first --plain render anyone ever ran. The flag arrived with
    # a docstring promising that a probe can never be resolved as a film plate;
    # that isolation was only half implemented, in all three copies of this
    # file. A guard present in one of three copies is not present.
    name = ((shot.OBJ_NAME if OBJ else shot.NAME)
            + ("_filtered" if FILTERED else ""))
    body = json.dumps({"prompt": graph(prompt, f"{name}\\{sid}", seed,
                                       shot.style_for(sid))}).encode()
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
    # ONE COPY OF THIS STAGE AT A TIME, refused at entry rather than at the
    # point of damage. `busy()` below already stops two renders overlapping;
    # it cannot stop two PROCESSES from waiting on each other forever. See
    # solo.py -- four copies of a batch tool once deadlocked on their own
    # correct queue guard, at 0% GPU, with nothing in any log.
    solo.solo("plates", where=os.path.dirname(os.path.abspath(__file__)),
              force="--force" in sys.argv)
    force = "--force" in sys.argv
    only = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--beat=")]
    # BARE SIDS ARE BEATS TOO, exactly as h3_shoot.py reads them. They were
    # silently IGNORED here: `gen_still.py --force 01 08` re-rendered the
    # whole film, because the two sids matched no --flag and fell through --
    # a fault class this repo already names (an argument that resolves to
    # nothing and still reports a pass). An unknown flag is refused outright.
    only += [a.zfill(2) for a in sys.argv[1:] if a.isdigit()]
    known = ("--force", "--obj", "--filtered", "--no-strip")
    bad = [a for a in sys.argv[1:]
           if not a.isdigit() and not a.startswith(("--beat=", "--seed="))
           and a not in known]
    if bad:
        sys.exit(f"FAIL: unrecognised argument(s) {bad} -- a beat is a bare "
                 f"sid or --beat=NN; anything else here renders the WHOLE film")
    # AND THE VALUES ARE CHECKED TOO (fault 131). Bare sids earned this guard
    # and --beat= never did: `--beat=99`, or a beat id carried from another
    # film, matched nothing, rendered nothing, and on a tree with plates on
    # disk fell through to the PASS line -- the exact class the comment
    # above names, through the other door.
    sids = {b["sid"] for b in shot.BEATS}
    ghost = [s for s in only if s not in sids]
    if ghost:
        sys.exit(f"FAIL: {ghost} are not beats of this film. It has "
                 f"{sorted(sids)}")
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

    # THE SUMMARY COVERS WHAT WAS ASKED FOR. It resolved plate() for EVERY
    # beat, so `gen_still.py --beat=01` on a fresh clone rendered beat 01
    # successfully and then exited "FAIL: no plate for beat 02" -- a FAIL
    # for a run that did what it was told (fault 131).
    done = [b for b in beats if not only or b["sid"] in only]
    print("\nPASS: " + "  |  ".join(
        f"{b['sid']} -> {os.path.basename(plate(b['sid']))}" for b in done))
    if only:
        print(f"  ({len(done)} of {len(beats)} beats -- the rest were not "
              f"asked for)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
