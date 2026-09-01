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

_TESTS = Path(__file__).resolve().parent
_HELPER = _TESTS / "module_loading.py"

# Call sites allowed to run `exec_module` without the shared helper, each mapped to
# the reason the guard is unnecessary there. A site that only ever loads from
# `tmp_path` writes its cache into a directory pytest discards, so it may be listed
# here instead of adopting the helper. Empty on purpose: every current site adopted
# the helper, which is the simpler outcome — adding an entry is a deliberate act that
# has to survive review of the reason.
_EXEMPT: dict[str, str] = {}


def _guarded(chain: list[ast.AST]) -> bool:
    """Report whether an `exec_module` call is lexically inside a bytecode guard.

    `chain` is the ancestor path from the module down to the call, outermost first.

    The shape recognized is the one `load_module_from_path` implements: the call sits
    in the body of a `try` whose `finally` restores `sys.dont_write_bytecode`. A
    hand-rolled guard of that shape passes; setting the flag without restoring it, or
    restoring it around a call that is not inside the `try`, does not.
    """
    for index, node in enumerate(chain):
        if not isinstance(node, ast.Try):
            continue
        if not any(_restores_flag(statement) for statement in node.finalbody):
            continue
        if index + 1 < len(chain) and chain[index + 1] in node.body:
            return True
    return False


def _restores_flag(statement: ast.stmt) -> bool:
    if not isinstance(statement, ast.Assign):
        return False
    return any(
        isinstance(target, ast.Attribute)
        and target.attr == "dont_write_bytecode"
        and isinstance(target.value, ast.Name)
        and target.value.id == "sys"
        for target in statement.targets
    )


def _call_sites(tree: ast.Module) -> list[tuple[int, bool]]:
    """Return `(line, guarded)` for every `<...>.exec_module(...)` call in a module."""
    sites: list[tuple[int, bool]] = []
    chain: list[ast.AST] = []

    def visit(node: ast.AST) -> None:
        chain.append(node)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "exec_module"
        ):
            sites.append((node.lineno, _guarded(list(chain))))
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
