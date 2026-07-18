"""Thin command routing for the manifest-declared agent-handoff providers."""

from __future__ import annotations

import argparse
import base64
import os
import posixpath
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import NoReturn, cast
from urllib.parse import unquote

from project_standards.adopt.errors import AdoptError
from project_standards.agent_handoff.legacy import legacy_report
from project_standards.agent_handoff.model import (
    ChangeKind,
    Finding,
    OperationReport,
    PlannedChange,
)
from project_standards.agent_handoff.paths import RepositoryBoundaryError, RepositoryRoot
from project_standards.control_plane.command_resolution import (
    CommandConfigurationError,
    CommandResolutionError,
    SelectedCommandPackage,
    capture_command_snapshot,
    invoke_selected_provider,
    managed_unit_snapshot,
    selected_command,
)
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.executor import apply_authoring_plan
from project_standards.control_plane.locking import LockMode
from project_standards.control_plane.schemas import MutationActionSchema, MutationPlanSchema
from project_standards.package_contract.payload import (
    JsonObject,
    ProviderEffect,
)
from project_standards.package_contract.payload import (
    ProviderOperation as V2ProviderOperation,
)
from project_standards.provider_runner import run_packaged_providers
from project_standards.standard_manifest import ProviderOperation as LegacyProviderOperation

_COMMANDS: dict[str, tuple[LegacyProviderOperation, tuple[str, ...]]] = {
    "validate": (LegacyProviderOperation.VALIDATE, ()),
    "size-report": (LegacyProviderOperation.VALIDATE, ("--view", "size")),
    "shape-check": (LegacyProviderOperation.VALIDATE, ("--view", "shape")),
    "drift-check": (LegacyProviderOperation.DRIFT_CHECK, ()),
    "legacy-report": (LegacyProviderOperation.EXTRACT, ()),
    "upgrade": (LegacyProviderOperation.UPGRADE, ()),
}

_READ_PATHS = (
    ".agents/hooks/agent-handoff/session_start.py",
    ".agents/skills/agent-handoff/SKILL.md",
    ".agents/skills/agent-handoff/agents/openai.yaml",
    ".standards/packages/agent-handoff/policy.toml",
    ".claude/settings.json",
    ".codex/config.toml",
    "AGENTS.md",
    "CLAUDE.md",
    "docs/STATUS.md",
    "docs/TODO.md",
    "docs/handoff/architecture.md",
    "docs/handoff/bugs",
    "docs/handoff/conventions.md",
    "docs/handoff/credentials.md",
    "docs/handoff/deployed.md",
    "docs/handoff/sessions",
    "docs/handoff/specs-plans.md",
    "docs/handoff/state.md",
)

_UPGRADE_RESOURCES = {
    ".agents/hooks/agent-handoff/session_start.py": "hook",
    ".agents/skills/agent-handoff/SKILL.md": "skill",
    ".agents/skills/agent-handoff/agents/openai.yaml": "skill-openai",
}

_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


class _ArgumentError(ValueError):
    """Keep argparse inside the embedding command boundary."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise _ArgumentError(message)


@dataclass(frozen=True, slots=True)
class _V2Args:
    repo: Path
    json: bool
    dry_run: bool


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


def _run_provider(operation: LegacyProviderOperation, argv: list[str]) -> int:
    try:
        return run_packaged_providers("agent-handoff", operation, argv)
    except AdoptError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code


def _repository_argument(argv: list[str]) -> Path:
    """Extract a repository option without allowing malformed authority fallback."""
    selected = Path.cwd()
    for index, argument in enumerate(argv):
        if argument == "--repo":
            if index + 1 >= len(argv):
                raise _ArgumentError("--repo requires a non-empty path")
            selected = Path(argv[index + 1])
        if argument.startswith("--repo="):
            value = argument.removeprefix("--repo=")
            if not value:
                raise _ArgumentError("--repo requires a non-empty path")
            selected = Path(value)
    return selected


def _parse_v2(operation: V2ProviderOperation, argv: list[str]) -> _V2Args:
    parser = _Parser(prog=f"project-standards agent-handoff {operation.value}")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    if operation is V2ProviderOperation.UPGRADE:
        parser.add_argument("--dry-run", action="store_true")
    parsed = parser.parse_args(argv)
    return _V2Args(parsed.repo, parsed.json, bool(getattr(parsed, "dry_run", False)))


def _walk_handoff_paths(repo: Path) -> tuple[str, ...]:
    """Declare every handoff document without following repository symlinks."""
    root = repo.resolve(strict=True)
    handoff = root / "docs/handoff"
    discovered: set[str] = set(_READ_PATHS)
    if handoff.is_dir() and not handoff.is_symlink():
        for current, directories, files in os.walk(handoff, followlinks=False):
            base = Path(current)
            for name in [*directories, *files]:
                discovered.add((base / name).relative_to(root).as_posix())
    return tuple(sorted(discovered, key=str.encode))


def _read_snapshots(selected: SelectedCommandPackage) -> JsonObject:
    snapshots = capture_command_snapshot(
        selected.repo,
        _walk_handoff_paths(selected.repo),
    )
    candidates: set[str] = set()
    for source, raw in snapshots.items():
        if not source.endswith(".md") or not isinstance(raw, dict):
            continue
        encoded = raw.get("content_base64")
        if not isinstance(encoded, str):
            continue
        text = base64.b64decode(encoded).decode("utf-8", errors="replace")
        for raw_target in _LINK_RE.findall(text):
            target = unquote(
                raw_target.strip().strip("<>").split(maxsplit=1)[0].split("#", maxsplit=1)[0]
            )
            if not target or "://" in target or target.startswith(("mailto:", "#")):
                continue
            for candidate in (PurePosixPath(target), PurePosixPath(source).parent / target):
                normalized = posixpath.normpath(candidate.as_posix())
                if not normalized.startswith(("../", "/")) and normalized not in {"..", "."}:
                    candidates.add(normalized)
    missing = tuple(sorted(candidates - snapshots.keys(), key=str.encode))
    if missing:
        snapshots.update(capture_command_snapshot(selected.repo, missing))
    snapshots["managed_units"] = managed_unit_snapshot(selected.lock, "agent-handoff")
    return snapshots


def _report(
    selected: SelectedCommandPackage,
    findings: tuple[Finding, ...] = (),
    changes: tuple[PlannedChange, ...] = (),
) -> OperationReport:
    return OperationReport(
        repository=str(selected.repo),
        standard_version=selected.resolved.value,
        findings=findings,
        changes=changes,
    )


def _provider_findings(
    selected: SelectedCommandPackage, operation: V2ProviderOperation
) -> tuple[Finding, ...]:
    result = invoke_selected_provider(selected, operation, _read_snapshots(selected))
    if result.effect is not ProviderEffect.FINDINGS:
        raise CommandResolutionError("selected Agent Handoff provider returned the wrong effect")
    return tuple(
        Finding(
            code=item.code,
            severity=item.severity,
            path=item.path,
            locus=item.locus or item.identity,
            message=item.message,
            guidance=item.hint,
        )
        for item in result.findings
    )


def _emit(report: OperationReport, *, as_json: bool) -> int:
    if as_json:
        print(report.to_json(), end="")
    else:
        for change in sorted(report.changes, key=lambda item: item.sort_key):
            print(f"{change.kind.value}: {change.path}")
        for finding in sorted(report.findings, key=lambda item: item.sort_key):
            print(f"{finding.severity}: {finding.path}: {finding.message}", file=sys.stderr)
    return 1 if report.blocked else 0


def _run_read_command(
    selected: SelectedCommandPackage,
    operation: V2ProviderOperation,
    view: str,
    args: _V2Args,
) -> int:
    if operation is V2ProviderOperation.EXTRACT:
        root = RepositoryRoot.from_input(selected.repo)
        evidence = _report(selected, legacy_report(root))
        result = invoke_selected_provider(
            selected,
            operation,
            cast(JsonObject, {"legacy_evidence": evidence.to_dict()}),
        )
        if result.effect is not ProviderEffect.CONTENT or result.content is None:
            raise CommandResolutionError(
                "selected Agent Handoff extract provider returned the wrong effect"
            )
        if args.json:
            # The selected provider owns the serialized evidence bytes.
            sys.stdout.write(result.content.decode("utf-8"))
            return 0
        return _emit(evidence, as_json=False)
    findings = _provider_findings(selected, operation)
    if view == "size":
        findings = tuple(item for item in findings if item.code.startswith("AH-SIZE"))
    elif view == "shape":
        findings = tuple(item for item in findings if item.code.startswith("AH-SHAPE"))
    return _emit(_report(selected, findings), as_json=args.json)


def _upgrade_plan(
    selected: SelectedCommandPackage,
) -> tuple[MutationPlanSchema, tuple[Finding, ...]]:
    actions: list[MutationActionSchema] = []
    locked = {
        unit.path.original: unit
        for unit in selected.lock.artifacts
        if "agent-handoff" in unit.owners and unit.path.original in _UPGRADE_RESOURCES
    }
    findings: list[Finding] = []
    for target, resource_id in _UPGRADE_RESOURCES.items():
        unit = locked.get(target)
        if unit is None:
            continue
        raw_state = capture_command_snapshot(selected.repo, (target,))[target]
        if not isinstance(raw_state, dict):
            raise CommandResolutionError("authoring snapshot has an invalid shape")
        state = cast(JsonObject, raw_state)
        if (
            state["kind"] != "regular"
            or state["content_digest"] != unit.content_digest.value
            or (unit.mode is not None and state["mode"] != unit.mode)
        ):
            findings.append(
                Finding(
                    code="AH-ARTIFACT-DRIFT",
                    severity="error",
                    path=target,
                    locus="managed artifact",
                    message="managed Agent Handoff artifact has local changes",
                    guidance="restore or reconcile the local change before upgrading",
                )
            )
            continue
        resource = next(
            item for item in selected.payload.manifest.resources if item.id == resource_id
        )
        if state["content_digest"] == resource.digest.value:
            continue
        result = invoke_selected_provider(
            selected,
            V2ProviderOperation.UPGRADE,
            {
                "authoring": {
                    "target": target,
                    "kind": state["kind"],
                    "precondition_digest": state["precondition_digest"],
                    "mode": state["mode"],
                    "overwrite": True,
                    "resource_id": resource_id,
                }
            },
        )
        if result.effect is not ProviderEffect.MUTATION_PLAN or result.mutation_plan is None:
            raise CommandResolutionError(
                "selected Agent Handoff upgrade provider returned the wrong effect"
            )
        actions.extend(result.mutation_plan.actions)
    return (
        MutationPlanSchema(
            schema_version="1.0",
            standard_id="agent-handoff",
            version=selected.resolved,
            actions=actions,
        ),
        tuple(findings),
    )


def _run_upgrade(selected: SelectedCommandPackage, args: _V2Args) -> int:
    plan, findings = _upgrade_plan(selected)
    changes = tuple(
        PlannedChange(
            kind=ChangeKind.UPDATE,
            path=action.target.original,
            precondition_sha256=action.precondition_digest.value.removeprefix("sha256:"),
        )
        for action in plan.actions
    )
    report = _report(selected, findings=findings, changes=changes)
    if findings or args.dry_run:
        return _emit(report, as_json=args.json)
    applied = apply_authoring_plan(selected.repo, plan)
    if not applied.success:
        active_path = changes[0].path if changes else "."
        failure = Finding(
            code="AH-APPLY-FAILED",
            severity="error",
            path=active_path,
            locus="upgrade apply",
            message=f"Agent Handoff upgrade failed: {applied.error_code or 'unknown error'}",
            guidance="Resolve the precondition or I/O failure, then re-plan before retrying.",
        )
        report = _report(selected, findings=(failure,), changes=changes)
    return _emit(report, as_json=args.json)


def _run_selected(
    selected: SelectedCommandPackage,
    operation: V2ProviderOperation,
    argv: list[str],
) -> int:
    view = "full"
    filtered = list(argv)
    if operation is V2ProviderOperation.VALIDATE and filtered[:2] == ["--view", "size"]:
        view, filtered = "size", filtered[2:]
    elif operation is V2ProviderOperation.VALIDATE and filtered[:2] == ["--view", "shape"]:
        view, filtered = "shape", filtered[2:]
    args = _parse_v2(operation, filtered)
    if operation is V2ProviderOperation.UPGRADE:
        return _run_upgrade(selected, args)
    return _run_read_command(selected, operation, view, args)


def run_adopt(argv: list[str]) -> int:
    """Route specialized top-level adoption through the scaffold provider."""
    return _run_provider(LegacyProviderOperation.SCAFFOLD, argv)


def run(
    argv: list[str] | None = None,
    *,
    distribution: InstalledDistribution | None = None,
) -> int:
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
    provider_args = [*prefix, *args[1:]]
    try:
        repo = _repository_argument(provider_args)
        dry_run = operation is LegacyProviderOperation.UPGRADE and "--dry-run" in provider_args
        mode = (
            LockMode.WRITE
            if operation is LegacyProviderOperation.UPGRADE and not dry_run
            else LockMode.READ
        )
        with selected_command(
            repo,
            "agent-handoff",
            distribution,
            mode=mode,
        ) as selected:
            if selected is None:
                return _run_provider(operation, provider_args)
            return _run_selected(selected, V2ProviderOperation(operation.value), provider_args)
    except (_ArgumentError, CommandConfigurationError, RepositoryBoundaryError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (CommandResolutionError, OSError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
