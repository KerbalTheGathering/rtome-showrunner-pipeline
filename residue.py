"""Find the PREVIOUS season in this one. Run it once per clone, then argue.

THE FAULT THIS LOOKS FOR HAS ONE SHAPE AND NO SYMPTOM.

Every session numbers its beats "01", "02", "03". Every reel numbers its
segments the same way. So a table keyed by beat id -- MOTION, START_FRAME,
BOARD_TYPE, PLATE_ALIAS, SHIFT, a cue's CROSSOVER_SID -- resolves perfectly in
a tree it was never written for. Nothing raises, no count comes out wrong, and
the film renders. It is just the wrong film, or the right film anchored on a
frame measured off a different actor in a different room.

The template already says this once, in motion.py, about `SESSION`:

    A KEY THAT EXISTS IN EVERY SESSION IS NOT AN IDENTIFIER.

It is true of six more files, and of every quoted proper name typed into a
tool -- `who = "DALE"` printed the previous presenter's name against every take
of a reel he is not in.

WHAT IT DOES. For each tree it works out that tree's vocabulary by IMPORTING
it -- the sids it actually has, the names it actually uses -- and then walks
every .py in the tree for:

  * two-digit string literals used as dict keys, as subscripts, in a list or
    tuple, or compared with == / in
  * quoted ALL-CAPS words, which is what a proper name typed into machinery
    looks like

and reports everything that is not in the vocabulary.

FALSE POSITIVES ARE FINE HERE IN A WAY THEY ARE NOT IN preflight.py. This is a
tool you run once and read, not a gate that blocks a render -- so it is tuned
to miss nothing rather than to be always right, and it exits 0 no matter what
it finds unless you ask it not to. A check that cries wolf gets ignored; a
report you read once does not have that failure mode.

    python residue.py               # every tree
    python residue.py show          # one tree
    python residue.py --strict      # exit 1 if anything is reported
    python residue.py --sids        # skip the ALL-CAPS half, ids only
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys

import parts
import smoke

ROOT = os.path.dirname(os.path.abspath(__file__))

TWO_DIGIT = re.compile(r"^\d{2}$")
SHOUTED = re.compile(r"^[A-Z][A-Z0-9]{2,}$")

# WORDS THAT ARE SHOUTED FOR A REASON THAT IS NOT A NAME. Log levels, ffmpeg
# and API vocabulary, colour spaces, and this repo's own idioms. Kept short on
# purpose: a name that slips through costs one line of reading, and a stoplist
# that grows to silence the report is how the report stops working.
NOT_NAMES = {
    "FAIL", "PASS", "SKIP", "OK", "WARN", "NOTE", "MISSING", "ALIAS", "TODO",
    "RGB", "RGBA", "PNG", "MP4", "MP3", "WAV", "AAC", "PCM", "LUFS", "CRF",
    "GET", "POST", "PUT", "URL", "API", "KEY", "ENV", "CSV", "JSON", "UTF",
    "TRUE", "FALSE", "NONE", "AUTO", "MAIN", "LATE", "OPEN", "SHUT", "RAW",
    "SESSION", "SEASON", "SHOW", "COLD", "EXAMPLE", "BEATS", "AUDIO", "STYLE",
    "THE", "AND", "NOT", "ALL", "ONE", "TWO", "SIX",
}


def vocabulary(folder: str, label: str) -> dict | None:
    """This tree's own sids and names, read by importing it.

    IMPORTED RATHER THAN PARSED, because shot.BEATS is built by a comprehension
    in one tree and typed out in another, and a scanner that has to guess which
    would be wrong in exactly the trees this matters most in. A tree that
    cannot be imported is reported as such -- that is smoke.py's question and
    this tool has nothing useful to say until it is answered.

    _session_template IS NEVER CONFIGURED, so it gets smoke.py's stubbed
    identity. Its example content still has beats, and those beats are still
    the vocabulary the example has to be consistent with.
    """
    env = dict(os.environ)
    args = [sys.executable, "-c", _VOCAB]
    if label == "_session_template":
        env["SMOKE_STUB"] = json.dumps(smoke._stub(label, 1))
        args.append("--stub")
    r = subprocess.run(args, cwd=folder, env=env, capture_output=True,
                       text=True)
    # The last line only -- see the same note in contract.py.
    try:
        got = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        got = None
    if got and (got["sids"] or label == "root"):
        return got
    # A FOLDER INSIDE A TREE BORROWS THE TREE'S VOCABULARY. show/_probes has no
    # shot.py of its own -- it imports show/'s -- so asking it for a beat list
    # in its own right gets nothing, and the probes then look like a folder
    # with no season. Which is how a scanner reports "clean" on files it never
    # actually checked.
    parent = os.path.dirname(folder)
    if parent != ROOT and os.path.isdir(parent):
        return vocabulary(parent, os.path.basename(parent))
    return None


_VOCAB = r"""
import json, os, sys, types

if "--stub" in sys.argv:
    spec = json.loads(os.environ["SMOKE_STUB"])
    season = types.ModuleType("season_identity")
    season.__dict__.update(spec["season"])
    season.check = lambda: None
    season.claim_clips = lambda *a, **k: None
    season.folder = lambda: spec["season"]["DELIVER"]
    ident = types.ModuleType("identity")
    ident.__dict__.update(spec["identity"])
    ident.season = season
    ident.check = lambda: None
    ident.claim_clips = season.claim_clips
    sys.modules["season_identity"] = season
    sys.modules["identity"] = ident

def grab(mod, *names):
    try:
        m = __import__(mod)
    except BaseException:
        return {}
    return {n: getattr(m, n, None) for n in names}

sids, words = set(), set()
s = grab("shot", "CUT", "NAME", "TITLE", "SLUG", "OBJ_NAME")
sids |= set(s.get("CUT") or ())
sc = grab("script", "SIDS", "HOST_BRIEF")
sids |= set(sc.get("SIDS") or ())
try:
    import script
    sids |= {ln[1] for ln in getattr(script, "LINES", ())}
    words |= {w for _l, _s, _v, _y, t in getattr(script, "LINES", ())
              for w in str(t).replace(".", " ").replace(",", " ").split()}
except BaseException:
    pass
i = grab("identity", "NAME", "TITLE", "SLUG", "TITLE_SUPER")
try:
    import identity
    se = identity.season
except BaseException:
    try:
        import season_identity as se
    except BaseException:
        se = None
for src in (s, i):
    words |= {str(v) for v in src.values() if isinstance(v, str) and v}
if se is not None:
    for n in ("SEASON", "SEASON_TITLE", "SEASON_SLUG", "SHOW_NAME", "END_CARD"):
        v = getattr(se, n, None)
        if isinstance(v, str) and v:
            words.add(v)
# Split every known string into words too: "THE LIGHTHOUSE" legitimises both.
words |= {w for v in list(words) for w in str(v).replace("_", " ").split()}
json.dump({"sids": sorted(sids), "words": sorted(w.upper() for w in words)},
          sys.stdout)
"""


def _two(node) -> str | None:
    """The value, if this node is a two-digit string constant."""
    if (isinstance(node, ast.Constant) and isinstance(node.value, str)
            and TWO_DIGIT.match(node.value)):
        return node.value
    return None


class Scan(ast.NodeVisitor):
    """Every literal worth suspecting, with the line it is on.

    A CONTAINER IS ONLY A BEAT TABLE IF *EVERY* KEY IS TWO DIGITS, and that
    rule is the whole difference between a report you read and a report you
    close. Without it the ComfyUI workflow graphs win: they are dicts keyed
    "1", "6", "13", "24", "104" and a fifteen-beat film has sids that collide
    with a third of them, so the first version of this tool printed ninety
    node ids and buried the four real findings. A table keyed by beat is
    HOMOGENEOUS -- MOTION, BOARD_TYPE, START_FRAME, PLATE_ALIAS -- and a graph
    never is.

    Comparisons are exempt from that rule and always reported: `sid == "06"`
    has no container to be homogeneous about, and it is the shape of the fault
    that welded the show to six segments.
    """

    def __init__(self) -> None:
        self.hits: list[tuple[int, str, str]] = []       # (line, kind, value)

    def _note(self, node, kind: str) -> None:
        v = _two(node)
        if v is not None:
            self.hits.append((getattr(node, "lineno", 0), kind, v))

    def visit_Dict(self, node: ast.Dict) -> None:
        keys = node.keys
        if keys and all(k is not None and _two(k) for k in keys):
            for k in keys:
                self._note(k, "key of a beat-keyed table")
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        # `sid == "06"` and `sid in ("01", "04")` are the two ways a literal
        # gets to decide something on its own.
        for part in [node.left] + list(node.comparators):
            self._note(part, "comparison")
            if isinstance(part, (ast.List, ast.Tuple, ast.Set)):
                for e in part.elts:
                    self._note(e, "comparison")
        self.generic_visit(node)

    def visit_List(self, node: ast.List) -> None:
        if node.elts and all(_two(e) for e in node.elts):
            for e in node.elts:
                self._note(e, "member of a beat list")
        self.generic_visit(node)

    visit_Tuple = visit_List                                   # type: ignore
    visit_Set = visit_List                                     # type: ignore

    def visit_Call(self, node: ast.Call) -> None:
        # `.get("07")` is a lookup by any other name, and it is what fault 4's
        # `PLATE_ALIAS.get("07") == "03"` looked like.
        if isinstance(node.func, ast.Attribute) and node.func.attr in (
                "get", "setdefault", "count", "index", "pop"):
            for a in node.args[:1]:
                self._note(a, "lookup")
        self.generic_visit(node)


_SYMBOLS: set[str] = set()


def symbols() -> set[str]:
    """Every identifier the WHOLE REPO uses, lowercased. Computed once.

    A SHOUTED STRING THAT IS ALSO A SYMBOL IS A LOOKUP, NOT A NAME. `"NAME"`,
    `"TITLE"`, `"CONTENT"`, `"SHORT"` and the rest are how this repo reads its
    own fields -- `globals()[k]`, `getattr`, a table of required keys, a local
    called `short` printed in caps -- and flagging them buried the one line
    that mattered under forty that did not. The first version of this tool did
    exactly that and was unreadable, which is the failure mode a report has
    instead of crying wolf.
    """
    if _SYMBOLS:
        return _SYMBOLS
    for _label, folder in smoke.trees():
        for mod in smoke.modules(folder):
            try:
                tree = ast.parse(open(os.path.join(folder, mod + ".py"),
                                      encoding="utf-8").read())
            except SyntaxError:
                continue
            for n in ast.walk(tree):
                if isinstance(n, ast.Name):
                    _SYMBOLS.add(n.id.lower())
                elif isinstance(n, ast.Attribute):
                    _SYMBOLS.add(n.attr.lower())
                elif isinstance(n, ast.keyword) and n.arg:
                    _SYMBOLS.add(n.arg.lower())
                elif isinstance(n, (ast.FunctionDef, ast.ClassDef)):
                    _SYMBOLS.add(n.name.lower())
                elif isinstance(n, ast.arg):
                    _SYMBOLS.add(n.arg.lower())
    return _SYMBOLS


def strings(path: str) -> list[tuple[int, str]]:
    """String literals that are ONE shouted word and nothing else.

    THE WHOLE LITERAL, NOT A WORD INSIDE IT. Splitting prose on non-letters
    turned "set SEASON_FFMPEG=..." into FFMPEG and "SEASON", and a name typed
    into machinery is never a fragment of a sentence -- it is the entire
    string, sitting on the right of an assignment, which is what `who = "DALE"`
    looked like.
    """
    try:
        tree = ast.parse(open(path, encoding="utf-8").read(), path)
    except SyntaxError:
        return []
    return [(n.lineno, n.value) for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and SHOUTED.match(n.value) and n.value not in NOT_NAMES]


def scan(path: str, vocab: dict, do_names: bool, syms: set[str]) -> list[str]:
    try:
        tree = ast.parse(open(path, encoding="utf-8").read(), path)
    except SyntaxError as e:
        return [f"    line {e.lineno}: will not parse -- {e.msg}"]

    sids = set(vocab["sids"])
    words = set(vocab["words"])
    v = Scan()
    v.visit(tree)

    seen, out = set(), []
    for line, kind, val in sorted(v.hits):
        if not TWO_DIGIT.match(val) or val in sids:
            continue
        if (line, val) in seen:
            continue
        seen.add((line, val))
        out.append(f"    line {line:>4}  {val!r:>6} as a {kind}"
                   f"   -- this tree has {sorted(sids) or 'no sids at all'}")
    if do_names:
        for line, w in sorted(set(strings(path))):
            if w in words or w.lower() in syms:
                continue
            out.append(f"    line {line:>4}  {w!r:>6} -- a shouted name this "
                       f"season does not use")
    return out


def main() -> int:
    argv = sys.argv[1:]
    strict = "--strict" in argv
    do_names = "--sids" not in argv
    named = [a for a in argv if not a.startswith("-")]

    want = smoke.trees()
    if named:
        want = [t for t in want if t[0] in named
                or os.path.basename(t[1]) in named]
        if not want:
            sys.exit(f"FAIL: {named} matched no tree")

    total = 0
    for label, folder in want:
        vocab = vocabulary(folder, label)
        print(f"  {label}")
        if vocab is None:
            # NO VOCABULARY MEANS NO OPINION. A tree whose shot.py will not
            # import has no list of its own beats, and reporting every literal
            # against an empty set would print the entire tree -- the "checker
            # that matched zero items and passed" fault, inverted.
            print("    no beat list -- `python smoke.py` first; there is "
                  "nothing to say about a tree that does not load")
            print()
            continue
        found = 0
        syms = symbols()
        for mod in smoke.modules(folder):
            path = os.path.join(folder, mod + ".py")
            rows = scan(path, vocab, do_names, syms)
            if rows:
                print(f"  {mod}.py")
                for r in rows:
                    print(r)
                found += len(rows)
        total += found
        if not found:
            print("    nothing that is not this season's")
        print()

    print(f"  {total} thing(s) to look at.")
    if total:
        print("  EVERY ONE OF THESE MAY BE FINE. What the tool cannot tell is\n"
              "  whether a two-digit literal is a beat id that belongs to\n"
              "  another film or a number that happens to have two digits.\n"
              "  Read them once; the ones that are real are the ones that\n"
              "  index a table keyed by beat.")
    return 1 if (strict and total) else 0


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
