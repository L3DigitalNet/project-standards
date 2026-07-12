"""Version-selected top-level validation and fix command adapters."""

from __future__ import annotations

import argparse
import base64
import datetime
import sys
from dataclasses import replace
from pathlib import Path
from typing import NoReturn, cast

from project_standards import validate_frontmatter
from project_standards.control_plane.command_resolution import (
    CommandResolutionError,
    SelectedCommandPackage,
    capture_command_snapshot,
    invoke_selected_provider,
    resolve_enabled_companion,
    selected_command,
)
from project_standards.control_plane.diagnostics import sort_findings
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.executor import apply_authoring_plan
from project_standards.control_plane.locking import LockMode, control_plane_lock
from project_standards.control_plane.providers import ProviderResult
from project_standards.control_plane.schemas import MutationPlanSchema
from project_standards.control_plane.state import StateKind, detect_control_plane_state
from project_standards.id_format import random_token
from project_standards.package_contract.payload import (
    JsonObject,
    JsonValue,
    ProviderEffect,
    ProviderOperation,
)


class _ArgumentError(ValueError):
    """Keep argparse inside the top-level embedding boundary."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise _ArgumentError(message)


def _parser(command: str) -> _Parser:
    parser = _Parser(prog=f"project-standards {command}", add_help=False)
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--schema", type=Path, default=None)
    parser.add_argument("--glob")
    parser.add_argument("--quiet", "-q", action="store_true")
    parser.add_argument("--no-require-frontmatter", action="store_true")
    return parser


def _documents(selected: SelectedCommandPackage, paths: list[Path]) -> list[JsonValue]:
    root = selected.repo.resolve(strict=True)
    relative = tuple(
        (path.relative_to(root) if path.is_absolute() else path).as_posix() for path in paths
    )
    captured = capture_command_snapshot(selected.repo, relative)
    documents: list[JsonValue] = []
    for path in relative:
        raw = captured[path]
        if not isinstance(raw, dict):
            raise CommandResolutionError("frontmatter snapshot has an invalid shape")
        state = cast(JsonObject, raw)
        documents.append(
            {
                "path": path,
                "kind": state["kind"],
                "mode": state["mode"],
                "content_base64": state["content_base64"],
                "precondition_digest": state["precondition_digest"],
            }
        )
    return documents


def _provider_inputs(
    selected: SelectedCommandPackage,
    paths: list[Path],
    *,
    schema_override: Path | None,
    no_require: bool,
) -> tuple[JsonObject, JsonObject]:
    config = dict(selected.effective_config)
    snapshots: JsonObject = {"documents": _documents(selected, paths)}
    if no_require:
        config["required"] = False
    if schema_override is not None:
        try:
            relative = (
                schema_override.relative_to(selected.repo)
                if schema_override.is_absolute()
                else schema_override
            )
            schema_path = relative.as_posix()
            raw = capture_command_snapshot(selected.repo, (schema_path,))[schema_path]
        except (OSError, ValueError) as exc:
            raise CommandResolutionError(
                f"custom schema must remain inside the repository: {schema_override}"
            ) from exc
        if not isinstance(raw, dict):
            raise CommandResolutionError("custom schema snapshot has an invalid shape")
        state = cast(JsonObject, raw)
        encoded = state.get("content_base64")
        digest = state.get("content_digest")
        if (
            state.get("kind") != "regular"
            or not isinstance(encoded, str)
            or not isinstance(digest, str)
        ):
            raise CommandResolutionError("custom schema must be a regular repository file")
        config["schema"] = "custom"
        config["schema_path"] = schema_path
        snapshots["referenced_input_content"] = [
            {
                "standard_id": "markdown-frontmatter",
                "extension_id": "custom-schema",
                "path": schema_path,
                "digest": digest,
                "content_base64": encoded,
            }
        ]
    elif config.get("schema") == "custom":
        schema_path = config.get("schema_path")
        if not isinstance(schema_path, str):
            raise CommandResolutionError("custom frontmatter schema requires schema_path")
        matching = [
            item
            for item in selected.lock.referenced_inputs
            if item.standard_id == "markdown-frontmatter"
            and item.extension_id == "custom-schema"
            and item.path.original == schema_path
        ]
        if len(matching) != 1:
            raise CommandResolutionError(
                "custom frontmatter schema requires one locked referenced input"
            )
        content = validate_frontmatter.read_locked_input_bytes(selected.repo, matching[0])
        snapshots["referenced_input_content"] = [
            {
                "standard_id": "markdown-frontmatter",
                "extension_id": "custom-schema",
                "path": schema_path,
                "digest": matching[0].digest.value,
                "content_base64": base64.b64encode(content).decode("ascii"),
            }
        ]
    return config, snapshots


def _emit_findings(result: ProviderResult, *, file_count: int, quiet: bool) -> int:
    if result.effect is not ProviderEffect.FINDINGS:
        raise CommandResolutionError("frontmatter validate provider returned the wrong effect")
    errors = [finding for finding in result.findings if finding.severity == "error"]
    warnings = [finding for finding in result.findings if finding.severity == "warning"]
    for finding in result.findings:
        print(f"{finding.path}: {finding.message}", file=sys.stderr)
    if errors:
        print(
            f"\n✗  {len(errors)} error(s) across {file_count} file(s)",
            file=sys.stderr,
        )
        return 1
    if warnings:
        print(f"\nwarning: {len(warnings)} warning(s)", file=sys.stderr)
    if not quiet:
        print(f"✓  {file_count} file(s) validated")
    return 0


def _emit_reference_findings(
    result: ProviderResult,
    *,
    document_count: int,
    quiet: bool,
) -> int:
    """Preserve the standalone reference validator's public summary shape."""
    errors = [finding for finding in result.findings if finding.severity == "error"]
    warnings = [finding for finding in result.findings if finding.severity == "warning"]
    if document_count == 0:
        print(
            "note: no managed docs matched — is the working directory the repo root?",
            file=sys.stderr,
        )
    for finding in (*warnings, *errors):
        print(
            f"[{finding.severity}] {finding.path}: {finding.message}",
            file=sys.stderr,
        )
    if errors:
        print(
            f"\n✗  {len(errors)} error(s), {len(warnings)} warning(s)",
            file=sys.stderr,
        )
        return 1
    if not quiet:
        print(f"✓  references valid ({document_count} docs, {len(warnings)} warning(s))")
    return 0


def _managed_document_count(snapshots: JsonObject) -> int:
    raw_documents = snapshots.get("documents")
    if not isinstance(raw_documents, list):
        return 0
    count = 0
    for raw in raw_documents:
        if not isinstance(raw, dict) or raw.get("kind") != "regular":
            continue
        encoded = raw.get("content_base64")
        if not isinstance(encoded, str):
            continue
        try:
            metadata = validate_frontmatter.parse_frontmatter(
                base64.b64decode(encoded, validate=True).decode("utf-8-sig")
            )
        except (
            UnicodeDecodeError,
            ValueError,
            validate_frontmatter.FrontmatterParseError,
        ):
            continue
        if isinstance(metadata, dict):
            count += 1
    return count


def _document_ids(snapshots: JsonObject) -> dict[str, str]:
    raw_documents = snapshots.get("documents")
    if not isinstance(raw_documents, list):
        return {}
    result: dict[str, str] = {}
    for raw in raw_documents:
        if not isinstance(raw, dict):
            continue
        path = raw.get("path")
        encoded = raw.get("content_base64")
        if not isinstance(path, str) or not isinstance(encoded, str):
            continue
        try:
            metadata = validate_frontmatter.parse_frontmatter(
                base64.b64decode(encoded).decode("utf-8-sig")
            )
        except UnicodeDecodeError, ValueError, validate_frontmatter.FrontmatterParseError:
            continue
        document_id = metadata.get("id") if isinstance(metadata, dict) else None
        if isinstance(document_id, str):
            result[path] = document_id
    return result


def _emit_authoring_diagnostics(
    plan: MutationPlanSchema,
    *,
    surface: str,
) -> int:
    """Emit package-owned authoring facts with the established exit classes."""
    for diagnostic in plan.diagnostics:
        prefix = "cannot auto-fix: " if diagnostic.refusal or surface == "validate-id" else ""
        print(
            f"{prefix}{diagnostic.path.original}: {diagnostic.message}",
            file=sys.stderr,
        )
    if any(item.refusal for item in plan.diagnostics):
        return 2
    return 1 if any(item.severity == "error" for item in plan.diagnostics) else 0


def _selected_context(
    parsed: argparse.Namespace,
    selected: SelectedCommandPackage,
) -> tuple[validate_frontmatter.ProjectConfig, list[Path], JsonObject, JsonObject]:
    config = validate_frontmatter.config_from_unified_options(
        selected.effective_config,
        selected_package_version=selected.resolved.value,
        custom_schema_bytes=None,
    )
    paths = validate_frontmatter.collect_paths(
        list(parsed.files),
        parsed.glob,
        config.include,
        config.exclude,
    )
    effective, snapshots = _provider_inputs(
        selected,
        paths,
        schema_override=parsed.schema,
        no_require=parsed.no_require_frontmatter,
    )
    return config, paths, effective, snapshots


_REPOSITORY_FINDING_CODES = frozenset(
    {
        "FM-DATE-ORDER",
        "FM-DUPLICATE-ADR",
        "FM-DUPLICATE-ID",
        "FM-RECIPROCITY",
        "FM-REFERENCE",
    }
)
_SCHEMA_FINDING_CODES = frozenset({"FM-DATE", "FM-PARSE", "FM-PATH", "FM-REQUIRED", "FM-SCHEMA"})


def _validate_selected(
    parsed: argparse.Namespace,
    selected: SelectedCommandPackage,
    config: validate_frontmatter.ProjectConfig,
    paths: list[Path],
    effective: JsonObject,
    snapshots: JsonObject,
) -> ProviderResult:
    references = effective.get("references")
    reference_enabled = isinstance(references, dict) and references.get("enabled") is True
    full_paths = (
        validate_frontmatter.collect_paths([], None, config.include, config.exclude)
        if reference_enabled
        else paths
    )
    scoped = {path.resolve() for path in paths} != {path.resolve() for path in full_paths}
    primary_config = dict(effective)
    if scoped:
        primary_config["references"] = {"enabled": False}
    primary = invoke_selected_provider(
        selected,
        ProviderOperation.VALIDATE,
        snapshots,
        effective_config=primary_config,
    )
    findings = list(primary.findings)
    if scoped:
        full_effective, full_snapshots = _provider_inputs(
            selected,
            full_paths,
            schema_override=parsed.schema,
            no_require=parsed.no_require_frontmatter,
        )
        repository = invoke_selected_provider(
            selected,
            ProviderOperation.VALIDATE,
            full_snapshots,
            effective_config=full_effective,
        )
        findings.extend(
            item for item in repository.findings if item.code in _REPOSITORY_FINDING_CODES
        )
    adr = resolve_enabled_companion(selected, "adr")
    if adr is not None:
        adr_result = invoke_selected_provider(
            adr,
            ProviderOperation.VALIDATE,
            {"documents": snapshots["documents"]},
        )
        findings.extend(adr_result.findings)
    return ProviderResult(
        effect=ProviderEffect.FINDINGS,
        findings=tuple(sort_findings(dict.fromkeys(findings))),
    )


def _validation_standard_id(
    repo: Path,
    distribution: InstalledDistribution | None,
) -> tuple[str | None, InstalledDistribution]:
    installed = distribution or InstalledDistribution.current()
    state = detect_control_plane_state(repo, tool_release=installed.tool_release.value)
    if state.kind is not StateKind.INITIALIZED or state.config is None:
        return "markdown-frontmatter", installed
    for standard_id in ("markdown-frontmatter", "adr"):
        desired = state.config.standards.get(standard_id)
        if desired is not None and desired.enabled:
            return standard_id, installed
    return None, installed


def run_locked_standalone_validate(
    argv: list[str],
    selected: SelectedCommandPackage,
    *,
    surface: str,
) -> int:
    """Run one legacy-named read command through the selected validate provider."""
    parsed = _parser(surface).parse_args(argv)
    config, paths, effective, snapshots = _selected_context(parsed, selected)
    if effective.get("schema") == "custom" and surface in {"validate-id", "validate-references"}:
        label = "id-format" if surface == "validate-id" else "reference"
        print(f"note: custom schema in use; skipping {label} validation", file=sys.stderr)
        return 0
    if surface == "validate-references":
        references = effective.get("references")
        if not isinstance(references, dict) or references.get("enabled") is not True:
            return 0
        paths = validate_frontmatter.collect_paths([], None, config.include, config.exclude)
        effective, snapshots = _provider_inputs(
            selected,
            paths,
            schema_override=parsed.schema,
            no_require=parsed.no_require_frontmatter,
        )
        allowed = _REPOSITORY_FINDING_CODES | {"FM-PARSE", "FM-PATH"}
    elif surface == "validate-id":
        effective = dict(effective)
        effective["references"] = {"enabled": False}
        allowed = frozenset({"FM-ID", "FM-PARSE", "FM-PATH"})
    else:
        effective = dict(effective)
        effective["references"] = {"enabled": False}
        allowed = _SCHEMA_FINDING_CODES
    result = invoke_selected_provider(
        selected,
        ProviderOperation.VALIDATE,
        snapshots,
        effective_config=effective,
    )
    findings = tuple(item for item in result.findings if item.code in allowed)
    if surface == "validate-references":
        findings = tuple(
            replace(
                item,
                severity="warning",
                message=(
                    "skipped (invalid frontmatter: frontmatter is not valid UTF-8 YAML)"
                    if item.code == "FM-PARSE"
                    else "skipped (cannot read: managed input is not a regular file)"
                ),
            )
            if item.code in {"FM-PARSE", "FM-PATH"}
            else item
            for item in findings
        )
    filtered = ProviderResult(
        effect=ProviderEffect.FINDINGS,
        findings=findings,
    )
    if surface == "validate-references":
        return _emit_reference_findings(
            filtered,
            document_count=_managed_document_count(snapshots),
            quiet=parsed.quiet,
        )
    return _emit_findings(filtered, file_count=len(paths), quiet=parsed.quiet)


def run_locked_standalone_fix(
    argv: list[str],
    selected: SelectedCommandPackage,
    *,
    surface: str,
) -> int:
    """Apply a legacy-named authoring surface through the selected fix provider."""
    removed = {"--fix"} if surface == "validate-id" else {"--write", "--bump-updated"}
    parsed = _parser(surface).parse_args([argument for argument in argv if argument not in removed])
    _config, paths, effective, snapshots = _selected_context(parsed, selected)
    if effective.get("schema") == "custom":
        label = "id-format" if surface == "validate-id" else "frontmatter formatting"
        print(f"note: custom schema in use; skipping {label}", file=sys.stderr)
        return 0
    snapshots["tokens"] = [random_token() for _ in range(max(2, len(paths) * 3))]
    snapshots["authoring_mode"] = "id-only" if surface == "validate-id" else "format-only"
    if surface == "format-frontmatter":
        snapshots["today"] = datetime.date.today().isoformat()
        snapshots["bump_updated"] = "--bump-updated" in argv
    result = invoke_selected_provider(
        selected,
        ProviderOperation.FIX,
        snapshots,
        effective_config=effective,
    )
    if result.effect is not ProviderEffect.MUTATION_PLAN or result.mutation_plan is None:
        raise CommandResolutionError("frontmatter fix provider returned the wrong effect")
    diagnostic_status = _emit_authoring_diagnostics(
        result.mutation_plan,
        surface=surface,
    )
    if diagnostic_status == 2:
        return 2
    previous_ids = _document_ids(snapshots)
    applied = apply_authoring_plan(selected.repo, result.mutation_plan)
    if not applied.success:
        raise CommandResolutionError(
            f"frontmatter apply failed: {applied.error_code or 'unknown error'}"
        )
    fixed_ids: list[tuple[str, str]] = []
    if not parsed.quiet:
        for action in result.mutation_plan.actions:
            if surface == "format-frontmatter":
                print(f"formatted: {action.target.original}")
                continue
            content = action.content_bytes
            metadata = (
                validate_frontmatter.parse_frontmatter(content.decode("utf-8-sig"))
                if content is not None
                else None
            )
            document_id = metadata.get("id") if isinstance(metadata, dict) else None
            if (
                isinstance(document_id, str)
                and previous_ids.get(action.target.original) != document_id
            ):
                fixed_ids.append((action.target.original, document_id))
                print(f"fixed: {action.target.original}: id → '{document_id}'")
    if surface == "validate-id":
        validation_status = run_locked_standalone_validate(
            [
                *[argument for argument in argv if argument not in {"--fix", "--quiet", "-q"}],
                "--quiet",
            ],
            selected,
            surface="validate-id",
        )
        status = max(
            diagnostic_status,
            validation_status,
        )
        if not parsed.quiet and status == 0:
            if fixed_ids:
                print(f"\n✓  {len(fixed_ids)} id(s) fixed")
            else:
                print(f"✓  {len(paths)} file(s) already valid")
        return status
    return diagnostic_status


def run_validate(
    argv: list[str],
    *,
    distribution: InstalledDistribution | None = None,
    validate_control: bool = False,
    _control_validated: bool = False,
) -> int | None:
    """Run selected frontmatter validation, or return None for legacy fallback."""
    try:
        parsed = _parser("validate").parse_args(argv)
        if parsed.config is not None and not parsed.config.exists():
            raise CommandResolutionError(f"config file not found: {parsed.config}")
        root = Path.cwd()
        installed = distribution or InstalledDistribution.current()
        if validate_control and not _control_validated and (root / ".standards").exists():
            from project_standards.control_plane.cli import validate_repository

            with control_plane_lock(root, LockMode.READ):
                control_status = validate_repository(root, distribution=installed)
                if control_status != 0:
                    return control_status
                return run_validate(
                    argv,
                    distribution=installed,
                    validate_control=True,
                    _control_validated=True,
                )
        standard_id, installed = _validation_standard_id(root, installed)
        if standard_id is None:
            if not validate_control:
                raise CommandResolutionError(
                    "markdown-frontmatter package is not enabled in unified config"
                )
            if _control_validated:
                return 0
            from project_standards.control_plane.cli import validate_repository

            with control_plane_lock(root, LockMode.READ):
                return validate_repository(root, distribution=installed)
        with selected_command(
            root,
            standard_id,
            installed,
            mode=LockMode.READ,
            explicit_legacy=parsed.config,
        ) as selected:
            if selected is None:
                return None
            if standard_id == "adr":
                paths = validate_frontmatter.collect_paths(
                    list(parsed.files),
                    parsed.glob,
                    ["README.md", "docs/**/*.md"],
                    ["**/*.template.md", "AGENTS.md", "CLAUDE.md", ".standards/**"],
                )
                if not paths:
                    if not parsed.quiet:
                        print("no files matched", file=sys.stderr)
                    return 0
                result = invoke_selected_provider(
                    selected,
                    ProviderOperation.VALIDATE,
                    {"documents": _documents(selected, paths)},
                )
                status = _emit_findings(
                    result,
                    file_count=len(paths),
                    quiet=parsed.quiet,
                )
                if validate_control and not _control_validated:
                    from project_standards.control_plane.cli import validate_repository

                    status = max(
                        status,
                        validate_repository(selected.repo, distribution=installed),
                    )
                return status
            config, paths, effective, snapshots = _selected_context(parsed, selected)
            if not paths:
                if not parsed.quiet:
                    print("no files matched", file=sys.stderr)
                return 0
            result = _validate_selected(
                parsed,
                selected,
                config,
                paths,
                effective,
                snapshots,
            )
            status = _emit_findings(result, file_count=len(paths), quiet=parsed.quiet)
            if validate_control and not _control_validated:
                from project_standards.control_plane.cli import validate_repository

                status = max(
                    status,
                    validate_repository(selected.repo, distribution=selected.distribution),
                )
            return status
    except CommandResolutionError as exc:
        if "legacy and unified" in str(exc):
            # Top-level validation owns this as a control-state finding (exit 1),
            # not an invalid command invocation (exit 2).
            print(f"CP-CONTROL-STATE: {exc}", file=sys.stderr)
            return 1
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (
        _ArgumentError,
        validate_frontmatter.ConfigError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def run_fix(
    argv: list[str],
    *,
    distribution: InstalledDistribution | None = None,
) -> int | None:
    """Apply only the selected frontmatter provider plan, then revalidate it."""
    try:
        parsed = _parser("fix").parse_args(argv)
        if parsed.config is not None and not parsed.config.exists():
            raise CommandResolutionError(f"config file not found: {parsed.config}")
        with selected_command(
            Path.cwd(),
            "markdown-frontmatter",
            distribution,
            mode=LockMode.WRITE,
            explicit_legacy=parsed.config,
        ) as selected:
            if selected is None:
                return None
            config, paths, effective, snapshots = _selected_context(parsed, selected)
            if effective.get("schema") == "custom":
                print("note: custom schema in use; skipping fix", file=sys.stderr)
                return 0
            snapshots["tokens"] = [random_token() for _ in range(max(2, len(paths) * 3))]
            snapshots["today"] = datetime.date.today().isoformat()
            result = invoke_selected_provider(
                selected,
                ProviderOperation.FIX,
                snapshots,
                effective_config=effective,
            )
            if result.effect is not ProviderEffect.MUTATION_PLAN or result.mutation_plan is None:
                raise CommandResolutionError("frontmatter fix provider returned the wrong effect")
            diagnostic_status = _emit_authoring_diagnostics(
                result.mutation_plan,
                surface="fix",
            )
            if diagnostic_status == 2:
                return 2
            applied = apply_authoring_plan(selected.repo, result.mutation_plan)
            if not applied.success:
                raise CommandResolutionError(
                    f"frontmatter apply failed: {applied.error_code or 'unknown error'}"
                )
            if not parsed.quiet:
                previous_ids = _document_ids(snapshots)
                for action in result.mutation_plan.actions:
                    print(f"formatted: {action.target.original}")
                    content = action.content_bytes
                    if content is None:
                        continue
                    try:
                        metadata = validate_frontmatter.parse_frontmatter(
                            content.decode("utf-8-sig")
                        )
                    except (
                        UnicodeDecodeError,
                        validate_frontmatter.FrontmatterParseError,
                    ):
                        continue
                    document_id = metadata.get("id") if isinstance(metadata, dict) else None
                    if (
                        isinstance(document_id, str)
                        and previous_ids.get(action.target.original) != document_id
                    ):
                        print(f"fixed: {action.target.original}: id → '{document_id}'")
            _, _, validation_effective, validation_snapshots = _selected_context(parsed, selected)
            validation = _validate_selected(
                parsed,
                selected,
                config,
                paths,
                validation_effective,
                validation_snapshots,
            )
            return max(
                diagnostic_status,
                _emit_findings(validation, file_count=len(paths), quiet=parsed.quiet),
            )
    except (
        _ArgumentError,
        CommandResolutionError,
        validate_frontmatter.ConfigError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
