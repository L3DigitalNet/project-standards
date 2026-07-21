"""Manifest provider entrypoints for agent-handoff operations."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Iterable
from importlib import import_module
from pathlib import Path
from typing import cast

from project_standards.agent_handoff.model import (
    Finding,
    Harness,
    OperationReport,
    StartupMode,
    emit_report,
)
from project_standards.agent_handoff.paths import RepositoryBoundaryError, RepositoryRoot
from project_standards.agent_handoff.planning import apply_adoption, plan_adoption, plan_upgrade


def _parse(parser: argparse.ArgumentParser, argv: list[str] | None) -> argparse.Namespace | int:
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1


def scaffold(argv: list[str] | None = None) -> int:
    """Plan and apply aggregate adoption containing agent-handoff."""
    parser = argparse.ArgumentParser(prog="project-standards adopt")
    parser.add_argument("standards", nargs="+", metavar="STANDARD")
    parser.add_argument("--dest", "--repo", type=Path, default=Path.cwd(), metavar="DIR")
    startup = parser.add_mutually_exclusive_group(required=True)
    startup.add_argument(
        "--harness",
        action="append",
        choices=[harness.value for harness in Harness],
        dest="harnesses",
    )
    startup.add_argument("--manual", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    parsed = _parse(parser, argv)
    if isinstance(parsed, int):
        return parsed
    if "agent-handoff" not in parsed.standards:
        parser.print_usage(sys.stderr)
        print("project-standards adopt: error: agent-handoff is required", file=sys.stderr)
        return 2
    harnesses = tuple(Harness(value) for value in (parsed.harnesses or ()))
    if len(set(harnesses)) != len(harnesses):
        print("error: --harness values must be unique", file=sys.stderr)
        return 2
    mode = StartupMode.MANUAL if parsed.manual else StartupMode.AUTOMATIC
    plan = plan_adoption(
        repository=parsed.dest,
        standard_ids=tuple(parsed.standards),
        startup=mode,
        harnesses=harnesses,
    )
    report = apply_adoption(plan, dry_run=parsed.dry_run)
    return emit_report(report, as_json=parsed.json)


def _read_parser(prog: str, *, view: bool = False) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    if view:
        parser.add_argument("--view", choices=("full", "size", "shape"), default="full")
    return parser


def _read_report(
    repository: Path,
    finder: Callable[[RepositoryRoot], Iterable[Finding]],
) -> OperationReport:
    root = RepositoryRoot.from_input(repository)
    return OperationReport(
        repository=str(root.path),
        standard_version="1.0",
        findings=tuple(finder(root)),
    )


def _load_finder(module_name: str, attribute: str) -> Callable[[RepositoryRoot], Iterable[Finding]]:
    module = import_module(module_name)
    candidate = getattr(module, attribute)
    if not callable(candidate):
        raise TypeError(f"agent-handoff provider target {module_name}:{attribute} is not callable")
    return cast("Callable[[RepositoryRoot], Iterable[Finding]]", candidate)


def validate(argv: list[str] | None = None) -> int:
    """Run the full, size-only, or shape-only validation view."""
    parser = _read_parser("project-standards agent-handoff validate", view=True)
    parsed = _parse(parser, argv)
    if isinstance(parsed, int):
        return parsed
    attribute = {
        "full": "validate_repository",
        "size": "size_report",
        "shape": "shape_check",
    }[parsed.view]
    finder = _load_finder("project_standards.agent_handoff.validation", attribute)
    try:
        report = _read_report(parsed.repo, finder)
    except RepositoryBoundaryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return emit_report(report, as_json=parsed.json)


def drift_check(argv: list[str] | None = None) -> int:
    """Report drift limited to standard-owned artifacts and integrations."""
    parser = _read_parser("project-standards agent-handoff drift-check")
    parsed = _parse(parser, argv)
    if isinstance(parsed, int):
        return parsed
    find_drift = _load_finder("project_standards.agent_handoff.validation", "drift_check")
    try:
        report = _read_report(parsed.repo, find_drift)
    except RepositoryBoundaryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return emit_report(report, as_json=parsed.json)


def extract(argv: list[str] | None = None) -> int:
    """Run the repository-confined, read-only legacy evidence report."""
    parser = _read_parser("project-standards agent-handoff legacy-report")
    parsed = _parse(parser, argv)
    if isinstance(parsed, int):
        return parsed
    legacy_report = _load_finder("project_standards.agent_handoff.legacy", "legacy_report")
    try:
        report = _read_report(parsed.repo, legacy_report)
    except RepositoryBoundaryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    emit_report(report, as_json=parsed.json)
    return 0


def upgrade(argv: list[str] | None = None) -> int:
    """Plan and apply a managed refresh guarded by the provenance lock."""
    parser = _read_parser("project-standards agent-handoff upgrade")
    parser.add_argument("--dry-run", action="store_true")
    parsed = _parse(parser, argv)
    if isinstance(parsed, int):
        return parsed
    plan = plan_upgrade(repository=parsed.repo, standard_ids=("agent-handoff",))
    report = apply_adoption(plan, dry_run=parsed.dry_run)
    return emit_report(report, as_json=parsed.json)
