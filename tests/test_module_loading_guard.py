"""Fail the suite when a test loads a module without the bytecode guard (issue #215).

Executing a source file writes `__pycache__/*.pyc` beside it. Test suites load
payload providers and repository scripts straight out of `standards/` and
`scripts/`, and `standards/` is byte-immutable: a stray cache breaks whole-tree
digest and projection comparisons, and on the self-hosted runner it survives into
the next session's workspace. `tests/module_loading.py` owns the
`sys.dont_write_bytecode` guard that prevents this; ten call sites had duplicated
the guard verbatim (PR #214) and nothing stopped an eleventh from omitting it.

This test is that stop. It reads the AST rather than the runtime, so a call site
that is never exercised by the selected tests is still caught.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_TESTS = Path(__file__).resolve().parent
_HELPER = _TESTS / "module_loading.py"

# Call sites allowed to run `exec_module` without the shared helper, each mapped to
# the reason the guard is unnecessary there. A site that only ever loads from
# `tmp_path` writes its cache into a directory pytest discards, so it may be listed
# here instead of adopting the helper. Empty on purpose: every current site adopted
# the helper, which is the simpler outcome — adding an entry is a deliberate act that
# has to survive review of the reason.
_EXEMPT: dict[str, str] = {}


_DEFERRING_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)


def _guarded(chain: list[ast.AST]) -> bool:
    """Report whether an `exec_module` site is inside a bytecode guard that still holds.

    `chain` is the ancestor path from the module down to the site, outermost first.

    The shape recognized is the one `load_module_from_path` implements: the site sits in
    the body of a `try` whose `finally` restores `sys.dont_write_bytecode` *from a
    captured name* (`previous = sys.dont_write_bytecode` … `sys.dont_write_bytecode =
    previous`). Assigning a literal in the `finally` is not a restore — it pins the flag
    to a value the caller never chose — so it does not count.

    A site inside a function or lambda defined in the `try` body is not guarded either:
    the body runs when that function is called, which is after the `finally` has already
    restored the flag. Only the paths that execute while the `try` is on the stack pass.
    """
    for index, node in enumerate(chain):
        if not isinstance(node, ast.Try):
            continue
        if not any(_restores_flag(statement) for statement in node.finalbody):
            continue
        if index + 1 >= len(chain) or chain[index + 1] not in node.body:
            continue
        if any(isinstance(inner, _DEFERRING_SCOPES) for inner in chain[index + 1 :]):
            continue
        return True
    return False


def _restores_flag(statement: ast.stmt) -> bool:
    if not isinstance(statement, ast.Assign):
        return False
    # The value must be a plain name: the guard's contract is to hand the flag back to
    # whatever the caller had, and `sys.dont_write_bytecode = True` satisfies neither
    # that nor this test's docstring while looking like a restore.
    if not isinstance(statement.value, ast.Name):
        return False
    return any(
        isinstance(target, ast.Attribute)
        and target.attr == "dont_write_bytecode"
        and isinstance(target.value, ast.Name)
        and target.value.id == "sys"
        for target in statement.targets
    )


def _is_getattr_exec_module(node: ast.AST) -> bool:
    """Report whether `node` is `getattr(<obj>, "exec_module"[, ...])`.

    `getattr(loader, "exec_module")(module)` reaches the same loader method without ever
    spelling it as an attribute, so an attribute-only scan misses it entirely.
    """
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "getattr"
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and node.args[1].value == "exec_module"
    )


def _call_sites(tree: ast.Module) -> list[tuple[int, bool]]:
    """Return `(line, guarded)` for every site that reaches `exec_module` in a module.

    Three shapes count, because all three execute the loaded module's code:
    a direct `<...>.exec_module(...)` call, a `getattr(<obj>, "exec_module")` lookup
    (called immediately or bound first), and a bare `<...>.exec_module` attribute that
    is not the callee of its own call — the bound-name form `run = loader.exec_module`,
    whose eventual call may be anywhere. The lookup, not the eventual call, is the
    reported site: it is the only position this scan can attribute to a source line.
    """
    sites: list[tuple[int, bool]] = []
    chain: list[ast.AST] = []

    def visit(node: ast.AST) -> None:
        parent = chain[-1] if chain else None
        chain.append(node)
        site: ast.expr | None = None
        if isinstance(node, ast.Call):
            direct = isinstance(node.func, ast.Attribute) and node.func.attr == "exec_module"
            if direct or _is_getattr_exec_module(node):
                site = node
        elif isinstance(node, ast.Attribute) and node.attr == "exec_module":
            # Skip the attribute that belongs to a direct call: it is already counted
            # there, and counting it again would report two sites on one line.
            if not (isinstance(parent, ast.Call) and parent.func is node):
                site = node
        if site is not None:
            sites.append((site.lineno, _guarded(list(chain))))
        for child in ast.iter_child_nodes(node):
            visit(child)
        chain.pop()

    visit(tree)
    return sites


def test_module_loading__every_exec_module_under_tests__is_guarded() -> None:
    unguarded: list[str] = []
    for path in sorted(_TESTS.rglob("*.py")):
        relative = path.relative_to(_TESTS.parent).as_posix()
        if relative in _EXEMPT:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for line, guarded in _call_sites(tree):
            if guarded:
                continue
            unguarded.append(f"{relative}:{line}")

    assert not unguarded, (
        "exec_module without a sys.dont_write_bytecode guard writes __pycache__ beside "
        "the loaded source, which corrupts the byte-immutable standards/ tree. Call "
        "tests.module_loading.load_module_from_path instead, at: " + ", ".join(unguarded)
    )


def test_module_loading__helper__holds_a_single_guarded_call() -> None:
    """Pin the helper as the one place the suite executes a module from a path."""
    sites = _call_sites(ast.parse(_HELPER.read_text(encoding="utf-8")))
    assert len(sites) == 1
    assert all(guarded for _, guarded in sites)


# Each case is source that reaches exec_module, paired with what the scan must say about
# it. The evasions are the reason this table exists: every one of them was accepted as
# "no site" or "guarded" by an earlier version of the scan, so each row pins a hole shut.
_DETECTION_CASES = (
    (
        "direct call, no guard",
        "spec.loader.exec_module(module)\n",
        False,
    ),
    (
        "canonical guard",
        "previous = sys.dont_write_bytecode\n"
        "sys.dont_write_bytecode = True\n"
        "try:\n"
        "    spec.loader.exec_module(module)\n"
        "finally:\n"
        "    sys.dont_write_bytecode = previous\n",
        True,
    ),
    (
        "getattr lookup, called immediately",
        'getattr(spec.loader, "exec_module")(module)\n',
        False,
    ),
    (
        "getattr lookup, bound then called",
        'run = getattr(spec.loader, "exec_module")\nrun(module)\n',
        False,
    ),
    (
        "bound attribute, called later",
        "run = spec.loader.exec_module\nrun(module)\n",
        False,
    ),
    (
        "call deferred out of the guarded try by a function definition",
        "previous = sys.dont_write_bytecode\n"
        "sys.dont_write_bytecode = True\n"
        "try:\n"
        "    def load():\n"
        "        spec.loader.exec_module(module)\n"
        "finally:\n"
        "    sys.dont_write_bytecode = previous\n"
        "load()\n",
        False,
    ),
    (
        "finally pins the flag to a literal instead of restoring it",
        "sys.dont_write_bytecode = True\n"
        "try:\n"
        "    spec.loader.exec_module(module)\n"
        "finally:\n"
        "    sys.dont_write_bytecode = True\n",
        False,
    ),
)


@pytest.mark.parametrize(
    ("source", "expected_guarded"),
    [pytest.param(source, guarded, id=name) for name, source, guarded in _DETECTION_CASES],
)
def test_module_loading__call_site_scan__scores_each_shape(
    source: str, expected_guarded: bool
) -> None:
    sites = _call_sites(ast.parse(source))
    assert len(sites) == 1, f"expected exactly one detected site, got {sites}"
    assert sites[0][1] is expected_guarded
