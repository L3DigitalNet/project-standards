"""Shared public command metadata used by parsers and documentation parity tests."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Final, ParamSpec, TypeVar

_P = ParamSpec("_P")
_R = TypeVar("_R", bound=int | None)

PACKAGE_AUTHORING_COMMAND_HELP: Final = {
    "validate-packages": "validate V2 package repositories",
    "render-consumer-catalog": "render or check a selected V2 consumer catalog",
    "generate-package-schemas": "write or check V2 JSON Schemas",
    "sync-payload-projection": "write or check installed payload projection",
}

PUBLIC_COMMAND_EXIT_CODES: Final = {
    "project-standards": frozenset({0, 1, 2, 3}),
    "validate": frozenset({0, 1, 2}),
    "fix": frozenset({0, 1, 2}),
    "init": frozenset({0, 1, 2}),
    "reconcile": frozenset({0, 1, 2}),
    "render": frozenset({0, 1, 2}),
    "mcp": frozenset({0, 1, 2}),
    "adopt": frozenset({0, 1, 2, 3}),
    "list": frozenset({0, 2, 3}),
    "agent-handoff": frozenset({0, 1, 2, 3}),
    "standards": frozenset({0, 1, 2}),
    "standards validate-graph": frozenset({0, 1, 2}),
    "standards render-catalog": frozenset({0, 1, 2}),
    "standards validate-packages": frozenset({0, 1, 2}),
    "standards render-consumer-catalog": frozenset({0, 1, 2}),
    "standards generate-package-schemas": frozenset({0, 1, 2}),
    "standards sync-payload-projection": frozenset({0, 1, 2}),
    "packages check-release": frozenset({0, 1, 2}),
    "packages": frozenset({0, 2}),
    "spec": frozenset({0, 2}),
    "spec validate": frozenset({0, 1, 2}),
    "spec lint": frozenset({0, 1, 2}),
    "spec extract": frozenset({0, 1, 2}),
    "spec next": frozenset({0, 1, 2}),
    "spec new": frozenset({0, 2}),
    "spec upgrade": frozenset({0, 2}),
    "spec import": frozenset({0, 2}),
    "validate-frontmatter": frozenset({0, 1, 2}),
    "validate-id": frozenset({0, 1, 2}),
    "sync-vscode-colors": frozenset({0, 1}),
    "sync-standards-include": frozenset({0, 1}),
    "format-frontmatter": frozenset({0, 1, 2}),
    "validate-references": frozenset({0, 1, 2}),
}


def validate_public_exit_code(command: str, result: int | None) -> int | None:
    """Reject an implementation result outside its documented public contract."""
    status = 0 if result is None else result
    if status not in PUBLIC_COMMAND_EXIT_CODES[command]:
        raise AssertionError(f"undocumented {command} exit status: {status}")
    return result


def enforce_public_exit_codes(command: str) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    """Bind a console entry point's returns and SystemExit paths to its exit contract."""

    def decorate(function: Callable[_P, _R]) -> Callable[_P, _R]:
        @wraps(function)
        def checked(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            try:
                result = function(*args, **kwargs)
            except SystemExit as exc:
                status = exc.code if isinstance(exc.code, int) else 0 if exc.code is None else 1
                validate_public_exit_code(command, status)
                raise
            validate_public_exit_code(command, result)
            return result

        return checked

    return decorate
