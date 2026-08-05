"""Thin command routing for the manifest-declared agent-handoff providers."""

from __future__ import annotations

import argparse
import base64
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn, cast

from project_standards.adopt.errors import AdoptError
from project_standards.agent_handoff.integrations.links import (
    _normalized_link_occurrences,  # pyright: ignore[reportPrivateUsage]  # predecessor enrichment
)
from project_standards.agent_handoff.legacy import legacy_report
from project_standards.agent_handoff.model import (
    ChangeKind,
    Finding,
    OperationReport,
    PlannedChange,
    emit_report,
)
from project_standards.agent_handoff.paths import RepositoryBoundaryError, RepositoryRoot
from project_standards.agent_handoff.policy import check_document, load_policy
from project_standards.agent_handoff.validation import (
    _reference_text,  # pyright: ignore[reportPrivateUsage]  # predecessor enrichment
)
from project_standards.control_plane.adapters.markdown import (
    MarkdownBlockAdapter,
)
from project_standards.control_plane.adapters.markdown import (
    _parse as _parse_managed_markdown,  # pyright: ignore[reportPrivateUsage]  # predecessor measure
)
from project_standards.control_plane.command_resolution import (
    CommandConfigurationError,
    CommandResolutionError,
    SelectedCommandPackage,
    capture_command_snapshot,
    invoke_selected_provider,
    selected_command,
)
from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.executor import apply_authoring_plan
from project_standards.control_plane.locking import LockMode
from project_standards.control_plane.provider_inputs import provider_dispatch_input
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

_COMMANDS: dict[str, tuple[LegacyProviderOperation, tuple[str, ...], str]] = {
    "validate": (LegacyProviderOperation.VALIDATE, (), "validate full repository conformance"),
    "size-report": (
        LegacyProviderOperation.VALIDATE,
        ("--view", "size"),
        "report managed document byte budgets",
    ),
    "shape-check": (
        LegacyProviderOperation.VALIDATE,
        ("--view", "shape"),
        "check managed document shapes",
    ),
    "drift-check": (
        LegacyProviderOperation.DRIFT_CHECK,
        (),
        "check standard-owned artifacts and integrations",
    ),
    "legacy-report": (
        LegacyProviderOperation.EXTRACT,
        (),
        "report legacy handoff evidence without mutation",
    ),
    "upgrade": (
        LegacyProviderOperation.UPGRADE,
        (),
        "refresh clean standard-owned artifacts",
    ),
}

_FIXED_VIEWS = {
    "size-report": "size",
    "shape-check": "shape",
}

_UPGRADE_RESOURCES = {
    ".agents/hooks/agent-handoff/session_start.py": "hook",
    ".agents/skills/agent-handoff/SKILL.md": "skill",
    ".agents/skills/agent-handoff/agents/openai.yaml": "skill-openai",
}


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
    view: str


def _group_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="project-standards agent-handoff")
    subparsers = parser.add_subparsers(dest="command")
    for command, (_operation, _prefix, help_text) in _COMMANDS.items():
        subparsers.add_parser(command, help=help_text, add_help=False)
    return parser


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


def _v2_argument_parser(
    command: str,
    operation: V2ProviderOperation,
) -> _Parser:
    parser = _Parser(prog=f"project-standards agent-handoff {command}")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    if command == "validate":
        parser.add_argument("--view", choices=("full", "size", "shape"), default="full")
    if operation is V2ProviderOperation.UPGRADE:
        parser.add_argument("--dry-run", action="store_true")
    return parser


def _parse_v2(
    command: str,
    operation: V2ProviderOperation,
    argv: list[str],
    *,
    fixed_view: str | None = None,
) -> _V2Args:
    parser = _v2_argument_parser(command, operation)
    parsed = parser.parse_args(argv)
    return _V2Args(
        parsed.repo,
        parsed.json,
        bool(getattr(parsed, "dry_run", False)),
        fixed_view or cast(str, getattr(parsed, "view", "full")),
    )


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


def _snapshot_content(snapshots: JsonObject, path: str) -> bytes | None:
    raw = snapshots.get(path)
    if not isinstance(raw, dict):
        return None
    encoded = raw.get("content_base64")
    if not isinstance(encoded, str):
        return None
    return base64.b64decode(encoded)


def _snapshot_text(snapshots: JsonObject, path: str) -> str | None:
    content = _snapshot_content(snapshots, path)
    return content.decode("utf-8", errors="replace") if content is not None else None


def _authenticated_markdown_envelope_bytes(
    snapshots: JsonObject,
    path: str,
    content: bytes,
) -> int:
    raw_units = snapshots.get("managed_markdown_units")
    if not isinstance(raw_units, list):
        return 0
    locked: dict[str, str] = {}
    for raw in raw_units:
        if not isinstance(raw, dict):
            return 0
        if raw.get("target") != path or raw.get("adapter") != "markdown-block":
            continue
        scope = raw.get("scope")
        digest = raw.get("semantic_digest")
        if not isinstance(scope, str) or not isinstance(digest, str) or scope in locked:
            return 0
        locked[scope] = digest
    if not locked:
        return 0
    try:
        document = _parse_managed_markdown(content)
        state = MarkdownBlockAdapter().inspect(content, tuple(locked))
    except ControlPlaneError:
        return 0
    observed = {unit.scope: unit.semantic_digest.value for unit in state.units}
    return sum(
        len(document.text[block.envelope_start : block.envelope_end].encode("utf-8"))
        for block in document.blocks
        if observed.get(f"block:{block.block_id}") == locked.get(f"block:{block.block_id}")
    )


_PREDECESSOR_SIZE_LIMIT = re.compile(
    r"^document exceeds (?P<limit>[1-9][0-9]*) byte (?:hard cap|target)(?: by .*)?$"
)


def _predecessor_size_measure(
    snapshots: JsonObject,
    path: str,
    message: str,
    *,
    subtract_authenticated_envelopes: bool,
) -> tuple[int, int] | None:
    match = _PREDECESSOR_SIZE_LIMIT.fullmatch(message)
    content = _snapshot_content(snapshots, path)
    if match is None or content is None:
        return None
    observed = len(content)
    if subtract_authenticated_envelopes:
        observed -= _authenticated_markdown_envelope_bytes(
            snapshots,
            path,
            content,
        )
    return observed, int(match.group("limit"))


def _predecessor_shape_locus(message: str) -> str:
    """Classify released provider prose without returning consumer fragments."""
    normalized = message.casefold()
    for fragment, locus in (
        ("invalid section:", "section heading"),
        ("exceeds its bullet count", "section bullet count"),
        ("contains an overlong bullet", "document bullet"),
        ("paragraph not allowed in section", "document paragraph"),
        ("overlong paragraph", "document paragraph"),
        ("target bytes exceeded", "document byte target"),
        ("hard byte cap exceeded", "document byte budget"),
        ("target lines exceeded", "document line target"),
        ("required section order", "required section order"),
        ("missing required section", "required section"),
        ("missing quick reference", "required section"),
        ("requires tables or bullets", "document structure"),
        ("changelog section", "section heading"),
        ("narrative history", "section heading"),
        ("rule summary", "rule summary cell"),
        ("rule entry", "section entry"),
        # 1.6 and later report one redacted per-section measure instead of
        # aggregating; line and observed size disambiguate repeats when the
        # enrichment pairing pops engine findings in the same section order.
        ("entry has", "section entry"),
        ("row is too long", "document row"),
        ("headline is too long", "document headline"),
        ("blocked phrase:", "blocked phrase"),
    ):
        if fragment in normalized:
            return locus
    return "document shape"


def _shape_candidate_compatible(message: str, candidate: Finding) -> bool:
    """Rule-identity guard for enrichment candidates sharing one locus (#75).

    Forbid-paragraph and overlong-paragraph provider prose both classify to the
    "document paragraph" locus, but the engine discriminates the rules by
    `limit`: the forbid rule never carries one and the length rule always does.
    Loci whose provider prose maps to a single engine rule stay order-paired.
    """
    normalized = message.casefold()
    if "paragraph not allowed in section" in normalized:
        return candidate.limit is None
    if "overlong paragraph" in normalized:
        return candidate.limit is not None
    return True


def _selected_shape_findings(
    selected: SelectedCommandPackage,
    snapshots: JsonObject,
) -> dict[tuple[str, str], list[Finding]]:
    resource = next(
        (item for item in selected.payload.manifest.resources if item.id == "policy"),
        None,
    )
    if resource is None:
        raise CommandResolutionError("selected Agent Handoff provider has no policy resource")
    policy = load_policy(selected.payload.root / resource.path.normalized)
    grouped: dict[tuple[str, str], list[Finding]] = {}
    for path in snapshots:
        text = _snapshot_text(snapshots, path)
        if text is None:
            continue
        for finding in check_document(path, text, policy):
            grouped.setdefault((finding.path, finding.locus), []).append(finding)
    return grouped


def _provider_findings(
    selected: SelectedCommandPackage, operation: V2ProviderOperation
) -> tuple[Finding, ...]:
    snapshots = provider_dispatch_input(selected, operation)
    result = invoke_selected_provider(selected, operation, snapshots)
    if result.effect is not ProviderEffect.FINDINGS:
        raise CommandResolutionError("selected Agent Handoff provider returned the wrong effect")

    shape_findings = (
        _selected_shape_findings(selected, snapshots)
        if any(item.code == "AH-SHAPE" for item in result.findings)
        else {}
    )
    link_occurrences: dict[tuple[str, str], list[tuple[int, int]]] = {}
    findings: list[Finding] = []
    for item in result.findings:
        locus = item.locus or item.identity
        message = item.message
        line = item.line
        column = item.column
        observed = item.observed
        limit = item.limit
        if item.code == "AH-REFERENCE-MISSING":
            raw_target = (
                locus.removeprefix("Markdown link: ")
                if locus.startswith("Markdown link: ")
                else None
            )
            locus = "Markdown link"
            text = _snapshot_text(snapshots, item.path)
            if raw_target is not None and text is not None:
                key = (item.path, raw_target)
                occurrences = link_occurrences.setdefault(
                    key,
                    [
                        (candidate.line, candidate.column)
                        for candidate in _normalized_link_occurrences(_reference_text(text))
                        if candidate.target == raw_target
                    ],
                )
                if occurrences:
                    line, column = occurrences.pop(0)
        elif item.code in {"AH-SIZE-CAP", "AH-SIZE-TARGET"} and (observed is None or limit is None):
            locus = "byte budget"
            measure = _predecessor_size_measure(
                snapshots,
                item.path,
                item.message,
                subtract_authenticated_envelopes=(
                    selected.resolved.major > 1
                    or (selected.resolved.major == 1 and selected.resolved.minor >= 4)
                ),
            )
            if measure is not None:
                observed, limit = measure
        elif (
            item.code == "AH-SHAPE"
            and locus == "shape"
            and all(value is None for value in (line, column, observed, limit))
        ):
            locus = _predecessor_shape_locus(item.message)
            candidates = shape_findings.get((item.path, locus), [])
            matched = next(
                (
                    position
                    for position, candidate in enumerate(candidates)
                    if _shape_candidate_compatible(item.message, candidate)
                ),
                None,
            )
            if matched is not None:
                enriched = candidates.pop(matched)
                message = enriched.message
                line = enriched.line
                column = enriched.column
                observed = enriched.observed
                limit = enriched.limit
            else:
                message = "document shape violates its configured policy"
                observed = None
                limit = None
        findings.append(
            Finding(
                code=item.code,
                severity=item.severity,
                path=item.path,
                locus=locus,
                message=message,
                guidance=item.hint,
                line=line,
                column=column,
                observed=observed,
                limit=limit,
            )
        )
    return tuple(findings)


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
        emit_report(evidence, as_json=False)
        return 0
    findings = _provider_findings(selected, operation)
    if view == "size":
        findings = tuple(item for item in findings if item.code.startswith("AH-SIZE"))
    elif view == "shape":
        findings = tuple(item for item in findings if item.code.startswith("AH-SHAPE"))
    return emit_report(_report(selected, findings), as_json=args.json)


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
            (item for item in selected.payload.manifest.resources if item.id == resource_id),
            None,
        )
        if resource is None:
            raise CommandResolutionError(
                f"selected Agent Handoff payload is missing resource {resource_id!r}"
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
        return emit_report(report, as_json=args.json)
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
    return emit_report(report, as_json=args.json)


def _run_selected(
    selected: SelectedCommandPackage,
    command: str,
    operation: V2ProviderOperation,
    argv: list[str],
    *,
    fixed_view: str | None = None,
) -> int:
    args = _parse_v2(command, operation, argv, fixed_view=fixed_view)
    if operation is V2ProviderOperation.UPGRADE:
        return _run_upgrade(selected, args)
    return _run_read_command(selected, operation, args.view, args)


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
        _group_argument_parser().print_help()
        return 0
    command = args[0]
    mapped = _COMMANDS.get(command)
    if mapped is None:
        print(f"error: unknown agent-handoff command: {command}", file=sys.stderr)
        return 2
    operation, prefix, _help_text = mapped
    command_args = args[1:]
    fixed_view = _FIXED_VIEWS.get(command)
    v2_operation = V2ProviderOperation(operation.value)
    if "--help" in command_args or "-h" in command_args:
        _v2_argument_parser(command, v2_operation).parse_args(command_args)
        raise AssertionError("argparse help did not exit")
    try:
        if fixed_view is not None:
            # Parse aliases before authority selection so selected and legacy routes
            # expose the same fixed-view command line and help surface.
            _parse_v2(
                command,
                v2_operation,
                command_args,
                fixed_view=fixed_view,
            )
        provider_args = [*prefix, *command_args]
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
            return _run_selected(
                selected,
                command,
                v2_operation,
                command_args,
                fixed_view=fixed_view,
            )
    except (_ArgumentError, CommandConfigurationError, RepositoryBoundaryError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (CommandResolutionError, OSError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
