"""A shim, not a copy (finding 140). The logic lives in ../find_voice.py --
this was byte-identical in every tree, and a template copy multiplies per
film, so a fix in one of the copies was not a fix (direction.py set the
precedent). This file keeps `python find_voice.py ...` and `import find_voice`
working unchanged inside this tree: the season file resolves the tree
through the modules this shim puts first on sys.path.
"""
from __future__ import annotations

import importlib.util as _ilu
import os as _os
import sys as _sys

_TREE = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _os.path.dirname(_TREE))   # the season root
_sys.path.insert(0, _TREE)                     # this tree wins the imports

_p = _os.path.join(_os.path.dirname(_TREE), "find_voice.py")
_spec = _ilu.spec_from_file_location("_season_find_voice", _p)
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
globals().update({k: v for k, v in vars(_mod).items()
                  if not k.startswith("__")})

if __name__ == "__main__":
    # -h/--help prints the docstring -- the usage has always lived
    # there; this makes it reachable without opening the file
    # (finding 146). Before main(), so no lock is taken and no
    # argument guard fires first.
    import sys as _hsys
    if "-h" in _hsys.argv or "--help" in _hsys.argv:
        print(__doc__ or "(no usage doc)")
        raise SystemExit(0)
    _sys.exit(_mod.main())
