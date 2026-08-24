"""The whole season as one video.

THE RUNNING ORDER IS [COLD OPEN] then [INTERSTITIAL n] -> [FILM n], and it comes
from parts.py rather than from a list in this file. It used to be typed here AND
in the season driver, which meant two lists free to disagree about what the
season was.

The cold open is the front door. Without one the feature begins on whatever the
first interstitial happens to be -- in the reference season, a man behind a desk
saying "Good morning", which is a front door for the SHOW with nothing above the
films saying what you are watching.

STREAM COPY, NOT RE-ENCODE. Every part is already the same codec, geometry, rate
and pixel format, so the concat demuxer joins them without touching a pixel -- a
fourteen-minute re-encode of finished work is both slow and lossy. THE
PARAMETERS ARE VERIFIED HERE RATHER THAN ASSUMED, because a concat demuxer given
a mismatch does not fail: it produces a file that plays wrong somewhere in the
middle. Anything that differs is reported as a MISMATCH and nothing is built.

THE SOUND IS A DIFFERENT STORY AND THE COMMENTS IN main() ARE THE IMPORTANT PART
OF THIS FILE. Copying thirteen AAC streams stacks thirteen encoder priming
delays and walks the voice late down the running order -- measured at +154 ms by
the back half. The picture is still copied; the audio is rebuilt once, from the
PCM mixes, and each mix is checked against its own part's picture first.

IT LIVES AT THE SEASON ROOT, AND IT USED TO LIVE IN `show/`. That was wrong in
a way nothing caught until a season without a show tried to build: `season.py`
offers `SHOW = False` for "a cold open and N films", then refused to join one,
because the joiner was inside the optional folder. The season's own driver told
you to go and join it by hand.

The coupling turned out to be nothing at all -- this file imported the show's
`identity` and `shot` and used NEITHER. Two dead imports were the whole reason
the join could not be run by a season that had no show. Everything it actually
reads (`parts.running_order()`, `season_identity`) is season-level and always
was.

    python feature.py            # verify and build
    python feature.py --check    # verify only, build nothing
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import season_paths                                                # noqa: E402


import os
import subprocess
import sys

# NO `import identity` AND NO `import shot`. They were here, they were never
# read, and they were the only thing making this a show-tree file. A dead
# import is not free: it decides where a module is allowed to live.

# THE RUNNING ORDER IS DISCOVERED, NOT TYPED HERE. It used to be a list of tree
# names in this file AND another list in the season driver, free to disagree.
# parts.py works it out from the folders on disk and both read that.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parts                                                       # noqa: E402
import season_identity as season                                   # noqa: E402

# HERE IS THE SEASON FOLDER. It used to be `show/`, with ROOT one level up;
# now they are the same directory and only one of them is kept, because two
# names for one path is how a wrong one gets used.
ROOT = HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")       # gitignored, like every other output
WORK = os.path.join(HERE, "_work")
FF = season_paths.FFMPEG


# (the cold open now comes out of parts.running_order() like everything else)

DEST = os.path.join(OUT, f"{season.SEASON_SLUG}.mp4")

# THE HANDOVER AT EVERY PART BOUNDARY -- see the join in main(). Seconds.
# A splice between two worlds (a film's last frame, the show's first) reads
# as an error, not a cut; a short dip is the grammar (LOSS OF SIGNAL v10).
JOIN_DIP = 0.5       # picture: out over the last 0.5 s, in over the first 0.5 s
JOIN_AFADE = 0.3     # sound: the same, shorter, so the dip is felt, not heard


def probe(path: str) -> dict:
    def q(sel: str, entries: str) -> list[str]:
        out = subprocess.run(
            [season_paths.ff("ffprobe"), "-v", "error",
             "-select_streams", sel, "-show_entries", entries,
             "-of", "csv=p=0", path],
            capture_output=True, text=True, check=True).stdout.strip()
        return out.split(",")
    v = q("v:0", "stream=width,height,r_frame_rate,codec_name,pix_fmt")
    a = q("a:0", "stream=codec_name,sample_rate,channels")
    d = subprocess.run(
        [season_paths.ff("ffprobe"), "-v", "error", "-show_entries",
         "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True).stdout.strip()
    return {"v": tuple(v), "a": tuple(a), "secs": float(d)}


def main() -> int:
    # `order`, not `parts` -- the module of that name is what supplies it.
    order, rows, missing = [], [], []
    for what, mp4, wav in parts.running_order():
        if os.path.exists(mp4):
            order.append((what, mp4, wav))
        else:
            missing.append(f"{what}: {mp4}")
    if missing:
        print("  MISSING:")
        for m in missing:
            print(f"    {m}")
        sys.exit("\nFAIL: those parts have not been built. `python "
                 "../season.py` builds everything in the right order, and "
                 "`python ../parts.py` explains the layout.")

    ref = None
    ok = True
    print(f"  {'part':26s} {'secs':>7}  video / audio")
    for what, p, _wav in order:
        i = probe(p)
        rows.append((what, p, i))
        tag = ""
        if ref is None:
            ref = i
        elif (i["v"], i["a"]) != (ref["v"], ref["a"]):
            tag = "   <-- MISMATCH, concat would silently misbehave"
            ok = False
        print(f"  {what:26s} {i['secs']:>7.2f}  "
              f"{','.join(i['v'])} / {','.join(i['a'])}{tag}")

    total = sum(i["secs"] for _, _, i in rows)
    bounty = sum(i["secs"] for w, _, i in rows if w.startswith("interstitial"))
    cold = sum(i["secs"] for w, _, i in rows if w == "COLD OPEN")
    print(f"\n  {len(rows)} parts, {total:.1f}s total ({total/60:.1f} min)")
    print(f"  {cold:.1f}s cold open + {bounty:.1f}s of show = "
          f"{100*(cold+bounty)/total:.1f}% of the running time is connective "
          "tissue")

    # DEAD AIR IS A TRIPWIRE, NOT A VERDICT. A part assembled from a stale
    # intermediate can carry 30s of silence and every other check passes --
    # the tenth season shipped one (the last third of a film went quiet and
    # the operator heard it before any tool did). A pause over 2s is legal;
    # this prints where they are so somebody LISTENS there. Ears are the
    # filmstrip of the mix.
    for what, p_, _i in rows:
        r = subprocess.run([season_paths.ff("ffmpeg"), "-v", "info", "-i", p_,
                            "-af", "silencedetect=n=-50dB:d=2.0",
                            "-f", "null", "-"], capture_output=True, text=True)
        hits = [ln.split("silence_start: ")[1].split()[0]
                for ln in (r.stderr or "").splitlines() if "silence_start" in ln]
        if hits:
            print(f"  NOTE: {what} has {len(hits)} silent stretch(es) over 2s, "
                  f"starting at {', '.join(hits[:4])}s -- listen there "
                  f"before publishing")

    if not ok:
        sys.exit("\nFAIL: the parts do not match -- fix the odd one out rather "
                 "than re-encoding the season")
    if "--check" in sys.argv:
        print("\n  --check: verified, nothing built")
        return 0

    os.makedirs(WORK, exist_ok=True)
    lst = os.path.join(WORK, "season.txt")
    with open(lst, "w", encoding="utf-8") as fh:
        for _, p, _wav in order:
            fh.write(f"file '{p}'\n")

    # THE VIDEO IS STREAM-COPIED. THE AUDIO IS RE-ENCODED ONCE, AS ONE STREAM.
    #
    # `-c copy` on both was the original and it is right about the picture:
    # thirteen identical h264 streams join without touching a pixel. It is wrong
    # about the sound, and the way it is wrong GROWS.
    #
    # Every AAC stream carries an encoder PRIMING DELAY -- roughly 2048 samples
    # of lead-in a decoder is meant to discard. Copied, each part brings its own
    # and the concat demuxer stacks them. Measured against the edit in the
    # delivered feature: the voice ran +70ms late two parts in, +157ms four
    # parts in, +232ms six parts in. A constant per JOIN rather than per second,
    # which is exactly why it was invisible inside any one film and a quarter of
    # a second by the middle of the season. 48 kHz makes each one ~43ms where
    # 96 kHz made it ~21ms, so consolidating the delivery rate is what took this
    # from unnoticed to unwatchable.
    #
    # The concat FILTER decodes to samples and joins those, so there is no
    # priming to inherit and no part boundary left in the stream. It costs one
    # AAC generation on a narration-over-bed mix, against a defect that puts the
    # back half of the film out of sync. The picture is still copied.
    # AND THE AUDIO COMES FROM THE PCM MIXES, NOT FROM THE PARTS' AAC.
    #
    # Filtering the parts' own audio removed most of the drift but not all of
    # it: measured part-start offsets still walked +10, +20, +57, +72 ... +154ms
    # down the running order, about 12ms per join. Decoding thirteen AAC streams
    # means inheriting thirteen priming allowances, and a decoder that does not
    # trim every one of them exactly hands the filter a few hundred extra
    # samples each time.
    #
    # Every part already wrote a PCM mix that is sample-locked to its own
    # picture -- that is what normalize() asserts. Using those skips AAC on the
    # way in entirely, so the audio timeline is the exact sum of the picture
    # durations by construction, and the season is encoded once from samples.
    #
    # THE MIXES ARE VERIFIED AGAINST THE PICTURE FIRST. A stale or missing wav
    # would otherwise put a whole part's sound under the wrong film with nothing
    # to say so -- which is a worse failure than the drift this replaces.
    wavs = []
    for name, p, w in order:
        if not os.path.exists(w):
            sys.exit(f"FAIL: {name} has no PCM mix at\n    {w}\n  Rebuild that "
                     "part; the feature will not guess its audio from the AAC.")
        vd = float(subprocess.run(
            [season_paths.ff("ffprobe"), "-v", "error", "-select_streams",
             "v:0", "-show_entries", "stream=duration", "-of", "csv=p=0", p],
            capture_output=True, text=True,
            check=True).stdout.strip().rstrip(","))
        ad = float(subprocess.run(
            [season_paths.ff("ffprobe"), "-v", "error", "-show_entries",
             "format=duration", "-of", "csv=p=0", w],
            capture_output=True, text=True, check=True).stdout.strip())
        if abs(ad - vd) > 0.002:
            sys.exit(f"FAIL: {name}: mix is {ad:.4f}s against {vd:.4f}s of "
                     f"picture\n    {w}\n  It is stale -- rebuild that part.")
        wavs.append(w)

    n = len(wavs)
    ins = []
    for w in wavs:
        ins += ["-i", w]
    # THE JOINS DIP TO BLACK (LOSS OF SIGNAL, v9 viewing: "the cuts to the
    # control room are abrupt"). Every part boundary is a change of world --
    # a film's set to the show's floor and back -- and a splice reads as an
    # error, not a cut. A short dip at each boundary is the handover: each
    # part's picture fades out over its last JOIN_DIP seconds and in over its
    # first, and its sound does the same over a shorter JOIN_AFADE, so the
    # loop's squelch and the room tone are not cut mid-sample.
    #
    # PER PART, NOT ON THE JOINED STREAM. ffmpeg's fade=t=in:st=X holds every
    # frame BEFORE X black and t=out every frame AFTER -- a chain of them on
    # the joined picture blacked the whole film (v10, first join: 1.7 MB, ten
    # minutes of black). So each part is re-encoded once with its own two
    # fades (cached by mtime), the concat copies those, and the audio fades
    # ride each mix input inside the concat filter. Durations are untouched.
    # JOIN_DIP = 0 restores the plain splice.
    dip, afade = JOIN_DIP, JOIN_AFADE
    first, last = 0, len(order) - 1
    if dip > 0:
        dipped = []
        for k, ((name, p, _w), (_n, _p, i)) in enumerate(zip(order, rows)):
            st = os.stat(p)
            dp = os.path.join(WORK, f"dip_{k:02d}_{int(st.st_mtime)}.mp4")
            if not (os.path.exists(dp) and os.path.getsize(dp) > 0):
                vf = []
                if k != first:
                    vf.append(f"fade=t=in:st=0:d={dip:.3f}")
                if k != last:
                    vf.append(f"fade=t=out:st={i['secs'] - dip:.3f}:d={dip:.3f}")
                print(f"  dip {name} ...", flush=True)
                subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                                "-i", p, "-an", "-vf", ",".join(vf) or "null",
                                "-c:v", "libx264", "-preset", "medium", "-crf", "16",
                                "-pix_fmt", "yuv420p", "-r", str(season.FPS),
                                dp + ".part.mp4"], check=True)
                os.replace(dp + ".part.mp4", dp)
            dipped.append(dp)
        with open(lst, "w", encoding="utf-8") as fh:
            for dp in dipped:
                fh.write(f"file '{dp}'\n")
    achain = []
    for k, (_n, _p, i) in enumerate(rows):
        f = []
        if dip > 0 and k != first:
            f.append(f"afade=t=in:st=0:d={afade:.3f}")
        if dip > 0 and k != last:
            f.append(f"afade=t=out:st={i['secs'] - afade:.3f}:d={afade:.3f}")
        achain.append(f"[{k + 1}:a]{','.join(f) or 'anull'}[f{k}];")
    # OUT WAS NEVER CREATED. WORK gets os.makedirs() above; OUT -- where
    # DEST (the actual join) is written -- did not, so ffmpeg refused with
    # "No such file or directory" on the first season with no earlier step
    # that happened to create out/ as a side effect.
    os.makedirs(OUT, exist_ok=True)
    subprocess.run([season_paths.ff("ffmpeg"), "-y", "-v", "error",
                    "-f", "concat", "-safe", "0", "-i", lst] + ins +
                   ["-filter_complex",
                    "".join(achain)
                    + "".join(f"[f{i}]" for i in range(n))
                    + f"concat=n={n}:v=0:a=1[a]",
                    "-map", "0:v:0", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", DEST], check=True)
    got = probe(DEST)
    print(f"\n  {got['secs']:.1f}s ({got['secs']/60:.1f} min), "
          f"{os.path.getsize(DEST)/1e6:.1f} MB -> {DEST}")
    if abs(got["secs"] - total) > 1.0:
        print(f"  !! expected {total:.1f}s -- a part may not have joined cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
