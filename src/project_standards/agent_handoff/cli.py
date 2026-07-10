"""Thin command routing for the manifest-declared agent-handoff providers."""

from __future__ import annotations

import sys

from project_standards.adopt.errors import AdoptError
from project_standards.provider_runner import run_packaged_providers
from project_standards.standard_manifest import ProviderOperation

_COMMANDS: dict[str, tuple[ProviderOperation, tuple[str, ...]]] = {
    "validate": (ProviderOperation.VALIDATE, ()),
    "size-report": (ProviderOperation.VALIDATE, ("--view", "size")),
    "shape-check": (ProviderOperation.VALIDATE, ("--view", "shape")),
    "drift-check": (ProviderOperation.DRIFT_CHECK, ()),
    "legacy-report": (ProviderOperation.EXTRACT, ()),
    "upgrade": (ProviderOperation.UPGRADE, ()),
}


def _print_help() -> None:
    print(
        "usage: project-standards agent-handoff COMMAND [OPTIONS]\n\n"
        "commands:\n"
        "  validate       validate full repository conformance\n"
        "  size-report    report managed document byte budgets\n"
        "  shape-check    check managed document shapes\n"
        "  drift-check    check standard-owned artifacts and integrations\n"
        "  legacy-report  report legacy handoff evidence without mutation\n"
        "  upgrade        refresh clean standard-owned artifacts"
    )


def _run_provider(operation: ProviderOperation, argv: list[str]) -> int:
    try:
        return run_packaged_providers("agent-handoff", operation, argv)
    except AdoptError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code


def run_adopt(argv: list[str]) -> int:
    """Route specialized top-level adoption through the scaffold provider."""
    return _run_provider(ProviderOperation.SCAFFOLD, argv)


def run(argv: list[str] | None = None) -> int:
    """Map package subcommands to generic provider operations."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"--help", "-h"}:
        _print_help()
        return 0
    command = args[0]
    mapped = _COMMANDS.get(command)
    if mapped is None:
        print(f"error: unknown agent-handoff command: {command}", file=sys.stderr)
        return 2
    operation, prefix = mapped
    return _run_provider(operation, [*prefix, *args[1:]])
