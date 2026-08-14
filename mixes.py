"""The audio bus, as a library. What sits under what, and how it gets out of
the way.

WHY THIS IS A FILE. `assemble.py` built one graph: every take on a bus, every
cue on a second bus, the second sidechained to the first. It is a good
arrangement and it was the only one -- a film that wanted its score at a fixed
level, or one with no voice in it at all, edited the assembler. Worse than
welded, it was *silently* welded in two places:

  * with no takes, the VO bus was `amix=inputs=0` -- and the non-narrated mode
    this template now offers is exactly the film that has none.
  * with no cues, the music bus was the same. A film with no score is not an
    exotic request.

Both produced an ffmpeg error a hundred lines into a filter graph, at the end of
a bake, which is the worst possible place to learn it.

WHAT A BUS IS. One function over two lists of already-placed labels:

    fn(vo, mus, ctx, o) -> (parts, out_label)

  vo       filter-graph labels carrying the placed voice takes, e.g. ["[v0]"]
  mus      labels carrying the placed score cues
  ctx      {"total": seconds of picture, "spans": [(start, end), ...] of speech}
  o        this bus's settings

  parts    filter chains to append to the graph
  out      the label the finished bus arrives on

THE BUS OWNS THE LENGTH. Every bus here ends `apad=whole_dur=<total>,
atrim=0:<total>`, and that is not decoration. `sidechaincompress` is bounded by
its sidechain input, and once ate forty frames off the end of a finished film --
the ducked score stopped when the last take did, `-shortest` cut the picture to
match, and the end card went with it. The same shape of bug turned up again in
the two-speaker graph. A bus that cannot state its own length in one place will
get it wrong somewhere.

    python mixes.py             # what is available, and its settings
    python mixes.py --graph     # the filter graph each one builds, for a toy film

NAMED ONCE, IN identity.py:  MIX = "ducked"
                             MIX_OPTS = {"music": 0.42}
"""
from __future__ import annotations

import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

MIXES: dict[str, dict] = {}


def register(name: str, **defaults):
    """Add a bus to the library. `defaults` are its settings."""
    def wrap(fn):
        if name in MIXES:
            raise ValueError(
                f"two mixes are called {name!r}. A name is how identity.py "
                f"asks for one, so the second would silently win.")
        MIXES[name] = {"fn": fn, "defaults": defaults,
                       "doc": (fn.__doc__ or "").strip().splitlines()[0]}
        return fn
    return wrap


def get(name: str) -> dict:
    m = MIXES.get(name)
    if m is None:
        raise SystemExit(
            f"FAIL: there is no mix called {name!r}.\n"
            f"  The library has: {', '.join(sorted(MIXES))}\n"
            f"  `python mixes.py` describes each one; `--graph` prints what "
            f"each builds.\n  It is named in identity.MIX. `python "
            f"contract.py` catches this before the bake.")
    return m


def settings(name: str, opt: dict | None = None) -> dict:
    d = get(name)["defaults"]
    s = dict(d)
    s.update(opt or {})
    unknown = sorted(set(s) - set(d))
    if unknown:
        raise SystemExit(
            f"FAIL: mix {name!r} was given settings it does not have: "
            f"{unknown}.\n  It takes: {sorted(d) or '(none)'}")
    return s


def bus(name: str, vo: list[str], mus: list[str], ctx: dict,
        opt: dict | None = None) -> tuple[list[str], str]:
    """Build one bus. Refuses on a name it does not have, and on silence."""
    if not vo and not mus:
        raise SystemExit(
            "FAIL: the mix has neither a voice take nor a score cue in it.\n"
            "  A silent film is a real thing to want, but it is not this: it "
            "means\n  script.LINES and edit.CUES are both empty and something "
            "upstream lost them.")
    total = float(ctx["total"])
    if total <= 0:
        raise SystemExit(f"FAIL: the mix was asked for {total}s of audio.")
    return get(name)["fn"](list(vo), list(mus), ctx, settings(name, opt))


# --------------------------------------------------------------------------
# pieces every bus needs
# --------------------------------------------------------------------------


def sum_to(labels: list[str], out: str) -> str:
    """One chain summing `labels` onto `out`. Handles the one-input case.

    `amix=inputs=1` works, and `anull` says what is happening. The case that
    matters is that neither of them is `inputs=0`, which is what the hand-built
    graph produced for a film with no cues -- an ffmpeg error at the end of a
    bake rather than a refusal before it.
    """
    if not labels:
        raise SystemExit("FAIL: sum_to() was given no inputs. This is a bug in "
                         "the bus, not in the film.")
    if len(labels) == 1:
        return f"{labels[0]}anull{out}"
    return ("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:"
            f"dropout_transition=0{out}")


def to_length(src: str, total: float, out: str) -> str:
    """Pad up to `total` and cut down to it. The one place the length is said."""
    return (f"{src}apad=whole_dur={total:.3f},atrim=0:{total:.3f},"
            f"asetpts=PTS-STARTPTS{out}")


def merge_spans(spans, slack: float) -> list[tuple[float, float]]:
    """Speech spans closer together than `slack` become one span.

    THE SCORE MUST NOT SWELL BETWEEN TWO LINES OF THE SAME SENTENCE. Without
    this the automation lifts in every 0.35s gap and the film breathes in a way
    nobody asked for -- and the expression gets one term per take instead of
    one per passage.
    """
    out: list[list[float]] = []
    for s, e in sorted((float(a), float(b)) for a, b in spans):
        if out and s - out[-1][1] <= slack:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [(a, b) for a, b in out]


# --------------------------------------------------------------------------
# the library
# --------------------------------------------------------------------------


@register("ducked", music=0.55, threshold=0.03, ratio=8, attack=25,
          release=380, makeup=1)
def _ducked(vo, mus, ctx, o):
    """Score sidechained to the voice: it gets out of the way and comes back.

    The carried arrangement, and the right default for anything narrated. The
    duck follows the actual signal, so a loud line pushes the music further
    down than a quiet one -- which is what you want and is also why it pumps if
    you set `ratio` past about 10.

    DEGENERATE ON PURPOSE. With no cues this is the voice alone; with no takes
    it is the score alone. Both are said out loud by the caller rather than
    quietly producing a graph with an empty sum in it.
    """
    total = float(ctx["total"])
    parts = []
    if not mus:
        parts.append(sum_to(vo, "[bus]"))
        return parts + [to_length("[bus]", total, "[out]")], "[out]"
    parts.append(sum_to(mus, "[musraw]"))
    parts.append(f"[musraw]volume={o['music']}[mus]")
    if not vo:
        return parts + [to_length("[mus]", total, "[out]")], "[out]"
    parts.append(sum_to(vo, "[vo]"))
    # THE KEY IS PADDED TO THE FULL LENGTH. sidechaincompress is bounded by its
    # sidechain input; without this the score stops when the last word does.
    parts.append("[vo]asplit=2[vo1][vokeyraw]")
    parts.append(f"[vokeyraw]apad=whole_dur={total:.3f}[vokey]")
    parts.append(f"[mus][vokey]sidechaincompress=threshold={o['threshold']}:"
                 f"ratio={o['ratio']}:attack={o['attack']}:"
                 f"release={o['release']}:makeup={o['makeup']}[musd]")
    parts.append("[musd][vo1]amix=inputs=2:normalize=0:"
                 "dropout_transition=0[bus]")
    return parts + [to_length("[bus]", total, "[out]")], "[out]"


@register("flat", music=0.55)
def _flat(vo, mus, ctx, o):
    """Voice and score summed at fixed levels. Nothing moves.

    RIGHT WHEN THE SCORE IS ALREADY WRITTEN AROUND THE VOICE -- a sting under a
    title, a bed with a hole in it -- and right whenever the pumping of a duck
    is more audible than the duck. Set `music` by ear and leave it there.
    """
    total = float(ctx["total"])
    parts, labels = [], []
    if mus:
        parts.append(sum_to(mus, "[musraw]"))
        parts.append(f"[musraw]volume={o['music']}[mus]")
        labels.append("[mus]")
    if vo:
        parts.append(sum_to(vo, "[vo]"))
        labels.append("[vo]")
    parts.append(sum_to(labels, "[bus]"))
    return parts + [to_length("[bus]", total, "[out]")], "[out]"


@register("under", music=0.55, duck=0.30, ramp=0.40, pad=0.15)
def _under(vo, mus, ctx, o):
    """Score ducked by automation, not by signal: the same dip every time.

    THE DIFFERENCE FROM `ducked` IS PREDICTABILITY, and it is the reason to
    choose it. A sidechain follows the voice, so the score moves differently
    under a shout than under a mutter and the film's floor wanders. This drops
    the score to `duck` for the length of each passage of speech and puts it
    back, `ramp` seconds either way, whatever the take is doing.

    It also ducks around silence a sidechain cannot see -- a beat where
    somebody is clearly about to speak stays down through the pause, because
    the spans come from the edit rather than from the waveform.

    Needs the speech spans in `ctx["spans"]`. With none it is `flat`.
    """
    total = float(ctx["total"])
    parts, labels = [], []
    spans = merge_spans(ctx.get("spans") or [], 2.0 * (o["pad"] + o["ramp"]))
    if mus:
        parts.append(sum_to(mus, "[musraw]"))
        if spans:
            r = max(0.01, float(o["ramp"]))
            terms = []
            for s, e in spans:
                a = s - o["pad"] - r
                d = e + o["pad"] + r
                terms.append(f"clip(min((t-{a:.3f})/{r:.3f},"
                             f"({d:.3f}-t)/{r:.3f}),0,1)")
            gate = terms[0]
            for t in terms[1:]:
                gate = f"max({gate},{t})"
            depth = 1.0 - float(o["duck"])
            parts.append(f"[musraw]volume=volume='{o['music']}*"
                         f"(1-{depth:.3f}*({gate}))':eval=frame[mus]")
        else:
            parts.append(f"[musraw]volume={o['music']}[mus]")
        labels.append("[mus]")
    if vo:
        parts.append(sum_to(vo, "[vo]"))
        labels.append("[vo]")
    parts.append(sum_to(labels, "[bus]"))
    return parts + [to_length("[bus]", total, "[out]")], "[out]"


# --------------------------------------------------------------------------
# a season's own buses
# --------------------------------------------------------------------------
#
# DROP A `mixes_extra.py` BESIDE YOUR identity.py, the same extension point as
# devices_extra.py. A stem-per-role bus -- one output file per speaker, for a
# season that hands its audio to somebody else to finish -- is the obvious one,
# and it is a different OUTPUT contract as well as a different graph: it wants
# more than one `dest`, so it is a bus plus a change in assemble.main(), not a
# bus alone. That is worth knowing before you start.
_LOADED: set[str] = set()


def load_extra(folder: str) -> str | None:
    """Import `<folder>/mixes_extra.py` if it is there. Idempotent."""
    path = os.path.join(folder, "mixes_extra.py")
    if not os.path.exists(path) or path in _LOADED:
        return None
    _LOADED.add(path)
    spec = importlib.util.spec_from_file_location("mixes_extra", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mixes_extra"] = mod
    spec.loader.exec_module(mod)
    return path


def main() -> int:
    print(f"  {len(MIXES)} mix(es):\n")
    for name in sorted(MIXES):
        m = MIXES[name]
        print(f"  {name:<10} {m['doc']}")
        if m["defaults"]:
            print(f"  {'':<10} settings: "
                  + ", ".join(f"{k}={v!r}" for k, v in
                              sorted(m["defaults"].items())))
    print("\n  Named in identity.py:  MIX = \"ducked\"\n"
          "                         MIX_OPTS = {\"music\": 0.42}")
    if "--graph" not in sys.argv:
        return 0

    # WHAT EACH ONE ACTUALLY BUILDS, for a film you can hold in your head:
    # three takes and two cues over 40s. Printed rather than described,
    # because the graph is the thing that has been wrong twice.
    ctx = {"total": 40.0, "spans": [(2.0, 6.5), (7.0, 9.0), (28.0, 33.0)]}
    cases = [("three takes, two cues", ["[v0]", "[v1]", "[v2]"], ["[m0]", "[m1]"]),
             ("no cues (unscored)", ["[v0]", "[v1]", "[v2]"], []),
             ("no takes (non-narrated)", [], ["[m0]", "[m1]"])]
    for name in sorted(MIXES):
        print(f"\n  {'=' * 68}\n  {name}")
        for label, vo, mus in cases:
            parts, out = bus(name, vo, mus,
                             dict(ctx, spans=ctx["spans"] if vo else []))
            print(f"\n    -- {label} -> {out}")
            for p in parts:
                print(f"       {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
