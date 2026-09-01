"""Load a module from a filesystem path without writing bytecode beside it.

Tests reach payload providers, repository scripts, and rendered gate scripts by
location rather than by import, because those files are delivered bytes with no
importable package layout. CPython writes `__pycache__/*.pyc` beside a source it
executes, and several of those sources live under `standards/`, whose contract is
byte-immutability: a stray cache breaks whole-tree digest and projection
comparisons, and on the self-hosted runner it survives into the next session's
workspace (`tests/payload_tree.py` records that failure mode in full).

`load_module_from_path` is the single place that owns the `sys.dont_write_bytecode`
guard. Ten call sites had duplicated it verbatim, and nothing stopped an eleventh
from omitting it; `tests/test_module_loading_guard.py` now fails the suite when an
unguarded `exec_module` appears anywhere under `tests/`.

Registration in `sys.modules` is opt-in: a loaded payload provider is a throwaway,
and leaving entries behind would let two versions of one family collide under a
shared name. Loading a module that defines dataclasses is the case that needs it —
`dataclasses._is_type` resolves a string annotation through `sys.modules[cls.__module__]`
while the class body executes, and raises when the entry is missing — so `register`
must publish the module *before* execution, which only this helper can do.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_module_from_path(name: str, source: Path, *, register: bool = False) -> ModuleType:
    """Execute `source` as a module named `name` and return it.

    With `register`, the module is published as `sys.modules[name]` before execution
    and left there; the caller owns the entry from then on. Raises ImportError when
    the path yields no loadable spec, so a moved or misspelled source fails with the
    path in the message rather than as an opaque AttributeError on `None` further
    down the test.
    """
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise ImportError(f"no loadable module spec for {source}")
    module = importlib.util.module_from_spec(spec)
    if register:
        sys.modules[name] = module
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module
